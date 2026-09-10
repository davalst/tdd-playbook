---
description: Produce the Playbook §0a question pack for a request — the load-bearing things nobody has said yet, each with a proposed answer to refute — before the §0 plan is written.
argument-hint: <the request, in the requester's own words>
---

Produce the **§0a question pack** for: $ARGUMENTS

**When this runs.** §0a inherits §0's ceremony threshold exactly — feature, multi-deliverable,
risky or ambiguous work. If a §0 plan is not warranted, neither is a pack, and "autocomplete"
skips both. There is no second threshold to consult.

**The split is the mechanism, so do not collapse it.** DISPATCH the `spec-producer` agent, fresh
context, and let it ask. Do not answer its questions on the requester's behalf and do not
pre-filter the pack down to what you already intended to build — an agent that both asks and
answers asks only what it is willing to resolve, which is the entire failure §0a exists to
break. You are the courier here, not the respondent.

Give it the request in the **requester's own words**. A paraphrase has already been narrowed by
whoever wrote it, and the pack would then be about your restatement.

**Render the pack as the agent returned it** — one block per question, each with its proposed
answer, its reasoning, and what a different answer would change; ordered by blast radius, not by
lens. If the agent stated a truncation, keep that line: a pack that hides its own tail is lying
about its denominator.

**Write the pack to the repo, then cite it by path.**
`docs/plans/gated/YYYY-MM-DD-<slug>-questions.md`, beside the plan it feeds and under the same
permanent-dated-slug rule. Not a chat message: a pack in a scrollback cannot be diffed, cannot
be cited by the block that consumes it, and is gone when round 2 happens in a fresh session.
This repo measured that exact cost on plans and wrote the rule down; the pack is the plan's
provenance and gets the same treatment.

**Where it goes.** The pack's named consumer is the **Spec integrity** block of the next
`/tdd-plan` — the unresolved questions land there, with the spec-producer's proposed answers, as the
plan's stated assumptions or its open questions for David. Say so when you render it. A pack
nobody cites is an emitter with no reader, which is the island this command would otherwise be.

**A pack with no questions is a real answer.** `Verdict: SPECIFIED` means the request carries
what a plan needs. Report it as the measured outcome it is; do not send the agent back to find
something. A spec-producer that never returns SPECIFIED is theater, and the paired calibration
control exists to catch exactly that.

**Invoked twice — Round 2 is response-driven.** Hand the agent the ANSWERS to round 1 and let it
read them for its three triggers only: the non-answer, the contradiction, the surprise. Round-1
questions are never replaced. Two rounds by default; a third needs a stated reason.

**Invoked after a plan already exists — say the pack is LATE, and say why it matters.** A plan
written first is a plan already committed to a spec, so the questions now have to argue against
work someone has done rather than shape work nobody has started. Run it anyway — a late finding
beats a shipped invention — but report which plan deliverables each answer would have changed,
so the cost of the ordering is visible rather than absorbed.

**Dropping a question needs a journaled reason.** If you discard something the producer asked,
write down why, in the plan. A question silently dropped and a question answered look identical
in the plan that follows.
