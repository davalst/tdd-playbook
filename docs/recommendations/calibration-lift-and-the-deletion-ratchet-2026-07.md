# Calibration Lift and the Deletion Ratchet

**A design decision on how to measure whether the playbook's gates earn their keep — without
building a mechanism that erodes them.**

Date: 2026-07-30 · Repo: `davalst/tdd-playbook` · Status: proposal, not yet implemented
Prompted by: review of arXiv:2607.21627, *Do Modules Stay in Their Lane? Role Drift in Compound
LLM Systems* (`docs/evaluations/paper-review-role-drift-2607.21627-2026-07.md`)

---

## 1. Why this document exists

A paper review turned into a self-audit, which turned up a genuine design flaw in the fix the
review recommended. This document records the flaw, the architectural rules that neutralize it, and
a revised — significantly *smaller* — set of changes.

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
4. So the review proposed adding a **no-agent control arm** to measure *lift*
   (`caught_with − caught_without`) per gate, and noted we could then delete gates showing no lift.

Step 4 contains the flaw. It is worth writing down because it is a class of error, not a one-off:
**a measurement whose only available action is subtraction will, given enough time, subtract
everything.**

---

## 2. The finding: the deletion ratchet

### 2.1 The mechanism

Lift is a *ranking*. A ranking always has a bottom. If the operational rule is "cut the
lowest-scoring gate," then after each cut the next-lowest becomes the new obvious candidate, and the
argument for cutting it is identical in form to the argument that justified the last one. The
process has no natural stopping point, because "worst of the remaining set" is defined no matter how
small the set gets. Nothing in the metric knows the difference between *pruning decoration* and
*disassembling protection*.

### 2.2 The friction asymmetry — the part that makes it inevitable rather than merely possible

Under current process, the two directions cost radically different amounts:

| Direction | Cost today |
|---|---|
| **Add** a gate | Author a plant (`author_plants.py`), pass validation, pair it with a clean control (`control_for`, mechanically required), human review, `--approve` |
| **Remove** a gate | Delete a file |

Adding is deliberately expensive; removing is free. A door with a spring on one side only is not a
two-way door. Over a long enough horizon the corpus grows and the gate set shrinks — exactly
backwards from what the playbook is for. This is the same structural insight as the paper's, applied
to our own process: the metric we would be optimizing (lift) is silent about the property we
actually care about (retained protection).

### 2.3 A zero-lift reading is ambiguous, and only one reading means "delete"

This is the technical crux. A gate can score zero lift for four distinct reasons:

| Cause | Correct response |
|---|---|
| It is genuinely redundant with another gate | **Cut candidate** — the only one |
| The plant is too easy; a bare model catches it anyway | **Strengthen the plant** |
| The 20-scenario suite doesn't cover the situation this gate exists for | **Add a scenario** |
| `DEFAULT_REPEAT = 3` is too small to separate signal from noise | **Get more data before acting** |

Three of four causes call for *adding* work to the corpus. One calls for cutting. A naive
lift-driven process inverts that distribution — it reads all four as the fourth. So the default
resolution must be the majority behavior, expressed as a rule that sits alongside the one already
in force:

> **Existing rule:** a plant surviving to a clean verdict is a BLOCKING failure —
> *fix the agent, never the plant.*
>
> **New sibling rule:** a gate showing no lift is a question, not a verdict —
> *strengthen the plant, never delete the gate.*

Deletion remains available. It just has to cost what addition costs.

### 2.4 Blast radius: only the judgment layer is exposed

The risk is narrower than it first appears, which matters for sizing the response.

- **Mechanical layer — not exposed.** The PreToolUse guards wired by the installer
  (`test_lock_guard`, `snapshot_guard`, `overmock_guard`) and the other scripts under
  `plugins/tdd-playbook/hooks/scripts/` are covered by deterministic planted-input tests in
  `plugins/tdd-playbook/tests/`. A planted violation is either blocked or it isn't. Binary, no
  ranking, nothing to game, no lift measurement involved.
- **Judgment layer — exposed.** The ten adversary agents in `plugins/tdd-playbook/agents/` and the
  prose of SKILL.md. These are what lift would score, and they are also the cheapest things in the
  repo to delete.

So the guardrail only has to cover agents and prose. That keeps it small.

---

## 3. What already protects us, and what doesn't

We solved this problem once already — on the corpus side, and mechanically rather than by
discipline.

**`calibration/check_scoreboard_integrity.py`** enforces, against a baseline revision:

