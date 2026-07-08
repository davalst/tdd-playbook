---
description: Run the Playbook §4 mutation pass on critical modules — the real anti-performative metric — and kill survivors.
argument-hint: <critical module(s) to mutation-test>
---

Run a **mutation-testing pass** (Playbook §4) on the CRITICAL modules: $ARGUMENTS

This is the ungameable check that tests actually catch bugs (100% coverage can assert
nothing). Steps:
1. Pick the right tool for this repo's stack (`mutmut`/`cosmic-ray` for Python,
   `Stryker` for JS/TS, etc.). Scope to the named critical modules only — never the whole
   repo (mutant explosion). Critical = auth, money, permissions, lifecycle, core algorithms.
2. Run it; collect surviving mutants from the machine-readable stats.
3. **Triage survivors:** for each, decide real-vs-equivalent. Equivalent mutants (e.g. SQL
   keyword case that SQLite treats identically, string-subscript case) are UN-KILLABLE —
   exclude them with a conservative case-only-in-SQL/subscript filter; do NOT chase them
   (that's gaming). For REAL survivors, write the test that kills each.
4. Report **raw %**, **effective % (killed / non-equivalent)**, and the count excluded —
   transparently. Aim ~80%+ effective on critical modules. If this repo has a mutation
   floor/gate, ensure it still passes and never lower it.

Report-only mutation nobody acts on is theater — the deliverable is killed survivors + the
score, not just a number.

**Close the loop (not optional):** the score proves tests kill GENERATED mutants; it does
not prove the suite catches a REAL planted defect end-to-end. After the pass, DISPATCH the
`planted-error-probe` agent on one critical module in scope — one meaningful planted bug,
suite must go red, mechanically verified revert. Survivor triage is half the loop; the
plant is the other half.

End the report with: `Loop closed: yes (planted-error-probe — <verdict>)` or
`Loop closed: NO — <why>` (a skipped plant is a visible decision, never a default).
