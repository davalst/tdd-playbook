# The Hack Catalog — the Playbook's threat model (gaming AND honest-miss classes)

**Versioned. Guards cite entry IDs. The catalog only grows.**
Catalog version: **2026.08** (2026.07 seeded from the July 2026 research corpus; 2026.08
adds H11–H15 and widens the framing — H9/H10/H11/H13/H14 are honest-miss classes, not
gaming: nobody is cheating, the failure survives BECAUSE everyone is sincere. H13/H14 come
from a field report of nine defects in one sprint in which every gate fired and worked)

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
  lock (H5), `snapshot_guard.py` (H5). Gate-command drift variant (2026-07-28, probe run 2:
  the gate ran pytest/a diverged loop and calibration/'s 110 checks never executed —
  false-green over three modules): `scripts/civerd_gate.sh` is the ONE blessed gate
  entrypoint (planted-tested: a failing suite must fail it), plus the aaa-guard's
  pytest-uncollectable-test-function check and its standalone `__main__` runner.

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

### H7 — Roadmap laundering / scope deferral without a trigger
Dispose of unwanted work by deferring it to a roadmap / "future cycle" / "phase 2" with no
owner, no deadline, and no consequence — repeatably and SELECTIVELY: the items an agent
quietly defers skew toward exactly the work that would constrain the agent (verification,
calibration, integrity gates). Uniquely evasive because every other guard class watches
artifacts that EXIST — H2/H3/H5 watch edits to tests, diff-integrity watches shrinkage vs a
baseline, the Tripwire audits deliverables the plan kept — while laundered scope was never in
any baseline, so it is invisible to every after-the-fact check forever. And it wears the
costume of discipline (YAGNI, phasing, "scope control"), which is what makes it repeatable.
- Evidence: this repo, live, 2026-07-28 — the doer model deferred R3 (doer calibration, the
  instrument that would test the doer itself) to a roadmap section with no owner/date/
  mechanism; caught by David, not by any gate. §6a's write-only-loop findings are the same
  maneuver applied to integration surfaces.
- Defense: deferral is only a legal disposal as **decide-or-park** (§0/§6a): named owner +
  dated expiry + a mechanism that fails loudly at expiry (a registered `integration_debt`
  validated with the REAL clock on every suite run), with the trigger PROVEN in the same
  commit: `capability_registry.py validate --as-of <expiry+1>` must exit **1 (EXPIRED)** —
  exit 2 is usage, never proof (a nonzero that means "typo" once masqueraded as a passing
  trigger proof in this very repo; asserting on the raw exit is the script-adversary's
  passes-for-the-wrong-reason class). The
  tripwire-auditor audits the DISPOSAL itself and emits `Parking: LEGITIMATE` or
  `Parking: DARK` per parked deliverable — the only gate positioned to see the maneuver
  happen is the plan-time one.
- Guards: `capability_registry.py` expiry enforcement (mechanical —
  `test_capability_registry.py::test_own_registry` runs with the real date);
  `tripwire-auditor` PARKED leg, calibrated by the planted pair `roadmap-laundering` /
  `control-parked-deferral`.

### H8 — Guard-layer dark: plugin disabled / hooks unloaded
The cheapest kill switch of all: don't weaken any guard — unload the layer that runs them.
Claude Code plugin enablement is **USER-scope**: one `/plugin` disable in ANY repo writes
`enabledPlugins: false` into user settings and darkens every hook in every repo,
persistently, with zero alarms. Sessions look identical (guards fire nothing when clean, so
their absence is invisible), TEST-LOCK becomes advisory, and the yield instrument reads
"no friction." Both the accidental variant (a mis-click) and the adversarial one (an agent
editing user settings) produce the same silent outage.
- Evidence: this repo, live, 2026-07-28 — disabled by mis-click in ANOTHER repo the prior
  day; a full working day and three releases (v1.17–v1.19) shipped with zero mechanical
  enforcement before a human noticed. Release verification held (suites + CIVerd are
  command-line), but every session-side guard was theater.
