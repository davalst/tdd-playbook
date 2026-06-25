---
description: Produce the Playbook §0 reviewable TDD plan for a feature — deliverables, edge cases, UX tests — before any code.
argument-hint: <feature or change to plan>
---

Produce a **reviewable TDD plan** for: $ARGUMENTS

Follow the TDD Playbook §0. FIRST, discover this repo's own testing conventions (project
`CLAUDE.md`/`AGENTS.md` testing/QA/security sections, `.claude/skills` testing addenda,
`docs/TESTING*`, the test config + markers) and state which you'll layer on top of the
universal floor — or "none found".

Then output a terse, SCANNABLE plan (plain chat, not a file). Per deliverable:
- **What** — one line of plain-English behavior (happy path).
- **Edge cases** — bullets of real-world scenarios from §2's checklist that genuinely
  apply (boundaries, empty/null, malformed, auth-negative, idempotency/double-submit,
  concurrency, failure/rollback, scale, second-order). One-line justification each; no padding.
- **UX tests** — bullets: what the user does → what they should see, driven through the
  REAL interface (web/Telegram/TUI/MCP/CLI per this repo).
- **Property tests** — name any pure/transform/parse logic worth a Hypothesis-style invariant.
- **Repo-local extras** — any stack-specific tests this repo requires on top.

End with the proposed **Tripwire deliverable list** (one row per deliverable to verify
BUILT + WIRED + EXERCISED). This plan is the single upstream spec — stop and let me review
before writing code.
