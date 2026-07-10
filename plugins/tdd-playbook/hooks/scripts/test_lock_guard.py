#!/usr/bin/env python3
"""PreToolUse(Edit|MultiEdit|Write) — enforce the TEST-LOCK (HACK_CATALOG H2 + H5).

While .claude/tdd-lock.json is active:
  - edits to any LOCKED file are blocked (H2: edit/weaken/delete the failing test);
  - edits to the VERIFIER SURFACE are blocked wholesale — conftest.py, pytest/jest/vitest
    configs (H5: exploit the harness — patching the test framework is equivalent to editing
    the test).
No lock -> exit 0, zero cost. Default mode: BLOCK (integrity hook). The unlock path is one
command with a journaled reason: bin/tdd_lock.py unlock --reason "...".
"""
import json
import os
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


def findings_for(path, lock, root):
    if not path:
        return []
    # realpath both sides — see tdd_lock.project_root (macOS /var symlink)
    ap = os.path.realpath(path if os.path.isabs(path) else os.path.join(root, path))
    rel = os.path.relpath(ap, os.path.realpath(root))
    base = os.path.basename(ap)
    if rel in lock.get("files", {}):
        return [
            "TEST-LOCK: '{}' is locked (red tests are committed and read-only during "
            "implementation) (H2)".format(rel),
            "implement the SOURCE to green; if the test itself is wrong, run: "
            "python3 <plugin>/bin/tdd_lock.py unlock --reason \"why\" (journaled, "
            "reviewed by /grade)",
        ]
    if base in _VERIFIER_BASENAMES:
        return [
            "TEST-LOCK active: '{}' is verifier surface — patching the harness is "
            "equivalent to editing the locked test (H5)".format(rel),
            "finish to green first, or unlock with a journaled reason",
        ]
    return []


def main():
    event = read_event()
    root = project_root()
    lock = active_lock(root)
    if not lock:
        sys.exit(0)
    emit(NAME, findings_for(file_path_of(event), lock, root))


if __name__ == "__main__":
    main()
