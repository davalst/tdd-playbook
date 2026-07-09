---
description: Produce the Playbook §0 reviewable TDD plan for a feature — deliverables, edge cases, UX tests — before any code.
argument-hint: <feature or change to plan>
---

Produce a **reviewable TDD plan** for: $ARGUMENTS

Follow the TDD Playbook §0. FIRST, discover this repo's own testing conventions (project
`CLAUDE.md`/`AGENTS.md` testing/QA/security sections, `.claude/skills` testing addenda,
`docs/TESTING*`, the test config + markers) and state which you'll layer on top of the
universal floor — or "none found".

Then output a terse, SCANNABLE plan (plain chat, not a file).

Open with **Spec integrity** (once per plan, before the deliverables — §0): assumptions stated
explicitly; if the request supports multiple readings, present them and say which one the plan
follows (never pick silently); if a materially simpler approach would satisfy the request, say
so; anything genuinely unclear becomes a question for review, not something planned around.

Per deliverable:
- **What** — one line of plain-English behavior (happy path).
- **Edge cases** — bullets of real-world scenarios from §2's checklist that genuinely
  apply (boundaries, empty/null, malformed, auth-negative, idempotency/double-submit,
  concurrency, failure/rollback, scale, second-order). One-line justification each; no padding.
- **UX tests** — bullets: what the user does → what they should see, driven through the
  REAL interface (web/Telegram/TUI/MCP/CLI per this repo).
- **Integration surface** (§0 — islands are cheapest to catch here). Four answers, each grounded
  in this repo (consult `capabilities.json` if the repo has one):
  - *Consumes:* which existing subsystems this plugs into — "none" stated, never implied.
  - *Emits → named consumer:* who READS everything this produces; "nobody yet" becomes an
    integration-debt entry with an owner + expiry, never a silent write-only loop.
  - *Surface parity:* which interfaces get the behavior; divergence stated, not discovered.
  - *Reverse sweep:* which existing features should now use this capability — each hit is a
    deliverable here or a dated debt entry.
  - *Activation:* on by default, or off behind a NAMED user-reachable switch (a plan that ships
    a feature dark with no switch is planning the next audit finding).
- **Property tests** — name any pure/transform/parse logic worth a Hypothesis-style invariant.
- **Repo-local extras** — any stack-specific tests this repo requires on top.

End with the proposed **Tripwire deliverable list** (one row per deliverable to verify
BUILT + WIRED + ACTIVATED + EXERCISED).

**Close the loop (not optional):** DISPATCH the `integration-adversary` agent on the drafted
plan — a fresh-context, refute-framed pass that assumes the plan builds an island and tries to
prove it (the author's integration list is bounded by the same imagination that wrote the plan).
Fold each gap it names into the plan as a deliverable or an owned debt entry, or explicitly
reject it with a reason.

Report `Loop closed: yes (integration-adversary dispatched — <its top gap>)` or
`Loop closed: NO — <why>`. Then stop — this plan is the single upstream spec; let me review
before writing code.
