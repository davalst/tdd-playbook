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
- **Integration surface** (§0 — islands are cheapest to catch here). Five answers, each grounded
  in this repo (consult `capabilities.json` if the repo has one):
  - *Consumes:* which existing subsystems this plugs into — "none" stated, never implied.
  - *Emits → named consumer:* who READS everything this produces — at FIELD granularity: cite
    the file:line in the consumer that reads the specific field, not the subsystem that receives
    the object (a consumer that ignores the field is no consumer — the H11 tell); "nobody yet"
    becomes an
    integration-debt entry with an owner + expiry, never a silent write-only loop. And if the
    plan adds members to a pluggable family consumed by a shared host (handlers, hooks,
    adapters, middleware), name the repo's §6c FAMILY PARITY SWEEP that will cover them — or
    add authoring it (vacuity-guarded, enumerated from the real registry) as a deliverable. For
    feature/multi-deliverable/migration work, render this as the §6c FLOW TABLE —
    `flow · producer · consumer · liveness test`, one row per flow — so an empty consumer
    cell is visible (it means dated debt, or the flow doesn't ship). A MIGRATION deliverable
    must enumerate the replaced seam's outputs as rows: what the old seam fed, and whether
    each consumer is fed / retired-with-deletion / dated debt. Small diffs keep the prose
    answer.
  - *Surface parity:* which interfaces get the behavior; divergence stated, not discovered.
  - *Reverse sweep:* which existing features should now use this capability — each hit is a
    deliverable here or a dated debt entry.
  - *Activation:* on by default, or off behind a NAMED user-reachable switch (a plan that ships
    a feature dark with no switch is planning the next audit finding).
- **Property tests** — name any pure/transform/parse logic worth a Hypothesis-style invariant.
- **Repo-local extras** — any stack-specific tests this repo requires on top.

End with the proposed **Tripwire deliverable list** (one row per deliverable to verify
BUILT + WIRED + ACTIVATED + EXERCISED).

**Close the loop (not optional):** DISPATCH TWO fresh-context, refute-framed adversaries on the
drafted plan — the author's own imagination bounds both lists:
- `integration-adversary` — assumes the plan builds an ISLAND and tries to prove it (subsystems it
  should touch but doesn't, emitters with no consumer, surfaces left behind, dark-by-default shipping).
- `architecture-adversary` — assumes the plan is a BAND-AID and tries to prove it (fixes a symptom
  at the wrong seam, duplicates a list/enum/helper that already exists, keys a check on a proxy name
  instead of the fact). Islands and band-aids are different failures — a plan can be fully connected
  and still be spaghetti.
Fold each gap either names into the plan as a deliverable or an owned debt entry, or explicitly
reject it with a reason.

**Then, LAST, dispatch `intent-adversary`** — the only reviewer whose subject is the REQUEST.
The two above judge the plan on its own terms; neither asks whether it still does what was
ASKED. Run it last and not first: adopting a reviewer's finding is the most common way a
requirement gets narrowed, so running it before them inspects a plan that has not yet drifted.
Give it the requester's words VERBATIM — it refuses a paraphrase, because reading the plan's
own restatement of the goal inherits the drift it is hunting. Origin: a requirement stated
twice was argued down to "on demand" by four sound reviews with no record of the requester
being asked, and a whole workstream was replaced by two unrelated real defect fixes. In both
the engineering was good, which is why nobody else saw it.

Report `Loop closed: yes (integration-adversary — <top island>; architecture-adversary — <top
band-aid or "clean">)` or `Loop closed: NO — <why>`. Then stop — this plan is the single upstream
spec; let me review before writing code.

**Once APPROVED — land the plan IN THE REPO it governs.** For feature/multi-deliverable work,
write the approved plan to `docs/plans/gated/YYYY-MM-DD-<workstream>.md` as ordinary markdown
and commit it with the work, so the spec the Tripwire is anchored to lives beside the code it
governs rather than in a chat scrollback.

(Until v1.32.0 this step scaffolded a machine-readable `civerd-plan` block via
`bin/plan_block.py`, whose only consumer was the CIVerd engine's plan-predicate evaluator.
That engine is retired, and the registry had already recorded the path as never armed — plans
landed INERT. Producer and consumer are gone together; the plan CONTENT rules below are
untouched, because they were never the engine's business.)

Rules that keep the plan honest:
- **Slugs are permanent and dated** — namespace by date + workstream so a later plan never
  silently supersedes an earlier one; a collision means pick a NEW slug, never reuse.
- **State the weaker truth and write against it.** "the test EXISTS at this sha, unskipped,
  gate green" is NOT "the behaviour was observed running" — §6's EXERCISED leg is the former
  and the RUNNING leg is the latter, and a plan that conflates them has already rounded up.
- **Research/docs/decision deliverables go in an explicit "Unenforceable deliverables (prose)"
  section** — never disguised as a mechanical one, which is the H7 prose-deferral shape.
- **Never gate small work** — a one-liner or a mechanical chore does not need a plan block;
  the gate is for the work the §0 plan discipline already applies to.
