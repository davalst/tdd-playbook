# §0 Plan — Mistake Miner D4–D6 (classifier, corpus, and THE BASELINE)

> **DATA MOVED TO A PRIVATE REPO — 2026-09-12.** The mistake miner reads real session
> transcripts, so its code, its corpus, its hand-built ground truth and its taxonomy
> sample now live in **`davalst/mistake-miner` (private)**. `davalst/tdd-playbook` is
> PUBLIC. This file is kept here as the §0 planning record the house rules require to land
> in-repo; every **verbatim session quote and session UUID has been redacted** out of it,
> and the unredacted copy is in the private repo under `docs/`.



**Date:** 2026-09-12, for the next session · **Workstream:** `mistake-miner`
**Parent:** `docs/plans/gated/2026-09-12-mistake-miner-and-reflex-router.md` (+ its
Appendix A, the FlyGM ground truth)
**Predecessor:** `docs/plans/gated/2026-09-12-mistake-miner-d1-d3.md` (D1–D3 landed,
commit `638c273`)

**Written from measurements, not intentions.** Every number below was measured in the
D1–D3 session and is reproducible with
`python3 calibration/mistake_miner/cli.py mine`.

---

## 0. What the previous session actually found, because it changes this plan

| measurement | value | consequence for D4–D6 |
|---|---|---|
| transcripts scanned (tdd-playbook) | 317 (214 main + 103 subagent) | fine |
| records | 45,638 | fine |
| events extracted | 266 | **D4's "≥200 events classified" is reachable in one repo** |
| extraction rate | **7.1 per 1,218 records** | less than half the reference's 16; the reference was one unusually dense session |
| event-bearing transcripts | 115 of 317 (36%) | 64% of sessions contain no detected mistake at all |
| back-linked | **175/266 (66%)** | a third of events have no commission, so D6's design matrix is n≈175, not 266 |
| gap distribution | min 2 · p25 17 · **median 52** · p75 132 · max 2,431 | finding 1 confirmed at scale |
| gap ≤ 1 (the self-link bug) | **0** | A3 holds on real data |
| link strategy | entity 53 · structural 122 · none 91 | **structural beats entity 2:1** — see §3 |
| hand-labelled precision | **44%** single real events (16/36) | ~117 of 266 are real; D4 must expect to discard most rows |
| signals that NEVER fired | **2 of 8** (`undercount`, `wrong_threshold`) | E8 and E10 are UNDETECTED, not rare |
| `stale_fact` share | 30% of all events, and mostly false | the largest single precision problem |
| thinking-block content in the store | **95.2% stripped** (21,706 of 22,806 empty; longest survivor 477 chars) | the planned recall widening via thinking is nearly worthless |
| identical `('Bash',)*6` tool tuples | **124 of 266 events** | finding 2 confirmed at scale |

**And one that should change the programme's expectations.** The corpus systematically
under-represents the failures nobody caught — the parent plan says this under
Survivorship — but the measured shape is worse than that framing suggests: 95% of the
model's own reasoning is not persisted, so the corpus can only ever contain mistakes that
were discovered *and* discussed in visible prose.

---

## 1. Deliverables

### D4 — the classifier pass
`calibration/mistake_miner/classify.py`

- Haiku 4.5, structured outputs pinning `error_class`, `nano_decision`, `confidence`, and
  an `evidence_quote` that must be a verbatim substring of the input. Batches API for the
  bulk pass.
- **Revised cost estimate.** The parent plan assumed ~16 events/session × 500 sessions ≈
  8,000 events ≈ $16 batched. Measured: 266 events per 317 transcripts of one repo, 770
  for cheliped (aggregate count only — no prose read into any store). So the whole local
  store is on the order of **1,000–1,500 events, not 8,000**, and the classification pass
  costs **single-digit dollars**. It was never the constraint and now it is not even close.
