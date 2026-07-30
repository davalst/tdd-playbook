# Calibration Lift and the Deletion Ratchet

**A design decision on how to measure whether the playbook's gates earn their keep — without
building a mechanism that erodes them.**

Date: 2026-07-30 · Repo: `davalst/tdd-playbook` · Status: proposal, not yet implemented
Revision: **v2** — incorporates peer review; see §9 for what changed and why
Prompted by: review of arXiv:2607.21627, *Do Modules Stay in Their Lane? Role Drift in Compound
LLM Systems* (`docs/evaluations/paper-review-role-drift-2607.21627-2026-07.md`, committed at
`911e06e` on branch `claude/paper-review-2607-2dqbql`)

---

## 1. Why this document exists

A paper review turned into a self-audit, which turned up a design flaw in the fix the review
recommended. This document records the flaw, the architectural rules that neutralize it, and a
revised — significantly *smaller* — set of changes.

The chain was:

1. The paper identifies **Role Drift**: in a multi-module system trained against a single
   end-to-end metric, a module can improve that metric while abandoning the job it was assigned.
   The terminal number goes up; the reason you partitioned the system goes away.
2. Its sharpest methodological criticism is a **missing baseline**: the authors compare
   "with our regularizer" against "without it," never against a standard control, so they cannot
   attribute the improvement to their specific mechanism.
3. That criticism applies to us. `calibration/run_calibration.py` builds every prompt as
   `agent_body(scenario["agent"]) + task` (~L249-255). Every figure in
   `docs/calibration/history.md` therefore answers *"did the playbook-equipped agent catch the
   plant?"* — and nothing answers *"would a bare agent have caught it anyway?"*
4. So the first draft proposed adding a **no-agent control arm** to measure *lift*
   (`caught_with − caught_without`) per gate, and noted we could then delete gates showing no lift.

Step 4 contains the flaw. It is worth writing down because it is a class of error, not a one-off:

> **A measurement whose only available action is subtraction will, given enough time, subtract
> everything.**

---

## 2. The finding: the deletion ratchet

### 2.1 The mechanism

Lift is a *ranking*. A ranking always has a bottom. If the operational rule is "cut the
lowest-scoring gate," then after each cut the next-lowest becomes the new obvious candidate, and the
argument for cutting it is identical in form to the one that justified the last cut. The process has
no natural stopping point, because "worst of the remaining set" is defined no matter how small the
set gets. Nothing in the metric distinguishes *pruning decoration* from *disassembling protection*.

### 2.2 The friction asymmetry — why it's inevitable, not merely possible

Under current process the two directions cost radically different amounts:

| Direction | Cost today |
|---|---|
| **Add** a gate | Author a plant (`author_plants.py`), pass validation, pair it with a clean control (`control_for`, mechanically required), human review, `--approve` |
| **Remove** a gate | Delete a file — *for the uncovered surfaces in §3* |

Adding is deliberately expensive. A door with a spring on one side only is not a two-way door. Over
a long enough horizon the corpus grows and the gate set shrinks — backwards from what the playbook
is for. Same structural insight as the paper's, applied to our own process: the metric we would be
optimizing (lift) is silent about the property we care about (retained protection).

### 2.3 A zero-lift reading is ambiguous, and only one reading means "delete"

This is the technical crux. A gate can score zero lift for four distinct reasons:

| Cause | Correct response |
|---|---|
| It is genuinely redundant with another gate | **Cut candidate** — the only one |
| The plant is too easy; a bare model catches it anyway | **Strengthen the plant** |
| The scenario suite doesn't cover the situation this gate exists for | **Add a scenario** |
| `DEFAULT_REPEAT = 3` is too small to separate signal from noise | **Get more data before acting** |

Three of four call for *adding* work to the corpus. One calls for cutting. A naive lift-driven
process inverts that distribution — it reads all four as the first. So the default resolution must
be the majority behavior, expressed as a rule alongside the one already in force:

> **Existing rule:** a plant surviving to a clean verdict is a BLOCKING failure —
> *fix the agent, never the plant.*
>
> **New sibling rule:** a gate showing no lift is a question, not a verdict —
> *strengthen the plant, never delete the gate.*

