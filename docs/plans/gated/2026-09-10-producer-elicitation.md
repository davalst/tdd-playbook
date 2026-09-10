# §0a Elicitation — the question pack before the plan

**Status:** APPROVED 2026-09-10 by David ("execute this plan using tdd-playbook"). Q1 and Q2
below were put to him before any code was written and are ANSWERED — the answers are recorded
inline at the questions, and the deliverables below are written against them.
**Date:** 2026-09-10
**Target:** 1.53.0
**Origin:** Hyper-τ-bench (TNS, Sept 2026): six autonomous coding-agent setups, none passing
more than 25% of tasks. On some tasks 20–25 requirements were discoverable ONLY by asking;
the developer agents asked no more than four. They produced working code against a spec they
had invented. Separately, one sentence proposing a different architecture moved a task from
31% to 67%.

## What prompted it

The failure is not laziness and it is not fixable by instruction. When ONE agent both asks the
questions and answers them, **the question set collapses to the answer set** — it asks what it
is already willing to resolve, feels no incompleteness at four, and starts building. A model has
no felt sense of a thin picture; four answers cohere as neatly as twenty-five.

The fix is structural and it is the same one TEST-LOCK makes for tests: **the party who must
satisfy a spec must not be the party who can quietly soften it.**

## Spec integrity

**Prior-art sweep (§0, mandatory before proposing to build):**

- `grep -ril 'clarify|clarifying|elicit|ask the user|question pack|underspecif' agents/ commands/`
  → **ZERO hits.** No agent and no command generates questions.
- All 16 agents operate on something that ALREADY EXISTS — a plan, a diff, a claim, a suite.
  Ten adversaries refute, three verifiers check a claim, three probes test the net. **None
  gathers.** The roster has no elicitation member.
- **Closest prior art, and it is the point:** `SKILL.md:201` — *"If something is genuinely
  unclear, name the confusion as a question for David — don't plan around it"*, and
  `SKILL.md:125` on stating assumptions. The REQUIREMENT already exists. What is missing is the
  MECHANISM — and today §0 asks the PLANNER to produce its own questions, which is exactly the
  collapse this plan addresses. So §0a is not a foreign import; it is the missing half of a rule
  §0 already states.
- `edge-case-adversary.md:29` — "flag any where you'd ask the human to confirm the correct
  behavior rather than guess" — one clause inside a critique agent, not a procedure.

**External prior art (do not re-derive):**
- Question GENERATION is a solved research area — GATE, STaR-GATE, TO-GATE. The stopping rule
  has a formal name (Expected Information Gain / EVPI) with a load-bearing formulation worth
  stealing: *high uncertainty alone does not make a question informative — different answers
  must lead to markedly different posterior updates.*
- GitHub Spec Kit ships `/speckit.clarify`: read the spec, ask structured questions, write the
  answers back into the artifact, run before planning. That is this design, shipped. **Confirm
  its licence before borrowing any text.**
- BMAD-METHOD (MIT) ships an Analyst agent with named elicitation lenses — Pre-mortem, First
  Principles, Inversion, Red Team vs Blue Team, Socratic, Constraint Removal, Stakeholder
  Mapping, Analogical Reasoning. **P2 seeds from that list rather than inventing one.** Note
  BMAD's elicitation has the AI re-examine ITS OWN output through a lens — self-directed, so it
  carries the collapse this plan exists to prevent.
- What is NOT covered by any of the above, as far as four searches can establish (which cannot
  prove a negative): the ask/answer SPLIT enforced at runtime, and the pack being LOCKED.

**Assumption stated:** the producer is a playbook component, not a Cheliped one. It guides
whichever agent is planning — Claude Code, Codex, or Cheli — like every other roster member.
Cheliped's own gaps are a SEPARATE plan in that repo.

**Materially simpler alternative, considered and rejected:** add "ask more questions" to §0's
wording. Rejected — the same instruction already exists at `SKILL.md:201` and the benchmark is
the evidence that instruction does not move an agent that both asks and answers.

**What happens if we do nothing:** §0 plans keep being written against invented specs, and the
drift is invisible because the plan is internally coherent. The cost is silent.

