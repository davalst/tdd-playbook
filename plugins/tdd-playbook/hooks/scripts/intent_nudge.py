#!/usr/bin/env python3
"""UserPromptSubmit — re-assert the TDD Playbook on build/fix/audit intent.

Belt-and-suspenders for triggering. The skill already auto-fires on its description,
but the always-on CLAUDE.md trigger reminders DON'T reach cloud/mobile sandboxes
(~/.claude isn't mounted there). This hook injects a one-line reminder when the user's
prompt clearly signals build/fix/audit work — so the discipline travels to every surface.

Conservative: fires only on clear intent, injects ONE terse line, and is trivial to
silence (TDD_PLAYBOOK_NUDGE=off). Never blocks. Adds context via stdout (exit 0).
"""
import json
import os
import re
import sys

_INTENT_RE = re.compile(
    r"\b(build|implement|add|create|write|fix|debug|refactor|change|patch|"
    r"audit|review|investigate|diagnose|root[- ]?cause|verify|grade|test|"
    r"feature|bug|regression)\b",
    re.IGNORECASE,
)
# Already talking about the Playbook? Don't repeat ourselves.
_ALREADY_RE = re.compile(r"tdd[- ]?playbook|the tdd playbook|tripwire|red[- ]?first", re.IGNORECASE)

_REMINDER = (
    "Reminder (TDD Playbook): this looks like build/fix/audit work — apply the TDD "
    "Playbook (reviewable plan → red-first behavioral tests → edge/property → mutation "
    "on critical modules → Tripwire N/N; for audits, the claims discipline). FIRST "
    "discover and layer this repo's own testing conventions (project CLAUDE.md/AGENTS.md, "
    ".claude/skills testing addenda, docs/TESTING) on top of the universal floor."
)


def main():
    if os.environ.get("TDD_PLAYBOOK_NUDGE", "").strip().lower() == "off":
        sys.exit(0)
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)
    prompt = (event.get("prompt") or "").strip()
    # Skip trivial / short replies and prompts that already invoke the Playbook.
    if len(prompt) < 12 or _ALREADY_RE.search(prompt) or not _INTENT_RE.search(prompt):
        sys.exit(0)
    out = {
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": _REMINDER,
        }
    }
    sys.stdout.write(json.dumps(out))
    sys.exit(0)


if __name__ == "__main__":
    main()
