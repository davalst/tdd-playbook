#!/usr/bin/env python3
"""tdd_lock — TEST-LOCK: make §1's iron rule mechanical (HACK_CATALOG H2/H5).

The strongest validated defense against agent test-gaming is making tests READ-ONLY to the
implementing agent: commit the failing tests, lock them, implement to green, unlock with a
stated reason if (and only if) the test itself turns out to be wrong. Prompts don't stop
test-editing; this does — `test_lock_guard.py` (PreToolUse) BLOCKS edits to locked files
while a lock is active, and to the verifier surface (conftest.py, test configs) wholesale.

    tdd_lock.py lock <file> [...]     # record path + sha256 of each test file
    tdd_lock.py unlock --reason "..." [--class phase|feature-end|test-wrong|gate-wrong]
    tdd_lock.py status                # active lock, if any

State: the Git common-dir's `tdd-playbook/active-lock.json` (one authority shared by linked
worktrees).  Non-Git scratch projects retain the legacy `.claude` path.  Existing Git locks
are imported once and the old source is consumed; there is no permanent dual-read mode.
The append-only event journal records WHY an unlock happened for `/grade`.
Exit codes: 0 ok · 1 refusal (bad unlock / nothing locked) · 2 usage.

REASON CLASS (v1.27) — why it exists: gate_yield counted EVERY journaled unlock as a block
adjudicated a false positive, so four cycles of the normal red-first lock/implement/unlock
rhythm printed `RETIREMENT CANDIDATE: testlock` with zero real false positives — the
instrument recommending retirement of the strongest anti-gaming defense there is. Only
`gate-wrong` means "the gate blocked work it should not have"; that is the ONLY class that
feeds retirement. `test-wrong` is the lock DELIVERING value (the agent hit the wall, stopped,
and said why the test was wrong) — counting it as a false positive inverts the sign.
Self-grading hazard, handled: the one class that moves the needle is the most expensive to
claim (>=30 chars naming which block was wrong and why, else REFUSED), and a phase-shaped
reason claiming `gate-wrong` is flagged `class_mismatch` — advisory only. Inference NEVER
rewrites a stated class: silently correcting the record would be the same fabrication this
fix exists to end.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import sys

from host_contract import (ContractError, append_event, clear_lock, events_path,
                           import_legacy_lock, lock_path as core_lock_path,
                           merge_lock, new_lock_record, read_lock, resolve_repository)

# Closed vocabulary. No `other`/`misc` bucket — an open bucket becomes the dumping ground and
# re-creates the ambiguity. Absent --class records `unclassified`, which is UNMEASURED (never
# a soft accept, never a zero): gate_yield's own rule is that absent data is not evidence.
REASON_CLASSES = ("phase", "feature-end", "test-wrong", "gate-wrong")
FEEDS_RETIREMENT = "gate-wrong"
GATE_WRONG_MIN = 30

# Advisory only — drawn from the REAL journal's text (26 locks / 24 unlocks as of 119e2de).
_PHASE_RX = re.compile(
    r"(?i)(implemented? to green|will re-?lock|re-?locking|phase (?:boundary|complete)"
    r"|feature complete|releasing v|all suites green|cycle complete)")


def project_root():
    # The neutral env is the adapter contract; CLAUDE_PROJECT_DIR remains compatible while
    # existing hooks migrate. realpath also normalizes macOS /var -> /private/var.
    return os.path.realpath(os.environ.get("TDD_PLAYBOOK_PROJECT_ROOT")
                            or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _identity(root):
    try:
        return resolve_repository(root)
    except ContractError:
        return None


def _session_id():
    return (os.environ.get("TDD_PLAYBOOK_SESSION_ID")
            or os.environ.get("CLAUDE_SESSION_ID")
            # Some hosts do not export their turn id into Bash subprocesses.  A stable
            # worktree fallback lets sequential CLI calls extend/unlock safely, while linked
            # worktrees remain competing owners.  Same-worktree agents serialize+merge.
            or "local-worktree-{}".format(
                hashlib.sha256(project_root().encode("utf-8")).hexdigest()[:16]))


def lock_path(root):
    identity = _identity(root)
    if identity:
        return core_lock_path(identity)
    return os.path.join(root, ".claude", "tdd-lock.json")


def journal_path(root):
    identity = _identity(root)
    if identity:
        return events_path(identity)
    return os.path.join(root, ".claude", "tdd-lock-journal.jsonl")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _journal(root, entry):
    identity = _identity(root)
    if identity:
        portable = dict(entry)
        portable.update({
            "schema_version": 1,
            "repo_id": identity["repo_id"],
            "worktree_id": identity["worktree_id"],
            "head": identity["head"],
            "session_id": _session_id(),
        })
        append_event(identity, portable)
        return
    os.makedirs(os.path.dirname(journal_path(root)), exist_ok=True)
    with open(journal_path(root), "a") as fh:
        fh.write(json.dumps(entry) + "\n")


def cmd_lock(args):
    root = project_root()
    identity = _identity(root)
    if identity:
        try:
            import_legacy_lock(identity, _session_id())
            fresh = new_lock_record(identity, args.files, _session_id())
            existing_record = read_lock(identity)
            fresh = merge_lock(identity, fresh)
            existing = dict(fresh["files"])
            files = {rel: fresh["files"][rel]
                     for rel in fresh["files"] if rel not in (existing_record or {}).get("files", {})}
        except ContractError as exc:
            sys.stderr.write("tdd_lock: {}\n".format(exc))
            return 2
    else:
        files = {}
        for f in args.files:
            ap = os.path.realpath(os.path.abspath(f))
            if not os.path.isfile(ap):
                sys.stderr.write("tdd_lock: no such file: {}\n".format(f))
                return 2
            rel = os.path.relpath(ap, root)
            files[rel] = _sha(ap)
        path = lock_path(root)
        existing = {}
        if os.path.isfile(path):
            with open(path) as fh:
                existing = json.load(fh).get("files", {})
        existing.update(files)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump({"locked_at": _now(), "files": existing}, fh, indent=2)
            fh.write("\n")
    _journal(root, {"ts": _now(), "event": "lock", "files": sorted(files)})
    print("tdd_lock: LOCKED {} file(s) ({} total in lock). Implement to green without "
          "touching them; `tdd_lock.py unlock --reason ...` if a test itself is wrong."
          .format(len(files), len(existing)))
    return 0


def cmd_unlock(args):
    root = project_root()
    identity = _identity(root)
    if identity:
        try:
            import_legacy_lock(identity, _session_id())
        except ContractError as exc:
            sys.stderr.write("tdd_lock: {}\n".format(exc))
            return 1
    path = lock_path(root)
    if not os.path.isfile(path):
        sys.stderr.write("tdd_lock: nothing is locked\n")
        return 1
    reason = (args.reason or "").strip()
    if len(reason) < 10:
        sys.stderr.write(
            "tdd_lock: REFUSED — unlocking needs a real reason (>=10 chars, e.g. why the "
            "test itself is wrong). The reason is journaled and reviewed by /grade.\n")
        return 1
    klass = args.reason_class or "unclassified"
    # The only class that feeds retirement is also the most expensive to claim (see header).
    # Refuse BEFORE any write, so a thin gate-wrong leaves the lock intact and nothing journaled.
    if klass == FEEDS_RETIREMENT and len(reason) < GATE_WRONG_MIN:
        sys.stderr.write(
            "tdd_lock: REFUSED — --class {} is the one class that counts a block as a false "
            "positive and drives gate retirement, so it needs >={} chars naming WHICH block "
            "fired and why it was wrong (got {}). Use --class phase/feature-end/test-wrong if "
            "the gate was right and the work simply moved on.\n"
            .format(FEEDS_RETIREMENT, GATE_WRONG_MIN, len(reason)))
        return 1
    mismatch = bool(klass == FEEDS_RETIREMENT and _PHASE_RX.search(reason))
    if identity:
        try:
            locked = read_lock(identity)
        except ContractError as exc:
            sys.stderr.write("tdd_lock: REFUSED — {}\n".format(exc))
            return 1
    else:
        with open(path) as fh:
            locked = json.load(fh)
    entry = {"ts": _now(), "event": "unlock", "reason": reason, "reason_class": klass,
             "files": sorted(locked.get("files", {}))}
    if mismatch:
        # Recorded, never corrected: the stated class stands and the contradiction rides
        # beside it. A silent rewrite would fabricate into the record /grade reads.
        entry["class_mismatch"] = True
        sys.stderr.write(
            "tdd_lock: MISMATCH — the reason reads like a phase boundary but claims --class "
            "{}. Recording your class as stated, flagged for /grade.\n".format(FEEDS_RETIREMENT))
    if not args.reason_class:
        sys.stderr.write(
            "tdd_lock: no --class given — recorded UNCLASSIFIED, so this unlock measures "
            "nothing either way. Pass --class {} next time.\n".format("|".join(REASON_CLASSES)))
    if identity:
        try:
            clear_lock(identity, expected_generation=locked["generation"],
                       expected_lock_id=locked["lock_id"],
                       expected_session_id=_session_id())
        except ContractError as exc:
            sys.stderr.write("tdd_lock: REFUSED — {}\n".format(exc))
            return 1
    else:
        os.remove(path)
    # Journal only after the conditional clear succeeds: a failed/stale CAS must never leave
    # a false unlock row. The same rule governs the derived yield/override event.
    _journal(root, entry)
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "hooks", "scripts"))
        from _common import log_yield_event
        log_yield_event("testlock", "override",
                        {"reason": reason, "reason_class": klass}, source="testlock")
    except Exception:
        pass
    print("tdd_lock: unlocked {} file(s). Reason journaled for /grade.".format(
        len(locked.get("files", {}))))
    return 0


def cmd_status(_args):
    root = project_root()
    identity = _identity(root)
    if identity:
        try:
            import_legacy_lock(identity, _session_id())
        except ContractError as exc:
            sys.stderr.write("tdd_lock: REFUSED — {}\n".format(exc))
            return 1
    path = lock_path(root)
    if not os.path.isfile(path):
        print("tdd_lock: no active lock")
        return 0
    if identity:
        try:
            locked = read_lock(identity)
        except ContractError as exc:
            sys.stderr.write("tdd_lock: REFUSED — {}\n".format(exc))
            return 1
    else:
        with open(path) as fh:
            locked = json.load(fh)
    print("tdd_lock: ACTIVE since {} — {} file(s):".format(
        locked.get("locked_at", "?"), len(locked.get("files", {}))))
    for rel in sorted(locked.get("files", {})):
        print("  - " + rel)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="TEST-LOCK: tests read-only during implementation.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_lock = sub.add_parser("lock")
    p_lock.add_argument("files", nargs="+")
    p_unlock = sub.add_parser("unlock")
    p_unlock.add_argument("--reason", default="")
    # dest is mandatory: `class` is a Python keyword, so args.class would not parse.
    p_unlock.add_argument("--class", dest="reason_class", choices=REASON_CLASSES, default=None,
                          help="why the lock is being released; only gate-wrong counts a "
                               "block as a false positive (see module header)")
    sub.add_parser("status")
    args = ap.parse_args(argv)
    return {"lock": cmd_lock, "unlock": cmd_unlock, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