**Genuinely unclear — questions for review, not planned around. ANSWERED 2026-09-10:**
- Q1: does `/producer` run before EVERY §0 plan, or only above a blast-radius threshold?
  **ANSWER: it INHERITS §0's existing threshold.** §0a is a sub-section of §0, so it fires
  exactly when a §0 plan is already warranted — feature / multi-deliverable / risky /
  ambiguous work — and is skipped wherever §0 is skipped, including "autocomplete". No new
  threshold is invented: a second ceremony table can disagree with the first, which is the
  CONFIG/KNOB SPRAWL the architecture-adversary hunts, and charging elicitation rent on small
  plans is the shape v1.32.0 retired when it dropped the calibration clock.
- Q2: should the producer be allowed WebSearch for the Analogical Reasoning lens? It is the
  only lens that reaches outside the repo, and it was the highest-yield question type in the
  session that produced this plan. Cost and determinism both argue against.
  **ANSWER: NO — `Read, Grep, Glob` only**, matching every other non-probe agent. Three
  reasons, in order of weight: (1) letting the producer SEARCH is letting it ANSWER, which is
  the ask/answer collapse this entire plan exists to prevent — the lens survives as a
  QUESTION ("how do systems of kind X solve this; is it worth looking?") handed to the
  planner, which is strictly more useful than a half-researched answer buried in a pack;
  (2) §0 already places the external prior-art search on the PLANNER, so a searching producer
  duplicates an obligation that already has an owner; (3) §5a/§5b hygiene excludes web search
  from an agent's action space, and a non-deterministic producer makes P5's oracles flakier
  for no measured gain.

---

## P1 · §0a — the doctrine section

**What:** A new `## 0a. Elicitation — the question pack before the plan` in `SKILL.md`, placed
between §0 and §1, matching the existing §4a / §5a / §6a / §6b / §6c pattern of sub-sections
that refine a parent.

**Content, in doctrine form:**
- The collapse rule: an agent that must answer will ask only answerable questions. The party
  who asks and the party who answers are SEPARATE.
- The pack is generated BEFORE the §0 plan and feeds its Spec integrity section.
- Every question carries the producer's PROPOSED ANSWER and its reasoning. A proposition
  invites refutation; an open field invites a shrug. This is also the anti-padding filter — you
  cannot propose a specific falsifiable answer to a question invented to hit a quota.
- The stopping rule: stop when the answer would not change what you build. Not "where is
  uncertainty high" but "where would different answers produce different plans."
- Bound the LENSES, never the COUNT. A quota manufactures questions; a lens checklist that may
  return "nothing here" does not.
- Round 2 is response-driven, triggered by the NON-ANSWER (answered without evidence, restated,
  or "it depends"), the CONTRADICTION, and the SURPRISE. Round-1 questions are never replaced;
  growth is fine. Two rounds by default.
- Dropping a question requires a journaled reason — the `/tdd-unlock` discipline, applied to
  questions.

**Edge cases (§2 categories that genuinely apply):**
- A well-specified request: §0a must state plainly that an EMPTY pack is a correct outcome, or
  the section trains the padding it exists to prevent.
