#!/usr/bin/env python3
"""ledger — pre-register what a gate-surface change is EXPECTED to do, then score it (§13).

The gap this closes: process mutations (agent-brief fixes, oracle adjudications, new guards,
knob changes) land with an IMPLICIT expected effect and are never scored against it. We
experience improvement and never verify it. `976364f` was the specimen — 14 distinct process
mutations, each with a clear implicit prediction, none of which anything mechanically checked.
Scored by hand afterwards: 6 hit, 2 partial, 5 FLAT, 1 REGRESSED, with aggregate recall
unchanged. Four days of felt improvement, mostly unearned.

WHAT THIS GATES, and what it deliberately does not. `check` blocks on PROCESS: an entry
existed before the diff, a bound entry got scored, a disappointing result got a dated
follow-up. It never blocks on the HIT RATE. A gate on "80% of predictions must land" teaches
authors to pre-register only changes they already know will work, which converts the
instrument into a compliance artifact measuring nothing. The uncomfortable number is the
product; making it cheap to report is the whole design.

Three corrections against the original spec, each of which had already bitten:

1. BINDING IS COMMIT-ORDERING, NOT A DATE. The spec said "score-by ~2026-08-10" and thereby
   missed its own scoring event: the run happened on 08-05, at the very sha the entries
   predicted about. An entry binds to the earliest run block measuring a tree that is a
   STRICT descendant of the entry's baseline — a run at the baseline itself measured the
   pre-change tree and must never score it.
2. VERDICTS DESCRIBE MOVEMENT, NOT k/k. Scoring CONFIRMED only at k/k means P = p**3 at three
   reps: an 80% bar demands per-rep p >= 0.928 and a 50% kill bar fires at p < 0.794. See
   power.py; per-entry significance is unobtainable at n=3 and is not attempted here.
3. COVERAGE IS SHA-CITED, NOT PATH-MATCHED. Matching on path alone lets one entry per file
   per cycle satisfy the gate while pre-registering nothing.

Exit codes: 0 clean · 1 finding · 2 usage · 3 unreadable (fail closed). Note the deliberate
divergence from check_scoreboard_integrity, which uses 2 for violations — civerd_gate.sh
treats any nonzero as failure, so the gate is unambiguous, but do not copy one tool's codes
into the other.

This tool NEVER writes ledger.md or capabilities.json. A writer bug against a rule-(a)
append-only file is indistinguishable from forgery, and a tool that files its own debt has no
independent auditor. `score` and `debts --emit` PRINT what a human appends.
"""
import argparse
import datetime
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import history_format as hfmt          # noqa: E402
import power as pw                     # noqa: E402

LEDGER = "docs/calibration/ledger.md"
HISTORY = "docs/calibration/history.md"
REGISTRY = "capabilities.json"
LEDGER_CAPABILITY = "gate-surface-ledger"

# The surfaces whose changes alter what the gates CATCH — deliberately the same set rules
# (b)/(c)/(d) of check_scoreboard_integrity already protect. No second list: a divergent copy
# is how one of them silently stops covering something.
SURFACE_PATTERNS = (
    "plugins/tdd-playbook/skills/tdd-playbook/SKILL.md",
    "plugins/tdd-playbook/agents/",
    "plugins/tdd-playbook/commands/",
    "calibration/scenarios.json",
    "calibration/corpus/approved/",
)
# Surfaces where `expect: none` is a lie by construction: an oracle or a brief IS the thing
# the run measures. Doctrine prose and command text can legitimately be inert.
EFFECTFUL = ("calibration/scenarios.json", "calibration/corpus/approved/",
             "plugins/tdd-playbook/agents/")

EXPECTS = ("up", "down", "none")
VERDICTS = ("HIT", "PARTIAL", "FLAT", "REGRESSED", "HELD", "SURPRISE")
_ID = re.compile(r"^L-\d{8}-\d{2}$")
_EPOCH = re.compile(r"^EPOCH:\s*([0-9a-f]{7,40})\s*$", re.MULTILINE)


# ----------------------------------------------------------------- git (injected in tests)

def _git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True,
                          timeout=60)


