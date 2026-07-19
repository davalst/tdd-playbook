#!/usr/bin/env python3
"""PostToolUse(Write) — flag an assertion-free "vibe" test file (HACK_CATALOG H4).

A test that executes code but asserts nothing is coverage without outcome — the
100%-coverage / ~0 mutation-score pathology (arXiv 2506.02954). The test_weakening
guard catches assertions *dropped* from an existing file (it needs an old side to
diff); it is structurally blind to a brand-NEW test file that never had an assertion
to begin with. This guard closes that one crisp case: a Write of a test file that
DEFINES test functions but contains ZERO assertions.

ADVISORY by design (default warn, not block): a suite that asserts through a shared
helper has no literal assertion and would false-positive, so this must never wedge a
session — it is the nudge that makes "assert an outcome, don't just run code" fire.
Deliberately Write-only: on an Edit we see a fragment, not the whole file, so a
zero-assertion verdict would be unreliable — assertion DROPS on edits are the
weakening guard's job (H2), not this one's.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit, is_test_file, file_path_of  # noqa: E402

NAME = "vibetest"

# A test DECLARATION across the common stacks (pytest/unittest, jest/vitest, go, rust).
_TESTDECL_RE = re.compile(
    r"\bdef\s+test\w*\s*\("            # pytest / unittest methods and functions
    r"|\bclass\s+Test\w*"             # unittest TestCase classes
    r"|\b(?:it|test)\s*\(\s*['\"]"    # jest / vitest / mocha
    r"|\bfunc\s+Test\w*\s*\("         # go
    r"|#\[(?:tokio::)?test\]"         # rust
)
# An ASSERTION across the same stacks. assertEqual/assertRaises/etc. are \bassert\w+\(;
# the bare `assert` statement and rust `assert!`/`assert_eq!` are \bassert\b; context
# managers (pytest.raises / assertRaises) and matcher styles count as real assertions.
_ASSERT_RE = re.compile(
    r"\bassert\b|\bassert\w+\s*\(|\bexpect\s*\(|\bpytest\.raises\b|\.raises\s*\(|\bshould\b"
    r"|\brequire\.(?:Error|NoError|Equal|True|Nil|NotNil)|\bt\.(?:Error|Fatal|Errorf|Fatalf)"
)


def main():
    event = read_event()
    ti = event.get("tool_input", {}) or {}
    # Write-only: we need the WHOLE file content to trust a zero-assertion verdict.
    is_write = "content" in ti and "old_string" not in ti and "edits" not in ti
    path = file_path_of(event)
    if not (is_write and is_test_file(path)):
        emit(NAME, [])
    content = ti.get("content", "") or ""
    n_tests = len(_TESTDECL_RE.findall(content))
    n_assert = len(_ASSERT_RE.findall(content))
    if n_tests >= 1 and n_assert == 0:
        emit(NAME, [
            "new test file defines {} test(s) but contains ZERO assertions (H4 — an "
            "assertion-free 'vibe' test executes code and verifies nothing; the "
            "100%-coverage / ~0 mutation-score pathology)".format(n_tests),
            "assert on an OUTCOME, not just that the code ran. If you assert through a "
            "shared helper, this is a false positive — name the helper so the next reader "
            "(and mutation testing) can see the check",
            "file: " + os.path.basename(path),
        ])
    emit(NAME, [])


if __name__ == "__main__":
    main()
