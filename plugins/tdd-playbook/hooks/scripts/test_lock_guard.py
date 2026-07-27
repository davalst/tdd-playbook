#!/usr/bin/env python3
"""PreToolUse(Edit|MultiEdit|Write + Bash) — enforce the TEST-LOCK (HACK_CATALOG H2 + H5).

While .claude/tdd-lock.json is active this guard defends four surfaces against BOTH the
structured-edit channel AND the shell channel (audit finding F1: the Edit-only guard was
blind to `sed -i` / `> file` / `git checkout -- test` / inline-python writes — the shell IS
the bypass a capable model reaches for):
  - LOCKED test files (H2: edit/weaken/delete the failing test);
  - the VERIFIER SURFACE — conftest.py, pytest/jest/vitest configs (H5: patch the harness
    instead of the test);
  - the LOCK'S OWN STATE — tdd-lock.json / its journal / tdd-pending-red.json (F2: deleting
    the lock file is a silent unlock that skips the journaled reason);
  - the ENFORCEMENT itself — the guard scripts, hooks.json, settings.json (disabling the hook
    is the quietest possible test-weakening; §10 "workflow files are risky paths").
Reads are always fine (you MUST be able to run the locked tests) — only WRITE-shaped
operations are blocked. No lock -> exit 0, zero cost. Default mode: BLOCK (integrity hook).
The one sanctioned exit is a journaled reason: bin/tdd_lock.py unlock --reason "...". This
guard is heuristic on the shell side (it catches the common write verbs, not every possible
command) — that is honest, and the deeper backstop is the independent verifier (memrebel/
CIVerd), not a perfect shell parser.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit, file_path_of  # noqa: E402

NAME = "testlock"

_VERIFIER_BASENAMES = {
    "conftest.py", "pytest.ini", "tox.ini", "setup.cfg",
    "jest.config.js", "jest.config.ts", "jest.config.mjs", "jest.config.cjs",
    "vitest.config.js", "vitest.config.ts", "vitest.config.mts",
    "playwright.config.js", "playwright.config.ts",
    ".mocharc.yml", ".mocharc.json", "karma.conf.js",
}
# F2 — the lock's own state; never legitimately hand-edited (tdd_lock.py owns them).
_LOCK_STATE_BASENAMES = {
    "tdd-lock.json", "tdd-lock-journal.jsonl", "tdd-pending-red.json",
}
# F1-extension — disabling the enforcement is editing the test by another name.
_GUARD_BASENAMES = {
    "test_lock_guard.py", "snapshot_guard.py", "test_weakening_guard.py",
    "flaky_guard.py", "overmock_guard.py", "red_lock.py", "_common.py",
    "hooks.json", "settings.json", "settings.local.json",
}

# write-shaped shell signals (reads are intentionally excluded)
_WRITE_VERB = re.compile(
    r"\b(?:sed\s+-i\S*|perl\s+-i\S*|rm|rmdir|mv|cp|tee|truncate|install|ln|dd|shred)\b")
_GIT_REVERT = re.compile(r"\bgit\s+(?:checkout|restore)\b")
_GIT_REVERT_ALL = re.compile(r"\bgit\s+(?:checkout|restore)\b[^;&|\n]*?(?:--\s+)?\.(?:\s|$)")
_INLINE_WRITE = re.compile(r"open\s*\([^)]*['\"](?:w|a|x|r\+|w\+)")  # python open(...,'w')
_SEP = re.compile(r"[;&|\n]| && | \|\| ")


def project_root():
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def active_lock(root):
    path = os.path.join(root, ".claude", "tdd-lock.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return None


def _classify_path(path, lock, root):
    """(kind, rel) for a path that touches a protected surface, else (None, None)."""
    if not path:
        return None, None
    ap = os.path.realpath(path if os.path.isabs(path) else os.path.join(root, path))
    rel = os.path.relpath(ap, os.path.realpath(root))
    base = os.path.basename(ap)
    if rel in lock.get("files", {}):
        return "locked", rel
    if base in _LOCK_STATE_BASENAMES:
        return "lockstate", rel
    if base in _VERIFIER_BASENAMES:
        return "verifier", rel
    if base in _GUARD_BASENAMES:
        return "guard", rel
    return None, None


def _msg(kind, name):
    unlock = ("your ONE sanctioned exit is a journaled reason: python3 <plugin>/bin/"
              "tdd_lock.py unlock --reason \"why\" (reviewed by /grade) — do NOT write around "
              "the guard")
    if kind == "locked":
        return ["TEST-LOCK: '{}' is a locked red test — read-only during implementation "
                "(H2). Running it is fine; MODIFYING it is the move the lock exists to "
                "stop.".format(name), unlock]
    if kind == "lockstate":
        return ["TEST-LOCK: '{}' is the lock's own STATE (F2) — editing/deleting it is a "
                "silent unlock that skips the journaled reason.".format(name), unlock]
    if kind == "verifier":
        return ["TEST-LOCK active: '{}' is verifier surface (conftest/runner config) — "
                "patching the harness while tests are locked equals editing the locked "
                "test (H5).".format(name), unlock]
    return ["TEST-LOCK active: '{}' is enforcement (a guard hook / settings) — disabling "
            "the guard is the quietest test-weakening (§10 risky path).".format(name), unlock]


def edit_findings(event, lock, root):
    kind, rel = _classify_path(file_path_of(event), lock, root)
    return _msg(kind, rel) if kind else []


def _cmd_writes(cmd, needle):
    # redirection target — the needle may sit at the end of a dir/path after `>`
    if re.search(r"(?:>>?|>\|)\s*['\"]?[^\s'\";|&]*" + re.escape(needle), cmd):
        return True
    for rx in (_WRITE_VERB, _GIT_REVERT):                            # verb + path in same cmd
        for m in rx.finditer(cmd):
            if needle in _SEP.split(cmd[m.start():], 1)[0]:
                return True
    if needle in cmd and _INLINE_WRITE.search(cmd):                  # python open(path,'w')
        return True
    return False


def _needles(lock):
    out = []
    for rel in lock.get("files", {}):
        out.append((rel, "locked"))
        b = os.path.basename(rel)
        if b != rel:
            out.append((b, "locked"))
    for b in sorted(_LOCK_STATE_BASENAMES):
        out.append((b, "lockstate"))
    for b in sorted(_VERIFIER_BASENAMES):
        out.append((b, "verifier"))
    for b in sorted(_GUARD_BASENAMES):
        out.append((b, "guard"))
    return out


def bash_findings(cmd, lock, root):
    if not cmd:
        return []
    for needle, kind in _needles(lock):
        if _cmd_writes(cmd, needle):
            return _msg(kind, needle)
    if lock.get("files") and _GIT_REVERT_ALL.search(cmd):  # `git checkout .` reverts locked tests
        return _msg("locked", "<all tracked files: git revert>")
    return []


def main():
    event = read_event()
    root = project_root()
    lock = active_lock(root)
    if not lock:
        sys.exit(0)
    if event.get("tool_name") == "Bash":
        cmd = (event.get("tool_input", {}) or {}).get("command", "")
        emit(NAME, bash_findings(cmd, lock, root))
    else:
        emit(NAME, edit_findings(event, lock, root))


if __name__ == "__main__":
    main()
