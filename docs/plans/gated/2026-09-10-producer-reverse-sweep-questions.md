# §0a question pack — producer reverse sweep (`/debug`, `/integration-audit`)

**Date:** 2026-09-10
**Produced by:** `spec-producer` (v1.53.0), dispatched fresh-context. This is the FIRST hand-run
of the agent, and it is the evidence the plan's own Tripwire named as the thing that separates
"the agent file exists at this sha and `test_agents.py` is green" from "the producer surfaced a
real missing requirement." It surfaced one — see Q3.
**Request, verbatim** (David, recorded in `capabilities.json` under the debt
`producer-reverse-sweep-debug-audit`): "/debug and /integration-audit also begin from an
under-specified ask — candidates for a later pass."
**Source read before asking:** `commands/debug.md`, `commands/integration-audit.md`,
`commands/tdd-plan.md`, `commands/spec-producer.md`, `SKILL.md` §0a (L200–303),
`capabilities.json:1742–1810`, `tests/test_agents.py`, `calibration/scenarios.json:576–606`,
`docs/plans/gated/2026-09-10-producer-elicitation.md`.

**Status:** OPEN — this pack is the input to a future plan, not a plan. Nothing here is built.
Its consumer is that plan's Spec integrity block (SKILL §0a).

---

**Q1. What FIRES the pack inside a command that has no §0 ceremony threshold — and does adopting it require editing §0a itself?**
`Proposed:` No new trigger is invented and §0a is NOT edited: the pack fires in `/integration-audit` only when the audit is itself planned work (a §0 plan already warranted), and `/debug` gets no trigger at all. Any other answer means writing a second threshold into SKILL §0a, which is a rule-(d) gate surface.
`Because:` §0a L287–291 and `capabilities.json:1751` both record David's 2026-09-10 Q1 answer — the trigger inherits §0's exactly, so that "a second ceremony table can disagree with the first" cannot happen; `/debug` and `/integration-audit` are invoked outside any §0 plan, so adoption has nowhere to inherit from.
`Changes:` Whether this workstream touches `SKILL.md` §0a at all (and therefore whether `calibration/gate-changes.md` and the doctrine needles in `test_v153_producer_doctrine` are in scope), and whether the `/debug` deliverable exists.

**Q2. Is adoption BLOCKED until `producer-yield-on-real-requests` is paid, or does it proceed in parallel?**
`Proposed:` Blocked. Widen only after the two numbers in that debt exist; if the yield says the pack pads, adopting it on two more entry points multiplies the padding across every bug and every audit.
`Because:` Both debts carry the same 2026-12-31 expiry (`capabilities.json:1791–1801`), so nothing today sequences them, and §0a L264–269 names padding — not omission — as this role's specific failure mode.
`Changes:` Whether any deliverable ships this cycle, or the outcome is a re-dated debt entry recording the dependency.

**Q3. `/debug`'s HARD GATE forbids exactly what a pre-loop pack does. Where can the pack sit, if anywhere?**
`Proposed:` Nowhere pre-loop — `/debug` DECLINES the pack and the decline is recorded as the debt's disposition. If elicitation lands anywhere in `/debug`, it is at step 3's existing 3-strike escalation, which already says "ask the human", and even there it is a narrower instrument than a §0a pack.
`Because:` **This is a FINDING, not a preference, and it is verbatim** — `commands/debug.md:8-9`: "**HARD GATE — no theorizing before a reproduction loop exists.** If you catch yourself reading code to build a theory before you can RUN the bug, stop." A `spec-producer` dispatch is a fresh-context agent reading code to build questions before the loop exists, so a pre-loop pack would make the command contradict its own first paragraph. The debt text itself anticipated it ("a symptom is evidence, not a spec") without noticing the textual collision.
`Changes:` Whether `/debug` is a wiring deliverable or a written decline; if a decline, the whole `/debug` half becomes an unenforceable-prose deliverable (§0 H7), not a command edit.

**Q4. For `/integration-audit`, what is the "under-specified ask" actually about — SCOPE, or FINDING DISPOSITION?**
`Proposed:` Scope and the standing-mechanism follow-ups, not the sweep itself: the five darkness classes and the claims discipline are fully specified, but `$ARGUMENTS` defaults to "the whole repo" with no statement of what is out of bounds, who owns a finding, what expiry is acceptable, or whether decide-or-park may retire a capability.
`Because:` `integration-audit.md:12–17` derives the inventory from `capabilities.json` and the entry points — the source already answers "what should run" — while `:74–79` demands "an OWNER and an EXPIRY" per finding, and nothing says who supplies those or with what authority.
`Changes:` Whether the deliverable is a generic dispatch or a narrow audit-specific pre-flight block; a generic dispatch would re-ask questions `capabilities.json` already answers, which is the fastest way to make a pack ignorable.

