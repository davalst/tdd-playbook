# Gate change journal — APPEND-ONLY (lift/ratchet D3)

Removing a gate surface — a SKILL.md `## ` section, an `agents/*.md` brief, or a
`commands/*.md` file — is the deletion-ratchet's cheap direction, and
`check_scoreboard_integrity.py` rule (d) exits RED on it unless the removed name appears
HERE, in text appended since the trusted baseline. Additions never need an entry: gate
removal costs what gate addition costs; addition never pays the removal toll.

This file is itself append-only under rule (a): truncating or rewriting it to
retro-authorize a removal is an integrity RED. Entry format, one line each:

`- <YYYY-MM-DD> · <exact removed name (heading text or filename)> · <why, and what supersedes it>`

## Entries