def git_helpers(repo):
    """(resolve, is_ancestor, path_state) closures. The pure core takes these as arguments so
    every rule is testable without a repository — the check_staleness `--as-of` pattern."""
    def resolve(rev):
        p = _git(repo, "rev-parse", "--verify", "--quiet", str(rev) + "^{commit}")
        return p.stdout.strip() or None

    def is_ancestor(a, b):
        return _git(repo, "merge-base", "--is-ancestor", a, b).returncode == 0

    def path_state(path, rev_a, rev_b):
        p = _git(repo, "diff", "--quiet", rev_a, rev_b, "--", path)
        return "same" if p.returncode == 0 else "differs"
    return resolve, is_ancestor, path_state


# ----------------------------------------------------------------- ledger.md parsing

class LedgerUnreadable(Exception):
    pass


def _cells(line):
    """Split a markdown row on UNESCAPED pipes. Entries quote regexes (`vacu(?:ous\\|ity)`),
    so a naive split on '|' invents extra cells and the row is rejected for the wrong reason.
    """
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", body)]


def parse_ledger(text):
    """(registered, scored, epoch). Rows are dicts; unknown/misshaped rows raise rather than
    being skipped — a silently dropped entry is an unregistered change that looks registered.
    """
    epoch_m = _EPOCH.search(text or "")
    epoch = epoch_m.group(1) if epoch_m else None
    registered, scored, section = [], [], None
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            # heading depth is a document-structure choice, not part of the record's
            # grammar — match the NAME, so nesting the blocks under a section never
            # silently empties the ledger
            head = line.lstrip("#").strip()
            if head.startswith("Registered"):
                section = "reg"
                continue
            if head.startswith("Scored"):
                section = "sco"
                continue
            section = None
            continue
        if not line.startswith("|") or section is None:
            continue
        c = _cells(line)
        if not c or c[0] in ("id", "") or set(c[0]) <= set("-: "):
            continue
        if section == "reg":
            if len(c) != 9:
                raise LedgerUnreadable("registered row needs 9 cells, got {}: {}"
                                       .format(len(c), line[:90]))
            registered.append({
                "id": c[0], "date": c[1], "baseline_sha": c[2],
                "surface": [s.strip() for s in c[3].split(";") if s.strip()],
                "change": c[4],
                "scenarios": [] if c[5] == "—" else
                             [s.strip() for s in c[5].split(";") if s.strip()],
                "expect": c[6], "claimed": c[7], "rationale": c[8]})
        else:
            if len(c) != 7:
                raise LedgerUnreadable("scored row needs 7 cells, got {}: {}"
                                       .format(len(c), line[:90]))
            scored.append({"id": c[0], "scenario": c[1], "baseline": c[2], "actual": c[3],
                           "delta": c[4], "verdict": c[5], "note": c[6]})
    return registered, scored, epoch


# ----------------------------------------------------------------- scoring (pure)

def score_cell(baseline, actual, expect, claimed, floor_reps=0):
    """(verdict, delta) from two (k, n) pairs. Works in REPS, never proportions.

    `floor_reps` is the measured noise floor: a movement at or below it is INCONCLUSIVE
    rather than PARTIAL, which is the only thing stopping the instrument from confidently
    reporting coin flips (power.py exists to supply this number).
    """
    if baseline is None:
        return "INCONCLUSIVE(no-baseline)", None
    if actual is None:
        return "INCONCLUSIVE(not-selected)", None
    if baseline[1] != actual[1]:
        return "INCONCLUSIVE(n-mismatch)", None
    raw = actual[0] - baseline[0]
    if expect == "none":
        if raw == 0:
            return "HELD", 0
        return ("REGRESSED" if raw < 0 else "SURPRISE"), raw
    d = raw if expect == "up" else -raw
    if d < 0:
        return "REGRESSED", d
    if d == 0:
        return "FLAT", 0
    if floor_reps and d <= floor_reps and d < int(claimed or 1):
        return "INCONCLUSIVE(below-noise-floor)", d
    return ("HIT" if d >= int(claimed or 1) else "PARTIAL"), d


def bind_entry(entry, blocks, resolve, is_ancestor):
    """(block or None, reason). The earliest run block measuring a tree that is a STRICT
    descendant of the entry's baseline."""
    base = resolve(entry["baseline_sha"])
    if not base:
        return None, "unbindable-sha"
    for b in blocks:
        if not b["repo_sha"] or b["repo_sha"] == "unknown":
            continue
        full = resolve(b["repo_sha"])
        if not full or full == base:
            continue
        if is_ancestor(base, full):
            return b, "bound"
    return None, "pending"


