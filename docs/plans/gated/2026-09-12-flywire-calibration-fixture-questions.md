# §0a Question pack — FlyWire v783 sub-circuit as a second calibration fixture family

Produced by `spec-producer` on 2026-09-12, dispatched with the requester's words verbatim,
before the §0 plan was drafted. Consumed by
`docs/plans/gated/2026-09-12-connectome-calibration-fixture.md` (Spec integrity).

`Verdict: UNDERSPECIFIED — 14 load-bearing questions`

Sources read before asking: `calibration/run_calibration.py`, `calibration/README.md`,
`calibration/plant-forms.md`, `calibration/oracle-changes.md`, `calibration/ledger.py`,
`calibration/power.py`, `calibration/history_format.py`, `capabilities.json::calibration-loop`,
`docs/calibration/history.md`, `scripts/civerd_gate.sh`, `scripts/install_into_repo.py`, and the
two rejected prior-art plans `docs/plans/gated/2026-08-28-replay-calibration-REJECTED.md` and
`…-drift-detector-REJECTED.md`.

---

**Q1. Which instrument does "more accurate and efficient at assisting AI to code better" name —
verifier recall/FP, or the with-playbook vs no-playbook effect?**
The repo carries both axes: `history_format.POPULATION_AXES = ("form", "isolation")` and
`--isolation no-playbook` measure whether the playbook changes outcomes; recall/FP measures
whether verifiers catch plants. The workstream as scoped improves the second; Turn 1's words
name the first.
*Proposed:* target **verifier recall/FP only**, with an explicit one-sentence disclaimer.
*Because:* Turn 2 demands verified claims; letting a recall number stand in for "the playbook
helps you code better" is the exact claim nobody has measured.

**Q2. Does the new deterministic oracle grade the AGENT's output, or the TREE's output?**
`oracle()` is pure regex over agent prose; the POC's comparison runs against the code. Two
instruments wearing one name.
*Proposed:* it grades **the agent**; the behavioural comparison becomes the *plant-validity*
precondition.
*Because:* if it grades the tree, this stops being agent calibration and becomes a golden-output
regression test — a different product.

**Q3. The scenario schema cannot express a second fixture. Is a schema change in scope?**
`FIXTURE` is a module global (`run_calibration.py:36`) read by `validate_scenario` (`:109`),
`stage()`, and `fixture_legibility_problems` (`:669`). There is no `fixture` key. Worse,
`validate_scenario` **requires** `must_match` (`:84`).
*Proposed:* yes — a `fixture` field defaulting to `"fixture"`, threaded through all four readers.
*Because:* this is a FINDING, not a preference — the proposal is unrepresentable today, and
discovering that mid-build is how scope doubles.

**Q4. `scenarios.json` is a rule-(d) gate surface AND a `ledger.EFFECTFUL` surface. Does this
workstream pre-register a ledger entry before the diff?**
`ledger.py:60-74`: both `scenarios.json` and `corpus/approved/` are EFFECTFUL, where
`expect: none` is a lie by construction, and the entry must exist before the diff.
*Proposed:* yes, one entry per effectful deliverable, predicting MOVEMENT (not significance —
`power.py` shows significance is unobtainable at 3 reps).
*Because:* landing a gate-surface change unregistered is the `976364f` specimen the ledger was
built from.