**Q5. Who READS the pack in each adopting command, and does it get a committed `docs/plans/gated/` artifact?**
`Proposed:` `/integration-audit` grows a named opening block (mirroring `tdd-plan.md:25–36`) declared as the pack's consumer, and writes the artifact ONLY when the audit is planned work. `/debug` writes no committed pack. Both exceptions stated in §0a's artifact bullet rather than left implicit.
`Because:` `SKILL.md` L295–299 and `commands/spec-producer.md:26–36` make the committed artifact and the named consumer non-optional, and a pack with no consumer is the write-only loop (§6c T2) the audit's own step 2 hunts — but a `docs/plans/gated/` file per bug is ceremony rent on a namespace whose slugs are permanent.
`Changes:` The command diffs, whether §0a gains an exception clause, and whether `docs/plans/gated/` acquires a per-invocation file class.

**Q6. Is a SPLIT verdict allowed — wire one, decline the other — and how does the debt entry close?**
`Proposed:` Yes, split, closing by recording BOTH dispositions in the same `what` field rather than a single verdict; a split does not need a second debt id.
`Because:` The debt is phrased as one either/or covering both commands, but Q3 and Q4 show they fail for different reasons, and `capability_registry.py validate` cares that the entry resolves, not that it resolved uniformly.
`Changes:` Deliverable count, and whether the debt is closed, split, or re-dated.

**Q7. Do the adopting surfaces reuse the exact `Verdict: SPECIFIED` / `UNDERSPECIFIED` contract lines?**
`Proposed:` Verbatim reuse, no new vocabulary. A symptom-shaped input does not get its own verdict words.
`Because:` `calibration/scenarios.json:582,599` anchor `must_match`/`must_not_match` on those literals and the `test_agents.py` roster entry pins them; a second vocabulary either forks the oracle or leaves the new surface unmeasured.
`Changes:` Whether `scenarios.json` and the contract map are touched, and whether the calibration oracle keeps working unchanged.

**Q8. Does each adopted surface need its own plant/control pair, or does the existing pair carry it?**
`Proposed:` One new PAIR only if `/integration-audit` adopts (its input is a scope, not a feature request, so the existing greenfield plant does not exercise it); a `/debug` decline needs none. Name the model-spend cost line before running it.
`Because:` §0a L264–269 makes the paired control the load-bearing half, and `capabilities.json:1781` states the FIRING probe is recall on the plant WITH the control staying SPECIFIED; a new surface with no control is an unmeasured surface.
`Changes:` Calibration cost and run time, and whether the `spec-elicitation` liveness probe text is amended.

**Q9. What mechanically pins the wiring so it cannot silently regress — and does anything notice `/debug` at all?**
`Proposed:` A needle per adopting command in `test_agents.py::test_commands` plus a planted stripped-text fixture in the v1.53 style. Note that `commands/debug.md` appears in NO `capabilities.json` entry, so a registry row would not notice a `/debug` edit being reverted.
`Because:` `test_agents.py:185–194` shows the house pattern is a literal needle per command, and `test_v153_planted_fixtures` shows every such pin ships with a fixture proving it can fail; grep of `capabilities.json` for `debug` returns only the debt entry itself.
`Changes:` The test deliverable, and whether registering `/debug` (alongside `/edge` and `/probe`, equally absent) becomes a scoped item or its own dated debt.

**Q10. Is the two-command list exhaustive, or was it the reverse sweep stopping where attention ran out?**
`Proposed:` Exhaustive for elicitation purposes. `/edge`, `/probe`, `/mutate`, `/readable`, `/claims` and `/tripwire` all take an artifact or roster that already exists as their subject; `/debug` and `/integration-audit` are the only two whose argument is free-form human intent.
`Because:` Across all thirteen command frontmatters the `argument-hint` fields split cleanly that way — the §0 reverse-sweep discipline applied to the reverse sweep itself, and a list of two written in a plan's closing bullet is exactly where an incomplete sweep hides.
`Changes:` The scope of the pass; a third hit is a third deliverable or a third dated debt line.

**Q11. Does adoption widen the Codex parity gap, and is that stated or absorbed?**
`Proposed:` It widens it and is STATED, not re-dated: every command edited here is Claude-only under `producer-codex-unavailable` (expires 2026-09-30), so a Codex install gets two more commands whose text names a mechanism it does not have.
`Because:` `capabilities.json:1802–1806` and the corrected surface-parity section of the producer plan already record that `commands/` and `agents/` are `unavailable` on Codex; §0's bar is "divergence stated, not discovered."
`Changes:` One line in the plan's Integration surface, and whether the 2026-09-30 debt is consciously re-dated as part of this work rather than by silence.

---

`Verdict: UNDERSPECIFIED — 11 load-bearing questions`

`Recommendation: Q1 — what fires the pack inside a command with no §0 ceremony threshold — because it decides whether this pass edits SKILL §0a (a rule-(d) gate surface with its own doctrine needles) or is confined to two command files, and because the only two available answers are "invent the second threshold David's 2026-09-10 Q1 answer explicitly refused" or "the pack does not fire in /debug at all", which are different builds with different deliverable counts.`

---

## Verification note (§12) — what was checked before this pack was believed

The Q3 collision is the load-bearing claim and it was verified independently of the agent that
raised it: `commands/debug.md:8-9` reads exactly as quoted. `capabilities.json` contains zero
occurrences of `commands/debug.md` (Q9's negative), and the repo has 13 commands (Q10's
denominator). The remaining questions are proposals for David to refute, not findings, and
carry no severity.