def baseline_row(scenario, blocks, bound):
    """The scenario's row in the latest block STRICTLY BEFORE the bound one. Runs are sparse;
    the last measurement before the scoring run is the only honest comparator."""
    prior = [b for b in blocks if b["line_no"] < bound["line_no"]]
    for b in reversed(prior):
        for r in b["rows"]:
            if r["scenario"] == scenario:
                return r
    return None


def actual_row(scenario, bound):
    for r in bound["rows"]:
        if r["scenario"] == scenario:
            return r
    return None


# ----------------------------------------------------------------- rules

def schema_problems(registered, known_scenarios, resolve):
    out, seen = [], set()
    for e in registered:
        i = e["id"]
        if not _ID.match(i):
            out.append("{}: id must look like L-YYYYMMDD-nn".format(i))
        if i in seen:
            out.append("{}: duplicate entry id".format(i))
        seen.add(i)
        if e["expect"] not in EXPECTS:
            out.append("{}: expect must be one of {}".format(i, "|".join(EXPECTS)))
        if e["expect"] == "none":
            if e["scenarios"] or e["claimed"] not in ("0", "—"):
                out.append("{}: expect=none takes no scenarios and claimed 0".format(i))
        else:
            if not e["scenarios"]:
                out.append("{}: expect={} needs >=1 named scenario — a prediction without a "
                           "scoreable target is not an entry".format(i, e["expect"]))
            if not str(e["claimed"]).isdigit() or int(e["claimed"]) < 1:
                out.append("{}: claimed must be a rep count >= 1".format(i))
            for s in e["scenarios"]:
                if known_scenarios and s not in known_scenarios:
                    out.append("{}: unknown scenario '{}'".format(i, s))
        if not e["surface"]:
            out.append("{}: surface must name >=1 path".format(i))
        if resolve and not resolve(e["baseline_sha"]):
            out.append("{}: baseline_sha '{}' does not resolve".format(i, e["baseline_sha"]))
        # `expect: down` is the one column that could pre-register a regression as a success,
        # so its justification is MECHANICAL, not a prose convention nobody checks.
        if e["expect"] == "down" and not any(
                s in e["rationale"] for s in e["scenarios"]):
            out.append("{}: expect=down must name one of its own scenarios in the rationale "
                       "(which false-positive control this loosening is FOR)".format(i))
    return out


def no_effect_problems(registered):
    out = []
    for e in registered:
        if e["expect"] != "none":
            continue
        for p in e["surface"]:
            if any(p.startswith(x) for x in EFFECTFUL):
                out.append("{}: expect=none is not available on {} — an oracle or an agent "
                           "brief IS what the run measures".format(e["id"], p))
    return out


def coverage_problems(changed_paths, registered, fresh_ids, path_state, head, rev, epoch,
                      is_ancestor):
    """A changed gate surface needs a covering entry. Coverage is sha-cited: the entry must be
    NEW this cycle, name the path, have been written while the path was still in its baseline
    state (i.e. BEFORE the change), and the path must actually have moved since."""
    out = []
    for p in sorted(changed_paths):
        covered = False
        for e in registered:
            if e["id"] not in fresh_ids or p not in e["surface"]:
                continue
            if path_state(p, e["baseline_sha"], rev) != "same":
                continue          # back-filled: the change already existed when written
            if path_state(p, e["baseline_sha"], head) != "differs":
                continue          # speculative: the path never actually moved
            covered = True
            break
        if not covered:
            out.append("{}: gate surface changed with no covering ledger entry (an entry must "
                       "be appended BEFORE the change, name this path, and be new this cycle)"
                       .format(p))
    return out


def unscored_problems(registered, scored, bindings):
    scored_ids = {s["id"] for s in scored}
    return ["{}: bound to the {} run but never scored — append its `## Scored` rows "
            "(`ledger.py score`)".format(e["id"], b["date"])
            for e, (b, why) in zip(registered, bindings)
            if b is not None and e["id"] not in scored_ids]


