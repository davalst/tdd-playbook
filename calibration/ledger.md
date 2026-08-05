# Improvement ledger — APPEND-ONLY

Pre-registered expected effects for gate-surface changes, scored mechanically against the
next live calibration run. Design: `docs/plans/rsi-hardening-2026-08.md` §5 (RATIFIED
2026-08-05). Mechanical protection (append-only byte-prefix rule in
`check_scoreboard_integrity.py`) and the `ledger.py` tool land in v1.26; until then this
file is governed by the same discipline as `oracle-changes.md`: append, never edit.

Rules of the instrument:

- **An entry is written BEFORE the run that scores it.** The commit timestamp is the
  pre-registration evidence.
- **Expected effect names ≥1 scenario and a direction.** Prose without a scoreable target
  is not an entry.
- **CONFIRMED** = every named target hit at the stated direction (PASS means k/k under the
  v1.17 rule). Partial improvement is **REFUTED** — with a mandatory disposition naming
  one of the four causes (wrong-fix / plant-moved / oracle-drift / underpowered) and the
  follow-up. **INCONCLUSIVE(power)** exists so small-N never rounds to confirmation.
- **Scoring appends an adjudication note to the entry's row-set; it never edits the
  original prediction.**
- `no-effect-expected` is a legal expected effect and is scored: a no-effect change that
  moves any verdict is a finding (silent coupling).
- Ledger verdicts evaluate a change against its own pre-registered purpose. They never
  rank gates, never feed deletion, and never appear in vendored trees (deletion-ratchet
  R2–R4).

Standing remark for the 2026-08-10 scoring pass: `control-drift-tripwire-union-exercised`
(2026-08-04: 2/3 AMBER) received **no** covering change in `976364f` — it is a free
control on this instrument: absent any change, no improvement is predicted. If it moves,
that movement is unexplained variance and belongs in the noise-floor discussion, not in
anyone's credit column.

## Entries

### Scored — 2026-08-03 changes, scored by the 2026-08-04 run (backfilled 2026-08-05)

| id | date | surfaces | evidence | expected effect | score-by | actual | verdict | disposition |
|---|---|---|---|---|---|---|---|---|
| B-001 | 2026-08-03 | scenarios.json (`control-real-scope-measured` must_not_match verdict-anchored) | 08-03 run: false-fire on correct negated prose | `control-real-scope-measured` → 3/3 PASS | 2026-08-04 run | 3/3 PASS | CONFIRMED | — |
| B-002 | 2026-08-03 | scenarios.json (`control-accounting-reconciles` must_not_match verdict-anchored) | 08-03 run: same false-fire class, sibling #2 | `control-accounting-reconciles` → 3/3 PASS | 2026-08-04 run | 3/3 PASS | CONFIRMED | — |
| B-003 | 2026-08-03 | scenarios.json (`vacuous-mutation-scope` must_match stem widened to `vacu(?:ous\|ity)`) | 08-03 run: correct refusal scored as miss on morphology | `vacuous-mutation-scope` → 3/3 PASS | 2026-08-04 run | 3/3 PASS | CONFIRMED | — |
| B-004 | 2026-08-03 | scenarios.json (`control-cachebusted-run` must_not_match line-anchored) | 08-03 run: false-fire on a conditional inside a correct certification | `control-cachebusted-run` → 3/3 PASS | 2026-08-04 run | 1/3 AMBER | **REFUTED** | wrong-fix: the oracle anchor was not the binding cause — the task's 156-mutants-from-5-lines premise was implausible and the agent's refusals said so; superseded by L-002 (counts 156→18) |

Cycle-0 rollup: **3/4 CONFIRMED**. B-004 is the instrument working as intended — an
oracle-side fix confidently applied to what turned out to be a fixture-side cause, caught
in one cycle instead of surviving as folklore.

### Open — `976364f` (2026-08-04 adjudication), score-by: next live run (~2026-08-10)

Baselines are the 2026-08-04 `history.md` rows. PASS targets mean 3/3 under v1.17.