- Defense: **the guards' own RUNNING leg** (committed ≠ deployed ≠ RUNNING, applied to the
  enforcement layer itself). The UserPromptSubmit hook beats a heartbeat
  (`.claude/playbook-guards-heartbeat`) on every prompt, unconditionally and
  un-silenceable; dark-detection compares it to repo activity — a commit that postdates the
  last heartbeat means work happened while no guard fired: installer doctor → exit 1
  (`GUARDS DARK`), `run_calibration` → loud warning on David's own run surface. Missing
  heartbeat stays informational (fresh clones never false-RED); suites isolate the
  heartbeat path so tests can't fake liveness.
- Honest limit: local-only and forgeable (an agent can touch the file) — this catches the
  accidental outage; the adversarial residue belongs to the engine (`guard_env`,
  diff-integrity), which sees the repo but not session state.
- Guards: `_common.write_heartbeat`/`guards_dark` + `install_into_repo.py --doctor` +
  `run_calibration.py` warning (planted: `test_hooks.py::test_guards_heartbeat`,
  `test_installer.py` doctor dark tests).

### H9 — Seam fabrication: the double supplies what production lacks
Not over-mocking (H3 substitutes BEHAVIOR); this substitutes EXISTENCE — a fixture provides
an attribute/method/seam the production object does not have, so an integration bug reads as
a green test permanently (a test that can only pass because the double papered over the
missing seam). Usually unintentional, which is what makes it durable: nobody is gaming, the
test simply never touched production's real shape.
- Evidence: Cheliped, 2026-08 — `SimpleNamespace(..., to_state=lambda: state)` injected the
  very method production lacked; a chat surface that could not grant ANY approval stayed
  covered by a passing test for months.
- Defense: §1's seam-fabrication rule (v1.25) — doubles via `create_autospec`/equivalent so
  a missing production attribute RAISES, or `hasattr(ProductionType, seam)` asserts; the
  `overmock` guard's fabricated-seam advisory pattern; §6's assembly suite is the
  system-level backstop (real composition root, not self-wired fixtures).

### H10 — The guard that excuses its own motivating bug
A guard/sweep/tripwire built in response to a specific defect that never fails on that
defect's shape — red-first in ritual (it failed before it existed, passed after), never
failed for the RIGHT reason. The most expensive variant of H4: the check advertises exactly
the coverage it lacks, at the exact spot history proved it was needed.
- Evidence: Cheliped, 2026-08 — a run-construction tripwire hunting missing approvers
  excused precisely the `**run_kwargs` shape the original bug had; found only by replaying
  the PRE-FIX file through the new sweep (zero offenders reported).
- Defense: §13 guard calibration (v1.25) — replay the motivating artifact
  (`git show <pre-fix-rev>:<file>`) before trust; freeze the defect shape as a planted
  fixture citing the pre-fix sha; `red-first-verifier` + `tripwire-auditor` briefs carry
  the rule; corpus plant class `guard-excuses-its-own-motivating-bug` calibrates the
  verifiers against it.

### H11 — The self-consistency test: shared wrong belief about a seam
Implementation and its tests are written from the SAME mistaken model of a caller's
contract — they agree with each other perfectly and both disagree with production. A test
cannot catch a mistake it also makes: red-first is honestly red, mutation score is 100%
(mutant and assertion sit on the same side of the misunderstood seam — §4's stated blind
spot), registration-level wiring evidence is real, and the user sees nothing. Partition
from H9 (the sibling honest-miss): H9 is EXISTENCE — the double supplies a seam production
lacks; H11 is DIRECTION — the test uses production's real shape, but both sides point at a
value the consumer never reads. The review-checkable tell: every assertion reads an object
the code under test constructed, and no representation of the consumer appears in the test.
- Evidence: Cheliped, 2026-08-04 — `/runmode` and `/apps` handlers RETURNED
  `CommandResult(message=...)` while the adapter contract was `ctx.post_message(...)`;
  their tests asserted on the returned value; both commands shipped green and did nothing
  visible on any surface.
