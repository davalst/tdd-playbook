#!/usr/bin/env python3
"""Pre/PostToolUse — block agent snapshot re-approval (HACK_CATALOG H5).

Blind snapshot updating is the cheapest way for an agent to "fix" a failing UI/output test:
re-approve the new (broken) output as the expected one. Snapshot diffs are HUMAN review
artifacts (Playbook §1/§7). Default mode: BLOCK.

Covers both channels:
  - Bash (PreToolUse): snapshot-update invocations — jest/vitest `-u`/`--update-snapshots`/
    `--updateSnapshot`, playwright `--update-snapshots`, pytest `--snapshot-update`/
    `--force-regen` (syrupy/pytest-regressions), `UPDATE_SNAPSHOTS=`/`SNAPSHOT_UPDATE=` envs.
  - Edit/Write (PostToolUse warns too late — register Pre): direct edits to `.snap` files or
    anything under `__snapshots__/` — hand-editing expected output IS re-approval.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit, file_path_of  # noqa: E402

NAME = "snapshotguard"

_BASH_RE = re.compile(
    r"--update-?snapshots?\b|--updateSnapshot\b|--snapshot-update\b|--force-regen\b"
    r"|\bUPDATE_SNAPSHOTS?\s*=|\bSNAPSHOT_UPDATE\s*="
    r"|\b(?:jest|vitest)\b[^\n|;&]*\s-u\b",
)


def snapshot_path(path):
    p = (path or "").replace("\\", "/")
    return p.endswith(".snap") or "/__snapshots__/" in p or p.endswith(".ambr")


def main():
    event = read_event()
    tool = event.get("tool_name", "")
    if tool == "Bash":
        cmd = (event.get("tool_input", {}) or {}).get("command", "")
        if _BASH_RE.search(cmd or ""):
            emit(NAME, [
                "snapshot auto-update invocation detected (H5 — re-approving output is "
                "the cheapest fake-green)",
                "snapshot diffs are HUMAN review artifacts: show the diff and ask; never "
                "auto-approve to go green",
            ])
        emit(NAME, [])
    path = file_path_of(event)
    if snapshot_path(path):
        emit(NAME, [
            "direct edit of a snapshot file: {} (H5 — hand-editing expected output IS "
            "re-approval)".format(os.path.basename(path)),
            "change the CODE or get human approval for the new expected output",
        ])
    emit(NAME, [])


if __name__ == "__main__":
    main()
