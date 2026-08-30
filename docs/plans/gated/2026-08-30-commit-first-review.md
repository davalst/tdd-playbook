# Commit-first review — reordering the reviewers so they aren't anchored

**Status:** PROPOSED — awaiting David's approval. Not built.
**Date:** 2026-08-30
**Origin:** research pass on multi-agent review practice, 2026-08-30 (this session).

## What prompted it

Sixteen reviewer briefs, all of which read the artifact and then critique it. A July 2026
paper on fooling LLM judges measured what happens when a judge is made to answer the
question ITSELF before seeing the candidate answer: false-positive rate fell from
**0.719 to 0.012** (arXiv 2607.05904). Ordering alone.

This session ran at a measured ~75% false-alarm rate on self-initiated proposals (8 of 8
rejected, 2026-08-29). Anchoring is a plausible contributor and the fix is a wording change,
not a build.

## Spec integrity

**Assumption stated, because the request was ambiguous.** David said "yes let's do this"
against a Do / Consider / Don't list. I read that as the **Do** (commit-first) plus a
SCOPED look at the **Consider** (a reviewer that audits a reviewer). D2 is separable and
can be dropped without touching D1. If he meant D1 only, delete D2 and nothing else moves.

**Prior-art sweep (§0, mandatory before proposing to build):**
- `grep -ril "before you read|independently first|form your own|commit.*first" agents/*.md`
  → **zero procedural hits.** Commit-first is genuinely absent.
- **Partial prior art, one brief:** `intent-adversary.md:68` — "enumerate them from the
  verbatim request, never from the plan's list of deliverables, or you will only ever check
  the requirements that survived." That IS commit-first, stated once for one narrow purpose.
  **So D1 is generalising an existing local pattern, not importing a foreign one.**
- `edge-case-adversary.md` says "independently brainstorm" in its DESCRIPTION only — not as
  a procedural instruction in the body. It is not commit-first today.
- **D2 largely already exists:** `control-quality-adversary.md` already audits a VERIFIER
  rather than the work — but only for flagged calibration controls, advisory, closed
  vocabulary. So D2 is a SCOPE question, not a new agent.

**What happens if we do nothing:** the panel keeps working — quality has been high all week.
The cost is efficiency, not correctness. Do-nothing is a live option and this plan is not
worth building if D1 cannot be shown to change any verdict (see D3).

**Materially simpler alternative, considered:** add the clause to only the 3–4 briefs most
implicated in this week's failures. Rejected because we do not know which those are; D3 is
cheaper than guessing and gives the answer.

## Deliverables

### D1 — the commit-first clause in the JUDGING briefs

**What:** before reading the artifact under review, the reviewer answers the question from
the SOURCE material (the request, the code, the diff), writes that answer down, and only
then reads the artifact and compares.

**Which briefs.** Twelve judges get it; four runners do not, because they execute
deterministic things and have nothing to be anchored by:

| gets the clause (12) | excluded — runners (4) |
|---|---|
| architecture, integration, security, test-quality, adoption, observability, script, edge-case, claims-verifier, tripwire-auditor, intent (has it partially), control-quality | mutation-runner, planted-error-probe, red-first-verifier, ux-probe-calibrator |

**Forced line**, so the effect is auditable rather than asserted:

    Prior: <n> expected · <m> confirmed · <k> found only on reading

`k` is legitimate — reading the artifact SHOULD reveal things. The number is a trend line,
never a gate (§5a oracle-split: models advise, deterministic checks decide).

**Edge cases**
- A reviewer with no way to form a prior (artifact IS the only source) → `Prior: N/A — <why>`,
  never a fabricated denominator. Same rule as the Means line.
- A reviewer that pads `n` with throwaway guesses to look diligent → `m`/`n` collapses; the
  ratio is the tell, which is why all three numbers are forced, not just `k`.
- Commit-first must NOT delay reading the verbatim request in `intent-adversary` — its prior
  is BUILT from that request. Clause must be worded so the source material is always readable.

**Integration surface**
- *Consumes:* the 12 agent briefs; the forced-line registry in `tests/`.
- *Emits → named consumer:* the `Prior:` line → `commands/tdd-plan.md` and `commands/claims.md`
  paste reviewer output; the line is read by a HUMAN at review time. **No code consumer, by
  design** — it is a trend line. This is deliberate write-only-to-human and is stated here so
  it is not mistaken for an oversight.
- *Surface parity:* briefs ship to claude + codex adapters via host parity; no divergence.
- *Reverse sweep:* `commands/tdd-plan.md`, `commands/claims.md`, `commands/integration-audit.md`,
  `commands/tripwire.md` dispatch these agents and must not contradict the new ordering.

**Deploy surface:** vendored `.claude/` copies in downstream repos (cheliped). Gets there via
`install_into_repo.py`. Verified by the standing refresh prompt in CLAUDE.md. Divergence: a
downstream repo keeps the old briefs until refreshed — acceptable, briefs are advisory.

### D2 — decide the scope of reviewer-audits-reviewer (NOT a build)

A 3-agent setup beat a 5-agent baseline by having the third agent audit **the reviewer**
rather than the code (arXiv 2608.18167). We already have `control-quality-adversary` doing
exactly this, confined to calibration controls.

**Deliverable is a DECISION, recorded, not code:** does that brief generalise to plan/code
review, or is its narrow scope correct? Answered from D3's evidence. If the answer is
"generalise", it becomes its own plan. **Nothing is built under this plan.**

### D3 — replay against the motivating artifacts (§13 guard calibration)

Red-first proves a clause CAN change a verdict; it does not prove it changes THIS one. So:
take 3 of this week's 8 rejected proposals, re-run one judging adversary on each in both
modes (anchored / commit-first), compare verdicts and finding counts.

**This is the deliverable that can kill D1.** If verdicts are identical, the clause is
ceremony and D1 is reverted.

**COST, named before the run (memory: model-spend discipline):** 3 plans x 2 modes x 1
adversary = **6 live agent dispatches**, no panel. Bounded, one-off.

## Tests (red-first, both directions)

Prose surfaces are the product here, so substring assertions are the CORRECT instrument —
this is the legitimate half of the distinction filed as debt `proxy-assert-on-own-prose`
today, and the test cites that debt so the two are not confused.

1. `test_commit_first_clause_in_judging_briefs` — each of the 12 carries the clause AND the
   forced line. RED before the edit.
2. `test_runner_briefs_have_no_commit_first` — the 4 runners do NOT. **The other direction**;
   without it the test passes if we blanket-apply to all 16.
3. `test_commit_first_forced_line_registry` — the `Prior:` line is pinned in the same registry
   as `Means:`/`Verdict:`, so removing it REDs the gate.
4. Vacuity guard: the roster is enumerated from `ls agents/*.md` at runtime, not hardcoded, so
   a new brief cannot silently fall outside the check.

## Gate-surface ledger

`agents/*.md` are EFFECTFUL ledger surfaces — this needs a `calibration/gate-changes.md`
entry with a real prediction (rule (d)). Prediction to register: commit-first raises
finding-count on the anchoring-prone categories in D3, or D1 is reverted.

## Tripwire

Four legs per deliverable: BUILT (clause present) + WIRED (dispatched by the commands that
call these agents) + ACTIVATED (briefs ship in both adapters) + EXERCISED (D3 replay).

## Adversaries to dispatch before building

`integration-adversary` and `architecture-adversary` on this plan (§0 close), then
`intent-adversary` LAST with David's verbatim words — because I already flagged that I
resolved an ambiguity in the request, and that is exactly where drift enters.
