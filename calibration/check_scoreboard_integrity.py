#!/usr/bin/env python3
"""check_scoreboard_integrity — the calibration trust floor's reference checker (D3).

The scoreboard (docs/calibration/history.md), the approved plant corpus, and the shipped
oracles are what every calibration claim rests on — and every one of them is writable by the
same session agents the gates police. This checker turns each forge into a deterministic
nonzero exit against a git BASELINE:

  (a) history.md      — baseline content must be a byte-PREFIX of the candidate (append-only:
                        an edited or deleted row is a forged scoreboard);
  (b) corpus/approved — every plant present at baseline must exist byte-identical ("the corpus
                        only grows" becomes enforced, not aspirational);
  (c) oracles         — DIRECTIONAL rule: removing or replacing a baseline must_match /
                        must_not_match regex (or removing a scenario) is RED unless the change
                        is journaled in calibration/oracle-changes.md IN THE TEXT ADDED SINCE
                        BASELINE. Pure additions/tightenings always pass (the dc72644 case —
                        a legitimate oracle tightening — must be able to ship). The journal is
                        itself append-only under rule (a), so it cannot be rewritten to
                        retro-authorize.

Exit codes (contract sentinels): 0 clean · 2 integrity_red · 3 baseline unreadable (fail
closed — an unverifiable baseline is never a pass). Stdlib-only by repo invariant.

Locally: run in the release gate with --baseline-rev <previous release tag> (test_harness.py
carries it mechanically). Engine-side: CIVerd runs the same logic against its root-owned
last-green baseline — see docs/plans/civerd-trust-floor-2026-07.md §2b.

    check_scoreboard_integrity.py --baseline-rev v1.16.0 [--repo PATH]
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HISTORY = "docs/calibration/history.md"
SCENARIOS = "calibration/scenarios.json"
CORPUS_DIR = "calibration/corpus/approved"
JOURNAL = "calibration/oracle-changes.md"
# Gate-surface protection (rule (d), lift/ratchet D3): removal of these names vs baseline
# requires a GATE_JOURNAL entry; additions are always free (R1's asymmetry — removal costs
# what addition costs, addition never pays the removal toll).
GATE_JOURNAL = "calibration/gate-changes.md"
# (v1.27) the improvement ledger: pre-registered expected effects, scored by the next run.
# Append-only for the same reason as history.md — a prediction you can revise after seeing
# the result is not a prediction.
LEDGER = "docs/calibration/ledger.md"
SKILL = "plugins/tdd-playbook/skills/tdd-playbook/SKILL.md"
AGENTS_DIR = "plugins/tdd-playbook/agents"
COMMANDS_DIR = "plugins/tdd-playbook/commands"


class BaselineUnreadable(Exception):
    pass


def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, timeout=60)


def baseline_bytes(repo, rev, path):
    """File bytes at baseline, or None if the path did not exist there."""
    p = _git(repo, "cat-file", "-e", "{}:{}".format(rev, path))
    if p.returncode != 0:
        return None
    p = _git(repo, "show", "{}:{}".format(rev, path))
    if p.returncode != 0:
        raise BaselineUnreadable("git show failed for {}:{}".format(rev, path))
    return p.stdout


def current_bytes(repo, path):
    full = os.path.join(repo, path)
    if not os.path.isfile(full):
        return None
    with open(full, "rb") as fh:
        return fh.read()


def appended_since_baseline(repo, rev, paths):
    """({path: appended-since-baseline text}, violations) for append-only files.

    Extracted from check() in v1.27 so `ledger.py` can reuse the ONE implementation of the
    byte-prefix rule instead of growing a second copy — the parallel-copy class this repo
    bans. A file ABSENT at baseline is not a violation: a newly protected file is free once,
    then locked forever after.
    """
    added, violations = {}, []
    for path in paths:
        base = baseline_bytes(repo, rev, path)
        cur = current_bytes(repo, path)
        if base is None:
            added[path] = (cur or b"").decode("utf-8", "replace")
            continue
        if cur is None or not cur.startswith(base):
            violations.append("{}: baseline content is not a byte-prefix of the candidate "
                              "(append-only violated — edited, truncated, or deleted)"
                              .format(path))
            added[path] = ""
            continue
        added[path] = cur[len(base):].decode("utf-8", "replace")
    return added, violations


def oracle_map(scenarios_blob):
    """id -> (must_match list, must_not_match list). Unparseable input raises ValueError —
    fail closed, a scoreboard whose oracles cannot be read is not a clean scoreboard."""
    data = json.loads(scenarios_blob.decode("utf-8"))
    out = {}
    for sc in data.get("scenarios", []):
        out[sc.get("id")] = (list(sc.get("must_match", [])),
                             list(sc.get("must_not_match", [])))
    return out


def check(repo, rev):
    """Returns (violations, journal_added): violation strings (empty = clean) and the text
    appended to the oracle journal since baseline. Raises BaselineUnreadable."""
    if _git(repo, "rev-parse", "--verify", "--quiet", rev + "^{commit}").returncode != 0:
        raise BaselineUnreadable("baseline rev not resolvable: {}".format(rev))
    violations = []

    # (a) append-only files: baseline is a byte-prefix of the candidate. `added` carries
    # each file's appended-since-baseline text — the journals authorize ONLY through it,
    # so a rewritten journal can never retro-authorize (and no per-file special cases).
    added, prefix_violations = appended_since_baseline(
        repo, rev, (HISTORY, JOURNAL, GATE_JOURNAL, LEDGER))
    violations.extend(prefix_violations)
    journal_added = added[JOURNAL]

    # (b) the approved corpus only grows, and approved plants are immutable
    p = _git(repo, "ls-tree", "-r", "--name-only", rev, CORPUS_DIR)
    if p.returncode != 0:
        raise BaselineUnreadable("git ls-tree failed for {}:{}".format(rev, CORPUS_DIR))
    for path in p.stdout.decode("utf-8").splitlines():
        if not path.endswith(".json"):
            continue
        base = baseline_bytes(repo, rev, path)
        cur = current_bytes(repo, path)
        if cur is None:
            violations.append("{}: approved corpus plant deleted (the corpus only grows)"
                              .format(path))
        elif cur != base:
            violations.append("{}: approved corpus plant modified (approved plants are "
                              "immutable; author a new one instead)".format(path))

    # (c) directional oracle rule on the shipped scenarios
    base_blob = baseline_bytes(repo, rev, SCENARIOS)
    if base_blob is not None:
        cur_blob = current_bytes(repo, SCENARIOS)
        try:
            base_map = oracle_map(base_blob)
            cur_map = oracle_map(cur_blob) if cur_blob is not None else {}
        except (ValueError, AttributeError) as e:
            base_map, cur_map = {}, {}
            violations.append("{}: unparseable ({}) — cannot verify oracles, failing closed"
                              .format(SCENARIOS, e))
        for sid, (base_mm, base_mnm) in base_map.items():
            journaled = sid in journal_added
            if sid not in cur_map:
                if not journaled:
                    violations.append(
                        "{}: scenario removed without an oracle-changes.md entry".format(sid))
                continue
            cur_mm, cur_mnm = cur_map[sid]
            for label, base_list, cur_list in (("must_match", base_mm, cur_mm),
                                               ("must_not_match", base_mnm, cur_mnm)):
                lost = [rx for rx in base_list if rx not in cur_list]
                if lost and not journaled:
                    violations.append(
                        "{}: {} regex removed/replaced without an oracle-changes.md entry: "
                        "{}".format(sid, label, "; ".join("/{}/".format(rx) for rx in lost)))
    # (d) gate-surface removals (lift/ratchet D3): SKILL `## ` headings, agent briefs, and
    # command files present at baseline and absent at candidate are RED unless named in
    # gate-changes.md's added-since-baseline text. Additions are FREE — no pin to edit, so
    # new doctrine never pays the removal toll (the deletion ratchet, inverted on purpose).
    gate_added = added[GATE_JOURNAL]

    def removed_names(base_names, cur_names):
        return sorted(set(base_names) - set(cur_names))

    base_skill = baseline_bytes(repo, rev, SKILL)
    if base_skill is not None:
        cur_skill = current_bytes(repo, SKILL) or b""

        def headings(blob):
            return [ln.strip() for ln in blob.decode("utf-8", "replace").splitlines()
                    if ln.startswith("## ")]
        for h in removed_names(headings(base_skill), headings(cur_skill)):
            if h not in gate_added:
                violations.append(
                    "{}: section '{}' removed without a gate-changes.md entry "
                    "(gate removal costs what addition costs)".format(SKILL, h))

    for dir_rel, kind in ((AGENTS_DIR, "agent brief"), (COMMANDS_DIR, "command")):
        p = _git(repo, "ls-tree", "--name-only", rev, dir_rel + "/")
        if p.returncode != 0:
            continue  # directory absent at baseline — nothing to protect yet
        base_files = [os.path.basename(x) for x in p.stdout.decode("utf-8").splitlines()
                      if x.endswith(".md")]
        cur_dir = os.path.join(repo, dir_rel)
        cur_files = ([f for f in os.listdir(cur_dir) if f.endswith(".md")]
                     if os.path.isdir(cur_dir) else [])
        for name in removed_names(base_files, cur_files):
            if name not in gate_added:
                violations.append(
                    "{}/{}: {} removed without a gate-changes.md entry "
                    "(gate removal costs what addition costs)".format(dir_rel, name, kind))

    return violations, journal_added


def main(argv=None):
    ap = argparse.ArgumentParser(description="Calibration scoreboard integrity vs a baseline.")
    ap.add_argument("--baseline-rev", required=True,
                    help="git rev of the trusted baseline (locally: the previous release "
                         "tag; engine-side: CIVerd's last green)")
    ap.add_argument("--repo", default=os.path.dirname(HERE))
    args = ap.parse_args(argv)
    try:
        violations, journal_added = check(args.repo, args.baseline_rev)
    except BaselineUnreadable as e:
        print("INTEGRITY UNKNOWN (fail closed): {}".format(e), file=sys.stderr)
        return 3
    if journal_added.strip():
        # The journal mechanically authorizes whoever writes it (the engine's ratification
        # token is the hard counter) — locally, every authorization is at least LOUD:
        print("oracle-changes.md journal additions since {} (each authorizes the ids it "
              "names — review them):".format(args.baseline_rev))
        for ln in journal_added.strip().splitlines():
            print("  | " + ln)
    if violations:
        for v in violations:
            print("INTEGRITY RED: " + v)
        return 2
    print("scoreboard integrity CLEAN vs {} (history append-only, corpus immutable+growing, "
          "oracles never weakened unjournaled, gate surfaces never removed unjournaled)"
          .format(args.baseline_rev))
    return 0


if __name__ == "__main__":
    sys.exit(main())