- `history.md` is append-only (baseline content must be a byte-*prefix* of the candidate)
- the approved corpus only grows, and approved plants are **immutable**
- oracles are never weakened without a journal entry in `calibration/oracle-changes.md` — and that
  journal is itself append-only under the first rule, so it cannot be retroactively rewritten

It runs in the release gate and is additionally enforced by `calibration/test_harness.py` against
the latest tag on every suite run. This is the F5 pattern applied correctly: the invariant is a
script, not a memory.

**Nothing equivalent covers the gate set.** There is no check on
`plugins/tdd-playbook/agents/` or on SKILL.md. An agent can be deleted and no gate notices.

That asymmetry is the actual gap. The corpus is protected from shrinking; the thing the corpus
*tests* is not.

---

## 4. Design rules

Four invariants. Each is intended to be mechanical — a script or a test, not a convention.

**R1 — Gate removal costs what gate addition costs.**
Extend `check_scoreboard_integrity.py` to treat `plugins/tdd-playbook/agents/*.md` and the SKILL.md
section inventory as protected: removal requires a dated entry in a journal (reuse
`oracle-changes.md` or add a sibling) that is itself append-only. Estimated ~20 lines, reusing the
existing baseline-diff machinery. **Build this before building anything that measures lift.**

**R2 — Lift data never reaches a coding agent.**
If a working agent can see "gate X has low lift," it has been handed a written argument for
ignoring gate X. That is a worse failure than gradual erosion, because it is immediate.

We are currently safe by accident: `scripts/install_into_repo.py`'s `COPY_TREES` is
`skills/tdd-playbook`, `commands`, `agents`, `bin`, `hooks/scripts` — `calibration/` is absent, so
none of this data vendors downstream. Convert the accident into an invariant with a one-line test
asserting `calibration/` never lands in `.claude/`. Then the boundary cannot erode by someone
helpfully extending the copy list.

**R3 — Lift is a quarterly diagnostic, not a metric.**
It is a property of the playbook as a product, not of any coding session. It belongs to a periodic
product review, produces prose findings, and lives in `docs/`. Not a dashboard, not a threshold, not
on any hot path, and explicitly *not* part of the weekly calibration cadence.

**R4 — Gates are evaluated against their own purpose, never ranked against each other.**
Ranking is what creates the bottom of the list. Ask "does this gate catch the thing it was written
to catch?" — an absolute question with a stable answer — not "is this gate better than that one?"

---

## 5. Revised recommendation set

Filtered against the operative test: **does this make Claude-in-the-playbook produce better code, or
is it bloat that dilutes what already works?** Three items changed rank on that basis, including one
cut entirely.