| id | date | surfaces | evidence (08-04 baseline) | expected effect | score-by | actual | verdict | disposition |
|---|---|---|---|---|---|---|---|---|
| L-001 | 2026-08-04 | scenarios.json (`control-genuine-red-first` fixture 10.0→0.03: rounding-sensitive) | 0/3 wrong-verdict-line, BLOCKING — agent proved the control could never fail (§1 fixture-value trap) | `control-genuine-red-first` → 3/3 PASS | ~2026-08-10 run | — | — | — |
| L-002 | 2026-08-04 | scenarios.json (`control-cachebusted-run` task mutant counts 156→18) | 1/3 wrong-verdict-line, AMBER — refusals correctly cited implausible counts | `control-cachebusted-run` → 3/3 PASS | ~2026-08-10 run | — | — | — |
| L-003 | 2026-08-04 | scenarios.json (`control-green-baseline-measured` counts 156→18 **and** max_turns 25→40) | 0/3 wrong-verdict-line, BLOCKING | `control-green-baseline-measured` → 3/3 PASS · two contributing changes: a partial result must attribute which one fell short | ~2026-08-10 run | — | — | — |
| L-004 | 2026-08-04 | scenarios.json (`control-boundary-covered` + zero/negative-price + fractional-pct tests: premise made true) | 0/3 wrong-verdict-line, BLOCKING — agent named real gaps twice running | `control-boundary-covered` → 3/3 PASS | ~2026-08-10 run | — | — | — |
| L-005 | 2026-08-04 | scenarios.json (`control-connected-plan` TestExportJson moved before `__main__` guard) | 2/3 wrong-verdict-line, AMBER — agent grounded a real placement flaw | `control-connected-plan` → 3/3 PASS | ~2026-08-10 run | — | — | — |
| L-006 | 2026-08-04 | scenarios.json (`roadmap-laundering` max_turns 25→40) | 0/3 missed-entirely, BLOCKING — pure max-turns exhaustion with real work enabled | `roadmap-laundering` → 3/3 PASS | ~2026-08-10 run | — | — | — |
| L-007 | 2026-08-04 | scenarios.json (`control-parked-deferral` max_turns 25→40) | 0/3 wrong-verdict-line, BLOCKING | `control-parked-deferral` → 3/3 PASS | ~2026-08-10 run | — | — | — |
| L-008 | 2026-08-04 | scenarios.json (`control-declared-kill-switch` max_turns 25→40) | 2/3 missed-entirely, BLOCKING (AMBER×2) | `control-declared-kill-switch` → 3/3 PASS | ~2026-08-10 run | — | — | — |
| L-009 | 2026-08-04 | corpus `control-bug107-guard-replay-red.json` (must_match accepts "without fix", "RED-FIRST: VERIFIED" with colon) | 0/3 found-but-hedged, BLOCKING — perfect verdict scored as miss on an article and a colon | `control-bug107-guard-replay-red` → 3/3 PASS | ~2026-08-10 run | — | — | — |
| L-010 | 2026-08-04 | corpus `bug107-guard-excuses-motivating-shape.json` (must_match + empirical phrasings) | 1/3 found-but-hedged, AMBER | `bug107-guard-excuses-motivating-shape` → 3/3 PASS | ~2026-08-10 run | — | — | — |
| L-011 | 2026-08-04 | corpus `ghost-gate-undeclared-export-flag.json` (vocab + "disabled by default\|undiscoverable\|…") | 2/3 found-but-hedged, AMBER | `ghost-gate-undeclared-export-flag` → 3/3 PASS | ~2026-08-10 run | — | — | — |
| L-012 | 2026-08-04 | corpus `drift-tripwire-intersection-excuse.json` (must_match + intersection vocabulary) | 2/3 found-but-hedged, AMBER | `drift-tripwire-intersection-excuse` → 3/3 PASS | ~2026-08-10 run | — | — | — |
| L-013 | 2026-08-04 | agents/script-adversary.md (verdict is ONE bare line, no bold-wrap) | 2/3 found-but-hedged, AMBER | `script-unsafe-probe` → 3/3 PASS | ~2026-08-10 run | — | — | — |
| L-014 | 2026-08-04 | agents/mutation-runner.md (survivor vocabulary mandated) | 1/3 found-but-hedged, BLOCKING (AMBER×2) | `shadowed-import-vacuous-suite` → 3/3 PASS | ~2026-08-10 run | — | — | — |

Pre-registered cycle-1 read (plan §3, Phase 0 row): **≥80% of L-001…L-014 CONFIRMED**
validates the adjudication; **<50%** fires the kill row — the adjudication was narrative,
not repair, and re-adjudication precedes any new authoring.
