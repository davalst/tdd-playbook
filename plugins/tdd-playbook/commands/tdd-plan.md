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
  - *Emits → named consumer:* who READS everything this produces; "nobody yet" becomes an
    integration-debt entry with an owner + expiry, never a silent write-only loop. For
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

Report `Loop closed: yes (integration-adversary — <top island>; architecture-adversary — <top
band-aid or "clean">)` or `Loop closed: NO — <why>`. Then stop — this plan is the single upstream
spec; let me review before writing code.

**Once APPROVED — land the plan IN THE REPO it governs (CIVerd plans-in-repo brief):** for
feature/multi-deliverable work in a CIVerd-watched repo, write the approved plan via

```
python3 "${CLAUDE_PLUGIN_ROOT}/bin/plan_block.py" scaffold --slug YYYY-MM-DD-<workstream> \
    --repo <the ENGINE'S repos.yml name — never a dirname guess> \
    --predicate TYPE:ARG [--predicate ...]
```

then paste the plan prose into the skeleton, `plan_block.py validate` it, and commit it with
the work. Rules that keep the block honest:
- **Slugs are permanent** (abandonment keys on the slug hash forever) — namespace by
  date + workstream; a collision means pick a NEW slug, never reuse.
- **Predicates state the weaker truth, write against it:** `test_passes path::name` = the
  function EXISTS at the judged sha, unskipped, gate green — NOT "the engine watched it run"
  (the repo's runs-guard in test_aaa closes the exists-vs-runs gap on our side);
  `symbol_referenced` is weak both ways — for config-wired deliverables use `file_exists` on
  the config + `test_passes` on a wiring test; `suite_min` counts AST test FUNCTIONS —
  near-useless in check()-style repos, prefer `test_passes`.
- **Research/docs/decision deliverables go in the "Unenforceable deliverables (prose)"
  section** — never faked with a weak `file_exists`.
- **Status is `active`, always.** `satisfied` is cosmetic to the engine; `abandoned` is
  David's word alone through the root-owned store on the box — the tool has no argument
  path that can emit either.
- **Never gate small work** — a one-liner or a mechanical chore does not need a plan block;
  the gate is for the work the §0 plan discipline already applies to.