Deletion remains available. It just has to cost what addition costs.

### 2.4 Blast radius: what is actually exposed

Narrower than the first draft claimed, which materially shrinks the response.

**Not exposed — mechanical layer.** The PreToolUse guards and the other scripts under
`plugins/tdd-playbook/hooks/scripts/` are covered by deterministic planted-input tests in
`plugins/tdd-playbook/tests/`. A planted violation is either blocked or it isn't: binary, no
ranking, nothing to game.

**Not exposed — 7 of 10 agents.** The calibration roster is *derived*, not hand-maintained:
`known_agents()` (`run_calibration.py:51`) reads `plugins/tdd-playbook/agents/` and subtracts
`TREE_TOUCHING_AGENTS = {planted-error-probe, ux-probe-calibrator}`. `validate_scenario` then fails
with `unknown agent` for any scenario naming an agent absent from that set (L85-87). So deleting a
**scenario-covered** agent REDs the dry-run → `test_harness` → the release gate → CIVerd's daily
run. Un-freezing the roster in v1.17 bought this protection.

**Genuinely exposed:**

| Surface | Why uncovered |
|---|---|
| `integration-adversary` | Calibratable, but **has no scenario** — so the derived-roster protection doesn't reach it. Deleting it today is silent. |
| `planted-error-probe`, `ux-probe-calibrator` | Tree-touching, deliberately outside headless calibration |
| SKILL.md sections | No inventory, no pin |
| `commands/` | No coverage invariant |

The `integration-adversary` gap was found while checking this document's own claims. It is a live
hole, not a hypothetical, and it is the argument for R1 as restated below: the coverage invariant
fails *on introduction*, which is what a good invariant does.

---

## 3. What already protects us

Two mechanisms, both mechanical rather than disciplinary.

**`calibration/check_scoreboard_integrity.py`** enforces, against a baseline revision: `history.md`
append-only (baseline must be a byte-*prefix* of the candidate); the approved corpus only grows and
approved plants are **immutable**; oracles never weakened without a journal entry in
`calibration/oracle-changes.md` — itself append-only under the first rule, so it cannot be
retroactively rewritten. Runs in the release gate and via `test_harness.py` against the latest tag on
every suite run.

**The derived agent roster** — §2.4. Coverage is a side effect of scenarios existing, not a stated
invariant, which is exactly why `integration-adversary` slipped through.

**Also already shipped: the yield instrument.** `_common.log_yield_event()`
(`hooks/scripts/_common.py:114`) logs every guard firing through the single `emit()` seam, and
`bin/gate_yield.py` rolls it into committed per-cycle rows. It already has the anti-ratchet shape
this document argues for — see item 6, which the first draft got backwards.

---

## 4. Design rules

Four invariants, each intended to be a script or a test rather than a convention.

**R1 — Gate removal costs what gate addition costs.** Three parts, in ascending cost:

1. **Coverage invariant** (do this first): *no calibratable agent without a plant.* One harness
   check reusing the existing pairing-invariant pattern. Currently fails on
   `integration-adversary` — that's the point.
2. **SKILL.md section-inventory pin** — a manifest of sections, checked, so removals surface.
3. **`gate-changes.md`** — an append-only journal for removals on the surfaces the first two can't
   reach, added to the integrity checker's protected list (~3 lines). *Separate file from
   `oracle-changes.md`*, because the consumers and the authorization semantics differ.

Note the CIVerd contract already lists `agents/*.md` briefs on its §1.3 extended watchlist, but
`capabilities.json` records that the floor's *coverage* of those files is unproven (debt expiring
2026-09-15). R1 is the local belt to that suspender and is worth building regardless of how the
engine-side item resolves.

**R2 — Lift data never reaches a coding agent.** If a working agent can see "gate X has low lift," it
has been handed a written argument for ignoring gate X — a worse failure than gradual erosion,
because it's immediate. We are currently safe *by accident*: `install_into_repo.py`'s `COPY_TREES` is
`skills/tdd-playbook`, `commands`, `agents`, `bin`, `hooks/scripts` — `calibration/` is absent.
Convert the accident into a one-line test asserting `calibration/` never lands in `.claude/`, so the
boundary can't erode by someone helpfully extending the copy list.