def followup_problems(scored, registry, today):
    """A disappointing result must become a DATED debt or the ledger is a write-only pile of
    unactioned refutations — the exact §6c defect class this repo bans. Expiry teeth are not
    restated here: capability_registry's R-DEBT already REDs an expired entry."""
    import json
    needs = sorted({s["id"] for s in scored
                    if s["verdict"] in ("FLAT", "REGRESSED", "SURPRISE")})
    if not needs:
        return []
    try:
        with open(registry) as fh:
            reg = json.load(fh)
    except (OSError, ValueError) as exc:
        raise LedgerUnreadable("registry unreadable: {}".format(exc))
    cap = next((c for c in reg.get("capabilities", [])
                if c.get("id") == LEDGER_CAPABILITY), None)
    debts = (cap or {}).get("integration_debt", [])
    out = []
    for i in needs:
        if not any(i in (d.get("what") or "") for d in debts):
            out.append("{}: scored FLAT/REGRESSED/SURPRISE with no dated follow-up — add an "
                       "integration_debt naming {} on the '{}' capability (a refutation "
                       "nobody owns is a write-only journal)".format(i, i, LEDGER_CAPABILITY))
    return out


# ----------------------------------------------------------------- helpers

def known_scenario_ids(repo):
    import json
    ids = set()
    try:
        with open(os.path.join(repo, "calibration", "scenarios.json")) as fh:
            ids |= {s["id"] for s in json.load(fh)["scenarios"]}
    except (OSError, ValueError, KeyError):
        return set()
    d = os.path.join(repo, "calibration", "corpus", "approved")
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                try:
                    with open(os.path.join(d, f)) as fh:
                        ids.add(json.load(fh)["id"])
                except (OSError, ValueError, KeyError):
                    continue
    return ids


def changed_gate_surfaces(repo, rev_a, rev_b):
    p = _git(repo, "diff", "--name-only", rev_a, rev_b)
    if p.returncode != 0:
        raise LedgerUnreadable("git diff {}..{} failed: {}".format(rev_a, rev_b, p.stderr[:200]))
    return [f for f in p.stdout.splitlines()
            if any(f == s or f.startswith(s) for s in SURFACE_PATTERNS)]


def _read(path):
    try:
        with open(path) as fh:
            return fh.read()
    except OSError:
        return ""


def _fresh_ids(repo, rev, ledger_rel, registered):
    """Entry ids appearing in ledger.md's text ADDED since the baseline — the same
    added-since-baseline mechanism the oracle/gate journals authorize through."""
    base = _git(repo, "show", "{}:{}".format(rev, ledger_rel))
    old = base.stdout if base.returncode == 0 else ""
    cur = _read(os.path.join(repo, ledger_rel))
    added = cur[len(old):] if cur.startswith(old) else cur
    return {e["id"] for e in registered if e["id"] in added}


def _floor_from(blocks, covered):
    """Noise floor in reps from the two most recent run blocks, or 0 when unknowable."""
    if len(blocks) < 2:
        return 0, None
    stats = pw.noise_floor(blocks[-2]["rows"], blocks[-1]["rows"], covered)
    return (1 if stats["moved_1"] else 0), stats


# ----------------------------------------------------------------- commands

