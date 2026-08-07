#!/usr/bin/env python3
"""PostToolUse(Edit|MultiEdit|Write + Bash) — AUTO-LOCK red-first tests (H2 closure).

The test-lock guard can only defend tests that are LOCKED — and in practice agents
don't run `tdd_lock.py lock` by hand, so most freshly-written red tests stayed freely
editable and were rewritten mid-build (observed live 2026-07-19: three assumption-wrong
tests silently rewritten to match behavior). This hook closes the adoption gap:

  1. A write/edit to a TEST FILE records it as "pending red" in core-owned Git state.
  2. A test-runner Bash command whose output shows FAILURES locks every pending file
     (merged into the canonical shared lock in exactly cmd_lock's shape, journaled as
     auto_lock_red) — the red phase is confirmed, so from here the test is read-only
     until green or an unlock with a journaled reason.
  3. A fully GREEN run clears pending without locking (that file's red window closed;
     whether it was ever red is the red-first verifier's concern, not the lock's).

Heuristic honesty: a failing run locks ALL pending test files, not just the ones that
failed — parsing per-file failures across runners is fragile, and in the red-first
workflow the pending set IS the current red phase. Default mode: warn (announces the
auto-lock so the agent knows the tests are now read-only); TDD_PLAYBOOK_HOOK_REDLOCK=off
disables. Needs the host to pass `tool_response` on Bash PostToolUse events; without it
the hook does nothing (fail-open — never wedges a session).
"""
import hashlib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit, file_path_of, is_test_file  # noqa: E402
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..", "..", "bin")))
from host_contract import (ContractError, PENDING_FILENAME, append_event,
                           lock_path as core_lock_path, merge_lock, new_lock_record, read_lock,
                           read_state_json, resolve_repository, state_path,
                           write_state_json)  # noqa: E402

NAME = "redlock"

_TEST_CMD_RE = re.compile(
    r"(^|[\s;&|])(python\d?\s+-m\s+)?(pytest|unittest|tox)\b"
    r"|(^|[\s;&|])(jest|vitest|mocha)\b"
    r"|(^|[\s;&|])go\s+test\b"
    r"|(^|[\s;&|])cargo\s+test\b"
    r"|(^|[\s;&|])npm\s+(run\s+)?test\b"
)
_RED_RE = re.compile(r"\b[1-9]\d* (failed|error)\b|\bFAILED\b|\bTraceback\b")
_GREEN_RE = re.compile(r"\b\d+ passed\b|\bok\b|\bPASS\b")


def project_root():
    # realpath: mirrors tdd_lock.project_root (macOS /var -> /private/var)
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
            or "local-worktree-{}".format(
                hashlib.sha256(project_root().encode("utf-8")).hexdigest()[:16]))


def _now():
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _pending_path(root):
    identity = _identity(root)
    if identity:
        return state_path(identity, PENDING_FILENAME)
    return os.path.join(root, ".claude", "tdd-pending-red.json")


def _lock_path(root):
    identity = _identity(root)
    if identity:
        return core_lock_path(identity)
    return os.path.join(root, ".claude", "tdd-lock.json")


def _load(path):
    if not os.path.isfile(path):
        return {}
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")


def _journal(root, entry):
    identity = _identity(root)
    if identity:
        portable = dict(entry)
        portable.update({"schema_version": 1, "repo_id": identity["repo_id"],
                         "worktree_id": identity["worktree_id"],
                         "head": identity["head"], "session_id": _session_id()})
        append_event(identity, portable)
        return
    jp = os.path.join(root, ".claude", "tdd-lock-journal.jsonl")
    os.makedirs(os.path.dirname(jp), exist_ok=True)
    with open(jp, "a") as fh:
        fh.write(json.dumps(entry) + "\n")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        h.update(fh.read())
    return h.hexdigest()


def record_pending(root, path):
    """A test-file write: mark it pending-red (unless already locked)."""
    ap = os.path.realpath(path if os.path.isabs(path) else os.path.join(root, path))
    rel = os.path.relpath(ap, root)
    if rel.startswith(".."):
        return                                  # outside the project — not ours
    identity = _identity(root)
    lock = (read_lock(identity) or {}) if identity else _load(_lock_path(root))
    if rel in (lock.get("files") or {}):
        return                                  # already locked — the guard owns it
    pending = read_state_json(identity, PENDING_FILENAME) if identity \
        else _load(_pending_path(root))
    files = pending.setdefault("files", {})
    files[rel] = _now()
    if identity:
        write_state_json(identity, PENDING_FILENAME, pending)
    else:
        _save(_pending_path(root), pending)


def resolve_test_run(command, response_text):
    """(is_test_run, verdict) — verdict 'red' | 'green' | None (can't tell)."""
    if not command or not _TEST_CMD_RE.search(command):
        return False, None
    text = response_text or ""
    if _RED_RE.search(text):
        return True, "red"
    if _GREEN_RE.search(text):
        return True, "green"
    return True, None                           # test run, outcome unknown → do nothing


def apply_run_outcome(root, verdict):
    """Red run → lock all pending (that exist); green run → clear pending.
    Returns the list of newly locked rel-paths (for the announce)."""
    identity = _identity(root)
    pending = read_state_json(identity, PENDING_FILENAME) if identity \
        else _load(_pending_path(root))
    files = pending.get("files") or {}
    if not files:
        return []
    if verdict == "green":
        if identity:
            write_state_json(identity, PENDING_FILENAME, {"files": {}})
        else:
            _save(_pending_path(root), {"files": {}})
        return []
    # red: merge into the lock in cmd_lock's exact shape
    locked_now = []
    lock = (read_lock(identity) or {}) if identity else _load(_lock_path(root))
    existing = lock.get("files") or {}
    for rel in sorted(files):
        ap = os.path.join(root, rel)
        if not os.path.isfile(ap):
            continue
        existing[rel] = _sha(ap)
        locked_now.append(rel)
    if locked_now:
        if identity:
            # Auto-red is a trusted extension of the active run, never a competing owner.
            session = lock.get("session_id") or _session_id()
            record = new_lock_record(identity, locked_now, session)
            merge_lock(identity, record)
        else:
            _save(_lock_path(root), {"locked_at": _now(), "files": existing})
        _journal(root, {"ts": _now(), "event": "auto_lock_red",
                        "files": locked_now})
    if identity:
        write_state_json(identity, PENDING_FILENAME, {"files": {}})
    else:
        _save(_pending_path(root), {"files": {}})
    return locked_now


def main():
    event = read_event()
    root = project_root()
    tool = event.get("tool_name") or ""

    if tool in ("Edit", "MultiEdit", "Write"):
        path = file_path_of(event)
        if is_test_file(path):
            record_pending(root, path)
        sys.exit(0)

    if tool == "Bash":
        cmd = (event.get("tool_input") or {}).get("command", "")
        resp = event.get("tool_response")
        text = resp if isinstance(resp, str) else json.dumps(resp) if resp else ""
        is_run, verdict = resolve_test_run(cmd, text)
        if not is_run or verdict is None:
            sys.exit(0)
        locked = apply_run_outcome(root, verdict)
        if locked:
            emit(NAME, [
                "auto-locked {} red test file(s): {} — implement the SOURCE to green "
                "without editing them".format(len(locked), ", ".join(locked)),
                "if a test itself is wrong: python3 <plugin>/bin/tdd_lock.py unlock "
                "--reason \"why\" (journaled, reviewed by /grade)",
            ])
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