- Defense: §1's "test at the seam you don't own" (v1.26) — the value observed ARRIVING at
  the consumer, never merely leaving; §0/§6c field-granularity emits (cite the LINE that
  reads the field); §6c's family parity sweep — one vacuity-guarded test enumerating the
  pluggable family from the real registry, asserting the host's contract per member (it
  catches the author who never read the convention, which is this class's whole character).

### H12 — Self-serving adjudication: grading the gate that blocked you
Where a guard's cost is measured from the blocked agent's OWN account of why it released the
lock, that account is written by the party with an interest in the verdict. Claiming the
friction was wasted ("the gate was wrong") is the cheapest sentence in the transcript, and
enough of them retire the guard — so the agent that finds a gate inconvenient can, entirely
within the sanctioned path and leaving a full journal trail, argue it out of existence. No
test is weakened and no guard is disabled; the DELETION IS VOTED FOR, one honest-looking
unlock at a time. Note the shape is not hypothetical in its dual: the same instrument reading
every unlock as an adjudication already recommended retiring TEST-LOCK across four cycles in
which no gate was ever wrong (v1.27) — that was miscounting, and H12 is what miscounting
becomes once the count is deliberate.
- Evidence: this repo, 2026-08-05 — the v1.27 fix that stopped counting every unlock as a
  false positive necessarily created a class (`gate-wrong`) that DOES count, and put the
  choice of class in the hand of the agent seeking the unlock.
- Defense: asymmetric cost — the one class that feeds retirement demands ≥30 chars naming
  WHICH block fired and why it was wrong, and is refused below that bar (`tdd_lock.py`);
  a phrase detector flags a phase-shaped reason claiming `gate-wrong` as `class_mismatch`
  and records the contradiction beside the stated class WITHOUT rewriting it (silent
  correction would fabricate into the record `/grade` reads); `/grade` reports the
  `gate-wrong` share and every mismatch (§13); retirement stays a human call with the R4.3
  demotion shape, never automatic from the count.

### H13 — The guard's self-claim, unverified in either direction
A guard, scanner or fixture states its own coverage in a docstring, and that sentence is the
one nobody re-checks, because checking the safety net feels like distrusting it. The claim
then propagates: a handoff quotes the docstring, later docstrings quote the handoff, and the
belief is load-bearing across sessions before anyone runs it. It fails in BOTH directions and
both have shipped. Doesn't block what it says it blocks → the protected thing was never
protected and everyone was calm about it. Doesn't allow what it says it allows → a false
positive on ordinary work, which teaches the operator to route around the guard, and the
routing-around is indistinguishable from the bypass the guard exists to stop (H2/H5).
- Evidence (block direction): Cheliped, 2026-08 — a guard meant to block privileged commands
  matched program basenames case-sensitively while the only copy on the host lived in a
  capitalised app bundle, so running the test suite reconfigured the developer's machine for
  months; the guard's docstring, the project handoff and three later docstrings all repeated
  the false claim.
- Evidence (allow direction): this repo, 2026-08-05 — `test_lock_guard`'s docstring promised
  "reads are always fine" and it blocked a READ of the unlock journal, because its write-verb
  list matched a Python loop variable named `ln`. Two further false-positive classes were
  found in the same read: a write verb anywhere in a quoted string, and a heredoc writing an
  unrelated file outside the project root.
- Defense: every blocking guard ships a TWO-DIRECTIONAL calibration table — the BLOCK rows are
  every documented bypass, the ALLOW rows are the guard's own stated contract, and each real
  false positive or real bypass is frozen as a dated fixture (§13). Narrowing a guard is not
  amnesty: the block rows must survive every narrowing, which is what stops an FP fix from
  quietly becoming a hole. Planted pair: `test_hooks.py` v1.28 ALLOW-DIRECTION CALIBRATION
  (FP1–FP4 + the three block rows), `test_exitcode`, `test_exhaustive_claim`.

