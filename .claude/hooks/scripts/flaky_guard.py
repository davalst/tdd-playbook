#!/usr/bin/env python3
"""PostToolUse(Edit|MultiEdit|Write) — flag NON-DETERMINISM newly added to a test.

Enforces Playbook §7 "deterministic by construction: no sleep/real clock/random/network."
Warn-first. On a test file, flags newly introduced:
  - sleeps / hard waits (time.sleep, await sleep, Thread.sleep);
  - real wall-clock (datetime.now, time.time, Date.now) without injection;
  - unseeded randomness (random., Math.random, np.random without a seed nearby);
  - live network (requests./httpx./fetch(/axios.) inside a test).
Looks at ADDED text only (new side of an edit, or full content of a Write), so a test
that already had a justified pattern isn't re-flagged on unrelated edits.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit, is_test_file, edit_pairs, file_path_of  # noqa: E402

NAME = "flaky"

_PATTERNS = [
    (re.compile(r"\btime\.sleep\s*\(|\bThread\.sleep\s*\(|await\s+sleep\s*\(|\bsetTimeout\s*\("),
     "sleep / hard wait — use auto-waiting or polling assertions, not real delays"),
    (re.compile(r"\bdatetime\.now\s*\(|\bdate\.today\s*\(|\btime\.time\s*\(|\bDate\.now\s*\("),
     "real wall-clock — inject/freeze time instead (a clock fixture)"),
    (re.compile(r"\brandom\.\w+\s*\(|\bMath\.random\s*\(|\bnp\.random\.|\buuid4\s*\("),
     "randomness — seed it or inject the value so the test is reproducible"),
    (re.compile(r"\brequests\.\w+\s*\(|\bhttpx\.\w+\s*\(|\burllib\b|\bfetch\s*\(|\baxios\."),
     "live network call in a test — stub the HTTP layer"),
]
# Per-category suppressors — a suppressor must actually address ITS category. (The old
# single regex let any `@pytest.fixture`/`monkeypatch` in the block silence a wall-clock
# warning — a fixture proves nothing about time control.)
_RAND_SUPPRESS = re.compile(r"seed\s*\(|random_state|\bRandom\s*\(|derandomize")
_CLOCK_SUPPRESS = re.compile(
    r"freeze_time|freezegun|FakeClock|fake_clock|frozen_time|mock_time"
    r"|monkeypatch\.setattr\s*\([^)]*(?:time|datetime|clock)|fakeTimers|useFakeTimers"
)


def analyze(added):
    """Findings for one block of ADDED text."""
    if not added:
        return []
    findings = []
    for rx, msg in _PATTERNS:
        if rx.search(added):
            # suppress only when the SAME block shows control of that specific category
            if "randomness" in msg and _RAND_SUPPRESS.search(added):
                continue
            if "wall-clock" in msg and _CLOCK_SUPPRESS.search(added):
                continue
            findings.append(msg)
    return findings


def added_text(event):
    """The text introduced by this tool call (new sides / Write content)."""
    pairs = edit_pairs(event)
    if pairs:
        return "\n".join(new for _old, new in pairs)
    ti = event.get("tool_input", {}) or {}
    return ti.get("content", "") or ""  # Write


def main():
    event = read_event()
    path = file_path_of(event)
    if not is_test_file(path):
        emit(NAME, [])
    findings = []
    seen = set()
    for f in analyze(added_text(event)):
        if f not in seen:
            seen.add(f)
            findings.append(f)
    if findings:
        findings.append("file: {}".format(os.path.basename(path)))
    emit(NAME, findings)


if __name__ == "__main__":
    main()
