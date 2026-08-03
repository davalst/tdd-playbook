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