**Q5. Who owns the reference answer, and where does it live given corpus immutability?**
Integrity rule (b) pins every file under `corpus/approved/` byte-identical forever — which is
why form assignment had to live outside the corpus. A stored reference there could never be
legitimately updated.
*Proposed:* reference outside `corpus/approved/`, governed by a new append-only journal on the
`oracle-changes.md` model.
*Because:* a reference that legitimately changes inside an immutable tree forces either a rule
violation or a dead fixture.
*(Plan's answer: sidestepped entirely — no stored reference; both sides computed at check time.)*

**Q6. Is the reference number reproducible off this machine?**
"Deterministic, seeded, numpy" is a claim about one host. The drift-detector rejection died
partly on this shape: fixtures that pass locally and go dark in the only independent
re-execution there is.
*Proposed:* pin the dependency and ship a red-first test that the reference reproduces in CI
before any plant is authored; if not bit-exact, the oracle becomes a tolerance band.
*Because:* float reductions over 36,826 connections are order- and BLAS-sensitive.
*(Plan's answer: the stdlib-only build removes numpy/BLAS from the path entirely.)*

**Q7. Can FlyWire FAFB v783 data be redistributed in this public repo?**
Handed over rather than answered: FlyWire data carries its own licence and citation terms, and
this plugin is public and vendored into other people's repos.
*Proposed:* do not commit upstream data; commit the derived sub-circuit only if the licence
permits, otherwise a generator plus hash manifest with the data gitignored. Someone must read
the actual licence before D1.
*Because:* a licence problem found after the tag is unfixable by a patch release.
*(Plan's answer: verified CC BY-NC 4.0 vs this repo's Apache-2.0 — escalated to D0.3, blocking.)*

**Q8. Does the new family get a cadence — and has the v1.32.0 retirement been re-opened
deliberately?**
The stated goal "so verifier decay can be detected without a human noticing it first" is a
clock. CLAUDE.md retired the clock and stated the accepted cost in those exact terms.
*Proposed:* **no cadence**; the decay-detection goal is dropped from scope, not smuggled in.
*Because:* "it's fast, so it may as well run every release" is how the retired obligation
re-enters — the cost was never runtime, it was the debt it minted.

**Q9. May the behavioural family BLOCK, or trend only?**
A plant surviving to a clean verdict is a BLOCKING failure today; the POC already produced one
false positive on the clean control.
*Proposed:* trend-only, in `PROMOTION_QUARANTINE` from birth, until three runs of paired rows;
never blocking on the FP side.
*Because:* a brand-new oracle that blocks is a gate calibrated against nothing, and the
quarantine mechanism already exists for this.

**Q10. Is the cheaper already-owed fix the real answer? `calibration-loop` carries four debts
expiring 2026-09-15 — three days from today.**
FINDING, contradicting the workstream's premise. `ORACLE NORMALISATION PASS` is now literally
"flip `oracle()`'s default"; the helper is authored and unit-tested. The 2026-08-05 run-4
adjudication states outright: **zero plants survived; every recorded "miss" was a correct verdict
scored down on an adjective.** Prose-oracle brittleness, not verifier weakness, is the measured
defect. `test_capability_registry.py::test_own_registry` runs with the real date, so the suite
REDs on 2026-09-16 regardless.
*Proposed:* pay the debts, re-run, and THEN decide whether a second fixture family is the
highest-yield next move. FlyWire is the follow-on, not the opener.
*Because:* the drift-detector plan died on exactly this — pilot the untested simpler alternative
first.

**Q11. False-positive scoring already exists. What is actually new?**
CONTRADICTION with the workstream summary. `history.md` run headers carry `· FP n/m ·`; the
2026-08-16 run reports 33 controls of 70 scenarios; `validate_scenario` refuses a control without
`must_not_match`; `pairing_problems` enforces the R2 invariant.
*Proposed:* drop "FP scoring" from the deliverables. What is new is exactly two things: a second
fixture with a numerical/data-pipeline shape, and a non-prose oracle kind.
*Because:* re-promising shipped capability inflates the apparent value of the workstream.

**Q12. Is the new family `dev` or `holdout`, and who approves mechanically generated plants?**
An id with no register entry IS `dev`. "Mechanically generated plant family" has no defined path
through either form.
*Proposed:* `dev`, registered explicitly rather than by absence; generation proposes into
`corpus/proposed/` and **every** plant still requires human approval.
*Because:* machine-generated plants that self-approve are an answer key nobody read.

**Q13. Is the shareable document a deliverable, or a separate artifact?**
*Proposed:* two artifacts, both committed — the §0 plan (technical, gates the build) and the
explainer as a **named deliverable** whose acceptance test is Turn 2's bar: a non-David reader
follows it end-to-end without a repo checkout.
*Because:* the repo's plan format is not shareable prose, and the measured failure mode is
artifacts that live only in scrollback.

**Q14. Which adversaries, against which artifact, and what closes the loop?**
*Proposed:* `architecture-adversary` (the fixture/oracle seam and the `FIXTURE` global),
`integration-adversary` (is the new oracle's output read at field granularity, or write-only),
`intent-adversary` (Q1 — does the build answer Turn 1's actual words), `claims-verifier`
(Turn 2's bar on every number in the explainer). Dispatched against the plan, before code.
*Because:* both rejected prior-art plans died at exactly that stage, which is the cheap place to
die.

*(4 lower-radius questions withheld by the producer: legibility scanning of neuroscience
docstrings; wall-clock budget for a second family against the serial cap; whether `calibration/`
staying un-vendored means this never reaches downstream repos and whether that is intended; and
the `gate_runner` roster digest going red when a new `calibration/` suite directory appears.)*

---

`Recommendation: Q10 — whether the four calibration-loop debts expiring 2026-09-15 are paid and
re-measured BEFORE a second fixture family is built, because the repo's own run-4 adjudication
measured that zero plants survived and every "miss" was prose-oracle brittleness — which decides
whether FlyWire is deliverable D1 of this workstream or the follow-on to a cheaper fix
addressing the same root cause.`
