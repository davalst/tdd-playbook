#!/usr/bin/env python3
"""Stop — remind to close the Tripwire loop when source changed without tests.

Enforces Playbook §6 "Tripwire last" + §1 "every bug gets a regression test FIRST".
When a turn ends, if the working tree has SOURCE changes but NO test changes, surface a
reminder to add the behavioral/regression test and report Tripwire N/N. Warn-first.

Cheap + language-agnostic: uses `git status --porcelain`, classifies paths as test vs
source, and only fires when source moved alone. When the Stop event carries a
transcript_path, the check narrows to THE SESSION'S OWN edits (Edit/Write/MultiEdit paths
mined from the transcript) — so a pre-existing test change elsewhere in the tree no longer
silences a source-only session. Falls back to whole-tree when no transcript is readable.
Silent when: not a git repo, the Stop is already a re-entry (avoid loops), or git is
unavailable.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit, is_test_file  # noqa: E402

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
        if is_test_file(p):
            tests.append(p)
        elif low.endswith(_CODE_EXT) and not low.endswith(_DOC_OR_CONFIG):
            src.append(p)
    return src, tests


def session_edited_paths(event):
    """Paths this session actually edited, mined from the transcript. None = unavailable."""
    tp = event.get("transcript_path")
    if not tp or not os.path.isfile(tp):
        return None
    paths = set()
    try:
        with open(tp, errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line or '"tool_use"' not in line:
                    continue
                try:
                    obj = json.loads(line)
                except ValueError:
                    continue
                stack = [obj]
                while stack:
                    cur = stack.pop()
                    if isinstance(cur, dict):
                        if (cur.get("type") == "tool_use"
                                and cur.get("name") in ("Edit", "Write", "MultiEdit")):
                            fp = (cur.get("input") or {}).get("file_path")
                            if fp:
                                # realpath, not abspath: macOS tempdirs are symlinked
                                # (/var -> /private/var), and a mismatch here silently
                                # empties the session intersection below
                                paths.add(os.path.realpath(fp))
                        stack.extend(cur.values())
                    elif isinstance(cur, list):
                        stack.extend(cur)
    except OSError:
        return None
    return paths or None


def main():
    event = read_event()
    if event.get("stop_hook_active"):  # re-entry guard — never loop
        sys.exit(0)
    paths = changed_paths()
    if not paths:
        emit(NAME, [])
    session = session_edited_paths(event)
    if session is not None:
        # narrow to what THIS session touched (still gated on the tree actually being dirty)
        paths = [p for p in paths if os.path.realpath(p) in session]
        if not paths:
            emit(NAME, [])
    src, tests = classify(paths)
    if src and not tests:
        sample = ", ".join(os.path.basename(p) for p in src[:4])
        more = "" if len(src) <= 4 else " (+{} more)".format(len(src) - 4)
        emit(NAME, [
            "source changed with NO test change this turn: {}{}".format(sample, more),
            "add the behavioral/regression test (red-first) and report Tripwire N/N "
            "before calling it done — built ≠ wired ≠ tested",
        ])
    emit(NAME, [])


if __name__ == "__main__":
    main()
