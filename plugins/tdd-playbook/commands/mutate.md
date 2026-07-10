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
   **Roster admission:** every rostered module needs its one-line "a survivor here costs ___"
   justification; rendering/presentation modules are out — flag unjustified entries for
   pruning instead of paying ceremony on them. **Scoped runs need the vacuity guard:** a
   scope matching zero generated mutants fails loudly ("refusing a vacuous pass"), never green.
   **Reviewing a diff rather than finishing a feature? Run DIFF-SCOPED** (Stryker
   `--incremental`/`--since origin/main`, pitest history, mutmut on the changed files) and
   surface survivors on the changed lines only. **For a concern-critical change** (auth,
   money, permissions), also run **targeted-mutant mode**: write 3–5 plausible
   concern-specific mutants (drop the permission check, flip the rounding, skip the state
   guard) and require a test that kills each — mutation as test generator, not just grader.
2. Run it; collect surviving mutants from the machine-readable stats.
3. **Triage survivors:** for each, decide real-vs-equivalent. Equivalent mutants (e.g. SQL
   keyword case that SQLite treats identically, string-subscript case) are UN-KILLABLE —
   exclude them with a conservative case-only-in-SQL/subscript filter; do NOT chase them
   (that's gaming). Equivalents the filter can't classify → the audited equivalence ledger
   (written proof + exact-substitution match + can't-overmatch test per entry; keep it short).
   **Class string survivors by role:** DATA strings (SQL/keys/hash inputs/persisted content)
   are real — kill them; operator-facing display prose is informational — never resolve it by
   pinning the prose verbatim in a test. For REAL survivors, write the test that kills each.
4. Report **raw %**, **effective % (killed / non-equivalent)**, and the count excluded —
   transparently. Aim ~80%+ effective on critical modules. If this repo has a mutation
   floor/gate, ensure it still passes and never lower it.

Report-only mutation nobody acts on is theater — the deliverable is killed survivors + the
score, not just a number.

**Context hygiene:** dispatch `mutation-runner` as a FRESH agent and keep the mutant list
out of the implementing context — a visible verifier is a gameable verifier; the implementer
sees verdicts, never the mutants it could special-case.

**Close the loop (not optional):** the score proves tests kill GENERATED mutants; it does
not prove the suite catches a REAL planted defect end-to-end. After the pass, DISPATCH the
`planted-error-probe` agent on one critical module in scope — one meaningful planted bug,
suite must go red, mechanically verified revert. Survivor triage is half the loop; the
plant is the other half.

End the report with: `Loop closed: yes (planted-error-probe — <verdict>)` or
`Loop closed: NO — <why>` (a skipped plant is a visible decision, never a default).
