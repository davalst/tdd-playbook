# Oracle change journal — APPEND-ONLY (D3)

Removing or REPLACING a shipped scenario's `must_match`/`must_not_match` regex — or removing a
scenario — is test-weakening one level up, and `check_scoreboard_integrity.py` exits RED on it
unless the change is journaled HERE, in text appended since the trusted baseline. Pure
additions and tightenings never need an entry (the directional rule: the 2026-07 count-regex
tightening after a live false-fire is the class of change that must always be able to ship).

This file is itself append-only under the same checker: truncating or rewriting it to
retro-authorize a weakening is an integrity RED. Entry format, one line each:

`- <YYYY-MM-DD> · <scenario-id> · <what changed, old -> new> · <reason>`

## Entries
- 2026-07-30 · control-cachebusted-run · must_not_match ["(?i)unmeasured|phantom|refus"] -> ["(?i)refus", "(?i)(?:scope|gate|run) is unmeasured"] · the bare word 'unmeasured' false-fired on the agent's CORRECT negated checklist prose ("no unmeasured segfaults ✓") — the confirmed-as-a-count class again; forbid refusal VERDICTS, not vocabulary. Found in live shakeout, first probe roll.
