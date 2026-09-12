# Connectome calibration fixture — a second fixture family, sequenced behind a cheaper fix

Date: 2026-09-12 · Workstream: `connectome-calibration-fixture` · Status: DRAFT, pre-approval
§0a question pack: `docs/plans/gated/2026-09-12-flywire-calibration-fixture-questions.md`

## Origin (the requester's words, verbatim)

> "Assuming yo now understand the flywire brain 783, would there be a way to leverage it to
> train the playbook to become more and more accurate and efficient in terms of assisting AI
> to code better and better"

> "Still too technical - explain this in plain language and verify your claims before you do
> it. I love that it potentially could work but you need to walk me exactly thru how it would
> actually work for real and simply"

> "Pull together this plan with the plain explanation and all of the technical detail so I can
> share this. Also then send multiple adversarial agents at this plan."

## Spec integrity

**§0a question pack — dispatched, and it moved the plan.** `spec-producer` was dispatched with
the requester's words verbatim. It returned `Verdict: UNDERSPECIFIED — 14 load-bearing
questions`, two of which are FINDINGS that contradicted the original pitch. Both were
independently verified against source before being adopted (below). Honest note on order: the
plan's structure and measured evidence were written while the pack was still running; every
answer was folded in before any adversary was dispatched and before approval was sought. That
is weaker than "read the pack before you write a deliverable" and is recorded, not smoothed.

**Reading followed.** "Train the playbook" has two readings. (A) Use connectome data as training
material for a model. (B) Use connectome-derived code as *measurement* material for the
Playbook's verifier agents. This plan follows **(B)**; (A) is rejected on the record — the 783
dataset is a wiring diagram of a fly, contains no information about software, and no transfer
path to code quality is known.

**Scope disclaimer (pack Q1), stated because the request's words are broader than the work.**
This workstream moves **verifier recall/FP only**. It does NOT measure "does the Playbook make
coding better" — that is the `isolation` axis (`history_format.POPULATION_AXES`,
`run_calibration.py --isolation no-playbook`) and it is out of scope here. A recall number from
this workstream must never be quoted as evidence for the broader claim.

**CORRECTION 1 — a load-bearing claim in the originating pitch was FALSE.** The pitch said the
harness does not measure false positives. It does: `run_calibration.py:195-199` partitions
plants from controls and reports recall AND FP; 13 of 31 approved corpus plants are `control-*`;
`pairing_problems()` (`run_calibration.py:419`) enforces at set level that every
non-grandfathered plant has a paired clean control. **"FP scoring" is struck from the
deliverables.**

**CORRECTION 2 — the repo's own measurement contradicts this plan's premise, and it wins on
sequencing.** `calibration/oracle-changes.md`, entry `2026-08-05 (run 4)`, verbatim: *"THE
DIRECTIONAL DECISION, stated once: prose-VOCABULARY oracles are the weak link, not the agents.
Run 4 had ZERO plants survive to a clean verdict — every recorded 'miss' quoted a correct agent
verdict scored down on an adjective, a markdown asterisk, or a verb form."* The measured defect
is the SCORER, not the verifiers. This plan proposes harder material for the verifiers.

The synthesis, stated so it is a decision rather than a dodge: the two diagnoses are not
contradictory — "zero plants survived" is also what an over-easy fixture looks like — but the
ORDER is forced. **You cannot read a new fixture's results through a scorer that is known to
mis-score correct answers.** So the cheaper fix is piloted FIRST, and the fixture family is
sequenced behind it and made conditional on what the re-run shows.

**CORRECTION 3 — a licensing constraint that the original pitch did not know about.** FlyWire
v783 data is **CC BY-NC 4.0** (non-commercial). This repo is **Apache-2.0** and public. That is
a licence mismatch requiring a decision (D0.3 below), and it is the single most likely reason
this plan should not proceed in its current form. Mitigating fact, verified: `calibration/` is
NOT vendored downstream — `scripts/install_into_repo.py` contains no reference to it — so the
exposure is this repo only, not the repos the plugin installs into.

**Open questions carried to review, each with a proposed answer to refute:**
1. *Blocking or trend-only?* Proposed: **trend-only, in `PROMOTION_QUARANTINE` from birth**,
   until three runs of paired plant/control rows exist. Never blocking on the FP side.
2. *Does this re-introduce the retired cadence?* Proposed: **no clock, and the decay-detection
   goal is DROPPED from scope** — it was in the original pitch and it is removed here, because
   "it's fast so it may as well run every release" is exactly how the retired obligation returns.
3. *Corpus mix.* Proposed: **cap this family at 25% of the approved corpus.**
4. *Licence.* Proposed: see D0.3 — three options, David decides; no code until he does.

## Evidence (executed in-session, not estimated)

Source: `/home/user/snedea/flybrain/data/connections.csv.gz` (FlyWire Codex v783 download).

| Fact | Measured |
|---|---|
| Sub-circuit (`neuropil == AL_R`, right antennal lobe) | 3,392 neurons · 36,826 connections · 9,730 inhibitory |
| Reference run, stdlib-only (no numpy) | **13,759 spikes / 266 neurons** · byte-identical across runs · **1.35 s** · data **0.49 MB** |
| Plant A — sign flip (`ww` → `abs(ww)`), one line | 40,992 spikes (+197.9% drift, neuron overlap 39.8%); runs clean, no error |
| Plant B — 100-spike/neuron recorder cap, one line | 13,581 recorded (**178 spikes lost, 1.3%**); output well-formed |
| Plant B leaves the COMPUTATION untouched | **PROVEN**: final voltage-vector SHA over all 3,392 neurons is `4e74f3a2f86d8bad` for BOTH clean and planted runs — bit-identical state, different record |
| 6-check test suite (columns, valid ids, in-range times, non-empty, ordered) | **GREEN on all three** |
| Compare-to-reference check | A: exit 1 · B: exit 1 · clean-vs-clean control: 0.0%, exit 0 |
| Live `claude -p --model haiku`, neutral prompt, Plant B (numpy build) | **CAUGHT** — named the cap, said spikes are dropped silently, listed why each test check misses it |
| Same model, same prompt, CLEAN file | **FALSE POSITIVE** — claimed an off-by-one (3,000 × 0.1 ms = exactly 300 ms; its `+1` would overrun) |
| Candidate fixture vs `_FIXTURE_TELLS` | 4 files scanned, **0 tells** |

**CORRECTION 4, found while assembling this table (and the reason D2.4's design changed).** The
first draft of this evidence mixed two builds: the reference from the stdlib variant and the
plant figures from the numpy variant (17,145 → 40,341 / 14,816). Re-measured on ONE build above.
The re-measurement also exposed a design flaw in the POC's own comparison script: it used a **1%
drift threshold**, and plant B lands at **1.3%** — it passes by 0.3 percentage points, and a
slightly gentler cap would have been scored as "no defect". For a DETERMINISTIC fixture the
threshold is not just arbitrary, it is unnecessary: **D2.4 compares outputs for exact equality**,
not drift. Percentage bands belong to the stochastic cross-backend comparison this POC was
modelled on, not here.

Plants A and B are modelled on real defects in `eonsystemspbc/fly-brain` (fix `33f1727`,
pre-fix tree `3d2605d`): NEST GPU silently truncated spike recording at a per-neuron ceiling;
PyTorch drove stimulation into the wrong state variable. §13's "freeze the defect shape citing
the pre-fix sha" is satisfiable with a real sha.

## Phase 0 — pay the cheaper fix first (the materially simpler alternative, piloted)

Doctrine requires naming a materially simpler approach. Here it is not merely simpler, it is
**already owed and due in three days**, and it addresses the measured root cause.

- **D0.1 — flip the oracle normaliser default.** `normalize_for_oracle` is authored and
  unit-tested (`run_calibration.py:341-347`; `test_harness.py:3119-3143`) and deliberately not
  the default. Paying the `ORACLE NORMALISATION PASS` debt (expires **2026-09-15**) is a
  one-line default flip plus bumping `ORACLE_NORMALIZATION_VERSION` off `"identity-v1"`.
- **D0.2 — the other three debts on the same capability expire 2026-09-15**: `SUPERSEDE
  PROSE-ORACLE PLANTS`, `MUTATION-RUNNER CLEAN-RUN DESCRIPTION`, `APPLY_EDITS CREATE
  capability`. `test_capability_registry.py::test_own_registry` runs with the real date, so the
  suite REDs on 2026-09-16 whatever this workstream does.
- **D0.3 — the licence decision (BLOCKS all of Phase 2).** FlyWire v783 is CC BY-NC 4.0; this
  repo is Apache-2.0 and public. Three options, each with its cost:
  - *(a) Commit the derived sub-circuit* with a per-directory NOTICE and attribution. Cost: the
    repo is no longer uniformly Apache-2.0; a downstream commercial user inherits an NC file if
    the no-vendoring fact ever changes.
  - *(b) Generator script + hash manifest, data gitignored.* Cost: the fixture cannot run in a
    clean clone or in `.github/workflows/gate.yml` — it ships **dark**, which is the failure
    class the registry exists to catch.
  - *(c) Synthetic network with the same statistical shape* (sparse, signed, ~3k nodes). Cost:
    honest but uncomfortable — **the calibration value lives in the pipeline's shape, not in the
    neurons being real**, so (c) works, and it means the FlyWire connection is decorative. That
    directly contradicts the requester's words ("leverage the flywire brain 783"), so it is a
    decision for David and not one this plan may take quietly.

**Gate between phases:** after D0.1, re-run calibration and read recall/FP. If the run-4 finding
holds and the verifiers still catch everything through a non-brittle scorer, then the toy
fixture's ceiling is real and Phase 2 has a measured justification. If instead misses appear,
they are verifier misses and Phase 2 is not the highest-yield next move. **Phase 2 does not
start until this reading exists.**

## Phase 1 — ledger pre-registration (process, before any effectful diff)

- **D1.1.** `calibration/scenarios.json` and `calibration/corpus/approved/` are `EFFECTFUL`
  surfaces in `ledger.py:60-74`, where `expect: none` is a lie by construction, and an entry
  must exist BEFORE the diff. One pre-registered entry per effectful deliverable, predicting
  MOVEMENT in recall/FP (not significance — `power.py` shows per-entry significance is
  unobtainable at 3 reps).

## Phase 2 — the fixture family (CONDITIONAL on the Phase 0 gate and D0.3)

### D2.1 — The fixture (`calibration/fixture-connectome/`)
**What.** A stdlib-only leaky-integrate-and-fire simulation over the 3,392-neuron sub-circuit,
its data, and its own green test suite.
**Edge cases.** Provenance (a generator rebuilds the data; no unexplained blob); determinism
(seeded; byte-identical verified); no third-party dependency (stdlib only — measured 1.35 s, and
it also removes the numpy/BLAS ordering risk that would make a cross-machine reference unstable);
fixture legibility (0 tells, verified); green unplanted; size discipline (0.49 MB, must not grow
toward the 137 MB shape of `snedea/flybrain`).
**UX tests.** `--dry-run` reports the new fixture green-unplanted and legibility-clean; a broken
fixture exits non-zero naming it.
**Integration surface.** *Consumes:* `stage()`, `dry_run()`. *Emits → named consumer:* the staged
tree read at `run_calibration.py:319`; the fixture suite read at `run_calibration.py:698-701` —
existing readers, no new emitter. *Surface parity:* local CLI only, as `fixture/`. *Reverse
sweep:* none; sibling of `fixture/`, which is untouched. *Activation:* inert until a scenario
names it; ships with D2.3 so it is not dark.

### D2.2 — Multi-fixture support (a SCHEMA finding, not a preference)
**What.** A per-scenario `fixture` key defaulting to `"fixture"`, threaded through
`validate_scenario` (`:109`), both `shutil.copytree` sites (`:109`, `:319`) and
`fixture_legibility_problems(fixture_dir=FIXTURE)` (`:669`); `dry_run()` checks EVERY fixture.
**Why it is a finding.** `FIXTURE` is a module global (`run_calibration.py:36`) with four
readers; the proposal is **unrepresentable** without this. Discovering it mid-build is how scope
doubles.
**Edge cases.** All 33 scenarios + 31 corpus plants run unchanged with zero edits (corpus files
are byte-pinned forever by integrity rule (b) — a scheme needing back-fill is unbuildable);
unknown fixture name is REFUSED, never silently defaulted; both copy sites changed together or
validation and execution disagree; the per-fixture sweep reports how many it scanned, zero is a
refusal.
**Integration surface.** *Consumes:* `validate_scenario` (THE validator, D0). *Emits → named
consumer:* resolved path read at the two copytree sites. *Surface parity:* shipped scenarios,
corpus plants and `author_plants.py` proposals all inherit it through the one validator — if
`author_plants.py` cannot name a fixture, that is a deliverable here. *Activation:* on; default
preserves behaviour byte-for-byte.

### D2.3 — First plant set: 2 plants + 2 paired controls
`sign-flip-inhibitory`, `bounded-spike-recorder`, each with a clean control, into
`corpus/proposed/` for the existing human approval cycle.
**Edge cases.** R2 pairing shipped in the same change (no grandfather entry); agent assignment
(`observability-adversary`, `test-quality-adversary`) is a review question, not the author's
private choice; **task prompts must not hint** — the demo prompt disclosed the test suite's
contents and the shipped task must not; once approved, byte-pinned forever, so a wrong plant
costs a new id; form is **`dev`, registered explicitly** rather than by absence.
**Integration surface.** *Consumes:* `load_corpus()`, `pairing_problems()`, `plant-forms.md`.
*Emits → named consumer:* verdict rows in `docs/calibration/history.md`, read by `read_current()`
recall/FP, `plant_vitality.scenario_streaks`, `power.comparable_blocks`, `ledger.bind_entry`, and
`check_scoreboard_integrity` rule (a). *Surface parity:* Claude host only; the Codex history is
NOT populated here — stated divergence.

### D2.4 — Behavioural plant-validity check (the genuinely new mechanism)
**What.** At validation time: run the fixture clean, run it planted, and require BYTE-EXACT
inequality for a PLANT and byte-exact equality for its paired CONTROL. Exact comparison, no
drift threshold — see CORRECTION 4. **No stored golden file** — both sides are computed
from the current fixture on every check, so a fixture edit can never silently invalidate a stale
reference, and the immutability problem the pack raised (Q5: a reference under `corpus/approved/`
could never be legitimately updated) does not arise.
**What it is NOT.** It does not grade agents. Agents are still scored on prose, unchanged. It
gates CORPUS ADMISSION only — a deterministic check of a stochastic subject would be a flaky
gate. It is also distinct from `plant_vitality.py`, which asks "do agents still fail this plant"
from scoreboard streaks; this asks "is there a defect here at all", from behaviour.
**Edge cases.** A plant that changes nothing is refused (no agent could fail it honestly); a
control that moves the output is refused (it poisons the FP denominator); cost is 2 × 1.35 s and
only for fixtures declaring a behavioural entrypoint, so the toy fixture pays nothing; two clean
runs that differ fail CLOSED rather than reporting drift.
**Integration surface.** *Emits → named consumer:* problems join the existing `problems` list
consumed by `dry_run()`'s non-zero exit (`:693-710`) — the channel every other validation finding
already uses; no new sink.

### D2.5 — Population separation (highest-risk item; precedes any reading of D2.3 rows)
**What.** Connectome-fixture rows must not pool with toy-fixture rows in any recall/FP reading,
as Codex rows are kept out of the Claude denominator.
**Edge cases.** Five readers assume one population — `read_current`, `plant_vitality.scenario_streaks`,
`power.comparable_blocks`, `ledger.bind_entry`, `run_calibration.last_kind` (the AMBER×2 →
BLOCKING promotion). The 2026-08-15 two-tier plan records that two take no population parameter
today; adding one is a signature change, not a filter reuse. A cross-population comparator
corrupts history SILENTLY — own red-first suite, one case per reader.

## §6c Flow table

| flow | producer | consumer | liveness test |
|---|---|---|---|
| normalised agent text | D0.1 flip | `oracle()` match loop | existing `test_harness.py:3139-3143` |
| ledger entry | D1.1 | `ledger check` at gate | gate red if diff precedes entry |
| licence decision | D0.3 (human) | D2.1 build start | — prose, see below |
| staged fixture tree | `stage()` (D2.2) | doer sandbox | per-fixture green + legibility in `--dry-run` |
| scenario `fixture` key | scenario/corpus JSON | validator + both copy sites | unknown-fixture refused, not defaulted |
| plant-validity verdict | D2.4 | `dry_run()` problems → exit code | no-op plant refused; moving control refused |
| verdict rows | `append_history()` | recall/FP, vitality, power, ledger, integrity (a) | D2.5 red-first suite, one case per reader |
| population axis | D2.5 | the five readers | planted cross-population block fails to bind/promote |

## Unenforceable deliverables (prose)

- **D3.1 — the shareable explainer.** Plain-language write-up plus technical appendix. Acceptance
  bar (the requester's, Turn 2): a reader who is not David can follow it end-to-end without a
  repo checkout. Named as a deliverable because an unowned explainer does not get written.
- **D0.3 — the licence decision.** A human judgment, not a mechanism.

## Tripwire deliverable list

| # | Deliverable | BUILT | WIRED | ACTIVATED | EXERCISED |
|---|---|---|---|---|---|
| D0.1 | normaliser default flip | one-line change + version bump | `oracle()` default | on for all scoring | `test_harness.py:3139-3143` |
| D1.1 | ledger entries | entries exist | `ledger check` | pre-diff | gate red if missing |
| D2.1 | connectome fixture | files exist | staged by `stage()` | named by D2.3 | per-fixture `--dry-run` |
| D2.2 | multi-fixture support | `fixture` key | validator + 2 copy sites | default preserves behaviour | unknown-fixture + default cases |
| D2.3 | 2 plants + 2 controls | corpus files | `load_corpus()` + pairing | live next run | `--dry-run` validates four |
| D2.4 | plant-validity check | check exists | called from validator | on where entrypoint declared | no-op-plant + moving-control cases |
| D2.5 | population separation | axis + param | five readers | pooling impossible | red-first suite per reader |
| D3.1 | explainer | document | — | — | none (prose) |

## Risks, stated

- **The premise may not survive Phase 0.** If a non-brittle scorer still shows the verifiers
  catching everything, this plan's justification weakens rather than strengthens. That is the
  point of sequencing it second, and stopping there is a cheap, successful outcome.
- **The licence may kill the FlyWire framing.** Option (c) preserves every calibration property
  and discards the thing the requester actually asked for. Naming that trade is David's call.
- **D2.5 edits shared history readers**; a mistake corrupts the scoreboard silently.
- **Overfitting** the corpus to numerical pipelines; mitigated by the 25% cap.

## Loop closed

Pending — adversaries dispatched on this draft; result recorded here before approval is sought.
