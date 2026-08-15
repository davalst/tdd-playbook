#!/usr/bin/env python3
"""plant_forms — the dev/holdout register, and the leakage tripwire that keeps it honest.

Item 3 of the ratified deletion-ratchet plan. Today the tuning loop and the reporting loop
share the same plants: "fix the agent, never the plant" means we iterate until a plant passes
and then quote the catch rate on that plant. A holdout set is the only way the externally
quoted number stops being the one the tuning loop touched.

WHY THE FORM IS NOT IN THE PLANT FILE. `check_scoreboard_integrity` rule (b) pins every file
under `calibration/corpus/approved/` byte-identical forever. That blocks back-filling the
legacy plants — foreseen — and it also blocks BURN-ON-FAILURE, which was not: a holdout plant
that fails must still drive an agent fix, and the moment it does it is contaminated and must
rotate into dev. A form that can change cannot live in a file that can never change. So it
lives in an append-only register beside the corpus, and a burn is an APPEND.

NAME-KEYED AUTHORIZATION (the d5dec34 lesson, applied rather than re-learned). This register
keys on a plant ID, and an id is a name. CIVerd's engine sweep found the same shape in plan
retirement: authorization granted for one content, carried over to whatever later took the
same name. So every entry pins a `content_sha256`, and `form_problems` RECOMPUTES it for any
id present in the corpus and REFUSES a mismatch. For a privately-held plant the hash is
recorded and stated as unverifiable HERE — never silently treated as checked.

Subcommands (exit 0 clean · 1 finding · 2 usage · 3 unreadable/fail-closed):
    plant_forms.py check    — register well-formed, hashes match, holdout ids not leaked
    plant_forms.py show     — the resolved form of every known plant
    plant_forms.py leakage  — the tripwire alone (what `check` runs, callable on its own)
"""
import argparse
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

REGISTER = "calibration/plant-forms.md"
CORPUS_DIR = "calibration/corpus/approved"
FORMS = ("dev", "holdout")
PRIVATE = "private"

# Where a holdout id must NEVER appear: the surfaces the DOER reads as guidance, plus the
# shipped scenario set (an id there means the body itself went public). A vendored tree is
# what leaves this machine, so it is scanned too.
#
# `docs/calibration/history.md` is deliberately NOT scanned, and the reason is the whole
# point of the split. The scoreboard records the id of every scenario a run touched — it is
# how a holdout RESULT gets reported. Scanning it would flag every holdout plant the instant
# it was first read, which is not a leak but the intended use. Ids are public by design here;
# what must stay private is the BODY (task, edits, oracles), and that is what `form` +
# the private sibling repo protect. (Caught by running this against a real id, 2026-08-06 —
# the first draft scanned history.md and every assignment would have burned on contact.)
LEAK_SCAN = (
    "plugins/tdd-playbook/skills/tdd-playbook/SKILL.md",
    "plugins/tdd-playbook/agents",
    "plugins/tdd-playbook/commands",
    "calibration/scenarios.json",
)
# `.claude/worktrees` is DELIBERATELY NOT SCANNED, decided 2026-08-06 rather than assumed.
# An audit flagged it as a gap — five live worktrees carry a full scenarios.json and the
# agent briefs, 851 files, none of them scanned. On examination it is not a gap: a worktree
# is ephemeral local state, not a vendoring surface, and its contents are copies of tracked
# repo content that IS scanned. A holdout id introduced in a worktree is caught the moment it
# merges into the tree this sweep reads. Scanning them would add 851 files of cost per gate
# run for no signal. Recorded here because "we thought about it and said no" and "nobody
# looked" are indistinguishable from the outside, which is the whole H15 lesson.
VENDOR_DIRS = (".claude/skills", ".claude/agents", ".claude/commands", ".claude/bin",
               ".claude/hooks")

_SHA = re.compile(r"^[0-9a-f]{64}$")


class RegisterUnreadable(Exception):
    pass


def _cells(line):
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|") and not body.endswith("\\|"):
        body = body[:-1]
    return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", body)]


def parse_register(text):
    """All entries oldest-first. A misshaped row RAISES: an entry silently dropped is a
    plant whose form is quietly `dev`, i.e. a holdout plant tuned against by accident."""
    out, in_entries = [], False
    for raw in (text or "").splitlines():
        line = raw.strip()
        if line.startswith("#"):
            in_entries = line.lstrip("#").strip().lower().startswith("entries")
            continue
        if not in_entries or not line.startswith("|"):
            continue
        c = _cells(line)
        if not c or not c[0] or c[0] == "date" or set(c[0]) <= set("-: "):
            continue
        if len(c) != 5:
            raise RegisterUnreadable(
                "register row needs 5 cells, got {}: {}".format(len(c), line[:80]))
        out.append({"date": c[0], "plant_id": c[1], "form": c[2],
                    "content_sha256": c[3], "reason": c[4]})
    return out


