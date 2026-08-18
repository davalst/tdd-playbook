---
description: Run the Playbook §4 mutation pass on critical modules — the real anti-performative metric — and kill survivors.
argument-hint: <critical module(s) to mutation-test>
---

Run a **mutation-testing pass** (Playbook §4) on the CRITICAL modules: $ARGUMENTS

This is the ungameable check that tests actually catch bugs (100% coverage can assert
nothing) — within a seam: the score is blind where test and code share the same wrong belief
about a caller's contract (§4 "What mutation score does not cover"; §1's seam rule is the
check across one). Steps:
1. Pick the right tool for this repo's stack (`mutmut`/`cosmic-ray` for Python,
   `Stryker` for JS/TS, etc.). Scope to the named critical modules only — never the whole
   repo (mutant explosion). Critical = auth, money, permissions, lifecycle, core algorithms.
   **Roster admission:** every rostered module needs its one-line "a survivor here costs ___"
   justification; rendering/presentation modules are out — flag unjustified entries for
   pruning instead of paying ceremony on them. **Scoped runs need the vacuity guard — two axes:**
   a scope matching zero generated mutants OR a RED baseline / zero mutants run / a discarded tool
   exit code all fail loudly ("cannot measure — refusing a vacuous pass"), never green (0 survivors
   ≠ pass, generated > 0 ≠ measured — a discarded exit code is a discarded truth).
   **Reviewing a diff rather than finishing a feature? Run DIFF-SCOPED** (Stryker
   `--incremental`/`--since origin/main`, pitest history, mutmut on the changed files) and
   surface survivors on the changed lines only. **For a concern-critical change** (auth,
   money, permissions), also run **targeted-mutant mode**: write 3–5 plausible
   concern-specific mutants (drop the permission check, flip the rounding, skip the state
   guard) and require a test that kills each — mutation as test generator, not just grader.
   **Precondition for a REVERT-BASED script** (one that `git checkout`s to restore source):
   commit/stash first, or gate it on `with_snapshot.py preflight` — a bare checkout silently
   clobbers uncommitted work.
2. **PREFLIGHT BEFORE THE EXPENSIVE PASS — seconds, not the 40 minutes you'd then discard.** In
   order, refusing on any failure: (a) roster integrity — no DUPLICATE `paths_to_mutate` entries
   (a duplicate makes mutmut 3.6 abort after stats collection and names the cause nowhere), every
   entry resolves, every entry is in a gate invocation; (b) the kill tests are COLLECTED by the
   configured killing suite, exact count asserted; (c) that suite is GREEN **against the tool's
   rewritten tree**, which is a different fact from green at HEAD (a test that reads its own source
   is the usual cause — register those individual TESTS in a mutation-only exclusion, never skip
   their module); (d) the tracer maps at least one mutated function to at least one test — if it
   maps none, suspect the ATTRIBUTION blind spot (§4): behavior exercised only in a CHILD process is
   unmeasurable by any tool, and the fix is an in-process twin beside the fresh-process test (§8),
   or hand-applied targeted mutants as the executed evidence with the broad pass labelled UNMEASURED.
   Then run it; CAPTURE the tool's exit/stats output and confirm the run actually EXECUTED (run-stats
   total > 0, baseline green) BEFORE reading survivors — an aborted run returns an empty survivor
   set that masquerades as a clean gate. Then collect surviving mutants from the machine-readable stats.
   **Account for every mutant:** if killed + survived < generated, the gap (segfault/timeout/
   no-covering-test/skipped) is UNMEASURED — refuse to certify, don't warn. **Discovery is
   per-module:** run ONE module, READ the actual survivor lines, write kills, re-run that module,
   then move on — a full pass VERIFIES, it doesn't discover (and the survivor list finds real bugs
   that guessing never will).
3. **Triage survivors:** for each, decide real-vs-equivalent. Equivalent mutants (e.g. SQL
   keyword/identifier case that SQLite treats identically, string-subscript case) are UN-KILLABLE —
   exclude them with a conservative case-only-in-SQL/subscript filter, but ONLY for keywords/
   identifiers: SQLite is case-SENSITIVE for VALUES, so `type='table'` → `'TABLE'` is a REAL mutant,
   never excluded. A too-permissive filter is a GATE DEFECT — every exclusion rule ships a negative
   test proving the nearest real mutant still blocks. Do NOT chase equivalents (that's gaming).
   Equivalents the filter can't classify → the audited equivalence ledger
   (written proof + exact-substitution match + can't-overmatch test per entry; keep it short).
   **Class string survivors by role:** DATA strings (SQL/keys/hash inputs/persisted content)
   are real — kill them; operator-facing display prose is informational — never resolve it by
   pinning the prose verbatim in a test. Informational = changes INSIDE the string literal
   only: logic mutants on a display line and mutants inside f-string `{expressions}` are CODE,
   stay real/blocking. For REAL survivors, write the test that kills each.
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
