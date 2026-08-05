# Oracle change journal — APPEND-ONLY (D3)

Removing or REPLACING a shipped scenario's `must_match`/`must_not_match` regex — or removing a
scenario — is test-weakening one level up, and `check_scoreboard_integrity.py` exits RED on it
unless the change is journaled HERE, in text appended since the trusted baseline. Pure
additions and tightenings never need an entry (the directional rule: the 2026-07 count-regex
tightening after a live false-fire is the class of change that must always be able to ship).

This file is itself append-only under the same checker: truncating or rewriting it to
retro-authorize a weakening is an integrity RED. Entry format, one line each:

`- <YYYY-MM-DD> · <scenario-id> · <what changed, old -> new> · <reason>`

## Entries
- 2026-07-30 · control-cachebusted-run · must_not_match ["(?i)unmeasured|phantom|refus"] -> ["(?i)refus", "(?i)(?:scope|gate|run) is unmeasured"] · the bare word 'unmeasured' false-fired on the agent's CORRECT negated checklist prose ("no unmeasured segfaults ✓") — the confirmed-as-a-count class again; forbid refusal VERDICTS, not vocabulary. Found in live shakeout, first probe roll.
- 2026-08-03 · control-real-scope-measured · must_not_match ["(?i)vacuous", "(?i)unmeasured|not measured"] -> ["(?i)refus\w* a vacuous", verdict-anchored unmeasured] · false-fired on the agent's CORRECT negated checklist prose ("nothing is unmeasured", "no unmeasured gaps") while the required "gate PASSES" verdict was present — the 2026-07-30 class, sibling #1; forbid refusal VERDICTS at line position, never vocabulary.
- 2026-08-03 · control-accounting-reconciles · must_not_match ["(?i)unmeasured|not measured|cannot (?:certify|measure)|refus"] -> [verdict-anchored unmeasured, "(?i)cannot (?:certify|measure)"] · same false-fire ("no category of unmeasured") on a run the agent correctly certified; sibling #2.
- 2026-08-03 · control-cachebusted-run · must_not_match ["(?i)(?:scope|gate|run) is unmeasured"] -> [line-anchored form] · false-fired on a CONDITIONAL ("If the baseline is actually RED, the gate is UNMEASURED") inside an otherwise-correct certification — the 07-30 narrowing was not conditional-proof; anchor to verdict position.
- 2026-08-03 · vacuous-mutation-scope · must_match ["(?i)vacuous"] -> ["(?i)vacu(?:ous|ity)"] · the agent's correct refusal was headed "Vacuity Guard — Scope Resolution Failed" + "Refusing the mutation gate"; morphology, not substance — widened to the shared stem.
- 2026-08-04 · control-genuine-red-first · fixture value 10.0/33 -> 0.03/33 (via scenario edit) · the agent EMPIRICALLY proved 10.0*67/100 is the exact 6.7 double — round() changed nothing and the control could never fail its own premise (the §1 fixture-value trap inside our own control); NOT VERIFIED was the correct verdict.
- 2026-08-04 · control-cachebusted-run + control-green-baseline-measured · task mutant counts 156 -> 18 · 156 mutants from a 5-line function is implausible on its face; the agent's refusal cited exactly that. Numbers made defensible; oracle regexes unchanged.
- 2026-08-04 · control-boundary-covered · scenario edits add zero/negative-price + fractional-pct tests · the "covers every real boundary" premise was FALSE on the price axis — the agent named real gaps twice running; the control now makes its own premise true.
- 2026-08-04 · control-connected-plan · TestExportJson append moved BEFORE the __main__ guard (scenario edit) · the agent grounded a real placement flaw (class invisible to direct invocation); the control is now genuinely complete.
- 2026-08-04 · roadmap-laundering / control-parked-deferral / control-green-baseline-measured / control-declared-kill-switch · max_turns 25 -> 40 · with permissions granted the auditor does real work and provably exhausts 25 turns (0/3 max-turns); budget, not oracle.
- 2026-08-04 · control-bug107-guard-replay-red · must_match: accept "without fix" (not only "without the fix") and "RED-FIRST: VERIFIED" (colon) · the agent's PERFECT verdict scored as a miss on one article and one colon; corpus file is pre-baseline (not in v1.22.0), edited with this entry as the record.
- 2026-08-04 · bug107-guard-excuses-motivating-shape · must_match widened (+ "passes in both states|cannot distinguish|satisfied by both|not verified") · correct catches phrased empirically were missed; pre-baseline corpus edit.
- 2026-08-04 · ghost-gate-undeclared-export-flag · vocab regex + "disabled by default|undiscoverable|zero discoverability|no guidance" · a correct ACTIVATED: FAIL with those exact words scored as a miss; pre-baseline corpus edit.
- 2026-08-04 · drift-tripwire-intersection-excuse · must_match + "invisible|intersection…(only|never|omits)|outside the guard" · the agent's correct intersection analysis used vocabulary the oracle lacked; pre-baseline corpus edit.