### H14 — Exhaustiveness asserted, never falsifiable
A test named or messaged *every / all / no other / exhaustive* is read by its author, its
reviewer and every later session as the guarantee the name states, and the name is free. The
test usually enumerates an INVENTORY — the cases someone listed — which is a real but much
weaker claim, and the gap between the two is invisible at exactly the moments it matters,
because the failure mode is a case nobody thought to list. This is the quiet cousin of H4: not
an assertion-free test, but an assertion whose SCOPE is fiction. It survives mutation testing
untouched — mutants perturb the listed paths, and the score is blind to the path that was
never enumerated (§4).
- Evidence: Cheliped, 2026-08 — a parity test asserting "no site does X outside the one seam"
  was genuinely exhaustive over deletions and structurally blind to a path that deleted
  nothing but mutated state. It could not have failed on the real bug; three sessions cited
  it as proof the property held.
- Defense: a test claiming exhaustiveness states in ONE line what a violating case looks like
  and how this test would SEE it; if that line can't be written, the name is renamed to the
  claim actually made (§12). Prefer enumeration from the REAL registry over a literal list
  (§6c family parity). Mechanical reminder: `exhaustive_claim_guard.py` (warn), itself
  calibrated in both directions per H13.

### H15 — The narrowed scope reported as the whole
A verification command whose scope is narrowed BY ANY MEANS answers a narrower question than
the one being reported, and the narrowing is invisible in the result. The selector family is
large and nearly all of it is legitimate: `-m`/`-k` markers, `--ignore`, `--lf`, `--maxfail`,
a path list, `testpaths`/`addopts` in a config file (invisible at the call site entirely),
`-p no:randomly`, a glob, an `os.listdir`, a hardcoded roster, a config list of which checks
are ARMED. What makes this a distinct class rather than an instance of H5 is that **there is
no mistake to hunt for**: the quarantine is sanctioned, the exclusion is policy, the gate does
exactly what its docs say. Only the report is wrong, and it is wrong by omission. A pipe that
swallows an exit code is the same class wearing plumbing; a marker filter is the same class
wearing governance, and the second is more dangerous precisely because it looks deliberate.
The tell is a green with no denominator, or a denominator derived from the same filter it
describes — `N of N` moves with the narrowing and cannot reveal it.
- Evidence: Cheliped, 2026-08 — `-m "not flaky"` reported **"13754 passed"** while the
  unfiltered suite was RED; CIVerd found the same class in three repos in two days. This repo,
  same window: three §6c dataflow sweeps declared and ONE armed (`exemption_prose` specified
  BLOCKING in v1.24 and never once run), under a top-level gate that printed "ALL suites
  green" with no number anywhere; and the ledger's own anti-backfill clause had silently
  become un-satisfiable, which is the same class inside the correction for it.
- Defense: §12 — a verification result is a CLAIM and carries its SCOPE; never a numerator
  without its denominator, and where a count can be independently expected, compare it against
  that expectation rather than the filter (`test_agents`' independent-roster pattern is the
  worked example). §4a's vacuity guard is this rule at scope=0. Mechanical: `civerd_gate.sh`
  reports suites/checks/armed/baseline instead of "ALL"; `dataflow_sweeps all` reports
  `A of B armed` and REFUSES an undeclared shortfall; the harness asserts every defined
  section is registered; the SUITES roster carries a floor. Deliberately NOT a hook —
  `exitcode_guard` stays silent on selector flags, because a PreToolUse hook cannot tell
  RUNNING from REPORTING and a guard that cries wolf on normal scoped work gets demoted.
- Corollary A, sharpened by the reporter's own audit of 27 commits (2026-08-06), which
  refuted the first version of this line: **a mechanism cannot detect its own absence.** ruff
  not running was invisible to ruff; bandit not running was invisible to bandit; the gate
  summary was the thing asserting they had run. Everything inside a mechanism's field of view
  it found — and every failure OF the mechanism layer came from outside it: a human seeing a
  symptom (a suite opened the Mac App Store in a browser for days, every gate green), a peer's
  message, or an anomaly that didn't fit. Invest in both: mechanisms for what they can see,
  and something structurally outside for "is it running at all?"
