#!/usr/bin/env python3
"""PostToolUse(Edit|MultiEdit|Write) — a test that CLAIMS exhaustiveness must say how it
could FAIL (§12/§6, v1.28; HACK_CATALOG H11).

A test named `test_every_deletion_goes_through_the_one_seam` is read by its author, its
reviewer and every later session as the guarantee its name states. It usually is not. The
motivating defect: that exact test WAS exhaustive over deletions and structurally blind to
a code path that deleted nothing — it could not have failed on the real bug, and three
sessions in a row cited it as proof the property held.

The rule this reminds you of: when a test's name or message says *every / all / no other /
exhaustive*, state in ONE line what a violating case would look like and how this test
would see it. If you cannot write that line, the test asserts your INVENTORY (the cases you
listed) rather than the property (that no others exist) — a real and much weaker claim,
which is fine as long as the name says so.

ADVISORY (warn) by design: exhaustiveness claims are often correct, and the fix is one
sentence, not a redesign. The guard's job is to make the sentence get written.

CALIBRATED IN BOTH DIRECTIONS (the v1.28 house bar, §13): it must flag a bare claim AND stay
silent when the falsifier line is present, on non-test files, and on the ordinary uses of
these very common words — `assert all(...)`, `for x in all_items`, a variable named
`all_handlers`. Only a TEST NAME or an assertion/case MESSAGE counts as a claim, because
those are the strings a later reader mistakes for the guarantee.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit, is_test_file, edit_pairs, file_path_of  # noqa: E402

NAME = "exhaustive"

# Claim vocabulary: strong universal/closure words only. "only"/"any" are deliberately out
# (too common, too weak a signal) — this is a reminder, not a dragnet.
_TOKENS = r"every|all|exhaustive|exhaustively|no_other|no\s+other|nothing_else|nothing\s+else|none_of|none\s+of"

# A claim in a TEST NAME: python `def test_*`, or a JS/TS `it(...)`/`test(...)` title.
_DEF = re.compile(r"^\s*(?:async\s+)?def\s+(test_\w+)", re.MULTILINE)
_JS_TITLE = re.compile(r"""^\s*(?:it|test)\s*\(\s*["'`]([^"'`]{4,})["'`]""", re.MULTILINE)
# A claim in a MESSAGE: the human-facing string on an assert / failure report.
_MSG = re.compile(r"""(?:assert[^\n]*?|check\s*\([^\n]*?)["']([^"'\n]{8,})["']""")
_NAME_TOKEN = re.compile(r"(?:^|_)(?:%s)(?:_|$)" % _TOKENS.replace(r"\s+", "_"))
_TEXT_TOKEN = re.compile(r"\b(?:%s)\b" % _TOKENS, re.IGNORECASE)

# The one line that discharges the claim: what a violating case looks like / how this sees it.
_FALSIFIER = re.compile(
    r"violat|counterexample|counter-example|falsif|would\s+(?:catch|fail|see|flag)"
    r"|fails\s+if|red\s+if|breaks\s+if|misses\s+nothing\s+because",
    re.IGNORECASE)


def claims(text):
    """Return the exhaustiveness claims a later reader would take as the guarantee."""
    text = text or ""
    out = []
    for name in _DEF.findall(text):
        if _NAME_TOKEN.search(name):
            out.append(name)
    for title in _JS_TITLE.findall(text):
        if _TEXT_TOKEN.search(title):
            out.append(title.strip())
    for msg in _MSG.findall(text):
        if _TEXT_TOKEN.search(msg):
            out.append(msg.strip())
    return out


def findings(old, new):
    fresh = [c for c in claims(new) if c not in claims(old)]
    if not fresh or _FALSIFIER.search(new or ""):
        return []
    return [
        "this test CLAIMS exhaustiveness but says nothing about how it could fail: {}"
        .format("; ".join('"%s"' % c for c in fresh[:3])),
        "add ONE line — what a violating case looks like, and how this test would see it. "
        "If you can't write it, the test asserts your INVENTORY, not the property; rename it "
        "to the claim it actually makes (§12). A parity test named 'every deletion goes "
        "through the one seam' was exhaustive over deletions and blind to the path that "
        "deleted nothing — it could not have failed on the real bug, and three sessions read "
        "the name as the guarantee.",
    ]


def main():
    event = read_event()
    path = file_path_of(event)
    if not is_test_file(path):
        emit(NAME, [])
    pairs = edit_pairs(event)
    if pairs:
        lines = []
        for old, new in pairs:
            lines = findings(old, new)
            if lines:
                break
    else:  # Write: no old side to diff — treat full content as added
        lines = findings("", (event.get("tool_input", {}) or {}).get("content", ""))
    if lines:
        emit(NAME, lines + ["file: " + os.path.basename(path)])
    emit(NAME, [])


if __name__ == "__main__":
    main()
