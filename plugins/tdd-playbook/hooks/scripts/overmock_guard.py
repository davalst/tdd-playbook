#!/usr/bin/env python3
"""PostToolUse(Edit|MultiEdit|Write) — flag NET-NEW MOCKS added to a test (HACK_CATALOG H3).

Over-mocking is the most common agent test-weakening in the wild: agents add mocks in 36%
of test commits vs 26% for humans (MSR 2026, arXiv 2602.00409), and a mock can replace the
very behavior the test exists to verify. This is ADVISORY by design (default warn, not
block): mocks are often legitimate — the Playbook rule is each new mock carries a one-line
justification (§1), and this guard is the reminder that makes that rule fire.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit, is_test_file, edit_pairs, file_path_of  # noqa: E402

NAME = "overmock"

_MOCK_RE = re.compile(
    r"\bMagicMock\b|\bAsyncMock\b|\bmock\.patch\b|\bpatch\s*\(|@patch\b|\bcreate_autospec\b"
    r"|\bmonkeypatch\.set(?:attr|item|env)\b|\bmocker\.patch\b"
    r"|\bjest\.mock\s*\(|\bjest\.spyOn\s*\(|\bvi\.mock\s*\(|\bvi\.spyOn\s*\(|\bsinon\.(?:stub|mock|fake)\b"
)


def _count(text):
    return len(_MOCK_RE.findall(text or ""))


def main():
    event = read_event()
    path = file_path_of(event)
    if not is_test_file(path):
        emit(NAME, [])
    pairs = edit_pairs(event)
    if pairs:
        old_n = sum(_count(o) for o, _n in pairs)
        new_n = sum(_count(n) for _o, n in pairs)
    else:  # Write: no old side to diff — treat full content as added
        ti = event.get("tool_input", {}) or {}
        old_n, new_n = 0, _count(ti.get("content", ""))
    if new_n > old_n:
        emit(NAME, [
            "net-new mock(s) in a test: {} -> {} (H3 — over-mocking is the most common "
            "agent weakening; agents mock ~36% vs humans ~26%)".format(old_n, new_n),
            "justify each new mock in one line: what real behavior does it stand in for, "
            "and where IS that behavior tested for real?",
            "file: " + os.path.basename(path),
        ])
    emit(NAME, [])


if __name__ == "__main__":
    main()