- **Three taxonomy changes before any money is spent** (from `corpus/taxonomy_sample.json`):
  1. **Add a `restraint` NEGATIVE class.** At least 3 of the 15 hand-labelled
     "not-an-event" rows are a coherent and *valuable* class: a mistake was suspected and
     correctly ruled out. The parent plan would discard these. But D8's headline metric is
     FALSE-ALARM RATE, and this repo's own record is that 701 ignored warnings killed a
     guard — so labelled examples of "looks like a mistake, isn't" are the most valuable
     negatives available. They are currently being thrown away.
  2. **Decompose container verdicts.** `Verdict: MIXED (9)` is evidence of nine mistakes,
     not one. 28 of 266 events (11%) are such containers, and they point at the densest
     source of labelled findings in the store. Decomposition is a D4 deliverable.
  3. **Mark E8 and E10 UNDETECTED, not rare.** Their detectors fired zero times in 45,638
     records. Any sentence of the form "E8 is uncommon" is unsupported.
- *Done when:* ≥200 events classified AND agreement against a ~50-event human gold set is
  measured and written down. The gold set is drawn and labelled BEFORE the classifier
  runs, in its own commit, exactly as `tests/ground_truth.json` was.

### D5 — the corpus
- SQLite + the existing JSONL export, append-only, at `calibration/mistake_miner/corpus/`.
- *Done when:* a query answers "how many E4 events, in which repos, over what period."
- **Blocked on Q2** (below): the rows carry verbatim session prose and are gitignored
  pending David's decision.

### D6 — THE BASELINE. This is the decision gate for the whole programme.
`calibration/mistake_miner/baseline.py`

Logistic regression and gradient boosting on the D3 features, predicting the nano-decision
per head. Stratified train/test split, precision/recall per head.

**Revised expectations, stated before the run so the result cannot be reinterpreted after
it:**
- **n ≈ 175**, not thousands — only back-linked events have features. After dropping the
  ~56% that hand-labelling says are not real events, the honest n is **nearer 80**. With
  six output heads, several will have single-digit positive counts.
- **Distinct semantic feature vectors: 85 of 175 (49%).** Half the events are
  feature-indistinguishable from another event. That is an upper bound on separability
  before any model is fitted.
- So D6's realistic verdict is not "does the fly beat the baseline" but **"is there enough
  signal here for any model at all"**, and the answer may well be no at this n. If so the
  correct next step is more data (Q1) or better features, not a connectome.

*Done when:* a precision/recall number exists per head with a stratified split, **and** a
learning curve over subsample sizes, so "not enough data" and "not enough signal" are
distinguishable rather than conflated.

**The gate, stated as a commitment:** if a plain classifier cannot beat a
stratified-random baseline on these features, D7 does not start. Appendix A of the parent
plan makes that cheaper to honour than it was: FlyGM's code is **not released**, there are
**no checkpoints**, and the paper's configuration is ~**15.1M trainable parameters** of
which 0.085% is the connectome-structured part. D7 is not a weekend port.

---

## 2. Integration surface

| deliverable | consumes | emits → named consumer | activation |
|---|---|---|---|
| D4 classify | `corpus/events.jsonl` rows from D1–D3 | `error_class`/`nano_decision`/`evidence_quote` → D5 rows and D6's `y` | `cli.py classify` |
| D5 corpus | classified rows | the query surface → D6's design matrix, and D8's replay set | `cli.py query` |
| D6 baseline | D5 rows | per-head precision/recall + learning curve → **the go/no-go for D7** | `cli.py baseline` |

This closes the one honest island the D1–D3 plan declared: D3's features had no consumer
in that session, and D6 is it.

**Still nothing wired into the gate. Still no guard touched.**

---

## 3. The design question D1–D3 raised and did not answer

**Structural linking (122) beat entity linking (53) by more than 2:1.** The parent plan
assumed back-linking would work by named entity; on real data the workhorse turned out to
be "the most recent write to a file of the relevant class". That matters because the two
strategies give different *kinds* of commission:

- an **entity** link points at the record that asserted a specific thing, which is what
  the label is about;
- a **structural** link points at the last plausible write, which may be the right file
  and the wrong record.

Nothing in D1–D3 measured structural-link *accuracy* beyond the three ground-truth cases
it resolves. **D4 must sample structural links and hand-check them**, and report entity-
and structural-linked events separately in D6. If structural links turn out to be
substantially noisier, two thirds of the corpus is weakly labelled and D6's numbers have
to be read per-strategy.

