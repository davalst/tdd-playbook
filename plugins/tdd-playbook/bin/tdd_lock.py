#!/usr/bin/env python3
"""tdd_lock — TEST-LOCK: make §1's iron rule mechanical (HACK_CATALOG H2/H5).

The strongest validated defense against agent test-gaming is making tests READ-ONLY to the
implementing agent: commit the failing tests, lock them, implement to green, unlock with a
stated reason if (and only if) the test itself turns out to be wrong. Prompts don't stop
test-editing; this does — `test_lock_guard.py` (PreToolUse) BLOCKS edits to locked files
while a lock is active, and to the verifier surface (conftest.py, test configs) wholesale.

    tdd_lock.py lock <file> [...]     # record path + sha256 of each test file
    tdd_lock.py unlock --reason "..." # journaled; the reason feeds /grade
    tdd_lock.py status                # active lock, if any

State: .claude/tdd-lock.json (the active lock — delete = unlock, but use `unlock` so the
journal records WHY). Journal: .claude/tdd-lock-journal.jsonl, append-only across locks —
an unlock without a reason is refused; frequent unlocks are a smell /grade must see.
Exit codes: 0 ok · 1 refusal (bad unlock / nothing locked) · 2 usage.
"""
import argparse
import datetime
import hashlib
import json
import os
import sys


def project_root():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def lock_path(root):
    return os.path.join(root, ".claude", "tdd-lock.json")


def journal_path(root):
    return os.path.join(root, ".claude", "tdd-lock-journal.jsonl")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def _now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _journal(root, entry):
    os.makedirs(os.path.dirname(journal_path(root)), exist_ok=True)
    with open(journal_path(root), "a") as fh:
        fh.write(json.dumps(entry) + "\n")


def cmd_lock(args):
    root = project_root()
    files = {}
    for f in args.files:
        ap = os.path.abspath(f)
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
    with open(path) as fh:
        locked = json.load(fh)
    _journal(root, {"ts": _now(), "event": "unlock", "reason": reason,
                    "files": sorted(locked.get("files", {}))})
    os.remove(path)
    print("tdd_lock: unlocked {} file(s). Reason journaled for /grade.".format(
        len(locked.get("files", {}))))
    return 0


def cmd_status(_args):
    root = project_root()
    path = lock_path(root)
    if not os.path.isfile(path):
        print("tdd_lock: no active lock")
        return 0
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
    sub.add_parser("status")
    args = ap.parse_args(argv)
    return {"lock": cmd_lock, "unlock": cmd_unlock, "status": cmd_status}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
