# RSI Hardening — Closing the Update Loop on the Verification Substrate

Date: 2026-08-05 · Repo: `davalst/tdd-playbook` · Status: **RATIFIED** (2026-08-05,
David) with his sequencing: Phase 0 authorized immediately (backfill committed with this
revision); Phases 1–4 stand ratified **conditional on Phase 0's §3 kill row not firing**
at the ~2026-08-10 run. All three ⚑ decisions are resolved — recorded in place (§4,
§6.1, §10) and in the ratification record (§12).
Prompted by: `docs/evaluations/two-agent-recursive-loops-2026-08.md` (external analysis of
two-agent recursive-improvement loops, committed alongside this plan) and the RSI placement
review performed in the same session.
Builds on: `docs/plans/calibration-lift-and-deletion-ratchet-2026-07.md` (**RATIFIED**, v3) —
this plan does not redesign anything that document settled. Its deferred set
(holdout · lift · cross-tier, the `calibration-loop` QUARTERLY BUNDLE debt, expires
**2026-11-01**) is *executed* here, not reopened.

---

## 1. Thesis

The external analysis converged, from first principles and literature, on the architecture
this repo already runs: a closed loop of models cannot verify its own improvement; every
real gain lives in scaffolding with different incentives — held-out plants, planted
mutations of the scorer, paired clean controls, pre-registered criteria, an independent
signed verdict engine, append-only history, a decaying item bank with budgeted refresh.
That is the playbook + CIVerd + memrebel stack, component for component.

What the stack does **not** yet have is the RSI core: a **measured update loop**. Process
mutations (agent-brief fixes, oracle adjudications, new guards, knob changes) land with an
*implicit* expected effect and are never scored against it. `976364f` (the 2026-08-04
adjudication) is the perfect specimen: seven distinct process mutations, each with a clear
implicit prediction ("this scenario's 0/3 becomes 3/3 for THIS reason"), none of which the
next run will mechanically confirm or refute. Under §13, that is the loudest gap left:
improvement events we experience but never verify.

Three imports close it, in this order of leverage:

1. **The improvement ledger** — pre-registered expected effect per gate-surface mutation,
   scored mechanically by the next live run. Turns guard accretion into measured selection.
2. **Execution of the ratified deferred bundle** — holdout split, then the lift read with
   the frozen contract stub, plus a plant-vitality instrument and a power line so
   "improved" has a noise floor.
3. **External verifiability** — CIVerd signs a memproof-2 attestation over each live
   calibration run, making recall/FP/lift numbers offline-verifiable by an outsider. This
   is the WS5 public-scoreboard input and the product seed.

## 2. Non-goals (stated so they don't reappear)

- **No two-agent conversational loop.** The analysis's own Part III + the ICLR 2025
  multi-agent-debate evaluation say it loses to matched-budget controls. Our
  doer/plant-author pair is already a *grounded* adversarial loop (mechanical verdicts, not
  mutual opinion) — strictly stronger. The analysis's value here is its checklist, not its
  architecture.
- **Nothing relaxes the deletion ratchet.** R1–R4 stand. Ledger verdicts never rank gates,
  never feed deletion, never appear in vendored trees (R2's boundary extends to
  `calibration/ledger.md`). A REFUTED entry is a question routed through the four-cause
  table (§2.3 of the ratified plan), never an auto-revert.
- **No wire-format change.** memrebel is frozen; the attestation must fit `civerd-1` and
  the existing snapshot schema unchanged, or the work STOPS and comes back to David as a
  `memproof-3`-class decision. (Expected outcome: no change needed — see Appendix B.)
- **No lift dashboard, threshold, or hot-path metric** (R3 stands; lift remains a
  quarterly diagnostic read on holdout).
- **No new weekly chores.** The ledger adds one step *at change time* (write the entry you
  were already implying) and zero steps at run time (scoring is mechanical).

## 3. Pre-registered success and kill criteria

