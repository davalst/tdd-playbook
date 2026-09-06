#!/usr/bin/env python3
"""Stop — remind to close the Tripwire loop when source changed without tests.

Enforces Playbook §6 "Tripwire last" + §1 "every bug gets a regression test FIRST".
When a turn ends, if THIS TURN edited uncommitted SOURCE and there is no test evidence for
it, surface a reminder — to the AGENT (Stop-hook additionalContext, v1.49), not the operator.

Test evidence, in order (plan 2026-09-06-tripwire-reminder-lock-aware, D1):
  1. a test file edited THIS TURN, regardless of commit state (the transcript is the
     evidence, not `git status`);
  2. a test file still UNCOMMITTED from earlier in this session (pre-1.49 behaviour, kept —
     not widened);
  3. an active TEST-LOCK that was taken in THIS worktree, at this HEAD or an ancestor of it,
     naming at least one test file whose on-disk hash still matches the lock.

Why (3) exists: before v1.49 the reminder intersected `git status` (uncommitted only) with
the session's edits, so a red test that was COMMITTED and then /tdd-lock'ed — the workflow
the playbook prescribes — vanished from the evidence and the reminder fired on every
implementing turn (cheliped, 2026-09-06; reproduced here first). The lock is the artefact
that proves the tests came first; it is the ONLY evidence allowed to cross a turn boundary
for a committed test, and each of its three conditions has a twin in test_hooks.py.

Cheap + language-agnostic: `git status --porcelain`, the shared transcript reader, the one
lock authority (host_contract). Silent when: not a git repo, git unavailable, or the Stop is
a re-entry (`stop_hook_active`). With NO readable transcript the check falls back to the
whole dirty tree (absent evidence is UNMEASURED, never zero — §12).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import transcript as tr  # noqa: E402
from _common import read_event, emit, is_test_file, log_yield_event  # noqa: E402
from fixture_guard import is_fixture_data  # noqa: E402  (one predicate, not a copy)
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..", "..", "bin")))

NAME = "tripwire"

_DOC_OR_CONFIG = (
    ".md", ".txt", ".rst", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg",
    ".lock", ".gitignore", ".env",
)
_CODE_EXT = (
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rs", ".rb", ".java", ".kt",
    ".c", ".cc", ".cpp", ".h", ".hpp", ".cs", ".php", ".swift", ".scala", ".sh",
)


def changed_paths():
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=10,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    paths = []
    for line in out.stdout.splitlines():
        # format: "XY <path>"  (path may be quoted / renamed "a -> b")
        p = line[3:].strip()
        if " -> " in p:
            p = p.split(" -> ", 1)[1]
        p = p.strip('"')
        if p:
            paths.append(p)
    return paths


def classify(paths):
    src, tests = [], []
    for p in paths:
        low = p.lower()
        if is_fixture_data(p):
            continue          # integ-#7: test DATA is neither a test change nor source —
                              # a fixture edit must not silence the "no test change" nudge
        if is_test_file(p):
            tests.append(p)
        elif low.endswith(_CODE_EXT) and not low.endswith(_DOC_OR_CONFIG):
            src.append(p)
    return src, tests


def session_edited_paths(event):
    """Paths this SESSION edited, mined from the whole transcript.

    Returns a SET (possibly EMPTY) when the transcript is readable, and None ONLY when it
    is not. That distinction is the whole fix: this used to `return paths or None`, which
    collapsed "this turn edited nothing" into "there is no transcript" — so a READ-ONLY
    turn skipped the session narrowing in main(), fell through to whole-tree `git status`,
    and reported *"source changed with NO test change THIS TURN"* on a turn that changed
    nothing, whenever the tree was dirty from earlier work. Absent evidence and zero
    evidence are different facts (§12), and here they had the same representation.

    The walk itself now comes from `transcript.py`, the one reader — this was one of TWO
    parsers and FOUR disagreeing tool-name sets before that module existed.
    """
    tp = event.get("transcript_path")
    if not tp or not os.path.isfile(tp):
        return None
    records = []
    try:
        with open(tp, errors="replace") as fh:
            for line in fh:
                if '"tool_use"' not in line:
                    continue
                obj = tr.parse_line(line)
                if obj is not None:
                    records.append(obj)
    except OSError:
        return None
    # realpath, not abspath — macOS tempdirs are symlinked (/var -> /private/var) and a
    # mismatch silently empties the session intersection in main(). Owned by transcript.py.
    return tr.edited_paths(records)


def turn_edited_paths(event, session):
    """Paths edited THIS TURN (`transcript.current_turn`), or None when unreadable.

    A CAPPED read (the current turn alone exceeds the byte cap) degrades to the SESSION
    set — the pre-1.49 behaviour — rather than to the whole tree: partial evidence beats
    none, and the shortfall is logged as UNMEASURED so it cannot read as a quiet turn.
    """
    tp = event.get("transcript_path")
    if not tp or not os.path.isfile(tp):
        return None
    turn = tr.current_turn(tp)
    if turn.status == tr.UNREADABLE:
        return None
    if turn.status != tr.COMPLETE:
        log_yield_event(NAME, "unmeasured", {"reason": "transcript-" + str(turn.status)})
        return session
    return tr.edited_paths(turn.records)


def project_root():
    return os.path.realpath(os.environ.get("TDD_PLAYBOOK_PROJECT_ROOT")
                            or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def _is_ancestor(root, older, newer):
    try:
        r = subprocess.run(["git", "merge-base", "--is-ancestor", older, newer], cwd=root,
                           capture_output=True, text=True, timeout=10)
    except Exception:
        return False
    return r.returncode == 0


def lock_test_evidence(root):
    """(locked intact test files, reason) — the only evidence allowed to cross a turn.

    Reads the SAME canonical record lock_guard enforces (host_contract), then applies three
    conditions `_validate_lock` deliberately does not (locks are shared across linked
    worktrees by design, and `lock` accepts any regular file):
      - the lock was taken in THIS worktree (`source_worktree_id`);
      - at this HEAD or an ancestor of it — ancestor, not equality, because the playbook's
        own git rule checkpoints mid-feature and strict equality would void the evidence at
        the first checkpoint and bring the false positive straight back;
      - at least one locked path is a test file whose on-disk sha256 still equals the lock
        entry (a locked test edited around the guard is not evidence).
    A MALFORMED record is NO evidence, never silence: the reminder keeps its predicate and
    logs an `unmeasured` row, so a broken lock is distinguishable from a quiet one.
    """
    try:
        from host_contract import ContractError, resolve_repository, read_lock, _sha256
    except ImportError as exc:
        log_yield_event(NAME, "unmeasured", {"reason": "lock-unreadable",
                                             "detail": "host_contract: {}".format(exc)[:200]})
        return [], "lock authority unavailable"
    try:
        identity = resolve_repository(root)
        record = read_lock(identity)
    except ContractError as exc:
        log_yield_event(NAME, "unmeasured", {"reason": "lock-unreadable",
                                             "detail": str(exc)[:200]})
        return [], "lock unreadable"
    if not record:
        return [], "no active lock"
    if record.get("source_worktree_id") != identity.get("worktree_id"):
        return [], "active lock belongs to another worktree"
    head, lock_head = identity.get("head"), record.get("head")
    if not head or not lock_head or not _is_ancestor(root, str(lock_head), str(head)):
        return [], "active lock was taken at a HEAD not on this branch"
    intact = []
    for rel, digest in (record.get("files") or {}).items():
        if not is_test_file(rel):
            continue
        absolute = os.path.join(identity["root"], *str(rel).split("/"))
        try:
            if _sha256(absolute) == digest:
                intact.append(rel)
        except OSError:
            continue
    return intact, ("lock" if intact else "active lock names no intact test file")


def _fire(src, why):
    sample = ", ".join(os.path.basename(p) for p in src[:4])
    more = "" if len(src) <= 4 else " (+{} more)".format(len(src) - 4)
    emit(NAME, [
        "uncommitted source edited this turn with no test edit this turn and no matching "
        "active TEST-LOCK ({}): {}{}".format(why, sample, more),
        "add the behavioral/regression test (red-first), commit it and /tdd-lock it, and "
        "report Tripwire N/N before calling it done — built ≠ wired ≠ tested",
    ], feedback_event="Stop")


def main():
    event = read_event()
    if event.get("stop_hook_active"):  # re-entry guard — never loop
        sys.exit(0)
    paths = changed_paths()
    if not paths:
        emit(NAME, [])
    session = session_edited_paths(event)
    turn = turn_edited_paths(event, session) if session is not None else None
    if session is None or turn is None:
        # no readable transcript: whole-tree fallback (unchanged since 1.2)
        src, tests = classify(paths)
        if src and not tests:
            _fire(src, "no readable transcript")
        emit(NAME, [])
    dirty = {os.path.realpath(p): p for p in paths}
    src, _ = classify([p for rp, p in dirty.items() if rp in turn])
    if not src:
        emit(NAME, [])
    _, tests_this_turn = classify(sorted(turn))
    _, tests_uncommitted = classify([p for rp, p in dirty.items() if rp in session])
    if tests_this_turn or tests_uncommitted:
        emit(NAME, [])
    locked, why = lock_test_evidence(project_root())
    if locked:
        emit(NAME, [])
    _fire(src, why)


if __name__ == "__main__":
    main()
