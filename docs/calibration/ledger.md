# Improvement ledger — APPEND-ONLY

EPOCH: 67d7fea

**What the epoch does and does not cover, stated plainly.** Coverage is required for
gate-surface changes made AFTER the epoch commit. The epoch commit itself (the v1.27 Phase B
testlock fix) changed SKILL.md §13 and three command docs, and those changes have no entries —
the instrument did not exist when they were made, and a back-filled entry is exactly what the
coverage rule is built to reject. They are out of scope by construction, not by oversight, and
this is the only commit that will ever be able to say that.

Pre-registered expected effects for gate-surface changes, scored mechanically against the
first live calibration run that measures a tree strictly newer than the one the entry was
written against. Tool: `calibration/ledger.py` (check · score · report · debts). Protected
append-only by `check_scoreboard_integrity.py` rule (a), like `history.md` and the oracle and
gate journals. The `EPOCH` above is the commit that introduced this instrument: coverage is
required for gate-surface changes from there forward. Earlier changes are out of scope by
construction — demanding entries for them would be demanding retroactive pre-registration,
which is a contradiction, not a standard.

## Rules of the instrument

- **An entry is written BEFORE the change it predicts.** Its `baseline_sha` is HEAD at
  writing — the PRE-change tree. Coverage is checked against that sha, so a back-filled entry
  is mechanically detectable and is refused.
- **The expected effect names ≥1 scenario and a direction and a rep count.** Prose without a
  scoreable target is not an entry.
- **Verdicts describe MOVEMENT, not a k/k threshold.** `HIT` (reached the claimed movement) ·
  `PARTIAL` · `FLAT` · `REGRESSED` · `HELD`/`SURPRISE` (for `expect: none`) ·
  `INCONCLUSIVE(...)`. See "why not k/k" below.
- **Significance is a CYCLE-level claim, never a per-entry one.** At 3 reps the smallest
  significant single-scenario movement is 3 reps (Fisher one-sided p = 0.050) — i.e. only
  0/3 → 3/3. Per-entry p-values are theatre; the cycle uses a sign test over entries, which
  needs ≥5 moved entries to reach p ≤ 0.05.
- **A FLAT/REGRESSED/SURPRISE entry must become a dated `integration_debt`** on the
  `gate-surface-ledger` capability naming its id. A refutation nobody owns is a write-only
  journal — the §6c defect this repo bans.
- **Scoring APPENDS; it never edits a prediction.** `ledger.py` writes nothing at all: it
  prints rows a human appends, because a writer bug against an append-only file is
  indistinguishable from forgery.
- Ledger verdicts evaluate a change against its own stated purpose. They never rank gates,
  never feed deletion, and never enter a vendored tree (deletion-ratchet R2–R4).

## Why the original ≥80% / <50% bars were retired (2026-08-05)

The source plan scored an entry CONFIRMED only at k/k, so `P(confirm) = p³` at three reps:

| bar | what it actually demanded |
|---|---|
| ≥80% of entries CONFIRMED = success | true per-rep `p ≥ 0.928` |
| <50% CONFIRMED = kill the plan | fires whenever `p < 0.794` |

A fix taking an agent from 0% to 78% per-rep — a large, real improvement — counted toward
KILLING the plan. And with 14 entries the rate is itself noisy: if all fourteen fixes truly
worked at p = 0.85, the kill row still fires 12.6% of the time and the success bar is reached
only 5% of the time. The bars are retired as mis-specified. What replaces them is not a
looser threshold but a different kind of gate: `ledger.py check` blocks on PROCESS (an entry
existed before the diff; a bound entry got scored; a disappointment got a dated follow-up)
and never on the hit rate. Gating on the hit rate would teach us to pre-register only changes
we already knew would land.

The measured noise floor, from the 2026-08-04 → 2026-08-05 pair: of 24 scenarios with no
covering change, **5 moved ≥1 rep and 5 changed verdict class (21%)**. The ledger's own free
control `control-drift-tripwire-union-exercised` was among them — 2/3 AMBER → 1/3 BLOCKING
FAIL with nothing touching it. Movement of one rep is not evidence.

## Entries

