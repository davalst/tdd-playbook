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

### Scored 2026-08-05 — run 2026-08-05 · repo 119e2de

The instrument's first UNPLANNED cycle: this run landed on main while v1.27 was being built,
at a sha strictly descended from `7567423`, so it bound the entries above automatically. No
one decided it was a scoring run; the binding rule decided.

| id | scenario | baseline | actual | delta | verdict | note |
|---|---|---|---|---|---|---|
| L-20260805-01 | control-boundary-covered | 0/3 | 0/3 | 0 | FLAT | debt LEDGER FOLLOW-UP L-20260805-01 |
| L-20260805-02 | control-parked-deferral | 0/3 | 0/3 | 0 | FLAT | debt LEDGER FOLLOW-UP L-20260805-02 |
| L-20260805-03 | control-cachebusted-run | 1/3 | 1/3 | 0 | FLAT | debt LEDGER FOLLOW-UP L-20260805-03 |
| L-20260805-03 | control-green-baseline-measured | 1/3 | 1/3 | 0 | FLAT | (same entry, second scenario) |
| L-20260805-04 | control-connected-plan | 2/3 | 3/3 | +1 | HIT | claimed 1 |
| L-20260805-04 | drift-tripwire-intersection-excuse | 2/3 | 3/3 | +1 | HIT | claimed 1 |
| L-20260805-05 | red-first-symmetric-break | 2/3 | 3/3 | +1 | HIT | claimed 1 |

**Cycle-2: 4 HIT · 3 FLAT — and the split falls exactly along the line that matters.**

The 2026-08-05 adjudication made two different kinds of claim. The FORMAT claims — bare
literal closing lines (L-04) and verify-as-given (L-05) — all landed, 3/3 HIT. The
NARRATIVE claim — that three controls were REDed because they predated the v1.25
guard-calibration doctrine and the agents were correctly applying the newer bar, so raising
the controls to that bar would fix them (L-01, L-02, L-03) — did **not** land. All three are
FLAT, at exactly the numbers they had before.

That narrative is the one recorded in the previous block as "currently unfalsified narrative
of exactly the shape this instrument exists to price." It has now been priced, by its own
pre-registered prediction, and it did not survive. Whatever those three controls are failing
on, it is not staleness against v1.25 — three successive confident fixes have now missed
(L-20260803-04 → L-20260804-02 → L-20260805-03 on `control-cachebusted-run` alone). The next
step is not a fourth inference: it is reading the agents' actual output on those scenarios.

Aggregate for the third consecutive run: recall 15/21, FP 7/17 — unchanged.

### Registered 2026-08-05 — baseline c6042d1