# The register SERIALIZER lives beside its parser so the column contract and the pipe-escaping
# cannot drift between writer and reader (holdout.cmd_approve_holdout is the first programmatic
# writer of this schema). `_cells` un-escapes `\|`; this escapes it. Keep the two in lockstep.
ENTRIES_SECTION = "## Entries"
ENTRIES_TABLE = ("| date | plant_id | form | content_sha256 | reason |\n"
                 "| --- | --- | --- | --- | --- |\n")


def format_register_row(date, plant_id, form, content_sha256, reason):
    """One register row that parse_register reads back exactly (pipe-escaped)."""
    return "| " + " | ".join(str(c).replace("|", "\\|") for c in
                             (date, plant_id, form, content_sha256, reason)) + " |\n"


def resolve_forms(entries):
    """{plant_id: form} from the LATEST entry per id. Absent ids are not present here —
    callers use form_of(), whose default is the safe direction."""
    resolved = {}
    for e in entries:
        resolved[e["plant_id"]] = e["form"]
    return resolved


def form_of(plant_id, resolved):
    """An id with no entry is `dev`. Absence is a decision and this is the safe one: an
    unassigned plant gets TUNED AGAINST, never quietly reported as a clean measurement."""
    return resolved.get(plant_id, "dev")


def plant_sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def shas_in_dir(d):
    """{plant id: sha256 of its file} for every .json in `d`, keyed by the id INSIDE the json
    (not the filename — nothing else keys on the filename). A dir that does not exist yields {}.
    ONE enumerator: corpus_shas AND the holdout controller's drift check both call it, so the
    drift check (holdout.verify_bodies -> form_problems) compares like with like by CONSTRUCTION
    (arch-F3), not by two copied loops agreeing to stay byte-identical."""
    out = {}
    if not os.path.isdir(d):
        return out
    for name in sorted(os.listdir(d)):
        if not name.endswith(".json"):
            continue
        p = os.path.join(d, name)
        try:
            with open(p) as fh:
                pid = json.load(fh).get("id")
        except (OSError, ValueError):
            continue
        if pid:
            out[pid] = plant_sha(p)
    return out


def corpus_shas(repo):
    """{plant id: sha256 of its approved file}."""
    return shas_in_dir(os.path.join(repo, CORPUS_DIR))


def form_problems(entries, shas):
    """Schema + the name-keyed-authorization rule. `shas` is injected so the check is
    testable without a corpus — a check nobody can plant against is not a check."""
    out = []
    for e in entries:
        i = e["plant_id"]
        if e["form"] not in FORMS:
            out.append("{}: form must be one of {}".format(i, "|".join(FORMS)))
        if not e["reason"]:
            out.append("{}: an assignment with no reason is not auditable".format(i))
        h = e["content_sha256"]
        if h == PRIVATE:
            if i in shas:
                out.append(
                    "{}: recorded `private` but the plant IS in this repo's corpus — a "
                    "privately-held body cannot also be public; use its real sha256"
                    .format(i))
            continue
        if not _SHA.match(h or ""):
            out.append("{}: content_sha256 must be a sha256 hex digest or `{}` — an "
                       "unpinned name-keyed assignment is the d5dec34 shape (authorization "
                       "granted for one content carrying over to another)".format(i, PRIVATE))
            continue
        actual = shas.get(i)
        if actual is None:
            out.append(
                "{}: a sha256 is recorded but no approved plant carries that id, so nothing "
                "here can verify it. Use `{}` if the body is held privately — the tool must "
                "not imply it checked something it could not see.".format(i, PRIVATE))
        elif actual != h:
            out.append(
                "{}: content_sha256 does not match the approved plant ({}... vs recorded "
                "{}...). Either the plant changed (which rule (b) forbids) or this entry "
                "authorizes a different content than the one it names."
                .format(i, actual[:12], h[:12]))
    return out


# ------------------------------------------------------------------ the leakage tripwire

def _iter_files(repo, rel):
    p = os.path.join(repo, rel)
    if os.path.isfile(p):
        yield rel, p
    elif os.path.isdir(p):
        for root, _dirs, files in os.walk(p):
            for f in sorted(files):
                fp = os.path.join(root, f)
                yield os.path.relpath(fp, repo), fp