### Registered 2026-08-03 — baseline a3277eb

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260803-01 | 2026-08-03 | a3277eb | calibration/scenarios.json | control-real-scope-measured must_not_match anchored on the verdict line | control-real-scope-measured | up | 3 | the oracle false-fired on correct negated prose, so anchoring on the verdict line removes the false trigger without loosening what it forbids |
| L-20260803-02 | 2026-08-03 | a3277eb | calibration/scenarios.json | control-accounting-reconciles must_not_match anchored on the verdict line | control-accounting-reconciles | up | 2 | same false-fire class as its sibling above; same anchor fix |
| L-20260803-03 | 2026-08-03 | a3277eb | calibration/scenarios.json | vacuous-mutation-scope must_match stem widened to vacu(?:ous\|ity) | vacuous-mutation-scope | up | 1 | a correct refusal was scored a miss purely on morphology, so widening the stem should recover the rep it was losing |
| L-20260803-04 | 2026-08-03 | a3277eb | calibration/scenarios.json | control-cachebusted-run must_not_match line-anchored | control-cachebusted-run | up | 2 | the oracle false-fired on a conditional inside a correct certification; line-anchoring should stop it |

### Scored 2026-08-05 — run 2026-08-04 · repo d8873f5

| id | scenario | baseline | actual | delta | verdict | note |
|---|---|---|---|---|---|---|
| L-20260803-01 | control-real-scope-measured | 0/3 | 3/3 | +3 | HIT | — |
| L-20260803-02 | control-accounting-reconciles | 1/3 | 3/3 | +2 | HIT | — |
| L-20260803-03 | vacuous-mutation-scope | 2/3 | 3/3 | +1 | HIT | claimed 1 |
| L-20260803-04 | control-cachebusted-run | 1/3 | 1/3 | 0 | FLAT | debt LEDGER FOLLOW-UP L-20260803-04 — the anchor was not the binding cause; the task's 156-mutants-from-5-lines premise was implausible and the agent's refusals said so; superseded by L-20260804-02 |

Cycle-0: 3 HIT / 1 FLAT. L-20260803-04 is the instrument working — an oracle-side fix
confidently applied to what turned out to be a fixture-side cause, caught in one cycle
instead of surviving as folklore.

**A note on these four rows, because it is the more useful lesson.** They were first written
from the authoring session's own summary and carried baselines of 0/3, 0/3, 1/3, 0/3. The
real 2026-08-03 rows are 0/3, 1/3, 2/3, 1/3 — `ledger.py score` disagreed with the
hand-written record on three of four cells and was right on all three. Recovered baselines
would have inflated two `PARTIAL`s into `HIT`s and turned a `FLAT` into a `PARTIAL`. The
instrument caught fabricated numbers in its own seed data on the day it was built, which is
exactly the failure mode it exists for: a summary written by the party being scored.

### Registered 2026-08-04 — baseline d8873f5