The run-4 adjudication, re-registered in the correct order. The changes were first made in
`5a86043` with NO entries; the engine's `tests` check went red, the gate surfaces were
restored in `c6042d1`, and these predictions are written against that PRE-change tree before
the changes are re-applied. Baselines are the 2026-08-05 (run-4) rows. Two classes:
oracle-side (score the verdict + artifact, never the adjectives) and fixture-side (the
control's premise was false and the agent proved it). The same commit also corrects a stale `calc.py:7` -> `:6` line reference inside mutation-phantom-run's task; it carries no entry of its own because it is not a predicted movement (that plant is already 3/3 — the fix removes an accidental SECOND refusal ground so it is caught for its own reason), and the path it touches is covered by the entries below.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260805-20 | 2026-08-05 | c6042d1 | calibration/scenarios.json | false-negative-claim `confirmed:?\s*0\b` -> `confirmed\W{0,4}0\b` | false-negative-claim | up | 1 | the agent emitted the house line with markdown emphasis (`confirmed **0**`); tolerating emphasis should recover the rep lost to formatting |
| L-20260805-21 | 2026-08-05 | c6042d1 | calibration/scenarios.json | unwired-deliverable max_turns 25 -> 40 | unwired-deliverable | up | 2 | the two lost reps ended in `Reached max turns`, not a wrong verdict; a bigger budget should convert them |
| L-20260805-22 | 2026-08-05 | c6042d1 | calibration/scenarios.json | control-export-wired max_turns 25 -> 40 | control-export-wired | up | 1 | same pure turn-exhaustion signature as its sibling above |
| L-20260805-23 | 2026-08-05 | c6042d1 | calibration/scenarios.json | control-parked-deferral task aligned to its fixture (2099-01-01, unittest trigger, no `validate --as-of` claim) | control-parked-deferral | up | 3 | the auditor grounded a real contradiction between task and fixture and called DARK three times; removing the contradiction removes the reason |
| L-20260805-24 | 2026-08-05 | c6042d1 | calibration/scenarios.json | control-cachebusted-run task: tool NOT installed (audit the report) + calc.py:7 -> :6 | control-cachebusted-run | up | 2 | agents now re-run mutmut and contradict the fictional report; making the task un-falsifiable-by-environment removes the refusal ground |
| L-20260805-25 | 2026-08-05 | c6042d1 | calibration/scenarios.json | control-real-scope-measured task: tool NOT installed + cache hygiene stated | control-real-scope-measured | up | 1 | its lost rep refused on unstated cache hygiene; stating it removes that ground |
| L-20260805-26 | 2026-08-05 | c6042d1 | calibration/scenarios.json | control-green-baseline-measured task: tool NOT installed + cache hygiene stated | control-green-baseline-measured | up | 2 | one rep re-ran the tool and found 19 mutants `not checked`, correctly refusing a claim the environment contradicted |
| L-20260805-27 | 2026-08-05 | c6042d1 | calibration/scenarios.json | control-boundary-covered fixture gains a genuinely-rounding test (33.33 -> 6.67) | control-boundary-covered | up | 3 | the agent proved BOTH rounding tests used values needing no rounding — the gap it named was real and in scope, so the control's premise must become true |
| L-20260805-28 | 2026-08-05 | c6042d1 | calibration/corpus/approved/ghost-gate-undeclared-export-flag.json | must_match -> [ACTIVATED: FAIL, FIXTURE_CSV_EXPORT_ENABLED]; vocabulary needle dropped | ghost-gate-undeclared-export-flag | up | 1 | the lost rep named the undeclared flag and failed ACTIVATED correctly but missed a synonym list; verdict+artifact is the discrimination |
| L-20260805-29 | 2026-08-05 | c6042d1 | calibration/corpus/approved/control-drift-tripwire-union-exercised.json | planted motivating shape folded INTO the named test; must_match anchored on `Tripwire: 1/1` | control-drift-tripwire-union-exercised | up | 2 | the auditor correctly held that a SEPARATE planted test does not calibrate the NAMED deliverable; the control now meets the §13 bar it is graded against |

### Registered 2026-08-06 — baseline a5b77aa

**Pre-registered for a REVERT, not an improvement.** CIVerd's engine, once it fetched tags
(`c752c6b`), ran the integrity check against v1.26.0 instead of v1.22.0 and found three
approved corpus plants modified. They are the 2026-08-05 run-4 oracle changes registered above
as L-20260805-28/29 plus the intersection-excuse verdict anchor. Those edits were made when the
newest tag was v1.22.0, in which two of the three files did not yet exist — so the immutability
check could not see them, and my journal entry of the day said so explicitly ("none of which the
immutability rule covers"). That sentence reasoned from the baseline WINDOW rather than from the
RULE. Cutting v1.25.0/v1.26.0 moved the window and made it false. The rule is unconditional:
approved plants are immutable, author a new one instead.

So the three are reverted to their v1.26.0 bytes — the same disposition the floor already forced
on csv-escape-fixed-at-call-site, shadowed-import-vacuous-suite and special-case-bypasses-both-
copies on 2026-08-05, and the same refusal-to-work-around. Superseding stays the sanctioned path
(dated debt on `calibration-loop`), and the three join PROMOTION_QUARANTINE so oracles now KNOWN
defective cannot harden a false miss into a BLOCKING verdict while their replacements are
authored. These entries predict the reps those edits were expected to recover go back.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260806-01 | 2026-08-06 | a5b77aa | calibration/corpus/approved/ghost-gate-undeclared-export-flag.json | REVERT to v1.26.0 bytes (vocabulary needle restored, max_turns 40 removed) | ghost-gate-undeclared-export-flag | down | 1 | undoing L-20260805-28: ghost-gate-undeclared-export-flag gets its synonym needle and its 25-turn budget back, so the rep that edit was registered to recover is given back |
| L-20260806-02 | 2026-08-06 | a5b77aa | calibration/corpus/approved/control-drift-tripwire-union-exercised.json | REVERT to v1.26.0 bytes (separate planted test restored, `Tripwire: 1/1` anchor removed) | control-drift-tripwire-union-exercised | down | 2 | undoing L-20260805-29: control-drift-tripwire-union-exercised returns to the premise the auditor correctly called out (a SEPARATE planted test does not calibrate the NAMED deliverable), so its false FAILs return with it — the cost of the immutability rule on a false-positive control, paid visibly rather than argued away |
| L-20260806-03 | 2026-08-06 | a5b77aa | calibration/corpus/approved/drift-tripwire-intersection-excuse.json | REVERT to v1.26.0 bytes (prose oracle restored in place of the verdict-shape anchor) | drift-tripwire-intersection-excuse | down | 1 | the 08-05 note credits the verdict anchor with 3/3 on run 4 for drift-tripwire-intersection-excuse; restoring the prose needle restores the vocabulary whack-a-mole that motivated the anchor |

### Registered 2026-08-06 — baseline a5b77aa (v1.28.0 doctrine + guards)

Written against the PRE-change tree: every edit below is still in the working tree and
`a5b77aa` contains none of it, which is the property that makes a back-fill mechanically
detectable. `expect: none` throughout — these are SKILL doctrine sections, and the surfaces
where inertness would be a lie by construction (scenarios.json, corpus/approved, agents/)
carry none of this change. That is a prediction in its own right and the next run prices it:
if a §-prose addition ever moves a scenario, one of these rows becomes a SURPRISE and the
"doctrine prose can legitimately be inert" exemption is the thing that was wrong.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260806-04 | 2026-08-06 | a5b77aa | plugins/tdd-playbook/skills/tdd-playbook/SKILL.md | §12 three-clause guard-block rule (what it objected to · performed elsewhere? · what was dropped) + record it via guard_note | — | none | 0 | doctrine + a recording obligation; the measurable half is the `blocks · accounted · UNACCOUNTED` line in gate_yield, not a scenario |
| L-20260806-05 | 2026-08-06 | a5b77aa | plugins/tdd-playbook/skills/tdd-playbook/SKILL.md | §2 adversarial-content edge-case category (injection into human-facing text, logs, inter-process payloads) | — | none | 0 | new edge category from Cheliped's approval-card injection defect; no calibration scenario exercises it yet — authoring one is the corpus's job next cycle |
| L-20260806-06 | 2026-08-06 | a5b77aa | plugins/tdd-playbook/skills/tdd-playbook/SKILL.md | §12 exhaustiveness rule: a test claiming every/all/no-other states what a violating case looks like and how it would see it | — | none | 0 | doctrine for H14; its mechanical half is exhaustive_claim_guard (warn), calibrated in both directions in test_hooks |
| L-20260806-07 | 2026-08-06 | a5b77aa | plugins/tdd-playbook/skills/tdd-playbook/SKILL.md | §13 guard self-claims are unverified claims — two-directional calibration table per blocking guard | — | none | 0 | doctrine for H13; the block half is Cheliped's case-sensitivity defect, the allow half is this repo's own `ln` false positive |
| L-20260806-08 | 2026-08-06 | a5b77aa | plugins/tdd-playbook/skills/tdd-playbook/SKILL.md | §9 `/security-review` at the phase boundary that introduces the surface, not at merge | — | none | 0 | timing change only; nothing in the suite measures when a human-invoked review runs, which is itself the honest reason this is `none` |
| L-20260806-09 | 2026-08-06 | a5b77aa | plugins/tdd-playbook/skills/tdd-playbook/SKILL.md | §7 a quarantine marker is not real until something deselects it | — | none | 0 | closes the same claim-about-a-gate gap as §13, applied to the flaky marker |

### Registered 2026-08-06 (later) — baseline ddbb856 (the narrowed-scope class, v1.30)

Written against the PRE-change tree: `ddbb856` contains the ledger coverage fix but none of
the doctrine or denominator work below. **This block is the first real customer of that fix.**
Under the previous rule its coverage would have been REFUSED — the clause required
SKILL.md@baseline to equal SKILL.md@EPOCH, and SKILL.md has moved since the epoch, so no
post-epoch baseline could ever satisfy it. That the rows below cover at all is the end-to-end
proof, on a real change rather than a fixture.

`expect: none` on the doctrine rows for the reason already recorded in the 08-06 block: SKILL
prose is not in EFFECTFUL, and inertness is itself the prediction — if a §-prose addition ever
moves a scenario, the row becomes a SURPRISE and the exemption was what was wrong.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260806-10 | 2026-08-06 | ddbb856 | plugins/tdd-playbook/skills/tdd-playbook/SKILL.md | §12: a verification result is a CLAIM and carries its SCOPE — never a numerator without its denominator; §4a cross-reference naming vacuity as the degenerate case | — | none | 0 | doctrine for H15 (Cheliped's narrowed-scope class). Deliberately NOT counted as the deliverable: their own data is three loaded rules walked past in one sprint, so the mechanical half (gate/sweep/harness denominators) is the work and this row exists so those mechanisms have something to cite |

### Scored 2026-08-06 — run 2026-08-06 · repo 113b0aa (PARTIAL RUN — read the denominator)

**This run measured 17 of 40 scenarios.** It hit a monthly spend limit 23 scenarios in, so
23 rows are INVALID: the CLI refused and no agent ran. The header's `selected 40 of 40` is
true and is not the number that matters here; `recall 13/13` and `FP 2/4` are computed over
the 17 that executed. Read them as a narrow sample, not a suite result — which is the H15
lesson landing on the same day it shipped.

Only the entries whose scenarios ACTUALLY RAN are scored below. The other eight remain
PENDING: `bind_entry` now requires a block to have measured *this entry's scenarios*, not
merely to have measured something. Before that fix (found by running it, minutes after
shipping the v1.30 doctrine) this run would have spent eight pre-registered predictions as
INCONCLUSIVE(not-selected) against scenarios that never executed. A prediction is spendable
once.

| id | scenario | baseline | actual | delta | verdict | note |
|---|---|---|---|---|---|---|
| L-20260805-20 | false-negative-claim | 2/3 | 3/3 | +1 | HIT | claims-verifier |
| L-20260805-21 | unwired-deliverable | 1/3 | 3/3 | +2 | HIT | tripwire-auditor |
| L-20260805-23 | control-parked-deferral | 0/3 | 3/3 | +3 | HIT | 0/3 -> 3/3, the only movement large enough to be significant on its own at n=3 (Fisher p=0.050) |

**3 of 3 scored entries HIT.** No follow-up debts owed. Cycle-level significance is not
claimed: three moved entries is below the five the sign test needs (`power.py`), and the
run's own scope was narrowed by a billing limit rather than by design.

The six `expect: none` doctrine rows registered against `a5b77aa` also bound to this run and
are scored here. They name no scenario, so there is nothing to compare and the honest verdict
is INCONCLUSIVE rather than HELD: their claim is that a §-prose change is inert, and a run
that measured 17 of 40 scenarios cannot confirm inertness. Recorded as a known weakness of
the `expect: none` shape — the row is spendable but not scoreable — rather than rounded up.

| id | scenario | baseline | actual | delta | verdict | note |
|---|---|---|---|---|---|---|
| L-20260806-04 | — | — | — | — | INCONCLUSIVE(no-baseline) | expect=none names no scenario; a partial run cannot confirm inertness |
| L-20260806-05 | — | — | — | — | INCONCLUSIVE(no-baseline) | as above |
| L-20260806-06 | — | — | — | — | INCONCLUSIVE(no-baseline) | as above |
| L-20260806-07 | — | — | — | — | INCONCLUSIVE(no-baseline) | as above |
| L-20260806-08 | — | — | — | — | INCONCLUSIVE(no-baseline) | as above |
| L-20260806-09 | — | — | — | — | INCONCLUSIVE(no-baseline) | as above |

### Registered 2026-08-06 (third) — baseline a54e772 (Cheliped's correction to v1.30's §12)

Cheliped audited the claim I put in SKILL.md and refuted half of it. I had written that every
mechanical guard that fired caught something the prose did not — true, and it implies
"mechanisms found everything", which their own 27-commit record does not support. Three of
their highest-impact defects came from OUTSIDE any mechanism: a human seeing a symptom (the
App Store launching in a browser, for days, on every full-suite run), a peer's message (my
note about their `opt()`, which surfaced 11 defects none of their gates could see because the
gates were the broken thing), and someone chasing an anomaly that did not fit.

Their sharpened rule is strictly better and is what lands here instead: **a mechanism cannot
detect its own absence.** ruff not running was invisible to ruff; bandit not running was
invisible to bandit; the summary asserting they had run was the thing that was wrong. And
their caveat, which I would not have thought to add: a LIVENESS plant and a DETECTION plant
are different tests — proving the reporting fires does not prove the gate is configured to
catch the right things.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260806-11 | 2026-08-06 | a54e772 | plugins/tdd-playbook/skills/tdd-playbook/SKILL.md | §12: correct the mechanisms-found-everything overclaim to "a mechanism cannot detect its own absence"; add liveness-plant vs detection-plant | — | none | 0 | a correction to text shipped hours earlier in v1.30, refuted by the peer whose data it cited — the doctrine row it replaces was itself an overclaim, which is the §12 claims discipline applied to §12 |

### Registered 2026-08-07 — baseline 3659abf (portable TEST-LOCK paths)

These two rows were recovered when the post-commit gate caught what the pre-commit gate did
not: `ledger.py` still reads committed state, the exact dated blind spot already registered
as debt on `gate-surface-ledger`.  The cited baseline is nevertheless the actual pre-change
tree (`3659abf`, immediately before `9296b9b`), not a post-change backfill; the coverage
predicate can therefore independently verify both paths changed after it.  This incident is
additional evidence for that existing debt, not a claim that late registration is normal.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260807-01 | 2026-08-07 | 3659abf | plugins/tdd-playbook/commands/grade.md | point `/grade` at the Git-common-dir event journal, retaining the legacy non-Git fallback | — | none | 0 | storage-path documentation only; no calibration scenario measures which local journal path the operator reads |
| L-20260807-02 | 2026-08-07 | 3659abf | plugins/tdd-playbook/commands/tdd-unlock.md | document the canonical event journal and legacy non-Git fallback | — | none | 0 | storage-path documentation only; the runtime behavior is covered by planted adapter suites, not an agent-output scenario |

### Registered 2026-08-09 — baseline 0c114ca (owner-control Phase 2: CIVerd retirement)

The CIVerd engine is retired in v1.32.0 (owner-control plan, rev 3). `plan_block.py` exists
solely to emit a `civerd-plan` block for that engine's plan-predicate evaluator to parse, and
`capabilities.json` already recorded it as never armed — "if repos.yml is never armed, plans
land INERT". With the consumer gone the producer is a writer with no reader, so it goes with
it, and `/tdd-plan` loses the scaffold/validate step that fed it. Approved plans continue to
land as ordinary markdown in `docs/plans/gated/`; the historical files are kept.

Registered BEFORE the edit, not after: `ledger.py check` reads committed state, so an entry in
the same commit as its surface change is invisible to the coverage predicate (the dated blind
spot already owned as debt on `gate-surface-ledger`, and the reason the 2026-08-07 block above
had to be recovered).

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260809-01 | 2026-08-09 | 0c114ca | plugins/tdd-playbook/commands/tdd-plan.md | remove the `plan_block.py scaffold/validate` step; approved plans land as ordinary markdown in docs/plans/gated/ | — | none | 0 | tooling-path documentation only — no calibration scenario measures how a gated plan FILE is scaffolded; the §0 plan CONTENT rules the agents are scored on are untouched |

### Registered 2026-08-12 — baseline 3fafc9e (the Readable Surface, v1.34.0 D1/D4)

Four NEW role-lens adversary briefs and one NEW command, per the approved plan
(`docs/plans/gated/2026-08-12-readable-surface.md`). Registered BEFORE the surface commit,
in its own commit, because `ledger.py check` reads committed state — an entry landing in
the same commit as its surface is invisible to the coverage predicate (the dated
`gate-surface-ledger` blind spot; the 2026-08-09 precedent).

The four agent entries predict `up` from zero: each brief is born WITH its plant/control
pair in `calibration/corpus/`, so the first live run scores recall (plant fired) and FP
(control quiet) from a baseline of nothing. `claimed` is 3 reps per scenario (the house
default). The command entry is `none`: `/readable` is a narration workflow — prose never
gates, and no calibration scenario measures narration quality by design (reading 2,
rejected, in the plan).

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260812-01 | 2026-08-12 | 3fafc9e | plugins/tdd-playbook/agents/security-adversary.md; calibration/corpus/approved/secret-token-reaches-output.json; calibration/corpus/approved/control-token-kept-out-of-output.json | NEW brief: CISO loss function, rows S17–S24, forced EXPOSED/CONTAINED verdict lines, born with its plant/control pair | secret-token-reaches-output; control-token-kept-out-of-output | up | 3 | first live run scores recall (plant fired) and FP (control quiet) from a baseline of zero |
| L-20260812-02 | 2026-08-12 | 3fafc9e | plugins/tdd-playbook/agents/test-quality-adversary.md; calibration/corpus/approved/assertion-free-smoke-test.json; calibration/corpus/approved/control-asserting-smoke-test.json | NEW brief: head-of-QA loss function, rows S25–S27+S31, forced HOLLOW/LOAD-BEARING verdict lines | assertion-free-smoke-test; control-asserting-smoke-test | up | 3 | same shape: plant (test that cannot fail) + paired control (real assertion) |
| L-20260812-03 | 2026-08-12 | 3fafc9e | plugins/tdd-playbook/agents/observability-adversary.md; calibration/corpus/approved/swallowed-export-failure.json; calibration/corpus/approved/control-export-failure-surfaces.json | NEW brief: 3am ops loss function, rows S02+S32+S33, forced SILENT/OBSERVABLE verdict lines | swallowed-export-failure; control-export-failure-surfaces | up | 3 | same shape: plant (except:pass, exit 0) + paired control (stderr + exit 1) |
| L-20260812-04 | 2026-08-12 | 3fafc9e | plugins/tdd-playbook/agents/adoption-adversary.md; calibration/corpus/approved/dead-end-error-message.json; calibration/corpus/approved/control-helpful-error-message.json | NEW brief: product-owner loss function, rows S38–S41, forced STRANDED/LANDS verdict lines | dead-end-error-message; control-helpful-error-message | up | 3 | same shape: plant (bare "error", no next step) + paired control (usage hint kept) |
| L-20260812-05 | 2026-08-12 | 3fafc9e | plugins/tdd-playbook/commands/readable.md | NEW command: render the readable surface; citation workflow (verify_citations, N>=1 floor); never dispatches; never gates | — | none | 0 | narration workflow only — prose never gates by design, and no calibration scenario measures narration quality (plan reading 2, rejected) |

### Registered 2026-08-12 — baseline 8a94ca8 (observability-adversary restraint fix)

First live calibration of the four new pairs: security 2/2 PASS, test-quality 2/2 PASS,
observability plant 3/3 PASS but its paired control **0/3 BLOCKING FAIL**
(wrong-verdict-line) — the agent called clean code SILENT, where the failure path writes
stderr AND returns 1. False-positive direction: the brief's restraint was prose
("match the ask to the repo's shape"), and a weak doer over-applied the S32/S33 hunt
items to demand alerting infrastructure from a CLI. Fix the AGENT, never the plant: the
restraint becomes a mechanical rule — for a CLI, stderr + nonzero exit IS a watched
surface, and SILENT is reserved for a path reaching NO surface.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260812-06 | 2026-08-12 | 8a94ca8 | plugins/tdd-playbook/agents/observability-adversary.md | restraint made mechanical: stderr+nonzero-exit is a surface for a CLI; SILENT requires a path reaching NO surface | swallowed-export-failure; control-export-failure-surfaces | up | 3 | the control must go 0/3->3/3 quiet AND the plant must STAY 3/3 (narrowing is not amnesty — replay both directions) |

### Registered 2026-08-13 — baseline 2eb92f0 (adoption-adversary scope rule + computed verdict)

Live run: plant 2/3 (found-but-hedged, AMBER), control 0/3 (wrong-verdict-line, BLOCKING
FAIL) — the SAME root cause as observability, which makes it a class, not an incident.
The task names ONE focus question (S40, error messages) and the control answers it
(prints the bad command AND the usage line), but the brief hunts FOUR rows; the fixture
legitimately has no README (S38) and no usage signal (S41), so a weak doer imports those
out-of-scope gaps into the verdict and reports STRANDED on clean work.

Fix the AGENT, never the plant: (a) a SCOPE RULE — when the request names a focus, the
verdict covers only that and everything else goes to notes; (b) the verdict is computed
from a table of in-scope rows; (c) explicit anti-hedging, since the plant was found but
the verdict line was qualified.

Security and test-quality passed 2/2 live, but they passed partly because this fixture is
clean on THEIR other hunt rows — the same latent mismatch exists there and is registered
as dated debt on role-adversaries rather than changed without a failing test to prove the
change right.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260813-01 | 2026-08-13 | 2eb92f0 | plugins/tdd-playbook/agents/adoption-adversary.md | scope rule (focus question bounds the verdict), computed verdict table, anti-hedging | dead-end-error-message; control-helpful-error-message | up | 3 | control must go 0/3->3/3 quiet AND the plant must reach 3/3 unhedged — both directions, narrowing is not amnesty |

### Registered 2026-08-13 — baseline 8a94ca8 (adoption pair RE-AUTHORED — the control was the bug)

The adoption control sat at 0/3 through an agent fix. Before touching the agent again I
captured what it actually says, and it was RIGHT: it produced the required table, computed
the verdict mechanically, and named FOUR genuine S40 dead ends in the fixture — missing
discount arguments (IndexError traceback), non-numeric price (ValueError), out-of-range
pct (ValueError), and a bare `print("denied")` — none of which tell a new user what to do
next. The control had cleaned only the unknown-command path, so it was never clean code
and could not measure restraint.

This is a THIRD category beyond "fix the agent, never the plant": a MIS-AUTHORED CONTROL.
That rule assumes the pair was authored correctly; blunting a verifier that is behaving
correctly, to satisfy a test that tests the wrong thing, is the inversion of it. Evidence
first (the captured transcript), then the pair changed — never the other way round.

Re-authored so plant and control differ ONLY in the planted defect: both now give guidance
on the discount and authorization paths; the plant alone degrades the unknown-command
message to bare "error". The plant's oracle is TIGHTENED (rule c — tightenings always
pass) to require it NAME the unknown-command defect, so it can no longer fire on ambient
noise. Legal vs baseline v1.33.1 because these files did not exist there; they freeze at
the v1.34.0 tag.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260813-02 | 2026-08-13 | 8a94ca8 | calibration/corpus/approved/dead-end-error-message.json; calibration/corpus/approved/control-helpful-error-message.json | re-author: pair differs only in the planted defect; plant oracle tightened to require naming it | dead-end-error-message; control-helpful-error-message | up | 3 | control must go 0/3->3/3 (it is finally clean) AND the plant must hold 3/3 firing for the RIGHT reason |

## Scored 2026-08-13 — run 2026-08-13 · repo f800c26

Only the entries the run actually BOUND are scored here. L-20260812-01..05 measured their
scenarios from a baseline of nothing (INCONCLUSIVE(no-baseline)) and stay PENDING — the
tool's own rule: a prediction can be spent once, and spending it on a comparison the run
never made is worse than leaving it open. That also keeps them fresh as coverage for the
surfaces they name, which is the property `coverage_problems` needs.

| id | scenario | baseline | actual | delta | verdict | note |
|---|---|---|---|---|---|---|
| L-20260812-06 | swallowed-export-failure | 3/3 | 3/3 | 0 | FLAT | plant held while the brief was narrowed — narrowing is not amnesty |
| L-20260812-06 | control-export-failure-surfaces | 0/3 | 2/3 | +2 | PARTIAL | genuine improvement, still not k/k at the haiku floor |
| L-20260813-01 | dead-end-error-message | 2/3 | 3/3 | +1 | PARTIAL | the computed-verdict table removed the hedging |
| L-20260813-01 | control-helpful-error-message | 0/3 | 0/3 | 0 | FLAT | **the signal**: an agent fix that moved the control NOT AT ALL is what said the control, not the agent, was broken |
| L-20260813-02 | dead-end-error-message | 3/3 | 3/3 | 0 | FLAT | plant held under a TIGHTENED oracle requiring it name the defect |
| L-20260813-02 | control-helpful-error-message | 0/3 | 3/3 | +3 | HIT | re-authored pair; largest single move in the record |

| L-20260806-10 | — | — | — | — | INCONCLUSIVE(no-baseline) | no-effect entry bound by the 2026-08-12 run; no comparison to make |
| L-20260806-11 | — | — | — | — | INCONCLUSIVE(no-baseline) | as above |
| L-20260807-01 | — | — | — | — | INCONCLUSIVE(no-baseline) | as above |
| L-20260807-02 | — | — | — | — | INCONCLUSIVE(no-baseline) | as above |
| L-20260809-01 | — | — | — | — | INCONCLUSIVE(no-baseline) | as above |

| L-20260812-01 | secret-token-reaches-output | — | 3/3 | — | INCONCLUSIVE(no-baseline) | born with its plant; nothing prior to compare against |
| L-20260812-01 | control-token-kept-out-of-output | — | 3/3 | — | INCONCLUSIVE(no-baseline) | as above; restraint held first time |
| L-20260812-02 | assertion-free-smoke-test | — | 3/3 | — | INCONCLUSIVE(no-baseline) | as above |
| L-20260812-02 | control-asserting-smoke-test | — | 3/3 | — | INCONCLUSIVE(no-baseline) | as above |
| L-20260812-03 | swallowed-export-failure | — | 3/3 | — | INCONCLUSIVE(no-baseline) | plant fired first time |
| L-20260812-03 | control-export-failure-surfaces | — | 0/3 | — | INCONCLUSIVE(no-baseline) | control failed first time — opened the three-fix sequence scored above |
| L-20260812-04 | dead-end-error-message | — | 2/3 | — | INCONCLUSIVE(no-baseline) | plant found but hedged |
| L-20260812-04 | control-helpful-error-message | — | 0/3 | — | INCONCLUSIVE(no-baseline) | control failed first time — the mis-authored pair, diagnosed from a captured transcript |

| L-20260812-05 | — | — | — | — | INCONCLUSIVE(no-baseline) | no-effect entry (/readable narrates, never gates); nothing to compare |

**Why pre-registration earned its cost here.** The FLAT row on L-20260813-01's control is the
one that mattered: a fix predicted to move the control moved it zero. A self-narrated summary
would have rounded that into "improved the agent"; the ledger priced the prediction and showed
it did nothing, which is what sent me to capture the agent's actual transcript — where it turned
out the agent was right and the control was mis-authored.


### Registered 2026-08-13 — the ledger's own coverage defect, found by hitting it

Not an entry: a note, because the change is to `ledger.py` and is covered by its own
red-first tests in `calibration/test_harness.py`.

`coverage_problems` diffed gate surfaces from the EPOCH while requiring the covering entry be
UNSCORED — and scoring is mandatory for any entry a run BINDS. So the moment `check` demanded
scoring for an entry covering a path, that path went permanently uncovered, including paths
untouched for two releases. Registering and scoring are each correct and were jointly
unsatisfiable. This is the trap this function's own docstring documents fixing for the
ANTI-BACKFILL clause ("un-satisfiable, and silent until the moment someone tried", naming
SKILL.md); the freshness clause still carried it.

Fixed at the property, not the symptom. `fresh_ids_from`'s docstring already states what
freshness was reaching for — a priced prediction "cannot be reused to authorize a LATER
edit". "Scored at all" was a proxy for that and also revoked an entry for the edit it was
written for. Coverage now asks the temporal question: a scored entry still covers a path that
has NOT MOVED since it was priced, and covers nothing after. Anti-reuse is preserved exactly,
anti-backfill is untouched, and a scoring block with no recorded `repo <sha>` fails CLOSED.

Four re-coverage entries written against the un-fixed mechanism (L-20260813-04..07, bookkeeping
for `grade.md`, `tdd-plan.md`, `tdd-unlock.md`, `SKILL.md`) were REMOVED rather than left
standing: the defect that forced them is gone, and no-effect entries nobody needs inflate the
very no-effect share the harness watches as a sign the instrument is being satisfied rather
than used.

**Correction, same day, found by CI and not by me.** The 2026-08-13 scoring blocks first
cited `repo 5eac709` — a commit my own resets and cherry-picks during this release ORPHANED.
It resolved locally (it was still in my object store) and does not exist in the pushed
history, so the fresh-clone gate could not place the pricing point and refused coverage. The
new fail-closed rule behaved exactly as designed: an unplaceable pricing sha covers nothing.
Re-pointed to `f800c26`, the shipped commit that carries the scored tree state, verified by
`git diff f800c26..HEAD` over the scored paths being empty — they have not moved since.

The transferable lesson is about EVIDENCE, not git: a durable record may only cite shas that
exist in the SHIPPED history, and a local object store hides orphaned ones. Verify records
that cite history in a FRESH CLONE, because the machine that wrote them is the one machine
that cannot detect the mistake.

**Second correction, same class, same day — the sweep I should have done the first time.**
`L-20260812-06` and `L-20260813-02` also cited baselines (`f4b4227`, `cd8eacc`) that this
session's squashing orphaned. When the scoring-block sha was found unreachable I fixed that
one instance and did not sweep the file for the rest, so CI round-tripped twice on the same
defect. Both re-pointed to `8a94ca8` — the shipped v1.34.0 commit carrying the pre-change
state for both surfaces (the briefs and the corpus pair existed there in their original
form, so the anti-backfill clause still holds). Fixing one instance of a class and not
sweeping for its siblings is the same failure as a narrowed check reporting a true fact
about the wrong scope.

### Registered 2026-08-13 — baseline 2a95101 (/readable narration: the business-owner test)

The surface's FIRST real read failed its only reader: the facts were fine, the narration
was repo idiom ("declared unarmed sweeps", "no liveness probe"), and David had to ask for
plain English again — the escape the feature exists to prevent, recorded as the first
finding of its own experiment. The command's step 2 gains the mechanical wording of the
rule so any session fails the same way visibly instead of by taste.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260813-08 | 2026-08-13 | 2a95101 | plugins/tdd-playbook/commands/readable.md | step 2 gains the business-owner test (plain-language rule made mechanical wording, with examples) | — | none | 0 | command prose; narration quality is deliberately not scenario-measured (reading 2, rejected) — the rule's teeth are the reader |

### Registered 2026-08-13 — baseline f72c5fc (/readable narration rule 2: size every worry)

Second narration failure of the surface's first day, distinct from the first: the render
was alarming without being sized — "13 possibly dead things", "7 off" — and the owner's
follow-up questions ("why aren't they on? are we violating anti-dark?") were all answered
by context the narration ALREADY HAD and did not say. Worry without disposition is not
readable; the reader must never leave more alarmed than the facts warrant.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260813-09 | 2026-08-13 | f72c5fc | plugins/tdd-playbook/commands/readable.md | step 2 gains SIZE EVERY WORRY: every count carries its disposition in the same breath; "off" is never bare (which KIND of off); the page ends with the one thing worth doing or "nothing to do" | — | none | 0 | command prose; narration quality is deliberately not scenario-measured — the rule's teeth are the reader |

### Registered 2026-08-13 — baseline 09d23fb (cheliped proposal adjudication: 7 doctrine additions)

Four proposals read from cheliped's handoff queue. Two REJECTED as already-landed doctrine
(seam-contract IS v1.26 — SKILL :180/:53-66/:668-690/:277; guard-calibration IS v1.25 —
:999-1002/:171-177/:220/:131). Two landed in part: deny-table-first (the real gap — deny=0,
enforcer=0, last-match=0 hits in SKILL) and 6 of gate-victim-sweep's 12 sub-proposals,
merged to seven edits: a §9 deny-table block (absorbing sub-proposal 7's three gate-diff
questions), a §1 victim-sweep bullet (sub-proposals 1+5+9 merged), a §2 check-vs-use row
(8), and one-liners in §4a (4), §4 (12), §10 (2), §12 (10). Rejected: 3 (covered :316-318),
6 (§6c family parity), 11 (cheliped-local).

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260813-10 | 2026-08-13 | 09d23fb | plugins/tdd-playbook/skills/tdd-playbook/SKILL.md | seven doctrine ADDITIONS (rule d — additions free): §9 deny-table-first block, §1 victim sweep, §2 check-vs-use row, §4a refusal-diagnosis line, §4 by-text-exemption clause, §10 checkpoint-out-of-place line, §12 parse-absence-claims line | — | none | 0 | doctrine prose; no calibration scenario measures doctrine text — the agents enforcing these rules are scenario-measured separately |

### Registered 2026-08-14 — review-as-judgment-surface: the six authoring briefs gain the record-output contract

D-A A6 (the plan budgeted this cost explicitly): `agents/` is EFFECTFUL, so the six brief
edits register with named scenarios and a claimed movement. The appended section is an
OUTPUT contract (class/recurrence_key/catalog_row on ledger-bound findings), not a
detection change — the claimed movement is therefore the both-directions replay (plants
stay caught, controls stay quiet; brief GROWTH burying the forced verdict lines is the
documented risk this measures). A FLAT score is itself informative and converts, per the
instrument's own rule, into the follow-up: author a PRODUCER scenario whose oracle checks
class/key emission — the behavior no current scenario measures.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260814-01 | 2026-08-14 | 8641b70 | plugins/tdd-playbook/agents/integration-adversary.md; plugins/tdd-playbook/agents/architecture-adversary.md; plugins/tdd-playbook/agents/tripwire-auditor.md; plugins/tdd-playbook/agents/script-adversary.md; plugins/tdd-playbook/agents/claims-verifier.md; plugins/tdd-playbook/agents/adoption-adversary.md | review-record output contract appended (class deterministic-or-judgment + short-kebab recurrence_key + optional catalog_row, required for records dated >= 2026-08-15) | island-write-only-plan; control-connected-plan; band-aid-parallel-list; good-fix-single-source; unwired-deliverable; control-export-wired; script-unsafe-probe; control-script-safe-probe; false-negative-claim; control-true-dead-code; dead-end-error-message; control-helpful-error-message | up | 3 | both-directions replay: every plant stays caught AND every control stays quiet at 3/3 despite the longer briefs (burial of the forced lines is the documented brief-growth failure); FLAT converts to the named follow-up — a producer scenario scoring class/key emission from a baseline of zero |

### Registered 2026-08-15 — baseline 4dc1ff0

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260815-01 | 2026-08-15 | 4dc1ff0 | plugins/tdd-playbook/agents/security-adversary.md; plugins/tdd-playbook/agents/test-quality-adversary.md | hunt #6 (ambient-input self-consistency / inert control) appended to both briefs — §1 hardening from the cheliped field report | secret-token-reaches-output; control-token-kept-out-of-output; assertion-free-smoke-test; control-asserting-smoke-test | up | 3 | both-directions replay (the brief-growth burial check): the longer briefs must not bury existing detection — every plant stays caught and every control stays quiet at 3/3. The NEW shape (a guard seeded by hand over an inert gate) has no corpus plant YET; that anchor is dated debt on calibration-loop and will register its own prediction when authored, so this entry claims only no-regression, not new coverage |

### Registered 2026-08-16 — baseline d817482: the §1 anchor's first replay exposes an over-trigger

The newly-authored §1 anchor (calibration/corpus/approved/ambient-input-seeded-gate-test.json
+ its control) was replayed against the hardened test-quality-adversary the same day it landed.
The plant was caught HOLLOW 3/3 — but the clean control was FALSE-POSITIVED 0/3: the adversary
called a correctly-wired test (one that DRIVES `run_agent_once`, whose body publishes the ambient
grants) HOLLOW. That is a precision defect in hunt #6, not a bad fixture (the control is genuinely
load-bearing — deleting the wiring fails it). The restraint clause below encodes the discriminator
the brief already implied but did not make load-bearing: hand-seeded input is HOLLOW; a driven
production entry that publishes the input is LOAD-BEARING. The claimed movement is the control
flipping to clean WITHOUT blinding the plant (the over-correction risk this measures), confirmed by
the same-day re-run (plant 3/3 caught · control 0/3 → 3/3 · FP 1/1 → 0/1).

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260816-01 | 2026-08-16 | d817482 | plugins/tdd-playbook/agents/test-quality-adversary.md; calibration/corpus/approved/ambient-input-seeded-gate-test.json; calibration/corpus/approved/control-ambient-input-driven-gate-test.json | hunt #6 restraint clause (flag HOLLOW ONLY when the TEST hand-seeds the ambient state; do NOT flag when the test drives a production entry that publishes it — trace the entry's body before flagging) PLUS the §13 anchor authored (the plant+control this entry names as scenarios) — fulfils L-20260815-01's promise to register the anchor's prediction when authored | ambient-input-seeded-gate-test; control-ambient-input-driven-gate-test | up | 3 | first §13 replay of the anchor caught the plant (3/3 HOLLOW) but false-positived the clean control (0/3 — the adversary called the correctly-wired driven test HOLLOW). The restraint clause removes the false green on the driven-entry case; the same-day re-run confirmed BOTH directions (plant holds 3/3, control 0/3 → 3/3, FP 1/1 → 0/1), proving the clause did not blind the plant. Baseline d817482 carries the pre-restraint brief AND predates both corpus fixtures (so each named surface genuinely MOVED after it). The plant+control are new scenarios (no baseline → INCONCLUSIVE on first score); the measurable claim is the control's 3-rep flip to clean |

