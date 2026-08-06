#!/usr/bin/env python3
"""PreToolUse(Bash) — a verifier's exit code must not be swallowed by a pipe (§4a, v1.28).

`cmd | tail` reports TAIL's exit status, not cmd's. So this reads as a passing gate:

    sh scripts/civerd_gate.sh | tail -2   ;   echo "gate: $?"      # always 0

and the gate can be scarlet red while the session records success. §4a already names the
class — "a discarded exit code is a discarded truth" — but naming it did not stop it:

  - 2026-08-05, this repo: I gated a commit chain on a piped gate run, read tail's 0, and
    pushed a commit the engine judged RED. Twice in two days.
  - 2026-08-06, CIVerd engine: a pytest exit masked by `| tail` in their runner.

Two independent instances in two days, in the two codebases that check each other — which
is the argument for a shared mechanical guard rather than two local fixes. WARN, not block:
piping a verifier is legitimate when you have already captured the code, and this hook
cannot always see that you did.

CALIBRATED IN BOTH DIRECTIONS (the v1.28 house bar): it must flag the masked case AND stay
silent on the honest ones — `set -o pipefail`, `rc=$?` captured before the pipe, redirect
to a file, or an exit code consumed directly by `||`/`&&`. Non-verifier pipes are none of
its business.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit  # noqa: E402

NAME = "exitcode"

# Commands whose exit code is a VERDICT — the ones where masking changes a decision.
_VERIFIER = re.compile(
    r"(?:civerd_gate\.sh|run_calibration\.py|check_scoreboard_integrity\.py|ledger\.py"
    r"|capability_registry\.py|dataflow_sweeps\.py|verify_verdict\.py|release_verify\.py"
    r"|verify_citations\.py|install_into_repo\.py|test_harness\.py"
    r"|\bpytest\b|\bunittest\b|tests/test_[A-Za-z0-9_]+\.py"
    r"|\bnpm\s+(?:run\s+)?test\b|\bgo\s+test\b|\bcargo\s+test\b|\bvitest\b|\bjest\b)")
# honest handling of a piped exit code
_PIPEFAIL = re.compile(r"set\s+-[a-zA-Z]*o\s+pipefail|set\s+-o\s+pipefail")
# `cmd | ...` but NOT `cmd || ...`
_PIPE = re.compile(r"(?<!\|)\|(?!\|)")


def _statements(cmd):
    """Split on statement separators, keeping pipelines intact."""
    return [s for s in re.split(r";|&&|\|\||\n", cmd) if s.strip()]


def findings(cmd):
    if not cmd or _PIPEFAIL.search(cmd):
        return []
    out = []
    for stmt in _statements(cmd):
        if not _PIPE.search(stmt):
            continue
        head = _PIPE.split(stmt)[0]
        if not _VERIFIER.search(head):
            continue
        out.append(
            "a verifier's exit code is being swallowed by a pipe: `{}` — the status you "
            "get back is the LAST command's, not the checker's, so a RED gate reads as 0"
            .format(stmt.strip()[:110]))
        out.append(
            "capture it first (`cmd > /tmp/out 2>&1; rc=$?; grep ... /tmp/out`), or set "
            "`set -o pipefail`, or consume it directly (`cmd || exit 1`). §4a: a discarded "
            "exit code is a discarded truth — this exact shape pushed a repo-red commit on "
            "2026-08-05 and masked a pytest failure in the CIVerd runner on 2026-08-06.")
        break                       # one finding per command is enough to stop and fix
    return out


def main():
    event = read_event()
    if event.get("tool_name") != "Bash":
        emit(NAME, [])
    emit(NAME, findings((event.get("tool_input", {}) or {}).get("command", "")))


if __name__ == "__main__":
    main()