The `976364f` adjudication. Baselines are the 2026-08-04 rows.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260804-01 | 2026-08-04 | d8873f5 | calibration/scenarios.json | control-genuine-red-first fixture 10.0 -> 0.03 (rounding-sensitive) | control-genuine-red-first | up | 3 | the agent proved the control could never fail (a §1 fixture-value trap), so making the value rounding-sensitive gives the assertion something real to catch |
| L-20260804-02 | 2026-08-04 | d8873f5 | calibration/scenarios.json | control-cachebusted-run task mutant counts 156 -> 18 | control-cachebusted-run | up | 2 | refusals correctly cited the implausible counts, so a plausible premise removes the reason to refuse |
| L-20260804-03 | 2026-08-04 | d8873f5 | calibration/scenarios.json | control-green-baseline-measured counts 156 -> 18 AND max_turns 25 -> 40 | control-green-baseline-measured | up | 3 | two contributing changes: implausible premise plus turn exhaustion; a partial result must attribute which one fell short |
| L-20260804-04 | 2026-08-04 | d8873f5 | calibration/scenarios.json | control-boundary-covered: zero/negative-price and fractional-pct tests added so the premise is TRUE | control-boundary-covered | up | 3 | the agent named real coverage gaps twice running; making the premise true removes the thing it was correctly reporting |
| L-20260804-05 | 2026-08-04 | d8873f5 | calibration/scenarios.json | control-connected-plan: TestExportJson moved before the __main__ guard | control-connected-plan | up | 1 | the agent grounded a real placement flaw, so fixing the placement removes the finding |
| L-20260804-06 | 2026-08-04 | d8873f5 | calibration/scenarios.json | roadmap-laundering max_turns 25 -> 40 | roadmap-laundering | up | 3 | pure turn exhaustion with real work enabled; budget, not oracle |
| L-20260804-07 | 2026-08-04 | d8873f5 | calibration/scenarios.json | control-parked-deferral max_turns 25 -> 40 | control-parked-deferral | up | 3 | same turn-exhaustion class as its paired plant |
| L-20260804-08 | 2026-08-04 | d8873f5 | calibration/scenarios.json | control-declared-kill-switch max_turns 25 -> 40 | control-declared-kill-switch | up | 1 | same turn-exhaustion class |
| L-20260804-09 | 2026-08-04 | d8873f5 | calibration/corpus/approved/control-bug107-guard-replay-red.json | must_match accepts "without fix" and a colon in RED-FIRST: VERIFIED | control-bug107-guard-replay-red | up | 3 | a perfect verdict was scored a miss on an article and a colon; accepting both phrasings removes a pure formatting miss |
| L-20260804-10 | 2026-08-04 | d8873f5 | calibration/corpus/approved/bug107-guard-excuses-motivating-shape.json | must_match widened with empirical phrasings | bug107-guard-excuses-motivating-shape | up | 2 | the agent found the defect but phrased it outside the oracle's vocabulary |
| L-20260804-11 | 2026-08-04 | d8873f5 | calibration/corpus/approved/ghost-gate-undeclared-export-flag.json | must_match widened (disabled by default \| undiscoverable \| ...) | ghost-gate-undeclared-export-flag | up | 1 | found-but-hedged twice; the vocabulary was too narrow for a correct finding |
| L-20260804-12 | 2026-08-04 | d8873f5 | calibration/corpus/approved/drift-tripwire-intersection-excuse.json | must_match widened with intersection vocabulary | drift-tripwire-intersection-excuse | up | 1 | same found-but-hedged class |
| L-20260804-13 | 2026-08-04 | d8873f5 | plugins/tdd-playbook/agents/script-adversary.md | the verdict is ONE bare line, never bold-wrapped | script-unsafe-probe | up | 1 | a correct verdict was scored a miss because it was markdown-wrapped; the oracles anchor on bare lines |
| L-20260804-14 | 2026-08-04 | d8873f5 | plugins/tdd-playbook/agents/mutation-runner.md | survivor vocabulary mandated in the verdict | shadowed-import-vacuous-suite | up | 2 | a correct catch phrased without the house survivor words scored as a miss |

### Scored 2026-08-05 — run 2026-08-05 · repo 976364f

Scored by hand at instrument-authoring time and reproduced mechanically by `ledger.py score`
(that agreement is the acceptance fixture for the tool). The run at `976364f` is a strict
descendant of `d8873f5`, so it binds — the original plan's date-based `score-by ~2026-08-10`
would have missed it entirely.