def cmd_check(args):
    repo = args.repo
    ledger_text = _read(os.path.join(repo, args.ledger))
    if not ledger_text.strip():
        print("ledger: no {} yet — nothing to check (the ledger is introduced with its "
              "EPOCH; see the file header)".format(args.ledger))
        return 0
    resolve, is_ancestor, path_state = git_helpers(repo)
    try:
        registered, scored, epoch = parse_ledger(ledger_text)
        if not epoch:
            print("ledger UNREADABLE: no `EPOCH: <sha>` line — coverage cannot be scoped "
                  "without it, and scoping to the tag would demand retroactive "
                  "pre-registration", file=sys.stderr)
            return 3
        head = resolve("HEAD")
        rev = resolve(args.baseline_rev)
        if not rev:
            print("ledger UNREADABLE: --baseline-rev {} does not resolve"
                  .format(args.baseline_rev), file=sys.stderr)
            return 3
        # THE EPOCH. Coverage is required only for changes at or after the commit that
        # introduced the ledger. With four releases untagged, `git describe` resolves to a
        # baseline long predating this instrument, and requiring entries back to it would
        # demand pre-registration of changes already made — a contradiction in terms.
        epoch_full = resolve(epoch)
        if epoch_full and is_ancestor(rev, epoch_full):
            rev = epoch_full
        problems = []
        problems += schema_problems(registered, known_scenario_ids(repo), resolve)
        problems += no_effect_problems(registered)
        problems += coverage_problems(changed_gate_surfaces(repo, rev, head), registered,
                                      _fresh_ids(repo, args.baseline_rev, args.ledger,
                                                 registered),
                                      path_state, head, rev, epoch, is_ancestor)
        blocks, skipped = hfmt.parse_run_blocks(_read(os.path.join(repo, args.history)))
        bindings = [bind_entry(e, blocks, resolve, is_ancestor) for e in registered]
        problems += unscored_problems(registered, scored, bindings)
        problems += followup_problems(scored, os.path.join(repo, REGISTRY), args.as_of)
    except LedgerUnreadable as exc:
        print("ledger UNREADABLE (fail closed): {}".format(exc), file=sys.stderr)
        return 3
    none_n = sum(1 for e in registered if e["expect"] == "none")
    print("ledger no-effect share: {} of {} entries ({:.0%}) — a rising share means the "
          "instrument is being satisfied rather than used"
          .format(none_n, len(registered), none_n / max(len(registered), 1)))
    if problems:
        for p in problems:
            print("LEDGER RED: " + p, file=sys.stderr)
        if args.warn_only:
            print("ledger: {} finding(s) — WARN-ONLY, not failing".format(len(problems)))
            return 0
        return 1
    print("ledger CLEAN: {} entr(ies), {} scored row(s); every changed gate surface since {} "
          "is covered by a pre-registered entry".format(
              len(registered), len(scored), (epoch or args.baseline_rev)[:7]))
    return 0


def cmd_score(args):
    repo = args.repo
    resolve, is_ancestor, _ = git_helpers(repo)
    try:
        registered, scored, _epoch = parse_ledger(_read(os.path.join(repo, args.ledger)))
    except LedgerUnreadable as exc:
        print("ledger UNREADABLE: {}".format(exc), file=sys.stderr)
        return 3
    blocks, _sk = hfmt.parse_run_blocks(_read(os.path.join(repo, args.history)))
    covered = {s for e in registered for s in e["scenarios"]}
    floor, _stats = _floor_from(blocks, covered)
    done = {s["id"] for s in scored}
    out = []
    for e in registered:
        if e["id"] in done:
            continue
        b, why = bind_entry(e, blocks, resolve, is_ancestor)
        if b is None:
            continue
        for sc in (e["scenarios"] or ["—"]):
            br = baseline_row(sc, blocks, b) if sc != "—" else None
            ar = actual_row(sc, b) if sc != "—" else None
            base = hfmt.split_runs(br["runs"]) if br else None
            act = hfmt.split_runs(ar["runs"]) if ar else None
            verdict, delta = score_cell(base, act, e["expect"], e["claimed"], floor)
            out.append("| {} | {} | {} | {} | {} | {} | {} |".format(
                e["id"], sc,
                "{}/{}".format(*base) if base else "—",
                "{}/{}".format(*act) if act else "—",
                ("+{}".format(delta) if (delta or 0) > 0 else str(delta))
                if delta is not None else "—",
                verdict, ""))
    if not out:
        print("ledger: no unscored entry binds to a run yet (PENDING is not a verdict)")
        return 0
    last = blocks[-1]
    print("## Scored {} — run {} · repo {}".format(
        args.as_of or datetime.date.today().isoformat(), last["date"], last["repo_sha"]))
    print("| id | scenario | baseline | actual | delta | verdict | note |")
    print("|---|---|---|---|---|---|---|")
    for ln in out:
        print(ln)
    print("\n(ledger.py never writes ledger.md — append the block above by hand, in the same "
          "commit as the run.)", file=sys.stderr)
    return 0