This plan eats its own dogfood: the criteria are written before any phase runs.

| Phase | Success looks like | Kill / rethink trigger |
|---|---|---|
| 0 | ≥80% of `976364f`'s backfilled entries score CONFIRMED on the ~2026-08-10 run | <50% CONFIRMED → the adjudication was narrative, not repair; stop and re-adjudicate before authoring anything new |
| 1 | `ledger.py check` red on a planted uncovered diff; first natural cycle scored | Entries degenerate into `no-effect-expected` boilerplate (>⅓ of entries in a cycle) → scope rule wrong, revisit |
| 2 | Holdout live; power line printed; lift read lands with pre-registration hash | Lift ≤ stub-arm noise floor → the "process improves agents" claim dies (§11); verification-infra value stands |
| 3 | A signed attestation bundle verifies via unmodified `verify_verdict.py` | Any pressure to change predicate/schema/reason strings → STOP, David decision |
| 4 | Vitality trend feeds authoring targets each cycle | Adversary-tier authoring produces only saturated-on-arrival plants two cycles running → escalation ceiling reached; incident mining becomes the sole refill |

## 4. Phase 0 — the run we already owe (trigger: ~2026-08-10 live run)

No new machinery. Two actions, in order:

1. **Backfill the ledger for `976364f`** — **DONE 2026-08-05, this commit:**
   `calibration/ledger.md` seeded with 14 open entries (one per scenario the 08-04
   adjudication touched, derived from `oracle-changes.md` + the commit, each with baseline
   and expected direction) plus 4 **already-scored** entries for the 2026-08-03 fixes,
   which the 08-04 run scored: 3 CONFIRMED, 1 REFUTED with disposition
   (`control-cachebusted-run` — the 08-03 oracle anchor didn't resolve it; the real cause
   was the implausible mutant counts, found 08-04). The instrument's first refutation is
   on the books before the tool exists.
