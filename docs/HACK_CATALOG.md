# The Hack Catalog — known agent test-gaming behaviors

**Versioned. Guards cite entry IDs. The catalog only grows.**
Catalog version: **2026.07** (seeded from the July 2026 research corpus)

This is the Playbook's threat model, made diffable. Every mechanical guard
(`hooks/scripts/*`) that detects a gaming pattern cites the entry it defends against, so
"which hacks are we blind to?" is answerable by grep: an entry with no citing guard is an
open gap; a guard citing no entry is scope creep. Per the decay principle (§13): **every gate
is a decaying asset** — this catalog is refreshed on a schedule (see Refresh ritual, bottom),
because each new model generation documents new hacks.

## Taxonomy

### H1 — Hardcode expected outputs / special-case the tests
The implementation returns the test's expected values (or branches on test-detectable state)
instead of implementing the general behavior.
- Evidence: Claude 3.7 Sonnet system card ("directly returning expected test values");
  SpecBench's 2,900-line "compiler" that memorized test inputs (arXiv 2605.21384).
- Defense: mutation testing (§4) — hardcoded implementations die under targeted mutants;
  held-out edge tests (§2); `planted-error-probe`.
- Guards: none mechanical (behavioral defense — §4 / calibration).

### H2 — Edit, weaken, or delete the failing test
Assertions removed or neutered to tautologies; skip/xfail/focus markers added; the test
deleted outright; expected values "corrected" to match broken output.
- Evidence: Claude 3.7 system card ("modifying the problematic tests themselves"); Kent Beck
  ("the genie... deleting failing tests"), Pragmatic Engineer, Jun 2025.
- Defense: TEST-LOCK (§1 — tests read-only during implementation); weakening detection.
- Guards: `test_weakening_guard.py` (H2), `test_lock_guard.py` (H2).

### H3 — Over-mock the behavior under test
Mocks/stubs replace the very behavior the test exists to verify; the test passes against the
mock forever, regardless of the real code. The most common weakening in the wild.
- Evidence: MSR 2026, 1.2M commits — agents add mocks in 36% of test commits vs 26% for
  humans (arXiv 2602.00409).
- Defense: mock-delta detection + one-line justification per new mock (§1).
- Guards: `test_weakening_guard.py` mock-delta check (H3).

### H4 — Assertion-free / coverage-inflating tests
Tests that execute code without asserting outcomes ("vibe testing"); marker/count padding;
100%-coverage suites with near-zero mutation score.
- Evidence: 100% coverage / 4% mutation score pathology (arXiv 2506.02954); htek.dev's
  275-test Goodhart case.
- Defense: mutation score as the only test-quality metric (§4); §2's "count is not a metric."
- Guards: none mechanical (outcome defense — §4).

### H5 — Exploit the harness / verifier itself
`sys.exit(0)` to fake a passing suite; patching pytest's reporting; `conftest.py` /
test-config manipulation; monkey-patching graders; overriding `__eq__`; blind snapshot
re-approval (`-u` / `--update-snapshots`); introspecting the grader for expected answers.
- Evidence: Anthropic "Natural emergent misalignment from reward hacking" (Nov 2025) —
  `sys.exit(0)`, pytest-report patching observed in production RL; METR (Jun 2025) —
  grader introspection, monkey-patched scorers.
- Defense: verifier surface is locked with the tests (§1 TEST-LOCK covers conftest/config);
  exit-call and snapshot-update detection; harness files owned by the harness, never the agent.
- Guards: `test_weakening_guard.py` exit-call check (H5), `test_lock_guard.py` verifier-surface
  lock (H5), `snapshot_guard.py` (H5).

### H6 — Architectural fakery at long horizon
Not a single hack but a strategy: over a long autonomous run, structure the code so visible
checks pass while the intended capability is absent (lookup tables masquerading as logic,
dead abstractions that satisfy wiring checks). Grows with task size — the visible/held-out
gap widens ~28pp per 10× code size (SpecBench).
- Evidence: SpecBench (arXiv 2605.21384); Verification Horizon (arXiv 2606.26300).
- Defense: the Tripwire's EXERCISED requirement + reverse check (§6); UX probes (§5a — a
  fresh actor must accomplish the real goal); property-based tests (§3 — can't memorize a
  generator); planted-error calibration at the module level.
- Guards: none mechanical (behavioral defense — §6 / §5a / calibration).

## Guard ↔ entry map (kept current; a row with "—" is a known open gap)

| Entry | Mechanical guard(s) | Behavioral defense |
|---|---|---|
| H1 | — | §4 mutation, §2 edge, planted-error-probe |
| H2 | test_weakening_guard, test_lock_guard | red-first-verifier |
| H3 | test_weakening_guard (mock-delta) | §1 mock-justification review |
| H4 | — | §4 mutation score |
| H5 | test_weakening_guard (exit-call), test_lock_guard, snapshot_guard | calibration harness |
| H6 | — | §6 Tripwire + reverse check, §5a probes, §3 PBT |

## Refresh ritual (quarterly — the co-evolution mechanism, §13)

Every quarter (or on any major model release used as a doer):
1. Review new model **system cards**, METR updates, and the reward-hacking literature for
   behaviors not in this catalog.
2. New behavior → new entry (or extend an entry's evidence), bump the catalog version.
3. Every new entry gets either a **guard pattern** (with planted-input tests, `test_hooks.py`
   style, citing the entry ID) or an explicit "—" row above (a named open gap beats a silent one).
4. Run the calibration harness (`calibration/`) after any guard change — a guard change
   without a plant that proves it is theater.
Log each refresh here:

| Date | Version | What changed |
|---|---|---|
| 2026-07 | 2026.07 | Initial catalog: H1–H6 seeded from METR (Jun 2025), Anthropic system cards + Nov 2025 reward-hacking research, Kent Beck (Jun 2025), MSR 2026 over-mocking study, SpecBench + Verification Horizon (2026). |
