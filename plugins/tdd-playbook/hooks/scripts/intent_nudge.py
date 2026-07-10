#!/usr/bin/env python3
"""UserPromptSubmit — re-assert the TDD Playbook on build/fix/audit intent.

Belt-and-suspenders for triggering. The skill already auto-fires on its description,
but the always-on CLAUDE.md trigger reminders DON'T reach cloud/mobile sandboxes
(~/.claude isn't mounted there). This hook injects a one-line reminder when the user's
prompt clearly signals build/fix/audit work — so the discipline travels to every surface.

Conservative: fires only on clear intent, injects ONE terse line, and is trivial to
silence (TDD_PLAYBOOK_NUDGE=off). Never blocks. Adds context via stdout (exit 0).

v1.6 anti-tax rules (origin: a downstream repo measured this hook firing TWICE on every
message — plugin registration + the vendored settings.json copy — and on meta-discussions):
  - RUNTIME SENTINEL DEDUPE: duplicate registrations of this script for the same prompt
    collapse to ONE reminder (an O_CREAT|O_EXCL per-prompt sentinel; the race loser stays
    silent). Works on every surface, regardless of install topology.
  - TIME DAMPING: once fired, stay quiet for TDD_PLAYBOOK_NUDGE_INTERVAL seconds per
    session (default 1800; "0" disables damping, dedupe still applies). One reminder per
    working stretch, not one per message.
  - META-EXCLUSION: opinion/decision questions ("should we…", "what do you think…") are
    not build work — no reminder, even when they contain intent verbs.
State lives in TDD_PLAYBOOK_NUDGE_STATE_DIR (default: the system temp dir). All state
handling FAILS OPEN: if the sentinel machinery breaks, the nudge fires rather than dying —
an occasional double reminder beats a silent discipline outage.
"""
import hashlib
import json
import os
import re
import sys
import tempfile
import time

_INTENT_RE = re.compile(
    r"\b(build|implement|add|create|write|fix|debug|refactor|change|patch|"
    r"audit|review|investigate|diagnose|root[- ]?cause|verify|grade|test|"
    r"feature|bug|regression)\b",
    re.IGNORECASE,
)
# Already talking about the Playbook? Don't repeat ourselves.
_ALREADY_RE = re.compile(r"tdd[- ]?playbook|the tdd playbook|tripwire|red[- ]?first", re.IGNORECASE)
# Meta-discussion, not build work: the user is asking for an opinion or a decision.
# Conservative list — "review this PR" must still fire; "what do you think of the review"
# must not.
_META_RE = re.compile(
    r"\b(should we|should i|what do you think|do you think|your (?:thoughts|opinion|take|read)"
    r"|any thoughts|thoughts on|would you recommend|is this something we|how do you feel)\b",
    re.IGNORECASE,
)

_REMINDER = (
    "Reminder (TDD Playbook): this looks like build/fix/audit work — apply the TDD "
    "Playbook (reviewable plan → red-first behavioral tests → edge/property → mutation "
    "on critical modules → Tripwire N/N; for audits, the claims discipline). FIRST "
    "discover and layer this repo's own testing conventions (project CLAUDE.md/AGENTS.md, "
    ".claude/skills testing addenda, docs/TESTING) on top of the universal floor."
)

_DEFAULT_INTERVAL = 1800  # seconds; one nudge per working stretch, not per message
_DUP_WINDOW = 600         # a same-prompt sentinel younger than this = duplicate registration


def _state_dir():
    d = os.environ.get("TDD_PLAYBOOK_NUDGE_STATE_DIR", "").strip()
    return d or tempfile.gettempdir()


def _interval():
    raw = os.environ.get("TDD_PLAYBOOK_NUDGE_INTERVAL", "").strip()
    try:
        return max(0, int(raw)) if raw else _DEFAULT_INTERVAL
    except ValueError:
        return _DEFAULT_INTERVAL


def _should_fire(session_key, prompt):
    """Dedupe + damping. True -> emit the reminder. FAILS OPEN on any OS error."""
    try:
        d = _state_dir()
        now = time.time()
        phash = hashlib.sha1(prompt.encode("utf-8", "replace")).hexdigest()[:12]
        dup_path = os.path.join(d, "tdd_nudge_{}_{}".format(session_key, phash))
        last_path = os.path.join(d, "tdd_nudge_{}_last".format(session_key))

        # 1) duplicate registration: same session + same prompt already handled moments ago
        try:
            fd = os.open(dup_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
        except FileExistsError:
            if now - os.stat(dup_path).st_mtime < _DUP_WINDOW:
                return False
            os.utime(dup_path, None)  # stale repeat of the same prompt — treat as new

        # 2) damping: fired recently for this session -> stay quiet
        interval = _interval()
        if interval > 0:
            try:
                if now - os.stat(last_path).st_mtime < interval:
                    return False
            except OSError:
                pass  # no last-fire record -> proceed

        # 3) record the fire (mtime is the record)
        with open(last_path, "w"):
            pass
        return True
    except Exception:
        return True  # fail OPEN: never let sentinel plumbing kill the nudge


def main():
    if os.environ.get("TDD_PLAYBOOK_NUDGE", "").strip().lower() == "off":
        sys.exit(0)
    try:
        event = json.loads(sys.stdin.read() or "{}")
    except Exception:
        sys.exit(0)
    prompt = (event.get("prompt") or "").strip()
    # Skip trivial / short replies, prompts that already invoke the Playbook,
    # meta-discussions, and anything without clear build/fix/audit intent.
    if (len(prompt) < 12 or _ALREADY_RE.search(prompt) or _META_RE.search(prompt)
            or not _INTENT_RE.search(prompt)):
        sys.exit(0)
    session_key = str(event.get("session_id") or "ppid{}".format(os.getppid()))
    session_key = re.sub(r"[^A-Za-z0-9_-]", "_", session_key)[:64]
    if not _should_fire(session_key, prompt):
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