def cmd_report(args):
    repo = args.repo
    try:
        registered, scored, _ = parse_ledger(_read(os.path.join(repo, args.ledger)))
    except LedgerUnreadable as exc:
        print("LEDGER: unreadable ({})".format(exc))
        return 0
    blocks, _sk = hfmt.parse_run_blocks(_read(os.path.join(repo, args.history)))
    covered = {s for e in registered for s in e["scenarios"]}
    floor, stats = _floor_from(blocks, covered)
    moved = [s for s in scored if s["verdict"] in ("HIT", "PARTIAL", "REGRESSED", "SURPRISE")]
    correct = [s for s in moved if s["verdict"] in ("HIT", "PARTIAL")]
    need = pw.min_entries_for_signal()
    if len(moved) >= need:
        print("LEDGER SIGNAL: {} of {} moved entries moved as predicted — p={:.3f} "
              "(one-sided sign test)".format(len(correct), len(moved),
                                             pw.sign_test_p(len(correct), len(moved))))
    else:
        print("LEDGER POWER: {} scored, {} moved — the sign test needs >={} moved entries to "
              "reach p<=0.05, so this cycle is INCONCLUSIVE(power) at the cycle level"
              .format(len(scored), len(moved), need))
    if stats:
        print("NOISE FLOOR (last two runs): {} uncovered scenarios; {} moved >=1 rep, {} "
              "moved >=2, {} changed verdict class — movement at or below {} rep(s) is not "
              "evidence".format(stats["uncovered"], stats["moved_1"], stats["moved_2"],
                                stats["class_moves"], floor))
    print("PER-CELL POWER: at 3 reps the smallest significant single-scenario movement is {} "
          "rep(s) (Fisher one-sided p={:.3f}) — no per-entry claim below that is significant"
          .format(pw.min_detectable_reps(3, 3), pw.fisher_one_sided(3, 3, 0, 3)))
    counts = {}
    for s in scored:
        counts[s["verdict"]] = counts.get(s["verdict"], 0) + 1
    if counts:
        print("LEDGER VERDICTS: " + " · ".join("{} {}".format(v, n)
                                               for v, n in sorted(counts.items())))
    return 0


def cmd_debts(args):
    repo = args.repo
    try:
        _reg, scored, _ = parse_ledger(_read(os.path.join(repo, args.ledger)))
        problems = followup_problems(scored, os.path.join(repo, REGISTRY), args.as_of)
    except LedgerUnreadable as exc:
        print("ledger UNREADABLE: {}".format(exc), file=sys.stderr)
        return 3
    if not problems:
        print("ledger: every FLAT/REGRESSED/SURPRISE entry has a dated follow-up")
        return 0
    for p in problems:
        print("LEDGER RED: " + p, file=sys.stderr)
    if args.emit:
        due = (datetime.date.fromisoformat(args.as_of) if args.as_of
               else datetime.date.today()) + datetime.timedelta(days=60)
        for p in problems:
            eid = p.split(":")[0]
            print('    {{"what": "LEDGER FOLLOW-UP {}: the pre-registered effect did not land '
                  '(FLAT/REGRESSED). Disposition per the four-cause table (wrong-fix / '
                  'plant-moved / oracle-drift / underpowered) and the next action. Done = the '
                  'disposition recorded in ledger.md and the cause addressed, or a '
                  'consciously re-dated entry", "owner": "david", "expires": "{}"}},'
                  .format(eid, due.isoformat()))
    return 1


def main(argv=None):
    ap = argparse.ArgumentParser(description="Improvement ledger: pre-register, then score.")
    ap.add_argument("command", choices=("check", "score", "report", "debts"))
    ap.add_argument("--repo", default=os.path.dirname(HERE))
    ap.add_argument("--ledger", default=LEDGER)
    ap.add_argument("--history", default=HISTORY)
    ap.add_argument("--baseline-rev")
    ap.add_argument("--as-of", help="inject today (tests never touch the real clock)")
    ap.add_argument("--warn-only", action="store_true")
    ap.add_argument("--emit", action="store_true", help="debts: print the JSON to paste")
    args = ap.parse_args(argv)
    if args.command == "check" and not args.baseline_rev:
        ap.error("check needs --baseline-rev")
    if args.as_of:
        try:
            datetime.date.fromisoformat(args.as_of)
        except ValueError:
            ap.error("--as-of must be YYYY-MM-DD")
    return {"check": cmd_check, "score": cmd_score, "report": cmd_report,
            "debts": cmd_debts}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