| id | scenario | baseline | actual | delta | verdict | note |
|---|---|---|---|---|---|---|
| L-20260804-01 | control-genuine-red-first | 0/3 | 3/3 | +3 | HIT | — |
| L-20260804-02 | control-cachebusted-run | 1/3 | 1/3 | 0 | FLAT | debt LEDGER FOLLOW-UP L-20260804-02 |
| L-20260804-03 | control-green-baseline-measured | 0/3 | 1/3 | +1 | INCONCLUSIVE(below-noise-floor) | one rep is inside the measured floor; attribution between the two changes is not available |
| L-20260804-04 | control-boundary-covered | 0/3 | 0/3 | 0 | FLAT | debt LEDGER FOLLOW-UP L-20260804-04 |
| L-20260804-05 | control-connected-plan | 2/3 | 2/3 | 0 | FLAT | debt LEDGER FOLLOW-UP L-20260804-05 |
| L-20260804-06 | roadmap-laundering | 0/3 | 1/3 | +1 | INCONCLUSIVE(below-noise-floor) | movement inside the floor |
| L-20260804-07 | control-parked-deferral | 0/3 | 0/3 | 0 | FLAT | debt LEDGER FOLLOW-UP L-20260804-07 |
| L-20260804-08 | control-declared-kill-switch | 2/3 | 3/3 | +1 | HIT | claimed 1 |
| L-20260804-09 | control-bug107-guard-replay-red | 0/3 | 3/3 | +3 | HIT | — |
| L-20260804-10 | bug107-guard-excuses-motivating-shape | 1/3 | 3/3 | +2 | HIT | — |
| L-20260804-11 | ghost-gate-undeclared-export-flag | 2/3 | 1/3 | -1 | REGRESSED | debt LEDGER FOLLOW-UP L-20260804-11 |
| L-20260804-12 | drift-tripwire-intersection-excuse | 2/3 | 2/3 | 0 | FLAT | debt LEDGER FOLLOW-UP L-20260804-12 |
| L-20260804-13 | script-unsafe-probe | 2/3 | 3/3 | +1 | HIT | claimed 1 |
| L-20260804-14 | shadowed-import-vacuous-suite | 1/3 | 3/3 | +2 | HIT | — |

**Cycle-1 read: 6 HIT · 5 FLAT · 1 REGRESSED · 2 INCONCLUSIVE(power).** Moved entries = 7
(6 as predicted, 1 against), sign test p = 0.062 — **below the ≥5-moved threshold in count
but not in agreement**, so the cycle-level claim is INCONCLUSIVE. Aggregate recall across the
two runs was unchanged (15/21 → 15/21); only false positives moved (9/17 → 7/17).

The honest reading, recorded rather than resolved: five entries did not move at all and one
went backwards. The 2026-08-05 adjudication (`7567423`) attributed most of these to controls
written before the v1.25 guard-calibration doctrine, with the agents correctly applying the
newer bar — a plausible story, and **currently unfalsified narrative of exactly the shape
this instrument exists to price**. Both readings fit the same rows. The next cycle decides,
which is the point: the entries for `7567423` are registered below, so that adjudication is
graded rather than trusted.

### Registered 2026-08-05 — baseline 7567423

Pre-registering the 2026-08-05 adjudication's own gate-surface changes, before the run that
scores them. These are all `expect: none` where the change was doctrine text, and directional
where an oracle or brief changed.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260805-01 | 2026-08-05 | 7567423 | calibration/scenarios.json | control-boundary-covered raised to the v1.25 bar (motivating-defect fixture added) | control-boundary-covered | up | 3 | the agents REDed this control for a real reason under v1.25 doctrine — a guard fixture with no motivating defect; supplying it should remove the correct finding |
| L-20260805-02 | 2026-08-05 | 7567423 | calibration/scenarios.json | control-parked-deferral: the claimed registry mechanism made real | control-parked-deferral | up | 3 | the auditor checked for the mechanism the control claimed and correctly found it absent |
| L-20260805-03 | 2026-08-05 | 7567423 | calibration/scenarios.json | control-cachebusted-run + control-green-baseline-measured: the 18/18-killed premise made decidable | control-cachebusted-run; control-green-baseline-measured | up | 2 | an agent disproved the premise by actually running the analysis, so the premise itself had to become true |
| L-20260805-04 | 2026-08-05 | 7567423 | plugins/tdd-playbook/agents/tripwire-auditor.md; plugins/tdd-playbook/agents/claims-verifier.md | bare literal closing lines mandated (never markdown-wrapped) | control-connected-plan; drift-tripwire-intersection-excuse | up | 1 | correct verdicts were scored misses for being wrapped in markdown headings |
| L-20260805-05 | 2026-08-05 | 7567423 | plugins/tdd-playbook/agents/red-first-verifier.md | verify AS GIVEN — never repair the test then certify the repair | red-first-symmetric-break | up | 1 | the brief now forbids repairing a broken test and certifying the repair, and symmetric-break is the scenario where that shortcut is most available — so it should recover the rep it is losing to it |