2. **Run the ~2026-08-10 live calibration** (David; real `claude` binary, non-root, per
   CLAUDE.md). Its history append is scored against the backfilled entries by hand this
   once (ledger.py doesn't exist yet); the hand-scoring becomes the acceptance fixture for
   `ledger.py score` in Phase 1.

⚑ **Decision 0 — RESOLVED (2026-08-05):** Phase 0 approved immediately; the rest of the
plan is ratified conditional on Phase 0's score (§3 kill row). The 08-10 run is therefore
both a calibration and this plan's own first prediction test.

## 5. Phase 1 — the improvement ledger (v1.26; the RSI core)

### 5.1 The artifact

`calibration/ledger.md` — append-only, added to `check_scoreboard_integrity.py`'s
protected list (byte-prefix rule, same as `history.md` / `oracle-changes.md` /
`gate-changes.md`). One table row per entry:

```
| id | date | surfaces | evidence | expected effect | score-by | actual | verdict | disposition |
```

- **surfaces** — paths touched (gate surfaces only; scope in §5.3).
- **evidence** — the motivating history row / incident sha (`history.md 2026-08-04
  control-genuine-red-first 0/3` or a repo incident ref). No entry without evidence: a
  change nothing motivated is a change nothing can score.
- **expected effect** — ≥1 *named scenario* plus a *direction* (`0/3→3/3`,
  `AMBER→PASS`, `no-effect-expected`). Free prose without a scenario+direction is
  **rejected at validate** — the analysis's load-bearing TDD borrow: if you can't write
  the check, you don't have a well-posed change.
- **verdict** — `CONFIRMED` / `REFUTED` / `INCONCLUSIVE(power)` — the third exists so
  small-N never silently rounds to confirmation; its threshold comes from the §6.3 power
  line, single source.
- **disposition** — mandatory for REFUTED: which of the four causes (§2.3 of the ratified
  plan, adapted: wrong fix / plant moved / oracle drift / underpowered) and the follow-up.
  A REFUTED row with an empty disposition is a red suite, not a judgment call.
- `no-effect-expected` is a legal expected effect (typo/comment class) — and it is
  *scored*: a no-effect change that moves any verdict is itself a finding (silent coupling).

### 5.2 The tool — `calibration/ledger.py` (stdlib only; plugin invariant)

| Subcommand | Behavior |
|---|---|
| `validate` | Schema + the scoreable-effect rule; exits nonzero on any malformed entry |
| `check --baseline-rev <tag>` | Diffs gate surfaces since baseline; any diff without a covering entry → nonzero. Reuses rule (d)'s surface list and diff machinery |
| `score` | Joins open entries (score-by ≤ latest run date) against `history.md` rows via `history_format.py`; writes actual + verdict as a NEW appended adjudication row (append-only — never edits the original entry) |
| `report` | Confirmation-rate rollup for the tail line |

`run_calibration.py`'s tail gains one pointer line (`LEDGER: n open · confirmation rate
x/y last cycle` — same pattern as DATAFLOW TREND: a pointer, not the check).

### 5.3 Scope rule

Entries required for diffs to: `plugins/tdd-playbook/agents/*.md`, SKILL.md `##` sections,
`plugins/tdd-playbook/commands/*.md`, `calibration/scenarios.json` oracles + run knobs
(`max_turns`, model), corpus approvals. **Not** required for: docs, tests, hooks/bin code
(those carry planted-input tests — a different, already-mechanical contract). This is
deliberately the rule-(d) list plus oracles: the surfaces whose changes alter what the
gates *catch*, which is exactly what the next run can score.

### 5.4 Red-first planted tests (in `calibration/test_harness.py`)

1. Scratch repo, planted agent-brief diff, no entry → `check` red; with well-formed entry
   → green (paired control).
2. Entry with prose-only expected effect → `validate` red; scenario+direction → green.
3. Planted REFUTED row, empty disposition → red.
4. Planted `no-effect-expected` entry whose scenario moved → `score` flags it.
5. **§13 v1.25 replay against the motivating artifact:** run `check` against
   `976364f^..976364f` with `ledger.md` absent → red — the mechanism catches the exact
   commit that motivated it; frozen as a fixture citing the sha in its docstring.
6. Integrity: `ledger.md` byte-prefix violation → `check_scoreboard_integrity` red
   (planted, with clean control).

### 5.5 Integration surface (per deliverable, per house rule)

- **Consumes:** gate-surface git diffs; `history.md` rows (via `history_format.py`).
- **Emits →** named consumers: `run_calibration.py` tail (LEDGER line);
  `scripts/civerd_gate.sh` (new `ledger.py validate` + `check` steps); release gate
  checklist; CIVerd daily `ledger-coverage` check (Phase 3).
- **Surface parity:** cloud = local — `ledger.py` is repo-side (`calibration/`), never
  vendored (R2 boundary test extended to assert it).
- **Reverse sweep:** no writer-without-reader — every entry has a `score-by` date; `score`
  flags entries past due, so the journal cannot silently become write-only.
- **Activation:** `civerd_gate.sh` runs it on every suite invocation from v1.26; the
  release gate blocks on it; CIVerd arms it independently in Phase 3.

§6c flow table:

| flow | producer | consumer | liveness test |
|---|---|---|---|
| expected-effect entry | author at change time | `ledger.py score` at next live run | planted past-due unscored entry → red |
| scored verdict | `ledger.py score` | `report` tail line + quarterly review | planted REFUTED-no-disposition → red |
| uncovered-diff signal | `ledger.py check` | release gate + CIVerd daily | planted uncovered diff → red (fixture cites `976364f`) |

Tripwire legs: **BUILT** (tool + tests) · **WIRED** (`civerd_gate.sh` + release gate,
through the production entrypoint, not a self-assembling fixture) · **ACTIVATED** (first
green `check` in the v1.26 release run) · **EXERCISED** (planted fixtures red-first + Phase
0 backfill scored by a live run). Registry: new `improvement-ledger` capability entry;
`validate` must pass before commit.

## 6. Phase 2 — execute the ratified deferred bundle (v1.27 + quarterly)

Execution of the deletion-ratchet plan §5 items 3, 4, 7 **as ratified** (pair-class split,
burn-on-failure, contract-stub arm, stub-freeze rule, quarterly cadence — none of that is
reopened here), plus three additions from the analysis:

### 6.1 Holdout split — with the contamination decision made explicit

As ratified, plus: ⚑ **Decision 1 — RESOLVED (2026-08-05): option (a), plus a standing
rule effective immediately.** A plant published in a public repo is *burned on a
model-generation fuse* — future doer models train on the answer key (the GSM8k→GSM1k
lesson). Resolution:

- **Standing rule, effective now:** holdout material never appears in anything
  open-sourced or published — including the WS5 public scoreboard, which publishes
  *results and signed verdicts*, never plants. This rule outlives any future
  "let's open-source the repo" decision and must be re-cited in that decision.
- **Mechanism:** holdout classes live in a **private sibling repo**; this repo records
  each holdout plant's **content hash**, so the integrity checker's corpus-immutability
  rule extends across the boundary — privacy without weakening auditability. Required
  before the first holdout assignment at `--approve` or before any repo-visibility
  change, whichever comes first.

Mechanism: `holdout` assignment at `--approve` (class grain, pair rides along);
`run_calibration.py` selects the dev form by default, `--form holdout` for quarterly
reads; **leakage tripwire** — holdout plant ids / fixture content must not appear in gate
surfaces or any vendored tree (planted test: seed a holdout id into an agent brief → red;
control: dev-form id → allowed).

### 6.2 Plant-vitality instrument (new, small)

`calibration/plant_vitality.py` — derives per-scenario streaks from `history.md` (already
machine-parseable; dates injected for tests, no clock). Classifies: **saturated** (all-reps
green ≥K consecutive live runs; default K=4) / **discriminating** / **failing**. Consumers,
in compliance with the anti-ratchet: the **authoring cycle** (a saturated plant names the
next harder sibling's target; a saturated class is a rotation-to-holdout candidate) and the
quarterly review. Explicitly **not** a deletion driver — the corpus only grows; vitality
answers "does this plant still discriminate?" (R4's absolute question), never "which plant
is worst?". One tail line: `VITALITY: s saturated / d discriminating / f failing`. Planted
tests on fabricated histories, paired controls.

### 6.3 Power line

Run-tail line computing, from reps × selected-form composition, the **minimum detectable
regression** (exact binomial, `math.comb`, stdlib): e.g. "at 3 reps × N scenarios, a true
recall drop of <X points is invisible". Single source for the ledger's
`INCONCLUSIVE(power)` threshold and for the Wilson intervals already in the header (v1.22
item 5). Converts the ratified plan's "get more data before acting" from prose to a
number, and turns corpus growth from hygiene into a target.

### 6.4 Lift read — with pre-registration

As ratified (contract-stub arm; ONE frozen stub, hash recorded, oracle-fix-never-stub-grow
rule). Addition: a **pre-registration file** committed *before* the run — arms, matched
budget caps, holdout form hash, analysis script — which `run_lift` refuses to run without;
the results row records the pre-registration's sha. This is the analysis's
pre-register-the-scoring-function discipline made mechanical, and it is what makes the
resulting number externally quotable. Results land in `docs/calibration/quarterly.md`
(existing clock) and are attested (Phase 3).

### 6.5 Cross-tier row

Item 7 as ratified: quarterly holdout run on the current doer tier, riding 6.4's
machinery. First execution due before the 2026-11-01 bundle expiry.

## 7. Phase 3 — external verifiability (CIVerd attestation; the product seed)

Engine-side work; full session prompt in **Appendix A**. Summary of the contract:

1. **`ledger-coverage` daily check** — CIVerd runs `python3 calibration/ledger.py check
   --baseline-rev <latest tag>` on its timer, exactly the `staleness` pattern. Arming
   order (fail-closed discipline: absence of evidence is RED, so sequence matters):
   advisory from when v1.26 ships → **required** at v1.27, promotion journaled.
2. **Calibration attestation** — on a `history.md` append to main, CIVerd executes the
   deterministic validators (scoreboard integrity vs latest tag, staleness real-date,
   `ledger.py check` + `score --verify`, the harness suite) as recorded checks and issues
   a signed `civerd-1` memproof-2 bundle pinned to that commit. **Hard constraint: no
   predicate, schema, or reason-string change** — the unmodified stdlib
   `verify_verdict.py` and the cross-validation corpus
   (`tests/fixtures/civerd_crossvalidation_corpus.json`) must stay green. If that can't
   hold, the work stops and returns to David (memproof-3 territory).
3. **Planted-error tests per CIVerd's own convention** — tampered history → red verdict;
   uncovered gate-surface diff → red; clean controls green; e2e on a scratch repo.

Why this is the product seed: a signed, replayable, offline-verifiable "state of the
gates" artifact (recall · FP · lift · ledger confirmation rate) is the thing no agent
vendor can currently produce about their own improvement claims. It feeds WS5's public
scoreboard without trusting the publisher — memrebel's whole point.

## 8. Phase 4 — corpus supply line (standing triggers, minimal build)

- **Incident mining:** every adjudicated live-run failure and every real Playbook-repo
  incident becomes a plant candidate at the next authoring cycle (extends the
  HACK_CATALOG ritual's bottom-section flow). Real defect distributions are the one
  refill self-play cannot saturate. The `create`-capability debt (expires **2026-09-15**)
  is load-bearing here and unchanged by this plan.
- **Escalation-ceiling watch:** the vitality saturated-share trend is the early-warning
  line (kill row in §3). Read it at each quarterly alongside the dataflow trend.

## 9. Sequencing · owners · triggers

Ordered so **every prefix is a coherent stopping point** (house rule):

| Step | What | Owner | Trigger / due |
|---|---|---|---|
| 0 | Ledger backfill for `976364f` (**done 2026-08-05**) + live re-run scores it | David (run) | ~2026-08-10 run |
| 1 | `ledger.py` + tests + gate wiring + integrity protection → **v1.26** | agent session | after 0 scores; nothing else ships first if 0's kill row fires |
| 2a–2c | Holdout split (Decision 1 resolved: private sibling + public hashes) · vitality · power line → **v1.27** | agent session; David creates the private repo | next authoring cycle (split assigned at `--approve`, so before the next batch) |
| 2d–2e | Lift read (pre-registered) + cross-tier row | David (needs `claude` binary + budget) | quarterly clock; before **2026-11-01** debt expiry |
| 3 | CIVerd checks + attestation (Appendix A prompt) | CIVerd session | after v1.26 tags (advisory), required at v1.27 |
| 4 | Incident mining + ceiling watch | standing | each cycle / quarterly |

## 10. Release-gate and version deltas

- **v1.26:** ledger tool + `civerd_gate.sh` steps + integrity protected-list extension +
  registry entry + R2 boundary test extension. CHANGELOG + both version files, per house
  rule.
- **v1.27:** holdout mechanism + leakage tripwire + vitality + power line; CIVerd
  `ledger-coverage` promoted to required.
- ⚑ **Decision 2 — RESOLVED (2026-08-05): adopted.** The v2.0 gate is now the existing
  "≥1 month live calibration history" **plus**: **(a) ≥1 lift read on holdout, completed
  and its result stated in the positioning** — an honesty gate, not a score threshold: a
  disappointing lift number doesn't block v2.0, an *unstated* one does — and **(b) ≥2
  ledger cycles with a reported confirmation rate**. Rationale: v2.0's positioning claim
  is "measured process improvement"; these are the two numbers that make the claim
  falsifiable, and they must be learned privately before being claimed publicly.

## 11. Kill criteria, restated once

- **Lift ≤ stub-arm noise at matched budget** → the improvement-engine claim is dead as
  stated; the verification-infrastructure value (memrebel/CIVerd/attestation) stands on
  its own. Positioning shifts; nothing is deleted (R1 toll applies as always).
- **Ledger degenerates to boilerplate** → scope rule wrong; fix the rule, don't abandon
  the instrument.
- **Attestation needs a format change** → stop; David; memproof-3 discussion.
- **Saturation-on-arrival two cycles running** → adversary-tier authoring has hit the
  ceiling; incident mining becomes the sole corpus refill and the quarterly must say so.

## 12. Ratification record — 2026-08-05

David reviewed the three decision points in plain-language form and adopted all three
recommendations verbatim:

| Decision | Resolution |
|---|---|
| 0 — timing | Phase 0 authorized immediately (backfill committed with this revision); Phases 1–4 ratified conditional on Phase 0's §3 kill row not firing at the ~2026-08-10 run |
| 1 — holdout privacy | Private sibling repo for holdout classes, content hashes recorded here; standing rule effective now: holdout never in anything published — the scoreboard ships results + signed verdicts, never plants |
| 2 — v2.0 gate | Both conditions adopted, with the honesty-gate softener: the lift read must be *completed and stated*, not *good* |

Consequence for CIVerd (folded into Appendix A): verdict bundles are publishable
artifacts, so captured check output must never embed plant or fixture content — exit
codes, counts, and content hashes only.

---

## Appendix A — CIVerd session prompt (verbatim; also delivered in-session)

```
Build the engine-side half of tdd-playbook's RSI hardening plan
(tdd-playbook: docs/plans/rsi-hardening-2026-08.md, branch
claude/tdd-playbook-rsi-analysis-ekw8up — RATIFIED 2026-08-05; this
Phase-3 work is triggered by tdd-playbook's v1.26 tag, so build now,
arm on the tag). Two deliverables, two hard constraints. CIVerd's own
conventions apply throughout: fail-closed
(absence of evidence is RED), the signing key never touches the process
that runs hostile code, every new check ships with a planted-error test
plus a clean control, and the runner installs only pytest.

CONTEXT. tdd-playbook is adding an improvement ledger:
calibration/ledger.md (append-only journal of gate-surface changes with
pre-registered expected effects) and calibration/ledger.py (stdlib-only:
validate / check --baseline-rev / score / report). `check` exits nonzero
when a gate-surface diff since the baseline tag lacks a covering ledger
entry. CIVerd already runs tdd-playbook's check_staleness.py as a
`staleness` check on the daily timer — read how that check is registered
and executed first; both deliverables follow that exact pattern.

DELIVERABLE 1 — `ledger-coverage` daily check.
Add a check that runs `python3 calibration/ledger.py check
--baseline-rev <latest release tag>` in the playbook checkout on the
daily timer, recording the real exit code. Arming order matters because
we are fail-closed: (a) do NOT arm before tdd-playbook v1.26 exists —
a required check whose script is absent would correctly RED every
verdict and wedge their releases on our schedule, not theirs; (b) arm
as a recorded-but-not-required check first; (c) promotion to the
required set happens at tdd-playbook v1.27, as a separate, journaled
config change. Detect the script's presence from the pinned tag, not
from the working tree.

DELIVERABLE 2 — calibration attestation.
When a commit on tdd-playbook's main appends to
docs/calibration/history.md (a live calibration run), execute the
deterministic validator set as recorded checks against that commit —
check_scoreboard_integrity.py --baseline-rev <latest tag>,
check_staleness.py (real date), ledger.py check, and the blessed suite
entrypoint sh scripts/civerd_gate.sh — and issue a signed civerd-1
memproof-2 bundle pinned to that commit sha, stored/published the same
way run verdicts are today. This is the externally-quotable "state of
the gates" artifact: anyone can replay the verdict offline against the
issuer key.

HARD CONSTRAINT — no format drift. The bundle MUST verify with
tdd-playbook's unmodified stdlib verify_verdict.py and MUST NOT add or
alter any civerd-1 predicate logic, snapshot schema field, or reason
string — tdd-playbook's tests/fixtures/civerd_crossvalidation_corpus.json
must stay green, and memrebel is frozen. New check NAMES are config, not
format, and are fine. If you find the attestation genuinely cannot be
expressed without a schema or predicate change, STOP and report — that
is a memproof-3-class decision for David, not an implementation detail.

HARD CONSTRAINT 2 — bundles are publishable; plants are secret
(Decision 1, ratified 2026-08-05). Attestation bundles will feed a
public scoreboard, and tdd-playbook's holdout calibration plants are
secure test items (private sibling repo; only content hashes are
public). Therefore any check output captured into a bundle must record
exit codes, counts, and content HASHES only — never fixture bodies,
plant content, or captured stdout that could embed them. If a
validator's stdout may contain fixture text, capture a digest of the
stream, not the stream. Add a planted test for this: a scratch run
whose check stdout contains a marker string -> the issued bundle must
NOT contain the marker anywhere in its signed bytes.

TESTS (planted-error convention, e2e on a scratch repo):
1. Scratch playbook-shaped repo with a gate-surface diff and no ledger
   entry -> ledger-coverage check nonzero -> verdict RED. Control: same
   diff with a covering entry -> GREEN.
2. Scratch repo with history.md tampered (append-only byte-prefix
   violated vs baseline) -> integrity check nonzero -> attestation
   verdict RED. Control: clean append -> GREEN.
3. Attestation bundle round-trip: issue on the scratch repo, verify
   with a vendored copy of tdd-playbook's verify_verdict.py (unmodified)
   and with `memrebel verify --evaluator civerd.verdict:evaluate` ->
   both accept; flip one byte -> both refuse.
4. Fail-closed: timer fires, playbook checkout unreachable -> no
   attestation issued and the absence is RED, never silently skipped.

SEQUENCING. Land the check-registration machinery and tests now behind
the not-yet-armed state; arming follows tdd-playbook's v1.26/v1.27 tags
as above. Nothing in this task touches the signing-key isolation
boundary — if an implementation approach would, that approach is wrong.

REPORT (Tripwire style): what was built, file paths, planted tests
red-first evidence, arming state (advisory/required and what flips it),
the round-trip verification transcript, commit sha, and "Loop closed:
yes/no". Flag any conflict with civerd-plan.md or the trust-floor plan
rather than resolving it silently.
```

## Appendix B — memrebel: no work required (and the tripwire that says if that changes)

The attestation is an ordinary `civerd-1` memproof-2 bundle: memrebel's frozen wire format
already carries it, `memrebel verify --evaluator civerd.verdict:evaluate` already verifies
it, and the golden vectors and cross-validation corpus already pin the canonicalization
both sides must agree on. **Any pressure to touch `src/memrebel/` arising from this plan is
a design error in the pressure, not a task for memrebel** — the standard being boring is
the product working. Contingency prompt, only if CIVerd's Deliverable 2 report flags a
format constraint:

```
CIVerd's calibration-attestation work reports that a civerd-1 memproof-2
bundle cannot express <X>. Do NOT change src/memrebel/. Assess whether
<X> is (a) expressible within the existing snapshot schema after all
(most likely — say how), (b) a CIVerd-side design error, or (c) a
genuine memproof-3 requirement. For (c) only: draft the memproof-3
delta as a proposal document (new domain-separation tags, version
string, migration and dual-verify story per SPEC.md's versioning rule)
— a proposal, not an implementation. Report which of a/b/c and why.
```
