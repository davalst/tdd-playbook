#!/usr/bin/env python3
"""PostToolUse(Edit|MultiEdit|Write) — flag edits that WEAKEN a test.

Enforces Playbook §1 "never weaken/delete a test to pass" (HACK_CATALOG H2/H5) — the
honor-system seam. INTEGRITY hook: defaults to BLOCK. Detects, on a test file:
  - assertions removed (fewer assert/expect after the edit) (H2);
  - a skip / xfail / focus marker introduced (hides tests from the run) (H2);
  - an assertion neutered into a tautology (assert True, ...) (H2);
  - an exit call added — sys.exit(0)/os._exit in a test or conftest fakes a passing
    suite; observed in production RL (H5). Also checked on conftest.py (verifier surface).
Heuristic by design: demote to warn with TDD_PLAYBOOK_HOOK_TESTWEAKEN=warn if it bites.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit, is_test_file, edit_pairs, file_path_of  # noqa: E402

NAME = "testweaken"

_ASSERT_RE = re.compile(
    r"\bassert\b|\bexpect\s*\(|\bassertEqual\b|\bassertTrue\b|\bassertFalse\b"
    r"|\bassertRaises\b|\bassertIs\b|\bassertIn\b|\bshould\b|\brequire\.|\bt\.(?:Error|Fatal)"
)
_SKIP_RE = re.compile(
    r"@pytest\.mark\.skip|@pytest\.mark\.xfail|pytest\.skip\s*\(|@unittest\.skip"
    r"|unittest\.skip|\bskip\s*=\s*True|\.skip\s*\(|\.only\s*\(|\bxit\s*\(|\bxdescribe\s*\("
    r"|\bfit\s*\(|\bfdescribe\s*\(|t\.Skip\s*\("
)
_TAUTOLOGY_RE = re.compile(
    r"assert\s+True\b|assert\s+1\b(?!\d)|expect\s*\(\s*true\s*\)\s*\.toBe\s*\(\s*true\s*\)"
    r"|assertTrue\s*\(\s*True\s*\)|assert\s+not\s+False\b"
)
_EXIT_RE = re.compile(r"\bsys\.exit\s*\(|\bos\._exit\s*\(|\bprocess\.exit\s*\(")


def _count(rx, text):
    return len(rx.findall(text or ""))


def analyze(old, new):
    """Return a list of finding strings for one (old,new) edit pair."""
    findings = []
    a_old, a_new = _count(_ASSERT_RE, old), _count(_ASSERT_RE, new)
    if a_new < a_old:
        findings.append(
            "assertions dropped {}→{} — confirm you didn't weaken coverage "
            "to go green (H2)".format(a_old, a_new)
        )
    if _count(_SKIP_RE, new) > _count(_SKIP_RE, old):
        findings.append("a skip/xfail/focus marker was added — the test now hides from the run (H2)")
    if _count(_TAUTOLOGY_RE, new) > _count(_TAUTOLOGY_RE, old):
        findings.append("an assertion was neutered into a tautology (asserts nothing real) (H2)")
    if _count(_EXIT_RE, new) > _count(_EXIT_RE, old):
        findings.append(
            "an exit call (sys.exit/os._exit/process.exit) was added to test/verifier code — "
            "exiting early fakes a passing suite (H5)"
        )
    return findings


def _is_verifier_surface(path):
    return os.path.basename(path or "").lower() == "conftest.py"


def main():
    event = read_event()
    path = file_path_of(event)
    if not (is_test_file(path) or _is_verifier_surface(path)):
        emit(NAME, [])
    findings = []
    for old, new in edit_pairs(event):
        findings.extend(analyze(old, new))
    # de-dup while preserving order
    seen, uniq = set(), []
    for f in findings:
        if f not in seen:
            seen.add(f)
            uniq.append(f)
    if uniq:
        uniq.append("file: {}".format(os.path.basename(path)))
    emit(NAME, uniq)


if __name__ == "__main__":
    main()