---

## 4. The three decisions — ANSWERED 2026-09-12, and what they changed

**Q1 — scope: ADD CHELIPED.** Done, and the corpus re-mined across both repos:

| | tdd-playbook only | **both repos** |
|---|---|---|
| transcripts | 317 | **1,032** (779 main + 253 subagent) |
| records | 45,638 | **197,368** |
| events | 266 | **1,040** |
| rate / 1,218 records | 7.1 | 6.4 |
| back-linked | 66% | **72%** |
| median gap | 52 | **89** (p75 296, max 11,233) |

Run it with `--scope=...` using the `=` form: the project directory names begin with `-`,
which bare `--scope <value>` parses as another option.

**This corrected a claim I made in the D1–D3 report.** On one repo, `undercount` and
`wrong_threshold` fired ZERO times and I reported E8/E10 as *undetected*. Across both they
fire **8** and **1** times. They are not undetected, they are vanishingly rare — 9 of
1,040 events. A signal that fires zero times in 45k records can still fire in 200k, so
"never fires" needed the widest sweep before assertion. The claim is fixed in
`corpus/taxonomy_sample.json`.

**Q2 — corpus tracking: KEEP GITIGNORED.** Unchanged. Re-mining is one command. Stated
cost: the corpus has no version history or integrity record, which is exactly what
happened to the reference transcript.

**Q3 — gate ordering: FIX PRECISION BEFORE D6.** This reorders the plan. The next session
does **D4a precision work first**, and D6 runs after, on a cleaner corpus:

### D4a — precision, BEFORE the baseline (the new first deliverable)

1. **Split `stale_fact`.** It is **531 of 1,040 events (51%)** of the combined corpus and
   mostly matches the bare word "stale" as subject matter. Target: a signal that requires
   a staleness *claim about a prior assertion*, not the word.
2. **Decompose container verdicts** into their constituent findings — 152
   `adversary_verdict` events, each standing for several real findings.
3. **Add the `restraint` negative class** rather than discarding it.
4. **Hand-check a sample of structural links** (§3) — they are now 263+ of the corpus and
   their accuracy is unmeasured beyond three ground-truth cases.
5. **Extend the pre-registered ground truth** from 5 cases to ~15, drawn from cheliped as
   well, and committed before any linker change — same discipline as `d7cea09`, which
   turned a 1/5 first run into four real mechanism fixes.

*Done when:* precision on a fresh hand-labelled sample of 36 is measured and compared
against the 44% baseline, and the ground truth still scores clean.

**Only then D6**, on a corpus whose real-event count should be nearer 500 than 80 — which
is the whole reason this ordering was chosen.

### The original three decisions, for the record:

- ~~**Q1 — scope.**~~ *(answered: add cheliped)* Measured, aggregate counts only, no prose stored: cheliped is 714 files
  / 151,513 records / **770 events**, a 2.9× volume increase for the corpus. The
  hypothesis that it would also be *cleaner* was tested and is **false** — its
  `stale_fact` share is 45% against tdd-playbook's 30%, because cheliped vendors this
  Playbook and shares its vocabulary. So the case for including it is volume alone, and
  volume is exactly what §1's n≈80 problem needs.
- ~~**Q2 — corpus tracking.**~~ *(answered: keep gitignored)* Currently gitignored. Two lines deleted and it is tracked.
- ~~**Q3 — the taxonomy.**~~ *(answered: fix precision first)* The three changes in D4 above are recommendations, not decisions.

## 5. What would falsify this work

- D6's best head does not beat a stratified-random baseline → the features are wrong, and
  the programme stops here having cost two sessions.
- The learning curve is flat → more data will not help either, which is a stronger stop.
- Hand-checking structural links shows they are mostly wrong → the corpus is a third the
  size it appears, and D6's n falls below anything defensible.
- Classifier/gold-set agreement is poor → the labels are noise and every downstream number
  inherits it.

Each of these is a cheap, reportable result. The programme is designed to die here rather
than after a connectome is built.
