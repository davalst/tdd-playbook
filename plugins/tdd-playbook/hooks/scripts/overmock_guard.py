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

# create_autospec is deliberately NOT in this set (v1.25): it is the PRESCRIBED
# mechanical check for §1's seam-fabrication rule (a missing production attribute
# RAISES) — counting it as mock noise would punish exactly the right move.
_MOCK_RE = re.compile(
    r"\bMagicMock\b|\bAsyncMock\b|\bmock\.patch\b|\bpatch\s*\(|@patch\b"
    r"|\bmonkeypatch\.set(?:attr|item|env)\b|\bmocker\.patch\b"
    r"|\bjest\.mock\s*\(|\bjest\.spyOn\s*\(|\bvi\.mock\s*\(|\bvi\.spyOn\s*\(|\bsinon\.(?:stub|mock|fake)\b"
)

# Seam fabrication (H9, v1.25 — the §1 rule's reminder): a double that GRAFTS a callable
# seam via SimpleNamespace is the shape that kept a production integration bug green for
# months (production lacked the very method the fixture supplied). Conservative on
# purpose: only callable members (lambda) — data-only SimpleNamespace is legitimate.
_SEAM_RE = re.compile(r"\bSimpleNamespace\s*\([^)]*=\s*lambda\b")


def _count(text):
    return len(_MOCK_RE.findall(text or ""))


def _seam_count(text):
    return len(_SEAM_RE.findall(text or ""))


def main():
    event = read_event()
    path = file_path_of(event)
    if not is_test_file(path):
        emit(NAME, [])
    pairs = edit_pairs(event)
    if pairs:
        old_n = sum(_count(o) for o, _n in pairs)
        new_n = sum(_count(n) for _o, n in pairs)
        old_s = sum(_seam_count(o) for o, _n in pairs)
        new_s = sum(_seam_count(n) for _o, n in pairs)
    else:  # Write: no old side to diff — treat full content as added
        ti = event.get("tool_input", {}) or {}
        old_n, new_n = 0, _count(ti.get("content", ""))
        old_s, new_s = 0, _seam_count(ti.get("content", ""))
    lines = []
    if new_n > old_n:
        lines += [
            "net-new mock(s) in a test: {} -> {} (H3 — over-mocking is the most common "
            "agent weakening; agents mock ~36% vs humans ~26%)".format(old_n, new_n),
            "justify each new mock in one line: what real behavior does it stand in for, "
            "and where IS that behavior tested for real?",
        ]
    if new_s > old_s:
        lines += [
            "fabricated-seam double (H9): a SimpleNamespace grafting a callable seam — a "
            "double may fake BEHAVIOR, never supply an attribute/method production lacks "
            "(§1); if the double needs it to work, production needs it to work",
            "prefer create_autospec/equivalent so a missing production seam RAISES",
        ]
    if lines:
        emit(NAME, lines + ["file: " + os.path.basename(path)])
    emit(NAME, [])


if __name__ == "__main__":
    main()