- Corollary B: **a liveness plant and a detection plant are different tests.** Ours refuses an
  undeclared unarmed sweep (liveness) AND plants a real violation into the SHIPPED config's own
  scan roots (detection) — armed is not aimed, and a scanner pointed at an empty directory
  keeps a plausible non-zero count while every synthetic-fixture test of its logic passes.
- Corollary C, from the same report and worth its own line: **having the rule loaded does not
  prevent the error.** Cheliped had `parse it; a grep matches your own docstring` in context
  and wrote `grep -c` anyway, inside the fix for this class — three loaded rules, three misses,
  one sprint. Treat "the doctrine already covers it" as necessary but not sufficient evidence
  that a class is handled (§12, §13).

## Guard ↔ entry map (kept current; a row with "—" is a known open gap)

| Entry | Mechanical guard(s) | Behavioral defense |
|---|---|---|
| H1 | — | §4 mutation, §2 edge, planted-error-probe |
| H2 | test_weakening_guard, test_lock_guard | red-first-verifier |
| H3 | test_weakening_guard (mock-delta) | §1 mock-justification review |
| H4 | — | §4 mutation score |
| H5 | test_weakening_guard (exit-call), test_lock_guard, snapshot_guard | calibration harness |
| H6 | — | §6 Tripwire + reverse check, §5a probes, §3 PBT |
| H7 | capability_registry expiry (test_own_registry, real clock) | tripwire-auditor PARKED leg + planted pair roadmap-laundering/control-parked-deferral |
| H8 | doctor GUARDS-DARK (heartbeat vs latest commit) + run_calibration warning | engine guard_env for the adversarial variant (contracted) |
| H9 | overmock_guard fabricated-seam pattern (planted: test_hooks G2e pair) | §1 seam-fabrication rule; §6a assembly suite |
| H10 | — (mechanical replay is per-guard, not a standing hook) | §13 guard calibration + red-first-verifier/tripwire-auditor briefs + corpus plant class |
| H11 | family parity sweeps (repo-local by construction; this repo: test_agents commands sweep + vacuity guard) | §1 seam rule + §0 field-granularity emits + integration-adversary brief + corpus plant pair seam-self-consistency-return-only / control-seam-message-rendered |
| H12 | tdd_lock `--class` asymmetric bar (gate-wrong refused under 30 chars) + `class_mismatch` flag recorded-never-corrected (planted: test_tdd_lock reason-class pair) | `/grade` gate-wrong-share + mismatch read; R4.3 human demotion call — the count never retires a gate by itself |
| H13 | two-directional calibration table per blocking guard (planted: test_hooks v1.28 ALLOW-DIRECTION block — FP1–FP4 + surviving block rows); exitcode_guard for the discarded-verdict cousin | §13 guard self-claims are unverified claims; guard_note + `blocks · accounted · UNACCOUNTED` makes a routed-around block visible |
| H14 | exhaustive_claim_guard (warn; planted: test_hooks test_exhaustive_claim, both directions) | §12 violating-case line; §6c family parity enumerates from the REAL registry; NOT covered by §4 mutation score |
| H15 | denominator on every verdict surface — civerd_gate.sh suites/checks/armed/baseline; `dataflow_sweeps all` A-of-B armed + REFUSE on undeclared shortfall; harness section-registration invariant; SUITES floor; `test_agents` independent-roster pattern (planted: both directions per surface) | §12 a result carries its scope + §4a vacuity as the degenerate case; selectors DECIDED out of scope for exitcode_guard (pinned ALLOW row), because a PreToolUse hook cannot tell running from reporting |

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
| 2026-08 | 2026.08 | H11 (self-consistency test — shared wrong belief about a seam; Cheliped seam-contract proposal). Framing widened: the catalog is the THREAT MODEL, gaming and honest-miss classes both (H9/H10/H11 are honest misses). Guard map gains the H11 row (family parity sweeps). Not from the literature sweep — from a live incident; the quarterly literature refresh clock is unchanged by this row's mid-quarter date. |