def leakage_problems(repo, holdout_ids, scan=LEAK_SCAN, vendor_dirs=VENDOR_DIRS):
    """A holdout id appearing in a gate surface or a vendored tree is a BURNED plant: the
    doer can read it, so the reporting set is now the tuning set.

    Returns (problems, files_scanned). The count is returned so the caller can refuse a
    VACUOUS run — a tripwire that scanned nothing passes everything, which is the failure
    mode this whole family of checks exists to prevent.
    """
    problems, scanned, roots_present = [], 0, 0
    targets = list(scan) + [d for d in vendor_dirs]
    for rel in targets:
        seen_here = 0
        for relpath, path in _iter_files(repo, rel):
            try:
                with open(path, "r", errors="replace") as fh:
                    body = fh.read()
            except OSError:
                continue
            scanned += 1
            seen_here += 1
            for pid in sorted(holdout_ids):
                if pid in body:
                    problems.append(
                        "HOLDOUT LEAK: '{}' appears in {} — a holdout id in a gate surface "
                        "or a vendored tree is a burned plant (the doer can read it). Rotate "
                        "it to dev with a `burn-on-failure` entry and replenish holdout, or "
                        "remove the reference.".format(pid, relpath))
        roots_present += 1 if seen_here else 0
    # Report the ROOT count as well as the file count (H15/§12): a scan root that vanishes
    # or is renamed drops silently out of a file total, which keeps looking plausible.
    return problems, scanned, roots_present, len(targets)


# ------------------------------------------------------------------ commands

def _read(path):
    try:
        with open(path) as fh:
            return fh.read()
    except OSError:
        return ""


def _load(args):
    text = _read(os.path.join(args.repo, args.register))
    if not text.strip():
        raise RegisterUnreadable("no register at {}".format(args.register))
    return parse_register(text)


def cmd_check(args):
    try:
        entries = _load(args)
    except RegisterUnreadable as exc:
        print("plant_forms UNREADABLE (fail closed): {}".format(exc), file=sys.stderr)
        return 3
    shas = corpus_shas(args.repo)
    problems = form_problems(entries, shas)
    resolved = resolve_forms(entries)
    holdout = {i for i, f in resolved.items() if f == "holdout"}
    leaks, scanned, roots, roots_total = leakage_problems(args.repo, holdout)
    problems += leaks
    # VACUITY: with no holdout ids the tripwire cannot fail, so it must not read as a pass.
    # (Scanning zero FILES is a separate, worse failure and is always a finding.)
    if scanned == 0:
        problems.append(
            "leakage tripwire scanned 0 files — the scan roots do not exist in this tree, so "
            "a green here would mean nothing")
    if problems:
        for p in problems:
            print("PLANT-FORMS RED: " + p, file=sys.stderr)
        return 0 if args.warn_only else 1
    if not holdout:
        print("plant_forms: {} entr(ies); NO holdout classes assigned yet — the tripwire "
              "scanned {} files across {} of {} roots and could not have failed. Reported "
              "as unarmed, not green: the first assignment is dated debt on the "
              "`plant-forms` capability.".format(len(entries), scanned, roots, roots_total))
        return 0
    print("plant_forms CLEAN: {} entr(ies) · {} holdout / {} dev · tripwire scanned {} files "
          "across {} of {} roots with no leak".format(
              len(entries), len(holdout), len(resolved) - len(holdout), scanned,
              roots, roots_total))
    return 0


def cmd_show(args):
    try:
        entries = _load(args)
    except RegisterUnreadable as exc:
        print("plant_forms UNREADABLE: {}".format(exc), file=sys.stderr)
        return 3
    resolved = resolve_forms(entries)
    shas = corpus_shas(args.repo)
    ids = sorted(set(shas) | set(resolved))
    for i in ids:
        where = "corpus" if i in shas else "private"
        print("  {:52} {:8} {}".format(i, form_of(i, resolved), where))
    print("{} plant(s): {} dev · {} holdout".format(
        len(ids), sum(1 for i in ids if form_of(i, resolved) == "dev"),
        sum(1 for i in ids if form_of(i, resolved) == "holdout")))
    return 0


def cmd_leakage(args):
    try:
        entries = _load(args)
    except RegisterUnreadable as exc:
        print("plant_forms UNREADABLE: {}".format(exc), file=sys.stderr)
        return 3
    resolved = resolve_forms(entries)
    holdout = {i for i, f in resolved.items() if f == "holdout"}
    problems, scanned, roots, roots_total = leakage_problems(args.repo, holdout)
    for p in problems:
        print("PLANT-FORMS RED: " + p, file=sys.stderr)
    print("leakage: {} holdout id(s) checked against {} file(s) across {} of {} "
          "roots".format(len(holdout), scanned, roots, roots_total))
    return 1 if problems else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="dev/holdout register + leakage tripwire")
    ap.add_argument("command", choices=("check", "show", "leakage"))
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--register", default=REGISTER)
    ap.add_argument("--warn-only", action="store_true")
    args = ap.parse_args(argv)
    return {"check": cmd_check, "show": cmd_show, "leakage": cmd_leakage}[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