- A repo-less / greenfield request: the lenses still run; source-answerable questions are absent.
- An "autocomplete" instruction (§0's existing escape): §0a must say whether it is skipped too.

**Unenforceable (prose):** doctrine text is not mechanically testable beyond P4's contract.

## P2 · `agents/producer.md`

**What:** The 17th roster member. Reads a request plus the repo, returns a QUESTION PACK.
Never answers, never plans, never writes.

**Frontmatter:** `tools: Read, Grep, Glob` (read-only, matching every non-probe agent).
`model: opus`. WebSearch pending Q2.

**Forced output contract (house convention — `test_agents.py:60-101` enforces that every agent
carries closed-vocabulary lines so it cannot hedge):**

```
Verdict: SPECIFIED
Verdict: UNDERSPECIFIED — <n> load-bearing questions
Recommendation: <the one question whose answer would most change the build>
                because <names the concrete decision it changes>
```

This mirrors `edge-case-adversary`'s `Coverage: ADEQUATE` / `Coverage: GAPS` pair EXACTLY,
including the norm already written there: *"Do not invent gaps to look useful: adequate
coverage called adequate is a measured outcome (paired controls), not a missed opportunity."*
The producer's anti-padding property is therefore an EXISTING house rule, not a new invention,
and the paired-control harness already measures it.

**Lenses** seeded from BMAD (MIT): Pre-mortem, First Principles, Inversion, Red Team vs Blue
Team, Socratic, Constraint Removal, Stakeholder Mapping, Analogical Reasoning. Each MAY return
nothing.

**Edge cases:**
- fully-specified request → `Verdict: SPECIFIED`, zero questions (the control; see P5)
- greenfield → lenses run, source-answerable questions absent
- request already carries a spec doc → questions must not restate it
- a proposed answer CONTRADICTED by source → that is a finding, surfaced not suppressed
- pack exceeds render budget → bounded, with the truncation stated in-band

## P3 · `commands/producer.md`

**What:** `/producer <request>` — runs the agent, renders the pack, and states that its output
belongs in the next `/tdd-plan`'s Spec integrity section.

**Edge cases:** invoked with no request; invoked after a plan already exists (it should say the
pack is late and why that matters); invoked twice (round 2 semantics).

## P4 · `tests/test_agents.py` — the contract entry

**What:** `"producer": (False, [r"Recommendation:", r"Verdict:\s*SPECIFIED",
r"Verdict:\s*UNDERSPECIFIED"])`. `may_hold_Edit=False`.

**Property test:** every agent in `agents/` has an entry; every entry names an agent that
exists. (Check whether this bidirectional assertion already exists — if not, it is worth adding
alongside, since a roster member with no contract entry is the darkness class §6a names.)

## P5 · `calibration/scenarios.json` — PAIRED scenarios

**What:** At least two entries with `"agent": "producer"`:
1. **The plant** — a request with a deliberately absent, load-bearing requirement. Oracle: the
   pack must surface it. Verdict `UNDERSPECIFIED`.
2. **The control** — a genuinely complete request. Oracle: `Verdict: SPECIFIED`, empty pack.

**Why the control is the important one:** the repo's own calibration history records a verifier
scoring recall 8/10 with FP 10/10 — high recall, catastrophic precision — and the diagnosis that
followed found the FP number was substantially measuring CONTROL-AUTHORING quality. So the
control request must be authored carefully and is itself reviewable. An agent with no
independent oracle always finds something; a producer that never returns `SPECIFIED` is theater
and this scenario is what proves it either way.

**Edge case:** the control must not be trivially short — a one-line request is complete for
uninteresting reasons.

## P6 · Inventory, docs, version

`docs/adversary-scenario-inventory.md`, `docs/reference/current-state.md`, `README.md`,
`CHANGELOG.md` → 1.53.0, and a `capabilities.json` entry if the roster is registered there
(verify at build time; the file has 36 entries and the agents may be covered collectively).

---

## Integration surface

- **Consumes:** the §0 plan flow (`commands/tdd-plan.md`), the agent loader, the calibration
  harness.
- **Emits → named consumer:** the pack is read by `/tdd-plan`'s **Spec integrity** section —
  `commands/tdd-plan.md:15-18` is the block that must be edited to cite it. Without that edit
  the producer is an emitter with no consumer, which is the island this plan would otherwise be.
- **Surface parity:** it is a plugin agent, so Claude Code, Codex (via the adapter) and Cheli
  (via the ccbridge) all get it from the one install. No per-surface work in THIS repo.
- **Reverse sweep:** `/tdd-plan` should invoke it (P3 + the `commands/tdd-plan.md` edit).
  `/debug` and `/integration-audit` also begin from an under-specified ask — candidates for a
  later pass, listed here as dated debt (owner: David, expiry 2026-12-31) rather than scoped in.
- **Activation:** ON on install, like every other roster agent. It has no config gate and
  therefore cannot ship dark.

## Tripwire list

P1 P2 P3 P4 P5 P6 — each BUILT + WIRED + ACTIVATED + EXERCISED.

Weaker-truth note: "the agent file exists at this sha and `test_agents.py` is green" is
EXERCISED. It is NOT "the producer surfaced a real missing requirement" — for that, P5's
calibration run, and a hand-run against one real request.