**R3 — Lift is a quarterly diagnostic, not a metric.** A property of the playbook as a product, not
of any coding session. Periodic product review, prose findings, lives in `docs/`. No dashboard, no
threshold, not on any hot path, explicitly not part of the weekly cadence.

**R4 — Gates are evaluated against their own purpose, never ranked against each other.** Ranking is
what creates the bottom of the list. Ask "does this gate catch what it was written to catch?" — an
absolute question with a stable answer — not "is this gate better than that one?"

---

## 5. Recommendation set

Filtered against the operative test: **does this make Claude-in-the-playbook produce better code, or
is it bloat that dilutes what already works?**

| # | Item | Verdict |
|---|---|---|
| **1** | **Symmetric-harness-break plants.** Several checks are *differential* in shape — `mutation-runner` (suite on mutated vs. clean code), `red-first-verifier` (fails before the fix, passes after), `snapshot_guard`. Any such check is blind to a break that degrades **both** sides equally: a suite that fails on everything, a scope resolving to nothing on both arms, a harness erroring identically pre- and post-fix. Add one plant per differential check. | **Highest.** Purely additive, existing pipeline, no new machinery, nothing to rank. Converts the 2026-07-27 `vacuous-mutation-scope` luck-catch into designed coverage. **Rider:** the pair quota mechanically demands a clean control per new plant — budget ~2× authoring. |
| **2** | **Anti-ratchet: R1 + R2.** Coverage invariant → SKILL.md pin → `gate-changes.md`; plus the vendoring test. | **High, and a precondition.** Small, reuses trusted machinery, must exist before item 4 or item 4 is net-negative. Part 1 pays for itself immediately by REDing on `integration-adversary`. |
| **3** | **Dev/holdout split of the corpus.** Two rules that are easy to omit and fatal if omitted: **(a) split by pair, not by scenario** — hash the *plant* id and let its `control_for` ride along, or you measure FP on dev while the paired plant sits in holdout; **(b) burn-on-failure** — a holdout plant that fails must still drive an agent fix (a known miss can't stand), but the moment it does it is contaminated and must rotate into dev, with the authoring cycle replenishing holdout. At 24 scenarios, hold out **whole plant classes** rather than individuals. | **High for honesty, low cost.** Today the tuning loop and the reporting loop share the same plants: "fix the agent, never the plant" means we iterate until a plant passes, then report the catch rate on that plant (`csv-escape-fixed-at-call-site`: failed twice, then passed). Without rule (b) the holdout decays into a second dev set within two quarters and the externally-quoted number is again the one the tuning loop touched. |
| **4** | **Lift diagnostic** — a control arm, run once, quarterly, on holdout. **Design change:** a *naive* bare-agent arm is confounded. Roughly 17 of 24 oracles key on house output contracts (`NOT VERIFIED`, `RED-FIRST: VERIFIED`, `verdict: band-aid`, `parking: DARK`, `Tripwire: 2/2`, `coverage: adequate`, `Recommendation:`, `confirmed: 0`). A bare agent can diagnose a defect perfectly and still miss `must_match` because it doesn't know the format — so the arm would measure "knows the house format," overstating lift almost everywhere. The confound is **bidirectional**: on controls, whose oracles key on `gate passes`, a bare agent also fails, so FP is equally uninterpretable. Fix: a **contract-stub** control prompt carrying the output format only, no doctrine — and it must cover the *control* verdict lines too, not just the plant ones. | **Real but indirect, gated on 2 + 3.** Value is *finding decoration*, not deleting things: dead prose isn't neutral, it eats context and competes with the instructions that do steer. Safe to look at only once cutting is expensive. |
| **5** | **Wilson intervals on the scoreboard.** `recall 9/9` implies certainty we don't have; at 3 reps, 3/3 is consistent with a true rate from roughly 0.4 to 1.0. The header carries `recall a/b · FP c/d`, so this is **two** intervals. ~10 lines, stdlib. | **Opportunistic** — next time anyone is in `history_format.py`. Docs-honesty, not coding-quality. |
| **6** | **Gate-yield logging — already shipped; verify the shape, don't cut.** The first draft proposed cutting this. That was wrong on both counts. It exists (`_common.log_yield_event`, `bin/gate_yield.py`) and already carries every protection the cut-rationale claimed was missing: fail-safe by construction (docstring: "telemetry failing must never change enforcement"), read on the calibration cadence rather than a dashboard, retirement candidates gated behind ≥2 **committed** cycles of all-overridden blocks, absent data reported `unmeasured this cycle` never zero, and demotion machinery deliberately unbuilt until a candidate exists. More importantly it is the **muzzled-gate detector**: `suppressed` events are findings that fired while a gate was demoted to `off`, which is how the H8 family gets caught — from a live incident. Cutting it would remove that visibility layer. | **Keep. Verify, don't cut.** |
| **7** | **Cross-tier calibration.** Calibration defaults to `haiku`; gates tuned against one cheap model's failure modes may not hold for the doer models in use. Add a quarterly holdout run on the current doer tier, record both rows. | **Later.** Real risk, real model cost. "Run calibration on any doer-model upgrade" covers the acute case; this closes the chronic one. |

### 5.1 Yield and lift are different instruments

Worth stating explicitly, since the first draft conflated them:

| | **Yield** (shipped) | **Lift** (proposed) |
|---|---|---|
| Measures | Friction in the field | Counterfactual value |
| Source | Telemetry from real sessions | Controlled experiment on the corpus |
| Question | "Is this gate firing, and is anyone adjudicating it?" | "Would the defect have been caught without this gate?" |
| Read | Calibration cadence | Quarterly, one-off |

Neither ranks gates against each other. Both feed the same review. Under both, deletion pays the
toll.

---

## 6. Sequencing

1. **Symmetric-harness-break plants** — additive, cheap, closes a proven blind spot. No dependencies.
2. **Anti-ratchet (R1 + R2)** — guardrail lands *before* the instrument that needs it. Building the
   measurement first is how §2's flaw becomes a shipped mechanism.
3. **Dev/holdout split** — makes any subsequent number mean something.
4. **Lift diagnostic** — only now, with the contract-stub arm, as a one-off read.

Items 5–7 opportunistic or later.

**If work stops after steps 1 and 2, the playbook is net better and has gained almost no
complexity.** Deliberate: the sequence is ordered so that **every prefix is a coherent stopping
point.**

---

## 7. Owners and triggers

Per our own rule — a proposal with sequencing but no owners is a roadmap, and this repo doesn't ship
roadmaps. Proposed hooks (owner assignment is David's call):

| Item | Proposed trigger |
|---|---|
| 1 (plants) | Author before the ~2026-08-10 calibration run so they are **live-calibrated in the same pass**. Realistic: they ride the existing cycle, no new trigger needed. |
| 2 (R1 part 1 — coverage invariant) | Same pass; it's a harness check, and it REDs today, so it wants fixing with the `integration-adversary` scenario item 1 would author anyway |
| 2 (R1 parts 2–3, R2) | Registry `integration_debt` entry, dated expiry |
| 3 (holdout) | Next authoring cycle — the split is assigned at `--approve`, so it wants to land before the next batch, not after |
| 4 (lift) | Quarterly product review; blocked until 2 + 3 |
| 5, 7 | Opportunistic / deferred, no entry |

---

## 8. Explicit non-goals

Stated so they don't reappear as "obvious next steps":

- No lift dashboard, threshold, or automatic action (R3, R4)
- No gate ranking (R4) — absolute questions only
- No lift data in any vendored `.claude/` tree, agent body, or SKILL.md (R2)
- No corpus deletion, ever — already mechanically enforced; nothing here relaxes it
- No change to the weekly cadence — `check_staleness.py` + `run_calibration.py` stay as they are;
  everything here is quarterly or one-off
- **No removal of the yield instrument** — the first draft's item 6, reversed

---

## 9. Revision history

v2 incorporates peer review. Five claims checked against the repo; four accepted, two of those with
refinements, one half-correct.

| Claim | Outcome |
|---|---|
| Item 6 cut a shipped mechanism and would reopen the H8 visibility hole | **Accepted.** Verified `_common.py:114`, the `suppressed` event, `≥2 committed cycles` gating, and `unmeasured` reporting. Item 6 inverted; §5.1 added to keep yield and lift distinct. |
| §3's "an agent can be deleted and no gate notices" is false | **Accepted, with a refinement against the reviewer:** it's **7** of 10 protected, not 8 — `integration-adversary` is calibratable but has no scenario, so the derived-roster protection doesn't reach it. Found while checking the claim; now the lead argument for R1's coverage invariant. R1 restructured from journal-for-everything to coverage-invariant-first. |
| Item 4's control arm is confounded by house output contracts | **Accepted, and understated:** ~17 of 24 oracles key on format tokens, and the confound is **bidirectional** — control oracles key on `gate passes`, so the bare arm's FP number is equally meaningless. The contract stub must cover control verdict lines too. |
| Holdout needs pair-splitting and burn-on-failure | **Accepted.** Both folded into item 3; class-level grain adopted, answering open question 1. |
| Appendix SHA doesn't resolve; the prompting paper review was never committed | **Half-correct.** The anchor was wrong and is fixed — reads happened at `89abcbc`, and the first draft cited `911e06e`, which postdates them. But the paper review **is** committed, at `911e06e` on `claude/paper-review-2607-2dqbql`, pushed to origin; the review was reading `main` (HEAD `89abcbc`), where the branch's commits are not yet present. Nothing to commit; anchor corrected. |

Open questions 1 and 2 are now answered (class-level grain; separate journal file). Remaining:

3. **SKILL.md granularity.** R1 part 2 needs a concrete definition of a "section" — heading level, or
   an explicit manifest? — before it can be a test rather than a judgment.
4. **Lift for prose vs. agents.** Stripping an agent body is trivial (`agent_body()` is one
   function). Stripping a SKILL.md *section* while leaving the rest coherent is not. Scope before
   committing to item 4's prose half.
5. **New:** does the contract-stub arm need per-agent stubs (each agent has its own verdict
   vocabulary) or one shared stub? Per-agent is more faithful and more work; it also risks the stub
   growing until it *is* the doctrine, which would collapse the measurement.

---

## Appendix — verified against the repo at `89abcbc`

`89abcbc` is `main`'s HEAD and the state at which every read below was performed. The two documents
produced from it (this file and the paper review) are committed on
`claude/paper-review-2607-2dqbql` and therefore postdate it.

- `calibration/run_calibration.py` — `run_agent()` composes `agent_body(scenario["agent"])` + task
  and invokes `claude -p <prompt> --model <model> --max-turns <n>`; `known_agents()` derives the
  roster from `AGENTS_DIR` minus `TREE_TOUCHING_AGENTS`; `validate_scenario` L85-87 rejects unknown
  agents; `DEFAULT_REPEAT = 3`, `MAX_TURNS = "25"`, `TIMEOUT_S = 600`; default model `haiku`
- `calibration/scenarios.json` — 20 shipped scenarios; oracles are `must_match` / `must_not_match`
  regex lists; `control_for` marks paired clean controls
- `calibration/corpus/approved/` — 4 approved plants (24 scenarios total)
- Oracle-format audit — ~17 of 24 `must_match` sets key on a house verdict token or label
- `calibration/check_scoreboard_integrity.py` — the three invariants quoted in §3
- `plugins/tdd-playbook/hooks/scripts/_common.py:114` — `log_yield_event`, single write path via
  `emit()`, never raises; `suppressed` emitted at L148 when findings fire under `off`
- `plugins/tdd-playbook/bin/gate_yield.py` — 6-column rollups; `unmeasured this cycle` on absent
  log; candidates require ≥2 committed cycles with every block overridden; `suppressed > 0` flags a
  muzzled gate
- `scripts/install_into_repo.py` — `COPY_TREES` = `skills/tdd-playbook`, `commands`, `agents`,
  `bin`, `hooks/scripts`; `calibration/` absent
- `capabilities.json` — `agents/*.md` briefs on the CIVerd §1.3 extended watchlist; coverage
  unproven, debt expires 2026-09-15
- `plugins/tdd-playbook/agents/` — 10 agents, 8 calibratable, 7 scenario-covered
- `plugins/tdd-playbook/hooks/scripts/` — 8 hook scripts; `plugins/tdd-playbook/tests/` — 10
  planted-input suites; plugin version 1.21.0