### Registered 2026-08-16 — baseline 068ab7b: TEST-LOCK deadlock-fix command-doc updates (inert)

The TEST-LOCK cross-session deadlock fix touched two COMMAND docs — `/grade` gains the forced +
session_downgrade unlock-journal readers, `/tdd-unlock` documents the `unlock --force` recovery.
Command text is deliberately OUT of EFFECTFUL (2026-08-14 decision): no calibration scenario
measures `/grade` or `/tdd-unlock` behaviour, so this is an INERT gate-surface change registered
purely for coverage — `expect=none`, no scenario, claimed 0.

| id | date | baseline_sha | surface | change | scenarios | expect | claimed | rationale |
|---|---|---|---|---|---|---|---|---|
| L-20260816-02 | 2026-08-16 | 068ab7b | plugins/tdd-playbook/commands/grade.md; plugins/tdd-playbook/commands/tdd-unlock.md | /grade reads the forced + session_downgrade unlock-journal flags; /tdd-unlock documents `unlock --force` recovery (TEST-LOCK cross-session deadlock fix) |  | none | 0 | command DOCS, not adversary briefs — commands/ is in SURFACE_PATTERNS (coverage) but OUT of EFFECTFUL, so no calibration scenario measures these; an inert doc change registered for coverage per the 2026-08-14 decision |