| # | Item | ROI verdict |
|---|---|---|
| **1** | **Symmetric-harness-break plants.** Several checks are *differential* in shape — `mutation-runner` (suite on mutated vs. clean code), `red-first-verifier` (fails before the fix, passes after), `snapshot_guard`. Any check of that shape is blind to a break that degrades **both** sides equally: a suite that fails on everything, a scope resolving to nothing on both arms, a harness erroring identically pre- and post-fix. Add one plant per differential check. | **Highest.** Purely additive, uses the existing pipeline, no new machinery, no ranking, nothing to game. Closes a blind spot we hit for real on 2026-07-27 (`vacuous-mutation-scope` BLOCKING FAIL) and found by luck rather than by design. |
| **2** | **Anti-ratchet: R1 + R2.** Journal requirement for agent/prose removal; test asserting `calibration/` never vendors into `.claude/`. | **High, and a precondition.** Small, reuses trusted machinery, and it must exist before item 4 or item 4 is net-negative. |
| **3** | **Dev/holdout split of the corpus.** Assign each plant + paired control to `dev` or `holdout` at `--approve` time (deterministic hash of the id, so it isn't selectable). Guard fixes may only consult `dev` failures. `holdout` runs quarterly, never drives a fix, and is the number quoted externally. | **High for honesty, low cost** — one JSON field, one filter flag. Today the tuning loop and the reporting loop share the same plants: the rule "fix the agent, never the plant" means we iterate until a plant passes, then report the catch rate on that plant. The `csv-escape-fixed-at-call-site` history (failed twice, then passed) is what that looks like from the inside. This is also the precondition for any lift number being trustworthy. |
| **4** | **Lift diagnostic** — a no-agent control arm, run once, quarterly, on the holdout. Answers "which of the ten agents and which SKILL.md sections actually change behavior?" | **Real but indirect, and gated on 2 + 3.** The value is not "delete things," it is *finding decoration* — because dead prose is not neutral. It consumes context and competes with the instructions that do steer, which is the "bouncing around, doesn't know what to do" failure. Safe to look at only once cutting is expensive. |
| **5** | **Wilson intervals on the scoreboard.** `recall 9/9` implies certainty we don't have; at 3 reps, 3/3 is consistent with a true rate anywhere from roughly 0.4 to 1.0. ~10 lines, stdlib. | **Do it opportunistically** — next time anyone is in `history_format.py`. A docs-honesty fix, not a coding-quality one. |
| **6** | **Block-event logging** (JSONL of guard blocks and their resolutions). | **CUT.** Over-recommended in the original review. Hooks are on the hot path, so a logging write path is real risk for a small payoff; the data is unlikely to be read; and a "demote rate" metric quietly invites demotion — the same ratchet in different clothes. |
| **7** | **Cross-tier calibration.** Calibration defaults to `haiku`; gates tuned against one cheap model's failure modes may not hold for the doer models actually in use. Add a quarterly holdout run on the current doer tier and record both rows. | **Later.** Real risk, real model cost. The existing "run calibration on any doer-model upgrade" policy covers the acute case; this closes the chronic one. |

---

## 6. Sequencing, and why this order

1. **Symmetric-harness-break plants** — additive, cheap, closes a proven blind spot. No dependencies.
2. **Anti-ratchet (R1 + R2)** — the guardrail lands *before* the instrument that needs it. Building
   the measurement first and the guardrail later is how the flaw in §2 becomes a shipped mechanism.
3. **Dev/holdout split** — makes any subsequent number mean something.
4. **Lift diagnostic** — only now, and as a one-off read rather than a cadence.

Items 5–7 are opportunistic or later.

**If work stops after steps 1 and 2, the playbook is net better and has gained almost no
complexity.** That is deliberate: the sequence is ordered so that every prefix of it is a coherent
stopping point.

---

## 7. Explicit non-goals

Stated so they don't get reintroduced as "obvious next steps":

- **No lift dashboard, threshold, or automatic action.** R3, R4.
- **No gate ranking.** R4. Absolute questions only.
- **No lift data in any vendored `.claude/` tree, agent body, or SKILL.md.** R2.
- **No new logging on the hook hot path.** Item 6, cut.
- **No change to the weekly cadence.** `check_staleness.py` + `run_calibration.py` stay as they are;
  everything proposed here is quarterly or one-off.
- **No corpus deletion, ever.** Already mechanically enforced; nothing here relaxes it.

---

## 8. Open questions

1. **Holdout ratio.** 70/30 dev/holdout is a guess. With only 20 shipped scenarios + 4 approved
   corpus plants, a 30% holdout is ~7 scenarios — thin. Options: start at 80/20 and let the holdout
   grow as the corpus grows, or hold out whole *plant classes* rather than individual plants (better
   generalization signal, coarser).
2. **Where the removal journal lives.** Reuse `oracle-changes.md` (one append-only file, simpler) or
   add `gate-changes.md` (clearer separation of concerns, second file to protect)?
3. **SKILL.md granularity.** R1 protects "the section inventory" — needs a concrete definition of a
   section (heading level? an explicit manifest?) before it can be a test rather than a judgment.
4. **Lift for prose vs. agents.** Stripping an agent body is trivial (`agent_body()` is one
   function). Stripping a SKILL.md *section* while leaving the rest coherent is not. Worth scoping
   before committing to item 4's prose half.

---

## Appendix — verified against the repo at `911e06e`

Claims in this document rest on the following, read directly rather than recalled:

- `calibration/run_calibration.py` — `run_agent()` composes `agent_body(scenario["agent"])` + task
  and invokes `claude -p <prompt> --model <model> --max-turns <n>`; `DEFAULT_REPEAT = 3`,
  `MAX_TURNS = "25"`, `TIMEOUT_S = 600`; default model `haiku`
- `calibration/scenarios.json` — 20 shipped scenarios; oracles are `must_match` / `must_not_match`
  string lists; `control_for` marks paired clean controls
- `calibration/corpus/approved/` — 4 approved plants
- `calibration/check_scoreboard_integrity.py` — the three invariants quoted in §3
- `scripts/install_into_repo.py` — `COPY_TREES` = `skills/tdd-playbook`, `commands`, `agents`,
  `bin`, `hooks/scripts`; `calibration/` absent
- `plugins/tdd-playbook/agents/` — 10 agent definitions
- `plugins/tdd-playbook/hooks/scripts/` — 8 hook scripts;
  `plugins/tdd-playbook/tests/` — 10 planted-input suites
