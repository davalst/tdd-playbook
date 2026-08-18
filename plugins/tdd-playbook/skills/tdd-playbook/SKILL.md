---
name: tdd-playbook
description: David's universal TDD/QA workflow — use whenever building or changing a feature, fixing a bug, writing or reviewing tests, or planning test coverage, in ANY repo. ALSO fires for ANALYSIS work — audits, code review, diagnosis/root-cause, "investigate/verify/grade X", and self-improvement loops. Covers the reviewable TDD plan, edge-case rigor, property-based + mutation testing, interface-agnostic UX journeys (web/Telegram/TUI/MCP), intent-only UX probes + agent evals (prompt/tool/model; oracle-split: deterministic gates, LLM-judge trends never gate), the Tripwire wiring check (BUILT + WIRED + ACTIVATED + EXERCISED + RUNNING), the integration surface + capability registry + wiring liveness (assembly suite, darkness doctor), dataflow liveness (flow tables, consumer parity), determinism/flaky policy, security tests, test shape, CI hygiene, the claims discipline (cite-or-refuse, exhaustive negatives, N/N), and the learning loop (process grading + planted-error calibration). Collective handle: "the TDD Playbook".
---

# The TDD Playbook

The standing way I build and test in every repo. Goal: ship features that are correct, fully wired,
and provably tested — with defenses against the documented AI failure mode of happy-path / weak /
"corrected-to-pass" tests. The anti-gaming defense is an OUTCOME (mutation score), not a ritual.

Scale ceremony to the work — in NUMBERS, not vibes (the hooks nudge toward the same table; ceremony
on sub-threshold turns is a tax, not diligence). Here path-criticality beats line count, both ways:
- **Trivial / cosmetic / docs-only** → just do it well (a one-line test note).
- **< ~20 changed lines on non-roster, non-security paths + green targeted tests** → no independent
  verifier pass, no full Tripwire (§6's one-line wiring check still applies).
- **Feature / multi-deliverable / risky / ambiguous / bug-with-blast-radius / ANY diff on mutation-
  roster or security paths** → the full flow below. A 3-line auth change gets full ceremony;
  salami-slicing a big change into small diffs doesn't dodge it.

**And the posture that governs the table: the Playbook is SILENT until it has something real to
say.** The hooks already work that way — they speak only when something is wrong. Artifacts are
things you REACH FOR when they have something to say, never tolls paid to proceed: a review
record when a review actually FINDS something; an adversary when you want the second pair of
eyes; a plan when the work is genuinely multi-deliverable. A record nobody needed is not
evidence of rigour, and an artifact produced on a schedule is bureaucracy wearing a lab coat.
(Origin, 2026-08-18: the upstream repo required a review record on EVERY non-metadata commit.
205 findings, 57% keyed, 12 UNBUILT-GUARD keys — and zero guards ever built from any of them.
The obligation fired on every commit; its output was read by nobody. Deleted.)

## Repo-specific testing extensions — ALWAYS layer these on top (do this FIRST in each repo)
This Playbook is the universal FLOOR, not the ceiling. It ships from one canonical plugin so it is
identical in every repo and on every surface (local, web, mobile). But each repo has its OWN stack and
its OWN extra testing on top — a different language/test runner, stack-specific harnesses, project gates.
Those are NOT optional add-ons; they are part of "tested" in that repo. So before building or testing in
any repo, DISCOVER and APPLY that repo's local testing conventions, checking ALL of:
- the project **`CLAUDE.md` / `AGENTS.md`** — any "Testing", "QA", "Security Rules", or "CI" section
  (e.g. one repo's raw-ASGI request-path rule, another's mock-ban gate or `scripts/ci_local.sh`,
  a data-layer repo's own stack-specific harness);
- any project skill under **`.claude/skills/`** whose name or description is about testing for THIS repo
  (convention: a repo addendum named `testing-local` / `tdd-*` auto-fires alongside this Playbook);
- repo testing docs — **`docs/TESTING*.md`, `CONTRIBUTING.md`**, a `tests/README*`, or the test config
  (`pytest.ini`/`pyproject.toml` markers, `vitest`/`jest` setup) — to learn the repo's runner, markers,
  fixtures, and existing gates.
Composition rules: repo-local conventions **ADD to, and never weaken,** this Playbook. Use the repo's own
test runner, markers, and harnesses (don't impose pytest on a non-pytest repo — translate the CONCEPTS:
edge/ux/tripwire/property/mutation map onto whatever stack the repo uses). When a repo rule and this
Playbook conflict, **the stricter rule wins.** State up front, per task, which repo-local conventions you
found and are applying (or "none found" if a repo has no addendum yet) — that discovery is itself part of
the plan in §0. New repos that grow stack-specific testing should capture it in one of the places above so
this Playbook keeps composing with it automatically.

## 0. Deliver a reviewable TDD plan first (unless told "autocomplete")
Only for feature/multi-deliverable/risky work. Terse, SCANNABLE, plain chat (not a file). Per deliverable:
- one-line plain-English description + happy-path behavior;
- **Edge cases:** bullet list of real-world scenarios (no jargon, e.g. "sign the same meeting twice → no duplicate");
- **UX tests:** bullet list (what the user does → what they should see);
- **Integration surface** — islands are cheapest to catch HERE (origin: a full-platform feature-wiring
  audit of a production multi-surface agent system, 2026-07 — whole subsystems built well, tested
  well, and never connected). Four mandatory answers:
  - *Consumes:* which EXISTING subsystems this plugs into (event bus, memory, config UI, telemetry,
    hooks). "None" must be stated, never implied.
  - *Emits → named consumer:* everything this produces names WHO reads it — at FIELD granularity:
    cite the file:line in the CONSUMER that reads the specific field, not the subsystem that
    receives the object. "The adapter consumes my result" is true and useless when the adapter
    ignores the field (the H11 tell); if you cannot cite a line, the field is write-only, and
    write-only is not "integrated." This converts a question answerable from memory into one
    answered from the code. Granularity partition, stated once: capability/topic-level write-only
    is the registry's R-WRITE-ONLY (§6a); field/value-INSTANCE-level dangling is this rule and
    §6c's sweeps. A write-only loop is not
    a design; "nobody yet" becomes an integration-debt entry with an OWNER and an EXPIRY (§7's
    quarantine rules — a loan, not a landfill). For feature/multi-deliverable/migration work this
    answer is a TABLE, not a sentence — `flow · producer · consumer · liveness test` — so an empty
    consumer cell is visible, and it means dated debt or the flow doesn't ship (small diffs keep
    the prose answer; the ceremony preamble governs). A MIGRATION deliverable must enumerate the
    replaced seam's outputs here — §6c's consumer-parity DoD starts in the plan, not the diff.
  - *Surface parity:* which interfaces (web/Telegram/TUI/MCP/CLI) get this behavior. Divergence is
    STATED at plan time, not discovered by a user later.
  - *Reverse sweep:* which EXISTING features should now use this new capability. Each hit becomes a
    deliverable in this plan or a dated debt entry — silent deferral is how old features go blind
    to new capabilities.
- **Deploy surface** — required whenever a deliverable RUNS where this session does not control it
  (a VPS, a server, a daemon, an installed plugin, a vendored `.claude/` in another repo). The
  integration surface asks what it connects to; this asks whether the copy that's RUNNING is the one
  you built — because in a laptop-only repo commit-and-push IS the deploy, and that reflex quietly
  breaks the moment a remote runtime exists. Four mandatory answers (they populate the §6a
  `deploy_surface` registry field and the §6 RUNNING leg):
  - *Runs where:* the actual host/process, NAMED.
  - *Gets there how:* the specific deploy mechanism. If the answer is "I'll paste files," that is a
    FINDING, not a plan — hand-patching produces a running state no checkout matches.
  - *Verified how:* how a session proves the RUNNING version equals the intended one (a version echo
    asserted against HEAD, §6a). "It's pushed" is not "it's running."
  - *Divergence:* what happens when the running and intended versions differ, and WHO notices.
  And **the deploy path is deliverable #1** — build the thing that PROVES and updates the running
  state (an `update.sh` + a version-echoing `verify_install.sh`) BEFORE the feature, same logic as
  red-first (origin: a remote engine ran code 97 min / six commits behind because the deploy path was
  built AFTER the damage and patched on by hand as base64 blobs; every "fixed" was about the laptop).
  Any operator-facing verify/deploy/health SCRIPT in the plan gets the `script-adversary` (fresh
  context, refute-framed: does the probe actually test its target, or report PASS having touched
  nothing — blocking on stdin, writing to what it checks, reading any non-zero as "control held"?).
  Close the plan by dispatching the `integration-adversary` (fresh context, refute-framed: "name
  what this plan should touch but doesn't"); a confirming reviewer rubber-stamps islands. **This
  dispatch is MANDATORY, not optional, for any deliverable that adds a config gate or a
  user-facing capability** — that is exactly the case where the author's own imagination is the
  blind spot (they know the flag works when set, so they never ask whether a real user can FIND
  and flip it). The one check built to counter your bounded imagination is the one it's tempting
  to skip; skipping it is how a toggle ships dark (origin: six downstream toggles built + wired +
  tested + registered yet unreachable, because the adversary was optional and skipped, 2026-07).
  The adversary must answer, per new gate/capability: does it appear in the user-facing control
  surface AND the health/status surface, or is it dark-by-default / un-toggleable / health-invisible?
  Dispatch the `architecture-adversary` alongside it — the DESIGN-quality counterpart, refute-framed
  "does this plan fix the ROOT at the right seam, or patch a symptom / add an Nth copy of something
  that already exists?" Islands and band-aids are DIFFERENT failures: a plan can be fully connected
  and still be spaghetti (origin: a false-positive "fixed" by adding a tool name to ONE of THREE
  disagreeing read-only lists instead of unifying them — every other gate passed it, because none
  evaluates design quality). Advisory, not a hard block; fold each finding in as a deliverable or an
  owned debt entry, or reject it with a reason.
And ONCE per plan, BEFORE the deliverables — **spec integrity**. Everything downstream (§§1–6)
rigorously verifies what the PLAN says; a wrong reading of the request here passes every gate. So:
- **Assumptions stated explicitly.** If the request supports multiple readings, present them and say
  which one the plan follows — never pick silently.
- **If a materially simpler approach would satisfy the request, say so** and let the review choose —
  don't build the bigger one by default.
- **Deferral needs a TRIGGER, not a roadmap (H7).** Moving work to "later / the roadmap / a
  future cycle" is only a legal disposal as decide-or-park: named owner + dated expiry + a
  mechanism that fails loudly at expiry (a registered integration_debt validated on the real
  clock), with the trigger PROVEN in the same commit — `validate --as-of <expiry+1>` exits
  **1 (EXPIRED)**; exit 2 is usage, never proof.
  Prose deferral is the H7 maneuver — it evades every artifact-watching guard because
  never-built scope was never in any baseline, and the items quietly deferred skew toward
  exactly the checks that would constrain the agent. The tripwire-auditor audits each
  disposal: `Parking: LEGITIMATE` or `Parking: DARK` — dark parking blocks.
- **If something is genuinely unclear, name the confusion as a question for David** — don't plan
  around it. Plan review is the cheap place to be wrong; §4 is the expensive place.
This reviewed plan is the SINGLE upstream spec for the unit/edge/property tests, UX journeys, and the
Tripwire. Default to a one-liner for small work; don't make David review ceremony he didn't ask for.

## 1. The TDD loop
- Author tests from the spec, run RED, then implement to green. **Never weaken/delete a test to pass.**
- Test BEHAVIOR and OUTCOMES, not implementation details or "did the route fire."
- **A new refusal needs a VICTIM SWEEP before the first test run.** A change that starts denying
  something breaks every caller and FIXTURE that relied on the old permissiveness; discovering
  them one test run at a time pushes the remainder into progressively slower gates (origin: 8
  fixture victims across 8 cycles ≈ 35 min — the last two caught by the pre-push hook and the
  mutation baseline; the sweep finding all 8 ran in under a second). Sweep for what CALLS the
  guarded thing, never for the attribute the guard reads: a fail-closed guard fires on ABSENCE,
  so grepping the wrong-value case misses every caller that supplies nothing — usually most of
  them (the 9th victim set no attribute at all). A RESEAM (moving a decision to a new source of
  truth) sweeps a second shape — fixtures that PRODUCE the old state (17 signature victims found
  in a second; 22 state victims found three slow runs later) — and doubles as a fixture-realism
  audit: every state victim was supplying a state production cannot produce. This is §12's
  exhaustive-negatives rule in the other direction (a CLAIM of absence needs a sweep; a CHANGE
  that creates absence needs the same sweep), and the tightening-side kin of §6c's consumer-parity
  DoD, which covers what a REPLACED seam fed.
- **Assert the outcome, not the proxy — this reaches every CHECK, not just tests.** A health check that
  inspects a systemd unit instead of exercising the service, a config READ instead of the remote QUERIED,
  source text GREPPED instead of parsed — each is the "route fired" trap wearing operational clothes.
  Exercise the effect. (Origin: `RuntimeMaxSec` is silently ignored for `Type=oneshot` — systemd said so
  in the journal and it was scrolled past for hours because the check read the directive, never the run.)
  Assert the resulting STATE, not the action that should have produced it: the store CONTAINS the
  grant, not "the recorder was called"; the port is FREE, not "kill returned 0". Proxies are locally
  plausible at the moment of writing — knowing this rule did not stop four of them in one documented
  session — so use the mechanical trigger below (the "what would still be true if this were broken?"
  question), not vigilance.
- **An `except` that hides a PROGRAMMING error is a proxy for "this worked".** Best-effort blocks log
  at a level someone reads, and never wrap the line that establishes the guarantee (origin: a broad
  `except Exception: pass` around a capability check swallowed a `TypeError` from a missing
  constructor argument — a security classification silently never applied; the same
  silence-over-error class as §6c's silent-default boundaries).
- **Built ≠ wired-in ≠ usable.** Verify the user-visible outcome AND reachability (nav/button/CLI/tool)
  AND second-order effects (what list it leaves/joins; consistency across surfaces). Report "route
  exists + unit-tested" separately from "reachable + behaviorally verified." Don't round up.
- **Regression is an IRON RULE — non-negotiable, no approval prompt, highest priority.** On every bug,
  write the failing test that reproduces it FIRST, then fix; pin it so it can't silently come back (e.g.
  the Postgres GROUP BY bug → a test that fails on the old query). A regression = any bug in behavior a
  prior test covered, or in a path once known-good. Never skip it or defer it to "later."
- **TEST-LOCK — make the iron rule mechanical (default for feature/multi-deliverable work):**
  once the plan's tests are authored, RED for the right reason, and COMMITTED, lock them
  (`/tdd-lock`) — the `lock_guard` hook then BLOCKS both structured EDITS and write-shaped
  SHELL commands (`sed -i`, `> file`, `git checkout -- test`, `rm`, inline-python writes) to four
  surfaces: the locked tests, the verifier surface (conftest, test configs), the lock's OWN state
  (one versioned authority under Git's common dir; linked worktrees cannot bypass it), and the
  guard/hook files themselves —
  until `/tdd-unlock` with a JOURNALED reason AND a class (`phase` | `feature-end` |
  `test-wrong` | `gate-wrong` — only the last claims the gate was wrong, and it is the only one
  the yield instrument counts as a false positive). Reads and running the locked tests stay free. The
  strongest validated defense against the documented top agent attack vector (editing the
  failing test — HACK_CATALOG H2/H5; prompts don't stop it, mechanisms do). Unlock reasons
  are reviewed by §13's `/grade`; "adjusted test to match output" is the move the lock exists
  to stop. Snapshots are the same rule (H5): agents NEVER auto-update snapshots
  (`-u`/`--update-snapshots` is blocked); a snapshot diff is a human review artifact.
- **Every new mock needs a one-line justification** — what real behavior it stands in for and
  where that behavior IS tested for real. Over-mocking is the most common agent weakening
  (H3: agents add mocks ~36% of test commits vs ~26% for humans); the `overmock` guard reminds.
- **A double may narrow or fake BEHAVIOR; it must never supply an attribute, method, or seam the
  production object lacks.** If the double needs it to work, the production code needs it to work
  (origin: a fixture injected the very method production was missing — `to_state` on a
  SimpleNamespace — converting an integration bug into a green test for months). Distinct from
  over-mocking: that substitutes behavior, this substitutes EXISTENCE; §6's self-wired-fixtures
  rule is the assembly-level twin. Mechanical check per stack: build doubles with
  `create_autospec`/equivalent so a missing production attribute RAISES, or assert
  `hasattr(ProductionType, seam)` for the seam under test; the `overmock` guard flags
  fabricated-seam doubles.
- **Test at the seam you don't own.** When your code hands a value to a caller you did not write,
  the test must observe the value ARRIVING at that caller — the real caller, or a stub standing in
  its position — never merely LEAVING yours. The review-checkable tell: if every assertion reads an
  object your own code constructed and the test contains no representation of the consumer at all,
  it is a SELF-CONSISTENCY test, not a contract test — it can only confirm you agree with yourself
  (origin: Cheliped 2026-08 — two commands whose handlers RETURNED `message` while the adapter
  contract was `post_message`; the tests asserted on the return, so implementation and tests shared
  the same wrong belief and both disagreed with production. A test cannot catch a mistake it also
  makes — HACK_CATALOG H11). The corollary is the trigger question below applied at the seam: if
  the test would still pass with the other side of the seam DELETED, you tested yourself. The error
  is invisible from inside the mistaken belief — only the SHAPE of the test (no consumer present)
  is checkable without already knowing the contract, which is why this is a rule, not an
  instruction to be careful. Partition among §1's seam-shaped rules: outcome-not-proxy governs WHAT
  you assert; seam-fabrication governs what a double may SUPPLY; the fixture-value trap governs
  which VALUES can fail; THIS rule governs which SIDE of the seam the assertion observes. §6's
  composition-root rule is the assembly-level twin, §6c the flow-level home, and the durable
  mechanical guard for a whole pluggable family at once is §6c's family parity sweep.
- **Drive a guard through the entry that POPULATES its input — never seed the input by hand.** A
  sharper cousin of the seam rule, for guards/gates/authorization checks that read AMBIENT state (a
  contextvar, a process/request-scoped object, a global registry) rather than an argument. If a test
  establishes the guard's input by SETTING that ambient state itself — `current_run_context.set(...)`,
  monkeypatching the store, synthesizing the authorization object — then asserts the guard's verdict,
  it is self-consistency: it proves the guard agrees with an input the TEST planted, never that the
  PRODUCTION path publishes that input. The gate can be inert — a new caller builds the right
  authorization object but forgets to publish it to the context the gate reads — and every such test
  stays green (origin: Cheliped 2026-08-15 — a write gate authorizing off `current_run_context` that a
  new `run_agent_once` path never `set`; 9 green tests over a DEAD control; a fresh-context
  security-adversary caught it by driving the real entry and observing what the gate ACTUALLY read).
  The review-checkable tell (grep-able): a `<ambient>.set(...)` / monkeypatch of the guard's input
  store, followed by an assertion on the guard's decision, with NO call to the production entry
  (`begin_run`, the request handler, the middleware) that sets it. The durable form: a guard test
  drives the guard through the SAME entry that populates its inputs and asserts the decision — it
  never seeds the guard's ambient input in the test body. This is the "which SIDE of the seam" rule
  applied to ambient authorization INPUTS: the code under test IS the input's consumer, and seeding
  the input by hand tests the wrong side. Distinct from seam-fabrication (what a double SUPPLIES) and
  the return-reading H11 (a value LEAVING your code): here the test fabricates the guard's ambient
  INPUT STATE rather than the path that establishes it. Mutation is BLIND to it (§4) — the mutants
  live in the guard, the test seeds the guard's input, and neither touches the production path that
  should publish it, so 100% is reachable over inert code.
- Red-first is a helpful habit but it is an HONOR SYSTEM and easy to fake; do not lean on it as the
  guarantee of test quality. The guarantee is §3–§4 (+ the TEST-LOCK above).
- **Tests that cannot fail — the fixture-VALUE trap.** Red-first proves a test fails without the
  FIX; it does NOT prove the test can fail AT ALL once the fix is in. A fixture can pick values
  where the correct code and a MUTATED version produce identical output — the test then asserts the
  right property, looks thorough in review, and passes forever while advertising coverage that
  doesn't exist (observed: 11 in one session, every one review-clean). Recurring shapes:
  - **A clamp/floor hides the difference** — `weight(samples=10_000, heeded=0)` hits the lower
    bound either way; the mutant only shows at a magnitude where no clamp binds. Test ON the
    boundary, not comfortably past it.
  - **The happy path takes the same branch** — `capture_output=True → None` is invisible against a
    command that succeeds silently; only a FAILING invocation produces output to capture. Include
    the negative case.
  - **A sibling branch produces the same observable** — two thresholds that both emit ⚠; a fixture
    tripping both tests neither.
  - **Correlated fixture inputs** — keying a class on `i % 4` and the outcome on `i % 2` gives
    PERFECT stratification in a fixture named "flat". Make the key INDEPENDENT of the outcome.
  - **An unconditionally-true assertion** — `record.exc_info is not None` cannot fail: Python
    logging stores `exc_info = False` when you pass `exc_info=False`, and `False is not None` is
    True. (An earlier session blamed the test framework for the "unexplained" pass; it was the
    assertion, and a two-line experiment settled it. **A mystery in a test is usually the test** —
    spend the two minutes, don't ship a note that says "unexplained".)
  The check, after writing any test — and its GENERAL form governs every assertion and every piece
  of claimed evidence (§12): **what would still be true if this were broken?** If the assertion
  survives the defect, it is a proxy. The fixture special case:
  **what value would make this pass with the bug present?** If such a value exists and your
  fixture uses it, change the fixture. Prefer EXACT values to orderings
  — `a > b` is satisfied by a dozen wrong implementations; `w == (h + 0.35*20)/(n + 20)` by one.
  This is the strongest argument for §4 as an OUTCOME gate, not a ritual: the mutation score is the
  only thing that reliably catches this whole class.

## 2. Edge cases — a never-skipped category (`@pytest.mark.edge`)
Run each deliverable methodically through this checklist; write tests for the ones that genuinely apply:
boundaries/limits · empty/null/missing · malformed/invalid/wrong-type input · permission & auth NEGATIVE
cases · state/lifecycle transitions + idempotency/double-submit/re-entry · concurrency/ordering/retries/
duplicates · failure & error paths + rollback/cleanup · scale/large input · second-order/cross-surface ·
**adversarial content** — injection into human-facing text, logs, and inter-process payloads
(newlines/CR/control chars, field forgery, truncation-to-mislead). ·
**check-vs-use divergence** — when a guard and the operation it guards each normalise the same
input (`~`, `..`, symlinks, case, unicode form, relative bases), assert they AGREE — or resolve
once in the consumer and hand the guard the resolved value, so divergence is unrepresentable
(origin: a containment guard judged the unexpanded path while the tool expanded `~`, and wrote
`$HOME/evil.py` from "inside" the root — every guard test passed, because none used a `~` path).
- The adversarial-content line is its own question, not a rephrasing of auth-negative: **for every
  string that reaches a human, a log, or another process, which parts can an ADVERSARY influence, and
  can they change its MEANING rather than just its content?** Tests overwhelmingly check PRESENCE
  ("the card contains the right fields") and almost never FORGEABILITY ("an attacker cannot add one").
  Origin: a human-facing approval card built from newline-joined `key: value` lines with model-authored
  values interpolated raw — a crafted value rendered a COMPLETE, well-formed card ending `expose: no`,
  pushing the real `expose: YES` off a phone screen, while a trailing `#` commented the injection out
  for `sh -c` so the command still ran. It defeated the exact consent boundary the code implemented.
- The COUNT is derived from real failure modes, one-line justification each — NOT a quota to pad (Goodhart).
- A `@pytest.mark.edge` count is NOT a quality metric (marker theater). Quality is measured in §4.

## 3. Property-based testing for pure logic (Hypothesis / fast-check)
Manual edge enumeration is bounded by my imagination — the documented AI weakness. For pure / transform /
validation / parsing / serialization logic, add property tests that assert INVARIANTS and round-trips, so
a generator finds the boundaries I'd never list (research: ~35–50% higher edge-defect detection).
- **Ground properties in code semantics** — types, docstrings, names, comments — never invent arbitrary
  constraints (Anthropic's #1 PBT-with-Claude finding). When semantics are subtle, ask the human for the
  correct property rather than guessing a plausible-but-wrong one.
- **Self-reflect:** ask "is this test finding a real bug or passing trivially?" Don't wrap a test in
  error-handling that masks a real failure. Keep example-based tests for end-to-end flows.
- **A repo with an OpenAPI/GraphQL schema gets Schemathesis at the API boundary** — the
  schema IS a property source (1.4–4.5× more defects than other API fuzzers in independent
  evaluation, near-zero authoring cost), and it feeds §9's "untrusted endpoints degrade to
  4xx, never 500" rule for free.
- **Verify the invariant is actually TRUE before asserting it.** Idempotence, symmetry, round-trips
  are COMMONLY FALSE (e.g. a `%`→`%%` translation isn't idempotent; prefix-matching breaks similarity
  symmetry; `\w+` tokens include `_` so they aren't `isalnum`). When Hypothesis finds a counterexample,
  decide: real bug → fix the code; wrong/over-strict invariant → fix the PROPERTY. And only feed inputs
  within the function's CONTRACT (e.g. a function whose `prev` arg is its own prior output — not
  arbitrary data; passing garbage tests a non-contract and yields false failures).

## 4. Mutation testing — the real anti-performative metric
This is the ungameable check that tests actually catch bugs (100% coverage can assert nothing).
The integrity of the gate ITSELF — the documented ways a green verdict can mean nothing was
measured — lives in §4a; this section is how to run mutation WELL.

**What mutation score does NOT cover (the seam blind spot).** A mutation score is a statement
about your tests' sensitivity to changes in YOUR code; it says nothing about whether your code
satisfies a caller you did not write. When test and code share the same wrong belief about a seam,
the mutant and the assertion sit on the SAME side of it: mutate the message a broken handler
returns and the return-reading test kills it — score 100%, user still sees nothing (the H11
origin case, Cheliped 2026-08). Mutation testing is the anti-performative check WITHIN a seam;
§1's "test at the seam you don't own" is the check ACROSS one. Neither substitutes for the other —
a high score is a claim about the code's interior, never global assurance of production behavior.
The AMBIENT-INPUT variant (§1's "drive a guard through the entry that populates its input") is the
same blindness turned inward: when a guard reads ambient state and the test SEEDS that state by
hand, the mutants live in the guard and the test's planted input still satisfies them — a 100%
score over a control that never runs in production, because the production path that should publish
the input is on neither side of what mutation touches (Cheliped 2026-08-15).

**What mutation score cannot REACH (the attribution blind spot).** A second structural blindness,
independent of the seam one: a behavior exercised ONLY by spawning a fresh process is unmeasurable
by mutation on any tool, because no coverage tracer attributes work done in a CHILD process to the
parent test. The tool generates mutants and executes none — observed at 889 generated / 0 executed
on a repo whose behavioral calls all shelled out (Codex `7e1f4539`, `fad338eb`, 2026-08-17). §4a's
`killed + survived < generated` rule CATCHES this and reports CANNOT MEASURE, which is the correct
verdict and not a fix. The fix is test SHAPE (§8): keep the fresh-process test — it drives the real
seam (§1) and is the only thing proving the executable runs and imports cleanly — and ADD an
in-process twin driving the same public function. Both, not either. Where no legitimate in-process
seam exists, hand-apply targeted mutants (targeted-mutant mode below) as the executed-mutant
evidence and label the broad pass UNMEASURED. Do not spend time making the tracer follow a child
process; it cannot, and the attempts are the documented time sink.

**Scope — what goes on the roster.**
- Run a mutation pass on CRITICAL modules only (auth, money, permissions, lifecycle, core algorithms) —
  not the whole repo (mutant explosion). Tools: `mutmut`/`cosmic-ray` (Python), `Stryker` (JS/TS).
- **Roster admission — anti-creep teeth for "critical only":** a module enters the mutation roster
  ONLY with a one-line justification IN the roster stating "a survivor here costs ___"
  (an irreversible/security/money/data-integrity/loop-safety consequence). Rendering,
  presentation, and formatting modules are explicitly OUT — a survivor there is a cosmetic glitch,
  and the ceremony costs the same as on an audit chain. Re-audit the roster at feature end (origin:
  doctrine said "critical only" and practice still drifted to 44 rostered modules, 5 of them TUI
  renderers — the rule is only real when every entry carries its cost line).
- **When a critical file mixes eras, scope the gate by FUNCTION (two-tier policy):** new/core work
  gates at ZERO real survivors on its NAMED functions (nothing to lower); pre-Playbook debt paths in
  the same file are named as tracked debt next to the roster entry, with an instruction not to widen
  the gated list until their survivors die. A whole-file floor either flatters the debt or lets the
  debt dilute the new floor — function-scoped gating keeps the strong floor undiluted and the debt
  visible.

**Run & discover — cadence is a discovery tool, not just a checkpoint.**
- **Diff-scoped on PRs; full pass at feature completion — and EACH PHASE is a feature for gating.**
  A multi-phase program runs the gate at every phase boundary, not once at the end. Deferring
  doesn't cost mutant count (8 new modules generate ~2,000 either way); it costs a systematic
  weak-test habit compounding across every module built before the first measurement (observed: one
  ranges-not-values habit → 8 modules at 52.5%; measured at phase 3, phases 4–7 write differently).
  The full critical-module pass stays at
  feature completion, but substantive changes to critical modules get a DIFF-SCOPED run in review
  (Stryker `--incremental`/`--since`, pitest history files, mutmut on changed files) — a handful of
  survivors surfaced on the changed lines, Google-style. A repo-wide score is NOT a KPI (noise,
  arid code); per-module floors on critical code are the gate.
- **The per-module discovery loop — full passes VERIFY, they don't DISCOVER.** To RAISE a score,
  iterate one module at a time: run ONE module → READ the actual survivor lines → write kills →
  re-run that module → repeat until it clears the floor → next module → full pass only at the end.
  Per-module feedback is minutes; a full multi-module pass is 40+. And the survivor list tells you
  what's weak — guessing doesn't: in one 52.5% → 91.2% session (8 modules, ~2,100 mutants) reading
  survivor lines surfaced FIVE production bugs no passing test could (a probe that raised on every
  real call, an unreachable branch, a 10-second teardown stall, a constant contradicting its own
  docstring, two write-only emitters with no caller). Mutation is a bug-finder, not only a test-grader.
- **Targeted-mutant mode — mutation as test GENERATOR (Meta ACH pattern):** for the CONCERN of the
  change (auth bypass, money rounding, permission drop, lifecycle skip), generate 3–5 plausible
  concern-specific mutants and require a test that kills each, BEFORE trusting the suite. Inverts
  the workflow: instead of only grading tests after the fact, mutants state what the tests must
  catch. (Validated at 10k-class scale, 73% engineer acceptance.)
  **Precondition — a CLEAN, COMMITTED tree (or a worktree).** A targeted-mutant pass that
  `git checkout`/`stash`-reverts to restore source WILL clobber uncommitted work, silently
  (origin: a hand-rolled targeted-mutant script git-checkout'd away uncommitted work mid-pass —
  detect-after is worse than refuse-before). Gate any revert-based script on
  `python3 "${CLAUDE_PLUGIN_ROOT}/bin/with_snapshot.py" preflight` (it REFUSES on uncommitted
  tracked changes) — or use `with_snapshot.py begin`/`verify`, which RECORDS a dirty tree and
  restores it rather than blindly reverting. Committing first is the cheapest form of both.

**Triage survivors — real vs equivalent.**
- **Surviving mutants = weak/missing tests.** Triage survivors on critical paths first; add the test that
  kills each. Aim ~80%+ EFFECTIVE mutation score on critical modules.
- **Equivalent mutants are real and UN-KILLABLE — don't chase them (that's performative gaming).** On
  DB/SQL-heavy code, tools (e.g. mutmut, no toggle to disable string mutation) case-mutate SQL keywords +
  dict/`Row` subscript keys, which SQL/SQLite treat identically — these survive forever. Exclude them with
  a CONSERVATIVE automated filter: a survivor whose single changed line differs by CASE ONLY *and* sits in
  a SQL statement or a string-subscript — and ONLY when the changed token is a KEYWORD or IDENTIFIER.
  SQL/SQLite is case-INsensitive for keywords and identifiers but case-SENSITIVE for VALUES, so a
  case-change to a quoted value (`WHERE type='table'` → `'TABLE'`) is a REAL mutant that makes the check
  match nothing forever — never exclude it, nor a free-text/user-facing string. A too-permissive filter is
  a GATE DEFECT, not a scoring detail: it silently removes a bug class from EVERY gate. So every exclusion
  rule — filter OR ledger — ships a NEGATIVE test proving the nearest REAL mutant still blocks, and you
  AUDIT the excluded SHARE over time: if it grows while the score improves, the filter is doing the work
  the tests should (a healthy run holds or shrinks it — e.g. 4.5% → 4.1% while the score went 55% → 91%).
  Gate on the EFFECTIVE score = killed / non-equivalent; print raw + effective + the count excluded
  (transparent). (Real example: reconcile went 62.8% raw → 67% → 89.7% effective once equivalents were
  filtered AND real `reconcile()` contract tests were added.)
- **Equivalents the heuristic can't classify go in an audited equivalence ledger**, never into a
  widened filter. One entry per mutant, with (a) a WRITTEN equivalence proof in the entry itself,
  (b) EXACT-substitution matching — the changed line must be exactly the documented before→after,
  so an entry can never swallow a neighboring real mutant — and (c) its own can't-overmatch test
  asserting a nearby DIFFERENT mutation is still kept. Ledger entries match by line TEXT, not
  location: before adding one, check the same line doesn't recur elsewhere in scope — and keep a
  STANDING recurrence audit (occurrences == expected per file), because a line COPIED later into
  gated scope silently extends the proof to code nobody proved; this governs every by-text
  exemption mechanism (equivalence ledgers, lint baselines keyed on content), and an accessor
  extracted to kill the duplication must be written in DIFFERENT text or it just moves the
  collision. Keep the
  ledger SHORT — a growing ledger is a smell that the code should be made killable instead.
- **String mutants are classed by ROLE, never chased uniformly:** logic and DATA strings (SQL,
  dict/subscript keys, hash-domain inputs, PERSISTED audit/forensic content) stay zero-survivor —
  a mutation there is a real bug. Operator-facing DISPLAY prose (status lines, refusal sentences,
  log copy) is an informational/floor class, NEVER resolved by pinning the prose verbatim in a
  test: a verbatim pin kills the mutant, catches no bug, and breaks on every wording tweak —
  Goodhart pressure the gate design itself generates (origin: a zero-survivor gate downstream
  forced exact-copy-text assertions; the fix is the class, not the pin). The informational
  exemption covers LITERAL STRING CONTENT only: a logic mutant on a display line (True→False,
  and/or flip, dropped guard) and anything inside an f-string `{expression}` is CODE and stays
  real/blocking — mask the string's characters, never the line it sits on.

**Anti-gaming hygiene.**
- **Mutants stay OUT of the implementing agent's context.** A visible verifier is a gameable
  verifier (METR: models introspect graders when they can see them). Dispatch `mutation-runner`
  fresh; the implementer sees killed/survived VERDICTS, never the mutant list it could special-case.
- Frame the anti-gaming story around mutation score, not the red-first ritual.

## 4a. Gate integrity — a gate can report green on nothing
A mutation gate is only as honest as its plumbing: a green verdict is worthless if the run measured
nothing. These are the documented false-green modes — each has bitten a real gate, and the abstract
"gate it properly" was not enough to prevent any of them.
- **Gate it (close the loop):** a small script parses the tool's machine-readable stats, prints
  `Mutation: N%`, and FAILS under a no-regression FLOOR — BLOCKING in CI. Raise the floor as genuine
  survivors are killed; never lower it. Report-only mutation that nobody must act on is theater.
  **A roster entry with no gate invocation is a comment.** The admission rule (§4) says whether a
  module BELONGS on the roster; it does NOT prove the entry is WIRED to a gate. Assert (tripwire-style)
  that every rostered module appears in at least one gate invocation, or is listed as explicitly-tracked
  debt — §6's BUILT-vs-WIRED applied to the gate itself (observed: 8 rostered modules with cost lines and
  a suite shim but in NO gate invocation, twice in one week — the second repeating a mistake the repo's own
  CI script documented six days earlier).
- **Every scoped gate needs a VACUITY GUARD — on TWO axes, scope AND execution.** (This is the
  DEGENERATE case of §12's scope rule: a result carries its denominator, and zero is just the
  loudest denominator. Everything between zero and complete fails the same way, quieter.)
  *Scope:* a
  pattern matching ZERO generated mutants (typo'd function name, module dropped from the tool
  config) must FAIL LOUDLY ("refusing a vacuous pass"), never read as green — a gate that can pass
  by testing nothing is the one gaming vector scope-based gating opens. Count that denominator from
  mutants the tool GENERATED, not from its survivors/problems report: a fully-killed scope looks
  empty there, and a naive guard would fail a perfect run. *Execution:* generated is NOT executed —
  the scope guard is necessary but NOT sufficient. A mutation tool needs a GREEN baseline to score;
  a RED baseline (one drifted test is enough) makes it print `failed to collect stats / runner
  returned N` and run ZERO mutants while still GENERATING them on disk, so the survivor collector
  comes back empty and `generated>0 / 0 survivors / exit 0` reads as a clean green. **0 survivors ≠
  pass, and generated > 0 ≠ measured** — before trusting any pass assert three things: (1) baseline
  GREEN **in the tool's own REWRITTEN TREE, not merely at HEAD** — mutation tools run the suite
  against an instrumented copy, so a suite green at HEAD can be red there and produce the identical
  generate-but-never-execute false green (the common cause is a test that reads its own source —
  below), (2) executed/run count > 0 read from the tool's RUN stats (not the on-disk generated set),
  (3) kill tests collected (below). The gate must CAPTURE the tool's exit code / output and
  detect its stats-abort markers — **a discarded exit code is a discarded truth**; a gate that runs
  the tool and ignores the result certifies unmeasured scopes as green. A SHARED baseline is a
  shared point of failure: one RED/drifted test anywhere disables EVERY scoped mutation gate at
  once, for as long as it stays red — surface "cannot measure," never a green. And calibrate this
  plumbing (§13): a deliberately-RED baseline must make the gate ABORT/FAIL — a mutation gate you
  can't demonstrate failing on a broken baseline has been asleep for an unknown duration (origin: a
  downstream gate false-greened intermittently since before 2026-07; the generated-count guard
  alone never noticed).
- **Account for EVERY mutant — killed + survived < generated means UNMEASURED.** Outcomes that are
  neither killed nor survived (SEGFAULT, timeout, no-covering-test, skipped) are INVISIBLE to a
  survivor collector that harvests only `": survived"` lines — while the vacuity guard counts
  mutants GENERATED. So a scope where every mutant SEGFAULTED prints "0 survivors — PASS" and sails
  the guard (observed: 151 segfaults + 56 no-covering-test in one pass, 94 of the segfaults in the
  single function carrying a feature's whole safety claim — the gate called it clean). RULE: if
  killed + survived < generated, the scope is UNMEASURED — REFUSE to certify, don't merely warn.
  And CHECK baseline-green as an explicit PRECONDITION — at HEAD *and* in the rewritten tree, which
  are different facts (don't assume either): under a shared baseline one pre-existing red test
  silently disables every scoped gate, so assume-green is exactly how it stays undetected.
- **Verify the gate's KILLING SUITE actually collects your kill tests.** Tools with a dedicated
  mutation suite (e.g. mutmut's `tests_mutation/`) never see kill tests written in the normal
  suite — the gate then measures the WRONG suite (red, or worse, vacuously green). Shim/star-import
  the real suites into the killing suite and assert the collected count MECHANICALLY (a star-import
  shadowing silently drops a test; a docstring claiming "collision-checked" is narration).
- **PREFLIGHT the cheap checks BEFORE the expensive pass — the same assertions, seconds instead of
  an hour.** Every rule above reads "before trusting a pass," which invites running them post-hoc,
  after you have already spent the 40 minutes you must then discard. Run them FIRST, in this order,
  and REFUSE the pass on any failure: (1) roster integrity — no DUPLICATE entries (a duplicated
  `paths_to_mutate` path makes mutmut 3.6 abort after stats collection, with the cause named nowhere
  in its output), every entry resolves to a real file, every entry appears in a gate invocation;
  (2) the kill tests are COLLECTED by the configured killing suite, asserted as an exact count;
  (3) that killing suite is GREEN against the tool's rewritten tree; (4) the tracer maps at least
  one mutated function to at least one test — if it maps none, the run cannot measure anything and
  the attribution blind spot (§4) is the first thing to check.
- **Tests that read their own SOURCE are structurally unsatisfiable under a rewritten tree.** §12's
  "absence claims about code PARSE the code" rule tells you to assert on AST nodes — and those exact
  tests fail against a mutation tool's instrumented copy. That is a COLLISION between two correct
  rules, not a defect in either. Register the individual TESTS in a mutation-only exclusion list;
  never skip their whole module, which silently drops the real kill tests sitting beside them.
- **A refusing gate prints the diagnosis it already holds.** "Refusing a vacuous pass" held for
  four days because nothing named the CAUSE sitting in the gate's own captured output — the
  refusal message carries the failing assertion/path, and the same condition is mirrored by a
  cheap test in the fast suite, so the breakage surfaces in seconds instead of on the next
  slow-gate run.

## 5. UX journeys — `@pytest.mark.ux` — interface-agnostic
A UX journey drives the REAL interface a user touches and asserts the user-visible outcome + the persisted
effect. Written from the UX request. The category is constant; the DRIVER swaps per interface:
- **Web** → Playwright (real browser; curl/TestClient miss JS/CSP). Verify DB, not just HTTP 200.
- **Telegram bot** → feed Updates through the dispatcher / bot-API harness; assert reply + side effects.
- **TUI** → Textual `Pilot` (press/click/assert screen) or `pexpect` over a PTY.
- **Telegram mini-app** → it's a webview → Playwright the web layer; test handlers beneath voice.
- **MCP server** → drive via an MCP client: call tools/resources, assert results + state.
- **Test the OUTERMOST real interface, not a layer beneath it** — "the handler returns X" is the no-web
  equivalent of "the route works ≠ usable." Drive it through its real dispatcher/protocol.
- **Manual scripted checklist = LAST RESORT** only for a genuinely un-automatable seam (real voice capture,
  hardware, a 3rd-party OAuth consent screen). Same scannable scenario format; say what's manual vs
  automated. Never use it to dodge automatable interfaces (Telegram/TUI/MCP are all automatable).
- Playwright determinism: role/text/user-facing locators; web-first auto-waiting assertions; verify a POST
  via `expect_response`, NOT `networkidle` (streaming/SSE pages never go idle). See §7.

## 5a. UX probes — intent-only agent probes (`ux_probe` — trend line, NEVER a gate)
A §5 journey proves the SCRIPTED path still works — its author already knows where the button is, so it
can never detect that a real user couldn't find it. A UX probe closes that gap: a FRESH LLM agent gets
only the user's INTENT ("sign up for the meeting") and must accomplish it through the real interface —
the UX analog of §13's fresh-context verifier: an unbiased actor DOING the thing, not confirming it.
Probes are probabilistic, so §7's zero-flake rule and §8's EVAL rule govern them:
- **Oracle split (the load-bearing rule):** the agent's self-reported success is telemetry, NEVER a
  gate. BLOCKING assertions are deterministic and HARNESS-owned: persisted effect (DB row), no-5xx
  (from the harness's own network/HAR capture), console-error budget, no forbidden hosts. TREND LINE
  (non-blocking, tracked per run): success rate over N runs, steps-to-done vs baseline, tokens/cost,
  friction events. A transcript of a FAILED goal is a deliverable — file it as a UX bug
  ("couldn't find how to cancel"), not a flaky test.
- **Engine contract (engine-agnostic):** any driver qualifies if it provides OBSERVE (interface state
  serialized for the LLM), ACT (an enumerated action space), EVIDENCE (per-step transcript/snapshots) —
  and leaves the ORACLE to the harness. The DRIVER swaps per interface, exactly like §5:
  - **Web** → harness owns the browser; the engine attaches over CDP. Blessed engines: **Stagehand**
    (TS/Node repos; its committed act-cache = probabilistic discovery → deterministic replay, so UI
    drift surfaces as a cache-file diff in the PR) · **browser-use** (Python repos; attach via
    `cdp_url`, HAR recorder feeds the no-5xx oracle, custom `report_ux_friction` action; set
    telemetry, cloud-sync, and the default LLM judge OFF). Both self-report success — oracle split applies.
  - **Telegram mini-app** → it's a webview: same browser engines + a `Telegram.WebApp` shim (signed
    test `initData`; MainButton/BackButton stubbed INTO the probe's action space — native chrome the
    DOM doesn't contain is still UX surface the probe must perceive).
  - **TUI** → tmux/PTY loop: `capture-pane` = perception (the screen is ALREADY text — no heavyweight
    engine needed), `send-keys` = action, asciinema cast + per-step buffer snapshots = evidence;
    oracles on files/DB/exit code/final screen. (Textual `Pilot` stays the deterministic §5 layer;
    `textual serve`/ttyd bridges a TUI into the browser engines when browser-grade evidence is worth it.)
  - **Telegram bot** → the reply + `reply_markup` JSON IS the serialized state; drive the dispatcher
    harness (or a user-client against the test DC for outermost fidelity).
  - **MCP server** → the probe is an agent-SDK client given only the tool list (converges with
    §5b, which tests the agent on the other side of that tool list).
- **Calibrate with planted UX defects** (§13's rule, same teeth): periodically mislabel the submit
  button / hide a required field / dead-end a flow, and require the probe to flag it. A probe that
  never fails a plant is theater.
- **Cost & cadence:** probes are slow and metered — SCHEDULED (nightly/weekly) on CRITICAL journeys
  only, with per-probe step/token caps; never per-commit. (Exception: Stagehand's cached replay is
  cheap enough for a per-commit warn lane — alert on cache-miss/self-heal.) Require N≥3 runs before
  trusting a success-rate delta.
- **Hygiene (non-negotiable):** staging + controlled fixtures ONLY — page/screen content is a
  prompt-injection surface, never point a probe at live user data; LLM keys stay harness-side, never
  in-page; pin engine versions; exclude dangerous actions (raw JS eval, web search) from the action space.
- **The free win regardless of engine:** what makes an interface agent-legible (semantic roles, real
  labels, accessible names) is exactly what §5's role/text locators and §9's axe gate already demand —
  enforce it at dev time and journeys, probes, and accessibility all strengthen together.

## 5b. Agent evals — testing what an agent DOES (`eval` blocking lane · `eval_judge` trend lane)
§5a tests an interface THROUGH an agent; §5b tests an AGENT through a harness. Same oracle split,
mirrored. Reach for it when the thing under test is a prompt, a tool definition, a model routing
rule, or an agent's behavior — §8's `[→EVAL]` resolves here. **This repo's own `calibration/` IS a
§5b eval**: it drives real agent briefs against planted defects, captures the transcript, applies a
deterministic oracle, repeats, and calibrates itself with controls. Read it as the worked example;
every rule below describes something it already does, and a rule that does NOT describe it is the
rule to distrust.

- **Premise:** the output is **a distribution, not a value**, so a fixed input scored against a fixed
  expected output is the wrong shape — while §7's zero-flake rule forbids gating on a probabilistic
  judge. The resolution is the split, and the split is finer than "deterministic vs LLM":
- **BLOCKING = agent-path-INDEPENDENT invariants** — true on every run *regardless of what the agent
  decided to do*: no forbidden tool invoked, no network egress, no secret in the output, structured
  output schema-valid *if* emitted. §5a's blocking oracles are this shape (no-5xx, no forbidden host,
  console budget) and that — not "the harness owns them" — is why they can gate.
- **Path-DEPENDENT outcomes are k/k over N, never a single run** — did it refuse the known-bad
  prompt, did it select the right tool, did it get the count right. These depend on what the agent
  chose, so one roll is a coin flip: `PASS` only at k/k, **AMBER** on a partial catch (nonzero;
  consecutive AMBER promotes to BLOCKING). Do not put them in a per-commit hard gate — that is a
  flaky gate wearing a deterministic costume, and it is the most common way a §5b lane gets
  disabled a month after it ships.
- **LLM-judge scores are a TRACKED TREND LINE, never a gate** (`eval_judge`). Score on a **0–5
  rubric** (the format with the highest measured human agreement), and **measure that agreement
  periodically** — a threshold with no measuring procedure is a smoke alarm with no battery. Below
  ~65% agreement the judge is noise: drop it rather than record it.
- **Grade OUTCOMES, not paths.** Process checks are for shortcut detection only. An eval that pins
  the route an agent took ossifies today's implementation and calls it correctness.
- **A parseable verdict requires a FORCED closed-vocabulary line — "parse, don't grep" is
  unactionable without one.** `calibration/holdout.py:630-637` is the compliant instance
  (`Control-Verdict: REJECT|FIX-ORACLE|KEEP` — *"Free prose never becomes a verdict"*). The
  counter-evidence is in-repo and expensive: `calibration/oracle-changes.md:35` records a correct,
  forceful refusal scored as a MISS on verb form and word order, and every widening on 08-04/08-05
  was the same class. Forcing the line is what stops the oracle drifting to meet the prose.
- **Test at the seam you don't own (§1), at agent scale.** An agent does not act; it EMITS an
  instruction something else executes. So assert the EFFECT at the consumer — the row written, the
  message delivered — never the emitted tool call. "Tool-call accuracy," the headline metric of most
  agent-eval tooling, compares the agent's emitted call against your own expectation of it: every
  assertion reads an object your side constructed, which is exactly H11. It passes green while a
  renamed tool, a drifted argument shape, or a call nothing executes ships silently.
- **Cost & cadence — OPT-IN and reactive, no clock.** Run evals when an agent misbehaves, when a
  doer-model upgrade lands (§13's verifier-strength policy), or to prove a gate against a planted
  defect. A standing nightly/weekly eval obligation is the shape v1.32.0 retired: it produces
  obligations faster than findings, and a cadence nobody meets stops being a control.
- **A per-commit lane REPLAYS; it does not call a model.** Record the transcript once, replay it
  against the oracles for free, and treat a cache-miss as the alert — §5a's cached-replay exception,
  same trick. A per-commit lane that hits a live model is metered on every push and stochastic on
  every push.
- **Pin the model, and a model change starts a NEW trend SEGMENT** — never silently continued. Same
  rule the plant corpus already applies by recording its authoring model: a trend across a model
  boundary is two populations wearing one line.
- **Calibrate with planted agent defects** (§13, same teeth): inject a known-bad behavior — a tool
  returning wrong output, a refusal that quietly complies, a schema dropping a field — and require
  the eval to flag it, with a paired clean control it must stay quiet on. An eval suite that never
  fails a plant is theater. Plants belong in the existing corpus under its existing rules
  (adversary-authored at ≥ the doer's tier, human-approved, supersede-never-edit), not a second
  uncalibrated library.
- **Hygiene (non-negotiable, inherited verbatim from §5a):** staging + controlled fixtures ONLY —
  observed content is a prompt-injection surface, never point an eval at live user data; LLM keys
  stay harness-side; exclude dangerous actions from the agent's action space during the run.
- **Downstream this is BYO-harness.** `calibration/` is a reference implementation, NOT a shipped
  tool — `install_into_repo.py` vendors no `calibration/`, so a repo adopting §5b supplies its own
  driver. What is canonical is the oracle split and the two lanes, not any engine.

## 6. The Tripwire — `@pytest.mark.tripwire` (runs LAST)
A plan-coverage catch-all tied to THE CURRENT plan's deliverables (re-anchored each plan, like TDD tests
target the feature). For each deliverable assert it is:
- **BUILT** — its route/entry/tool is registered; AND
- **WIRED IN** — a real user entry point references it (UI button / CLI command / MCP tool); AND
- **ACTIVATED** — its state in the SHIPPED default config: on, or off behind a NAMED, user-reachable
  switch (UI toggle / wizard step / documented command). "Off with no on-switch" trips RED — built +
  wired + tested + dark is the largest documented darkness class (in the origin audit: a whole
  verify-oracle stack behind a config gate with no switch, a delivery target shipping as "none").
  A feature whose gate depends on another DISABLED
  gate must REPORT itself dark, never silently no-op. Repos with a capability registry (§6a): the
  deliverable's entry is part of this proof — `capability_registry.py validate` must pass.
  **For a USER-CONTROLLABLE (toggle-gated) deliverable, reachability of the SWITCH is the bar — and
  it's a TWO-surface test, asserted mechanically:** code that merely READS the flag is the
  route-exists trap ("the flag works when set"); the real bar is "a human other than the author can
  FIND and flip it." So ACTIVATED for such a deliverable must assert its toggle is (1) reachable
  through the project's canonical feature-control surface — the `/features`/settings equivalent,
  where a user turns things on — AND (2) visible in the project's health/status surface — the
  doctor/dark-inventory equivalent, where an operator sees it exists-but-off. Absent from (1) it is
  dark-to-the-USER; absent from (2) it is dark-to-the-OPERATOR (the doctor can't report what it
  can't see). The documented failure was BOTH at once: six toggles that read their flags correctly,
  were tested, and were even registered, yet appeared in neither `/features` nor `doctor` (§6a names
  HOW that slips through — a coverage-test exemption). Where the repo HAS these surfaces, asserting
  reachability in both is not optional polish; it's what "wired-in" MEANS for a toggle. AND
- **EXERCISED** — point at a SPECIFIC `file::test_name`; assert (via `ast`) that the test is DEFINED and
  NOT skip-marked (`@pytest.mark.skip`/`skipif` or a module-level `pytestmark` skip). A string-token grep
  only proves a *reference*; a hollow button or a `@skip`'d test must trip the Tripwire.
- **RUNNING** — a FIFTH leg, required ONLY for a REMOTE deliverable (one whose execution host is not the
  session's repo/process: a VPS, a daemon, an installed plugin, a vendored `.claude/` in another repo).
  The first four legs are all answerable *about the laptop* — BUILT/WIRED/ACTIVATED/EXERCISED can every one
  be green while the DEPLOYED instance runs different code. RUNNING closes that: the deployed instance
  ECHOES the sha/version it is executing, and a probe asserts it equals the intended sha (§6a version-echo).
  In a laptop-only repo commit-and-push IS the deploy, so "fixed" and "running" are the same event; the
  moment a remote runtime exists they come apart and nothing else re-separates them. (Origin: a deployed
  engine ran code **97 minutes / six commits behind** while all four other legs "passed" — every reported
  fix had never executed anywhere.) This sharpens the EXTERNAL-STATE proof class below from "cite how you
  checked" into a named probe. Capability registry (§6a): a remote deliverable MUST carry a
  `deploy_surface` with a `running_version_probe` — `validate` fails without it (`R-DEPLOY`). Report
  `Tripwire: N/N (+ RUNNING M/M for remote deliverables)`.
- **Prove wiring through the PRODUCTION composition root, not a self-assembling fixture.** The
  documented root cause of whole-subsystem darkness: every component ships tests that wire the
  component up THEMSELVES, so it works in a fixture that never exists in production (the handler on
  a private bus while emitters publish to the global one; adapters nothing starts; an agent
  advertised a tool its build never attaches). The WIRED proof must construct the REAL object graph
  — the actual daemon/app factory, the actual per-platform agent build — and reachability checks
  must be SYMMETRIC: everything registered is reachable in the real build AND everything reachable
  is registered (a one-direction check passes the inverse bug class forever).
- **Multi-deliverable plans: classify each deliverable by HOW it can be proven** (forbids a lazy "done"):
  DIFF-VERIFIABLE (a path/line/test you can `[ -f ]` / grep / run right here) → prove it now; CROSS-REPO
  (lands elsewhere) → cite where + how you checked; EXTERNAL-STATE (DB row, deployed endpoint, message
  sent) → name the probe that confirms it; UNVERIFIABLE → say why AND what would verify it (never a dodge).
  And **code that *handles* a deliverable is not the deliverable** — a parser for X is not X working.
- **Reverse check (diff → plan):** the Tripwire proves every deliverable is in the diff; before reporting
  it, also check the inverse — every changed line traces to a plan deliverable. What doesn't trace is
  scope creep, a drive-by refactor, or an orphaned helper: remove orphans YOUR change created; unrelated
  cleanup/dead code gets MENTIONED, not done ("dead" is a negative claim — §12 requires the exhaustive
  sweep before acting on it).
- **Design-quality pass (diff → debt):** the Tripwire proves the fix is wired and tested; it does NOT
  prove the fix is at the RIGHT SEAM. Run the `architecture-adversary` on the diff — does the change fix
  the root, or add debt (an Nth copy of a list/enum, a special-case branch, a helper that duplicates one
  that exists, a check keyed on a proxy name instead of the fact it's about)? A green, fully-wired diff
  that band-aids the architecture is exactly the failure this catches. Advisory like the
  integration-adversary, not a hard block, but its findings are specific enough to act on.
- Author it red-first, drive to green; report `Tripwire: N/N`. It's a FLOOR, not a target — never add a
  hollow button/stub to go green. Anchor it to the PLAN, not the implementation. And a NEW
  guard/check/tripwire a plan ships is itself subject to §13's guard-calibration rule before it
  is trusted. A plan that
  carries a §0 flow table reports `Tripwire: N/N (+ FLOWS M/M)` — each flow row's liveness test
  named and GREEN (§6c); a deliverable can be four-leg green while its flow dead-ends.
- Scale it: full Tripwire for multi-deliverable plans; for a 1–2 deliverable change the regular behavioral
  tests + a one-line wiring check suffice.

## 6a. Wiring liveness — darkness must be enumerable (standing, not per-plan)
The Tripwire (§6) is a snapshot at build time; wiring ROTS as later work moves seams — §13's decay
principle applies to wiring itself. And the meta-bug that lets rot hide: health surfaces that report
only on what RAN make a dead feature indistinguishable from a quiet one ("healthy, no runs recorded
yet"). Darkness is invisible by construction unless you enumerate from what SHOULD run. And every
health surface DECLARES its evidence tier — the ladder is
`config-read < import < runtime-probe < composition-root` — because
import-existence alone can never render OK (the §6c origin excavation found three health checks
green-lighting ~1k LOC of provably unreachable code on import-success):
- **The capability registry (`capabilities.json`)** — small, machine-readable, per repo: each
  capability's surfaces, activation default + named on-switch, production wiring site (`wired_by`),
  assembly-level test (`exercised_by`), emitted topics with NAMED consumers, and integration debt
  (owner + expiry, expired debt FAILS). Corpus rules apply: **it only grows**; registering there is
  part of a deliverable's WIRED proof. Mechanical gate:
  `python3 "${CLAUDE_PLUGIN_ROOT}/bin/capability_registry.py" validate` (BLOCKING in the release
  gate) · `… doctor` prints the dark-feature inventory — every built-but-off capability WITH its
  on-switch, write-only emitters, debt aging. The doctor makes the next archaeology audit unnecessary.
- **Version-echo — for capabilities that run ELSEWHERE (the RUNNING leg's mechanism).** Wiring rot has a
  remote twin: DEPLOY DRIFT — the deployed instance silently runs an older version than HEAD, and a health
  check that inspects the local checkout can't see it. The invariant is "running == intended," the same
  assertion `verify_verdict.py` makes (`commit == SHA`) and `install_into_repo.py --doctor` makes (vendor
  stamp vs canonical) — copy those. Convention: every deployed/remote component EXPOSES the sha/version it
  is running (an endpoint, a `--version`, a heartbeat field, a stamp file) and its verifier ASSERTS it
  equals the intended sha, failing LOUD on drift or an unreachable echo (never a silent pass). Mechanically:
  a capability that runs elsewhere declares a `deploy_surface` — `{runs_on, gets_there_by,
  running_version_probe, divergence}` (the four questions §0's deploy surface asks); `validate` FAILS a
  remote surface with no `running_version_probe` (`R-DEPLOY`), and `doctor` lists remote surfaces flagging
  any missing probe. "No way to tell if the box runs the right version" is a hard failure, not an omission.
- **Exemption is for internals, NEVER a darkness hatch.** A coverage/registration test that
  enforces "everything that should be registered IS" almost always ships an ignore / exempt /
  allow-list escape hatch for genuine internals (a private helper, a dev-only flag, a
  build-plumbing capability with no user surface). That hatch is for NON-USER-FACING internals
  ONLY. Using it to silence the coverage test for a user-facing (or measured-rollout) feature is
  the single most efficient darkness vector there is: the very same exemption entry that quiets
  the test ALSO drops the feature from the control surface (`/features`) and the health surface
  (`doctor`) — the exact two surfaces the test exists to protect (§6 ACTIVATED). One
  inappropriate exemption defeats every automated guard at once, silently, and looks like green.
  (Origin: six downstream toggles, all hidden by ONE exemption entry — the guards weren't
  bypassed, they were told the feature didn't exist.) So pair the exemption list with a COMPANION
  test that asserts every user-facing / measured-rollout gate is REGISTERED, never exempted — an
  exemption entry pointing at a user-facing capability must FAIL the suite. An exemption is a
  claim "no user can reach this"; §12 says a claim needs evidence, and a user-facing toggle
  refutes it on its face.
- **The ASSEMBLY suite (`@pytest.mark.assembly`)** — the standing antidote to self-wired fixtures:
  build the real production object graph per platform (real daemon factory, real agent build) and
  assert every ENABLED registry capability is reachable in it, both directions (§6's symmetric rule).
  Symmetric reachability is proven through the real dispatch order, not a membership list — a
  membership test passes a shadowed handler forever (the §6c T6 escape: `/plan` registered twice,
  the second registration silently winning); duplicate registration RAISES at load, and
  last-write-wins is banned. Fast and deterministic → runs every CI push, not on a schedule.
- **Liveness canaries + staleness sweep** — §13's planted-error rule applied to wiring, two layers:
  ACTIVE — on a schedule, plant a synthetic event through the PRODUCTION seam and assert the consumer
  processed it (a subscriber-count probe would have caught the dead-bus orchestrator months early);
  PASSIVE — "registered but zero runs in N days" from telemetry (`liveness.max_quiet_days`). Weekly
  Routine, like the calibration scoreboard: a diffable line, not an annual dig. Monitors
  record SUCCESS as well as failure, and a standing check compares the SCHEDULED set against
  observed rows — silence goes RED, because a job that stopped being scheduled leaves no failure
  row and dead-and-quiet look identical from the run side (the §6c absence-blind-monitor class).
- **Half-built-and-silent is the WORST state — decide-or-park.** A dormant package, an unactioned
  review finding, a "we'll wire it later": each gets an owner + expiry (debt entry) or gets parked
  LOUDLY (removed from the registry with a stated reason). Findings without owners rot; the registry
  makes the rot expire instead of accumulate.

## 6b. Onboard, don't hide — a default-OFF feature needs an onboarding contract
§6 catches "off with no on-switch." This catches the subtler darkness: an on-switch that nobody is
scheduled to throw. **A switch with no scheduled hand on it is a switch that will never be thrown** —
the feature is built, wired, and quietly zero forever, which is dark WASTE wearing the disguise of
caution. So a deliverable that ships default-OFF must ship an ONBOARDING CONTRACT, five parts, or it
doesn't ship default-OFF:
- **(a) A named ONLINE metric that populates the moment it's on** — a real production signal
  (telemetry counter, dashboard row, success-rate lane) that moves off zero once the switch flips,
  NOT a synthetic offline eval someone has to remember to run. "OFF pending an offline eval someday"
  is the dark-rollout trap: the eval never gets run and the feature lives at zero indefinitely.
- **(b) A turn-on-at-deploy step** — the concrete action, with an owner, that flips it on in the
  target environment. In the plan, not a vague "we'll enable it later."
- **(c) A scheduled review with a keep / flip / kill call** — a DATED checkpoint (the §13 cadence)
  where a human reads (a)'s metric and makes the decision. Unscheduled = never.
- **(d) A kill condition** — the metric threshold or the date at which the feature is removed if it
  hasn't earned its keep, so a dead default-OFF feature EXPIRES instead of accreting (§6a's
  decide-or-park, made numeric).
- **(e) A user-reachable toggle** — through the canonical control surface AND visible in the health
  surface (§6 ACTIVATED's two-surface bar), so someone other than the author can find it.
**The forcing rule: if a feature can't be measured online, it ships ON, or it doesn't ship
default-OFF.** A feature you can't watch is a feature you can't onboard, and shipping it dark is
shipping it into a silence you designed yourself. This section is the rollout MIRROR of §6a: §6a
enumerates darkness that already happened; the onboarding contract prevents the default-OFF rollout
that becomes it.

## 6c. Dataflow Liveness — nodes are necessary; edges are the truth
§6/§6a prove NODES: the feature is built, wired, activated, exercised. This section proves EDGES —
because a wiring net can be perfect on its home turf and still leak: in the origin excavation
(Cheliped, 2026-08-03) the node-level registry caught zero of 12 post-safeguard escapes, and every
one was an EDGE failure — a flow produced with no live consumer, a value accepted with no reader, a
fix verified at the supply end. The doctrine: **every flow names a live consumer, every migration
proves parity for the seam it replaces, and every "wired" claim is proven at the output end.**
- **The flow kinds — sweep them ALL, not just the ones that look like features:** persisted
  rows/fields (incl. WHO PRUNES them — unbounded growth is a missing consumer) · queryable
  telemetry (every event type emitted has a query consumer) · config fields AND each accepted enum
  value (a value accepted but read by nothing is a silent no-op wearing a knob) · template/prompt
  keys (every supplied key has a placeholder; every placeholder a supplier) · registry/dispatch
  names + ORDER (a shadowed handler is dark despite registration) · lifecycle events per surface
  (an event only one surface fires starves every consumer on the others) · queues/dirs/caches
  incl. eviction · **silent-default boundaries** — `dict.get`/`getattr`/`**kwargs` sinks, the
  general class where a misspelled or orphaned key degrades to a default instead of an error ·
  **schedule overlap** for time-windowed flows (a producer and consumer whose windows never
  intersect is a dead edge with two live ends).
- **The escape taxonomy (report against it, §13):** **T1–T7** — T1 refactor orphaned a consumer ·
  T2 written, never read · T3 built, never called · T4 accepted value, no reader · T5 render-seam
  gap (key supplied, no placeholder — `str.format` drops it silently) · T6 registry collision /
  interception · T7 event never fired on a surface. One successful strangler migration caused five
  of the twelve origin escapes — migrations are the highest-yield hunting ground.
- **Standing sweeps, in two decidability tiers.** Tier 1 EXACT (no false positives by
  construction): render pairing (template keys ↔ placeholders, BOTH directions) · the **family
  parity sweep** — registration uniqueness + dispatch-order reachability + HOST-CONTRACT parity:
  where N pluggable members share a host (command handlers, hooks, span processors, tool adapters,
  middleware), ONE repo-local test enumerates the family FROM THE REAL REGISTRY and asserts the
  host's contract for every member, with a vacuity guard on the enumerator count MANDATORY (§4a's
  vacuous-pass rule applied to sweeps — the origin author's first version imported a registry
  accessor that did not exist; only the count assertion surfaced it). This flow kind is repo-local
  BY CONSTRUCTION — only the repo's own test can import the real registry, so a generic scanner
  cannot cover it (unlike the pairing sweeps the reference tool ships); one test per family, not
  per member, and it catches the member written by someone who never read the convention — the H11
  failure mode (evidence it is doctrine, not a tip: one repo independently invented this shape
  three times after three different incidents — features registry, hook seam parity, command
  output parity; Cheliped 2026-08). Naming: SURFACE parity (§0) is about interfaces, CONSUMER
  parity (below) about migrations, FAMILY parity about registry members × host contract. ·
  exemption-prose consistency (a claim like "always-on"
  checked against the artifact holding the real default). Tier 1 sweeps are MANDATORY where the
  flow kind exists, and BLOCKING. Tier 2 HEURISTIC (name-glob / pattern scoped): storage pairing ·
  telemetry pairing · enum-value readers · ghost gates (undeclared `*_enabled`-shaped reads).
  Tier 2 ships with an explicit FP budget, yield-instrumented (per-sweep summary counts into the
  gate-yield record), and is PROMOTED to blocking only on pilot data — never by default. The
  Tier-1 reference tool is `plugins/tdd-playbook/bin/dataflow_sweeps.py` (config-driven: repos
  tailor the pairing map, they don't fork the scanner).
- **Sweep governance — exemptions are debt, not prose.** A new sweep obeys §13's guard-calibration
  rule first (replayed against its motivating defect before it gates anything). A sweep exemption REUSES the house debt
  shape `{what, owner, expires}` (the registry's R-DEBT contract; an EXPIRED exemption REDs the
  sweep, provable via `--as-of`) — never a new sibling format. An exemption naming a user-facing
  flow FAILS the suite, by §6a's companion rule (one canonical statement — cross-reference, don't
  restate), keyed on the registry's `user_facing` attribute, not a proxy. And the EXCLUDED SHARE is
  audited mechanically — committed per-cycle summary rows (`checked · violations · exempted ·
  unresolvable`) plus a trend check: a growing exemption list under a green sweep means the list
  is doing the tests' work (§4's equivalent-mutant filter-audit rule, same teeth).
- **Migration consumer-parity DoD.** A strangler/migration is DONE when every consumer the OLD
  seam fed is enumerated in the diff and each one is fed by the new seam / retired WITH deletion /
  a dated debt entry — and a seam-parity test pins the enumeration. "New path works" is half a
  definition of done; the other half is what the old path FED. Leftover references to the deleted
  mechanism (a stale exclusion comment, a config key nobody strips) are DEFECTS — they encode a
  false model of the system — swept in §12's exhaustive-negatives pass.
- Edge cases the sweeps must state, never silently skip: external/cross-repo consumers → named AND
  probed (version-echo shape, §6a); dynamic templates → a NAMED dated exemption, never a silent
  skip; values consumed outside the repo → a dated exemption naming the external reader.
Happy path: an agent planning a migration reads this section and produces the old-seam output
enumeration unprompted — the flow table in §0 is where it lands.

## 7. Determinism & flaky tests (zero tolerance)
- Deterministic by construction: no `sleep`/hard waits (use auto-waiting/polling assertions); full test
  isolation (fresh fixtures/contexts); no real clock/`random`/network — inject time, seed, stub HTTP.
- A flaky test is a bug. **Quarantine** it (a marker that runs but doesn't block) and FIX it — never paper
  over with blind retries (`--repeat-each` is for DETECTING flakiness, not hiding it). Retry-into-green
  hides real bugs, the exact failure mode this Playbook exists to prevent.
- **Quarantine entries carry an OWNER and an EXPIRY** (e.g. `@pytest.mark.flaky(expires="2026-08-01")`
  or a dated comment the suite checks): an expired quarantine FAILS the suite. Quarantine-without-
  deadline is how flake graveyards form — the marker is a loan, not a landfill.
- **A quarantine marker is not real until something DESELECTS it.** The marker is a claim about the
  gate's behaviour, and a claim about a gate is unverified until tested (§13). Ship one test that a
  known-quarantined case does not block the gate — otherwise a "quarantined" test is either still
  failing the build or, worse, silently deselected by nothing at all and merely believed to be
  handled. Same shape as the expiry rule: the mechanism, not the intent, is the control.
- **Hunt order-dependence with `pytest-randomly`** (shuffles collection order + seeds randomness each run,
  prints the seed to reproduce). A suite green across seeds is provably order-independent. Combine with
  `--count=N` (`pytest-repeat`) in a BLOCKING `flake-detect` job to surface both repeat- and order-flakiness.
- **An ENVIRONMENT restriction is never a reason to weaken a test.** A sandbox that refuses a loopback
  bind, a write outside the allowed roots, or a repo-local tool cache is an environment fact, not a
  test defect. Name the restriction and use the host's escalation path, or MOVE the artifact rather
  than the assertion (`ruff --no-cache`, pytest `-p no:cacheprovider`, a mypy cache under a temp dir —
  tools that create repo-local caches fail for purely environmental reasons in a sandboxed workspace,
  and sibling worktrees are commonly readable but not writable). Rewriting the assertion to fit the
  sandbox is "never weaken a test" with a new excuse.
- **A network-free suite ENFORCES offline before collection, and a retry loop is a CONFIG failure, not
  slowness.** Libraries that phone home by default (model/asset hubs, telemetry SDKs) need their
  offline switches exported before the run — e.g. `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1` where
  those libraries are present — not stubbed per-test and hoped for. A suite hanging on retries against
  a remote host is diagnosed as environment/configuration; it is never re-labelled "slow" and never
  re-run hoping.
- **A hang must yield a STACK, not a mystery:** a per-test timeout plus `faulthandler` (or the
  stack-dump equivalent) so a wedged run names the frame it wedged in. A long run that dies nameless
  costs a second long run to learn nothing.

## 8. Test shape (don't drift E2E-heavy)
- Use the FASTEST layer that gives real confidence: most coverage in fast unit/integration; reserve slow
  browser/E2E UX journeys for CRITICAL user paths, not every flow. (Pyramid ~70/20/10; trophy weights
  integration. Pick per architecture.) Slow + flaky E2E sprawl is a maintenance tax.
- **Pick the layer deliberately:** pure logic/transform → unit + property (§3); cross-module/IO/DB →
  integration; a real user path through the outermost interface → ONE UX journey (§5); **a prompt /
  tool-definition / model-routing / agent-behavior change → an EVAL (`[→EVAL]`), not a unit test** — a
  fixed input set scored on OUTCOMES, deterministic-oracle checks as the blocking gate, any LLM-judge
  score as a tracked trend line, never a hard gate (§7's zero-flake rule). Don't unit-test what only an
  eval can catch, or E2E what a unit covers. **§5b is that discipline** — including which half of an
  eval may block (agent-path-INDEPENDENT invariants) and which half is k/k-over-N.
- **A subprocess-only contract needs an IN-PROCESS TWIN.** When the only test exercising a behavior
  spawns a fresh process (CLI, hook, worker, `python -m`), keep it — it is the real seam (§1) and
  the only proof the thing executes and imports — and add a twin that calls the same public function
  in-process. Without the twin the behavior is invisible to coverage and unmeasurable by mutation
  (§4's attribution blind spot); with only the twin, nothing proves the executable runs at all. The
  pair is the shape; picking one is choosing which blindness to keep.

## 9. Security & supply chain
- Run `/security-review` (CC) on any diff touching security-relevant surfaces — auth/session, routes/tools
  accepting input, file/secret handling, external webhooks/ingest, deserialization, permissions, SQL — and
  as a final pass before merging a feature. Skip purely cosmetic/test-only diffs (noise).
- **Run it at the PHASE BOUNDARY that introduces the surface, not at merge.** The moment a phase adds
  a network-facing endpoint, an auth/consent decision, or a new subprocess/exec seam, review THAT phase
  — a merge-time pass reviews a design already built on top of the flaw, when the finding is expensive
  and reads as rework. Three of the nine defects in the field report that produced this rule were
  consent/exec-seam defects that a boundary-time review would have caught while the seam was one commit
  old.
- **A boundary is specified by its DENY TABLE, written first.** A sandbox profile, permission
  gate, firewall rule, or authz check is defined by what it REFUSES — write the enumerated
  refusals BEFORE the boundary and assert them against the real enforcement engine (the kernel,
  the live policy evaluator, a real request): red-first applied to the only half of a boundary
  that matters, and §1's assert-the-outcome rule at its highest stakes — the config text you
  generated is the proxy; the enforcer is the fact. **Deny-lists are banned at boundaries**:
  enumerate the few state paths the tool MAY touch (deny-the-root-then-allow), never the
  dangerous ones — the list that named `config.toml` missed `hooks.json` beside it (origin: 9
  real holes across 3 review rounds, several inside fixes for the previous round's holes, each
  under a confident docstring — "I wrote the narrative of the security and treated having
  written it as having done it"). Emission ORDER is policy in a last-match-wins engine — §6's
  T6 shadowing ban at a boundary, visible only to an enforcer probe (an allow emitted after a
  home-dir deny exposed `~/.ssh` through a review-passing profile). **When a strengthened
  boundary turns an artefact-shaped test red** (three per-path greps broke on a strictly-better
  root-deny), the disposal is §1's journaled `test-wrong` unlock class — re-point the test at
  the enforcer; editing the assertion to match the new config text is exactly the move the lock
  exists to stop. **Every security sentence in prose names the test that proves it, or is
  deleted** (§12 — a claim about a defence is a claim). A guard that NARROWS fails safe when its
  inputs are unavailable — degrade to the other guards, never widen. Test the kill switch
  against a RUNNING instance; switches tested static fail live. And a diff that adds or moves a
  gate gets the fresh-context pass (`security-adversary`) with three questions: what reaches the
  guarded operation WITHOUT the gate; does every error path fail closed; and does the guard
  resolve its input exactly as the guarded operation does (§2 check-vs-use).
- Beyond review, WRITE security tests: negative authz (denied → 403/refused), input fuzzing/injection on
  untrusted surfaces, rate-limit. Keep dependency/SAST scanning in CI (supply chain).
- **LLM-app repos: layer adversarial red-teaming on top of the floor** (e.g. [DeepTeam](https://github.com/confident-ai/deepteam) —
  simulated prompt injection, jailbreaks, PII/prompt leakage, excessive agency). Same oracle-split as
  §5a/§7: deterministic guardrail tests are the blocking gate; LLM-judged verdicts are a tracked trend
  line, never a gate.
- **Untrusted endpoints must DEGRADE to 4xx, never 500.** Webhooks often parse the body (decode +
  `json.loads`) BEFORE auth, so malformed/non-UTF-8/oversized input from an unauthenticated caller 500s —
  guard the parse → 400. Confirm injection content (`<script>`, `'; DROP TABLE`) is stored INERTLY (bound
  params; table intact). Wrap parser libs (pypdf/docx) so a corrupted upload is a friendly error, not 500.
- Web a11y: inject axe-core via `page.evaluate` (bypasses the app's `script-src 'self'` CSP); gate
  CRITICAL + SERIOUS only (minor/moderate = noise); skip cleanly if axe can't load so it never flakes.
  Finds real defects — contrast (4.5:1 AA), missing accessible names (`aria-label` on bare selects/icons).

## 10. CI hygiene — gates fire automatically on risky diffs (cost-aware)
- Treat CI failures as a queue to drain as we build, not a weekly batch — after a substantive push,
  `gh run list` / `gh run view --log-failed` and fix now.
- **The inner loop runs AFFECTED tests; the checkpoint runs the suite.** An agent runs tests ~50×
  per task — feedback latency is a first-order quality lever. Give the inner loop a first-class
  "tests affected by my diff" command (the repo's graph/coverage tool, or the cheap floor:
  `pytest <changed test files + tests importing changed modules>`); the FULL suite still gates
  every checkpoint commit (§11) and merge. Selection speeds the loop; it never replaces the net.
- **A full-suite run mid-phase is a checkpoint run out of place** — its cost is its wall-clock
  plus a serialised session (felt, on a developer machine, as heat and a blocked laptop).
  Reaching for the full suite to ask "did I break anything else?" is the victim-sweep question
  (§1): answer it statically, then run the affected slice.
- **Trust gates must fire AUTOMATICALLY on the diffs that can break them** — "remember to run it" is the
  honor-system seam §13 calls gameable (a regression sits green-on-`main` until someone remembers). The
  PRINCIPLE is auto-on-risky-diff; the MECHANISM scales to need:
  - **Solo dev / no clean-room need → a local pre-push hook** (versioned, wired via `core.hooksPath`)
    running the fast gates (lint, targeted tests, security scan, custom gates) and BLOCKING on failure.
    Zero hosted-CI cost/email, path-filtered so doc-only pushes stay instant. Usually the right answer —
    hosted CI earns its keep ONLY for a clean room you lack locally, an OS/Python/backend MATRIX, or
    PR-enforcement on machines you don't control. Don't reach for it by reflex.
  - **Need clean room / matrix / PR-enforcement → path-filtered `push`/`pull_request`**: fast gates on
    push to RISKY paths (backend/SQL/migration/deps/auth/routes/critical modules); slow gates (mutation,
    matrix, full E2E) on `schedule`+`dispatch`, excluded from push via a job `if:`. Strip any `schedule:`
    nobody reads (§4's report-only-is-theater applies to CI too).
- Manual dispatch is the FALLBACK for slow gates, not the primary control for fast ones. After editing a
  workflow, VALIDATE THE YAML locally (`python -c "import yaml; yaml.safe_load(open(...))"`) — an unquoted
  colon in a step `name:` silently invalidates the whole workflow.
- **Determinism comes from pinning, not the vendor:** hosted runner images churn (`ubuntu-latest`
  updates monthly), so a "clean room" on a floating image isn't one. SHA-pin third-party actions
  (`uses: owner/action@<full-sha>`, not `@v4`) and run gate jobs in a PINNED container image. What the
  hosted vendor uniquely provides is THIRD-PARTY INTEGRITY (results the working session can't edit),
  not determinism — keep the two properties straight when weighing CI alternatives.
- **Workflow files ARE risky paths.** A diff touching `.github/workflows/` or the pre-push hook itself
  can silently disable a blocking gate — the quietest possible test-weakening (H2 aimed at the harness
  instead of the test). Path-filter them INTO the fast local gates (a one-line pre-push check that
  flags gate-file edits for review) and review such diffs like auth code.

## 11. Checkpoint commits — the rollback backstop (standing authorization, solo dev)
David is the solo dev and wants automatic checkpoints so there's always a state to roll back to — a
manual policy means he could forget and lose the backstop. So, proactively and without being asked:
- **At every phase boundary and at sprint/feature end → commit + push.** A phase ends GREEN (its tests,
  incl. its slice of the Tripwire, pass), so checkpoints to `main` are never broken WIP and `main`
  stays releasable. Report each checkpoint (commit sha) so the rollback points are visible.
- **Mid-phase**, before a risky refactor, make a LOCAL checkpoint commit; push once green. Don't push
  red WIP to `main`.
- **Never** commit secrets, credentials, or large build artifacts; respect `.gitignore`.
- **Divergence:** before pushing, `git fetch`; if the remote moved (e.g. another machine), rebase or
  merge and resolve conflicts by integrating BOTH sides, re-run the suite, then push. Solo → rare.
- Default to checkpointing on `main` (matches how David works). A per-plan feature branch with
  checkpoints + a merge at sprint end is a fine alternative if `main` must stay pristine — offer it,
  don't impose it.
- Optional belt-and-suspenders: a Stop hook in `settings.json` can make a local WIP checkpoint commit
  when a turn ends with uncommitted changes (forget-proof local backstop; squash later). Offer it; the
  semantic "phase boundary" itself can't be hook-detected, so the habit above is the primary mechanism.
- **Auto-checkpoints must be CONCURRENCY-AWARE** (origin: an auto-checkpoint twice swept a mutation
  runner's transient `pyproject` edit into unrelated wip commits, costing untangle-and-squash work):
  skip the checkpoint when another session or a subagent holds the tree mid-operation; exclude tool
  transients (mutation-tool source copies, generated `mutants/` dirs, lockfile churn); tag wip
  commits with a session id so concurrent sessions stop absorbing each other's work. Better still,
  run slow tree-mutating passes (mutation testing) in an isolated worktree so their transients never
  touch the main tree at all. A REVERT-BASED targeted-mutant script (one that `git checkout`s to
  restore source) gates on `with_snapshot.py preflight` — it refuses over uncommitted work instead
  of checkout-clobbering it (§4).

## 12. Analysis & audit discipline — claims are code
For audit / review / diagnosis / "investigate X" work the deliverable is CLAIMS, and the same
anti-performative rules apply. TDD says no code before a failing test; this says **no claim before
resolving evidence**. (Origin: a self-audit shipped 8 findings, 4 false — every false one was an
unverified NEGATIVE about a file it never read.)
- **§1's trigger question governs evidence too:** before citing, ask what would still be true if
  the claim were false — evidence that survives the defect is a proxy, not proof (one canonical
  statement lives in §1; this is the claims-side application, not a copy).
- **A guard block is a claim you owe three clauses on, and a RECORD — not a narration.** When any
  guard blocks you, state and record: (1) what it objected to; (2) whether that action was
  performed by ANY other route — yes/no, no hedge; (3) what you dropped or changed instead.
  "I re-ran it in pieces" is behaviourally identical to "I split it until something got through",
  and a reader cannot tell them apart from the transcript — which is exactly how the H-class
  write-around hides. Record it with `bin/guard_note.py record` so the answer survives the
  session: the HOOK writes the block count mechanically, you write only the responses, and
  `gate_yield rollup` prints `blocks N · accounted M · UNACCOUNTED N−M` per cycle. Silence
  therefore shows up as an unaccounted count, never as a clean record. A `yes` on clause (2) is
  a FINDING with its own alarm — the whole instrument exists to make that one answer visible.
- **A test that CLAIMS exhaustiveness must be able to fail for the right reason.** When a test's
  name or message says *every / all / no other / exhaustive*, state in ONE line what a violating
  case would look like and how this test would see it. If you cannot write that line, the test
  asserts your INVENTORY, not the property — it proves the right thing happens on the paths you
  listed, which is not the same claim. (Origin: a parity test asserting "no site does X outside the
  one seam" — genuinely exhaustive for deletions, and structurally blind to a path that deletes
  nothing. It could not have failed on the actual bug. Its author, its reviewer and two later
  sessions all read the name as the guarantee.) The same rule governs a guard, scanner or fixture
  claiming coverage in its own docstring — see §13's guard-calibration rule, which is this rule
  applied to verification machinery.
- **Cite-or-refuse, and NEGATIVES need exhaustive search:** "X is never called / unreachable / not
  wired / dead" requires grepping ALL reference/assignment sites and citing the SWEEP. Citing one
  file where X *should* appear proves nothing — the refutation usually lives in a file you didn't
  open (e.g. the "unreachable" toolset that was wired via a profiles file nobody cited).
- **An absence claim is CITABLE — cite it, or it is not a claim.** Write it as
  `(absent: <path>)` and `verify_citations.py` RE-RUNS the check, REFUTING the finding if the
  thing is there. Until v1.42 a positive cited `file:line` and got resolved while a negative
  cited NOTHING, so the gate could not see the strictest claims in the discipline — doctrine
  demanded more evidence for a negative and the mechanism supplied none. The live shape that
  closed it: "this repo has no capability registry", inferred from unrelated missing tooling,
  never checked; it had ten. A directory counts as present — "no `docs/reviews/`" is the same
  claim. **Absence is the one claim it is cheapest to check and easiest to skip**, which is why
  it is the one that ships false.
- **Absence claims about code PARSE the code.** `assert "x" not in source` matches the very
  comment explaining the removal (4-for-4 false REDs in one cycle) and, inverted, stays green on
  a comment while the real call remains — assert on AST nodes (attribute access, calls),
  excluding docstrings. The sweep above says WHERE to look; this is the instrument it must use —
  the general parse-over-grep rule (§1, §6's EXERCISED leg) applied to the absence direction.
- **Evidence you cannot RE-READ is not evidence — a long run's output must outlive the session.**
  Write the COMPLETE log to a FILE (`… > run.log 2>&1`), never a `tail` you keep INSTEAD of the log,
  and record the run/process identifier in continuation state. An agent's context gets summarized;
  a buffer holding a nearly-complete result is simply gone at that boundary, and the claim it would
  have supported becomes unsupportable. (Origin: a near-complete full-suite run lost to a compaction
  boundary, Codex 2026-08-17.) The correct recovery is to retrieve the artifact and re-run only the
  IDENTIFIED failure slices — re-running the whole suite to reconstruct output you already produced
  buys no new information. Corollary for the run itself: once on a quiet, committed tree at the
  merge/deploy gate; named slices during development.
- **Built ≠ wired-in ≠ usable applies to claims too:** trace the wire end-to-end — who SETS the
  value, who CONSUMES it, which config gates it — before claiming wired or unwired. A registration,
  an export, or a comment is not a wire.
- **"Done" about a REMOTE RUNTIME is a claim needing a probe, never a commit sha.** "Fixed"/"working"
  about a VPS/daemon/deployed service requires evidence the DEPLOYED instance changed — a version echo, a
  log line, a health probe — because a pushed commit is not a running one (§6 RUNNING). And when a human
  must run something for the fix to land, that instruction ships in the SAME message as the fix, not a
  message later. (Origin: six "fixed" reports over a box running code from before any of them — "how have
  you fixed things if you didn't give me something to paste into the VPS terminal?")
- **A "now wired" claim is proven at the OUTPUT end, or it is not proven.** Supply-side evidence —
  the key added, the handler registered, the config set — is necessary-not-sufficient: the same
  move as the remote-runtime rule above (a pushed commit is not a running process; a supplied key
  is not a rendered value). The probe is ONE SENTINEL observed in the rendered / delivered /
  persisted artifact. (Origin, §6c T5: a fix "wired" a prompt layer by supplying its key; the
  template had no placeholder, `str.format` dropped it silently, and the claim was verified
  entirely at the supply end.)
- **Subagent/secondhand reports are UNVERIFIED claims.** Spot-check load-bearing ones before
  publishing (a subagent confidently reported a whole subsystem unreachable; one runtime probe
  killed it). When a cheap runtime check exists (`python -c` import/registration probe, hit the
  route), prefer it over static inference. This governs the fresh-context reviewers too — the
  `integration-adversary`'s islands and the `architecture-adversary`'s band-aid findings obey this
  section: no "these are the only two copies" / "no existing helper does this" without the exhaustive
  grep sweep cited, and a hedged finding is demoted to a lead, never worn as a severity.
- **No severity without verification.** A hedged claim cannot carry a severity or a scoreboard row.
  Demote it to an explicit "Unverified leads" section WITH its falsification path ("confirmed/
  refuted by grepping X"). Leads are first-class — the sin is uncertainty wearing a severity badge;
  demotion must cost the badge, so hedging is never the free escape from verification.
- **Report `Claims: N load-bearing · N verified (grep/runtime/cited) · N demoted to leads`** on any
  findings-bearing deliverable (NOT chat turns — a ubiquitous line is wallpaper). Each "verified"
  points at the actual grep/read/probe so the line is auditable against the transcript. Where a
  mechanical seam exists (e.g. a repo's own grounding/claims hooks), the SEAM emits the count — a
  self-reported N/N is narration with a colon in it.
- **A verification result is a CLAIM, and a claim carries its SCOPE — never report a numerator
  without its denominator.** A suite result, a sweep, a check, an audit: each answers the question
  its SELECTOR asked, not the question the reader hears. Selectors are everywhere and nearly always
  legitimate — `-m`/`-k` markers, `--ignore`, `--lf`, `--maxfail`, a path list, `testpaths` in a
  config file (invisible at the call site), a glob, an `os.listdir`, a hardcoded roster, a config
  list of which checks are ARMED. **The narrowing is rarely the error; the silence is.** So a green
  states what it covered — `checked N`, `selected N of M`, `N of M armed`, `scanned N files` — and
  where the count can be independently expected, it is compared against that EXPECTATION rather
  than derived from the same filter it describes: a self-referential `N of N` moves with the
  narrowing and cannot reveal it (the working form: a roster this file cannot drift with, never
  `>= 0`). §4a's vacuity guard is this rule at its degenerate point, scope narrowed to zero;
  everything between zero and complete is the same failure at a smaller magnitude. (Origin:
  Cheliped, 2026-08 — `-m "not flaky"` reported "13754 passed" while the unfiltered suite was RED.
  The quarantine was sanctioned, the exclusion was policy, the gate did what its docs said: every
  decision legitimate, only the report wrong. You cannot catch this class by hunting for mistakes.)
- **Doctrine is recall-at-authoring-time, and authoring is when attention is elsewhere.** "The rule
  already covers it" is necessary but NOT sufficient evidence that a class is handled — the useful
  number is not whether a rule exists but how often a LOADED rule gets walked past. (Origin:
  Cheliped, 2026-08 — three rules in context the whole time, three misses in one sprint, including
  a `grep -c` that counted docstrings, written inside the fix for that very class.) So when a class
  is named, ship the mechanism; the doctrine line exists so the mechanism has something to cite,
  not instead of it.
- **A mechanism cannot detect its own absence.** ruff not running was invisible to ruff; bandit not
  running was invisible to bandit; the gate summary was the thing asserting they had run.
  Everything inside a mechanism's field of view, it found — and every failure OF the mechanism
  layer came from outside it: a human seeing a symptom, a peer's message, or an anomaly that
  didn't fit. So spend in two places, not one: mechanisms for what they can see, and something
  STRUCTURALLY OUTSIDE them for "is this running at all?" That is the trust-boundary case
  generalised past attestation — an independent engine catches you not only because you cannot
  edit it, but because it asks a question your own gates cannot ask about themselves. The part a
  repo CAN do for itself is make each gate assert its own liveness (a check that refuses an
  undeclared shortfall; a selftest that plants an absent tool and asserts the verdict names it).
  (Origin: Cheliped, 2026-08, audited across 27 commits and correcting their own earlier claim —
  a suite opened the Mac App Store in a browser for days with every gate green, and no mechanism
  was ever going to report it.)
- **A LIVENESS plant and a DETECTION plant are different tests, and passing one says nothing about
  the other.** Liveness proves the reporting fires; detection proves the gate is pointed at the
  right things and would catch a real violation. A scanner can be armed, green, and aimed at an
  empty directory — its count stays plausible and non-zero, and every synthetic-fixture test of
  its logic keeps passing. So plant into the REAL configuration's REAL scope, not only into a
  fixture. (Origin: Cheliped, 2026-08 — bandit came up clean on its first armed run only because
  the five HIGH findings had been fixed minutes earlier; armed is not aimed.)

## 13. The learning loop — grade the process, calibrate with planted errors
**The decay principle (why this section exists):** every gate is a DECAYING asset —
verification must co-evolve with the generator, because no fixed check stays effective as
model capability grows (Verification Horizon, arXiv 2606.26300; METR's capability-vs-hacking
trend). The calibration schedule below is not maintenance; it IS the product. Corollaries:
the plant corpus only GROWS (a frozen plant library is itself a static gate); the guards'
hack catalog (`docs/HACK_CATALOG.md`) is refreshed quarterly; a doer-model upgrade requires a
calibration run before its work is trusted (verifier-strength policy, below).
**Decay runs in BOTH directions.** A gate can decay by becoming weaker than the threat (the
direction calibration instruments), OR by becoming more expensive than the risk it retires —
ceremony built for a weaker doer, still charging rent against one that no longer needs it. The
second direction is instrumented by the gate-yield record (`gate_yield.py`, one committed rollup
per calibration cycle from the hooks' own event log — telemetry, never self-report): a gate with
repeated cycles of friction whose every CLASSIFIED block was adjudicated a false positive is a
RETIREMENT CANDIDATE, surfaced by the calibration run itself. **A journaled unlock is not by
itself an adjudication (v1.27).** Releasing a lock at a phase boundary, at feature end, or
because the TEST was wrong all mean the gate was RIGHT; only `unlock --class gate-wrong` says
the friction bought nothing, and only that class feeds retirement. Reading every unlock as a
false positive is not a rounding error — it made the instrument recommend retiring TEST-LOCK,
the strongest anti-gaming defense there is, across four cycles in which no gate was ever wrong.
Cycles predating class recording are UNMEASURED and are never reinterpreted. Retirement is never silent
deletion: demote to warn with an owner and a dated re-check (the flaky-quarantine shape), and
the PLANT CORPUS stays append-only regardless — only human/doer-facing ceremony is retirable.
Absent yield data is UNMEASURED, never zero.
After substantive work, grade the CYCLE (spend → evidence → claims → outcome) against a NAMED
benchmark (e.g. "Claude Code on the same task"), so the system improves instead of re-learning.
The design rule for every check below: make the honest path the cheap path and the dishonest path
visible — never "trust the agent more."
- **Grade from telemetry, never self-narration:** files actually read, greps actually run, tokens
  in/out (net of cache), turn count — tool logs, not the model's account of its own diligence.
- **Score claim-evidence LINKAGE, not volume:** more files read must not raise the grade unless
  claims cite them — count-pumping is §2's marker theater wearing a new badge.
- **Grade WHO CAUGHT IT — the over-confidence signal.** Split each caught defect by discovery path:
  self-caught by a mechanical oracle (best), caught accidentally (a check went red on correct code — a
  weak check, not diligence), caught by the human, or caught by a peer/cross-session review. A defect the
  human caught in output you had already declared "green" is the loudest signal there is — it means the
  oracle ended exactly where your confidence began. Track the ratio, not just the count; a run heavy on
  human-caught / accidental is over-confidence to flag NOW, not at the next retro. (Reference ratio from
  the CIVerd build: 3 self / 3 accidental / 3 human / 1 peer — the 3 human-caught were the most
  consequential and all three were places already called green.)
- **Track escapes BY CLASS, not just by count.** Audits and excavations report each escape against
  the shared taxonomy (the §6 node classes + §6c's T1–T7 edge classes). A class that repeats
  across cycles means its standing mechanism ISN'T REAL YET — the class row, not the instance
  fix, is what the next retro acts on (the origin excavation's twelve escapes collapsed to seven
  classes, five of them from one migration — one mechanism gap, not twelve bugs).
- **Grader independent of doer:** fresh context, refute-framing, a different (cheap) model.
- **Planted-error calibration is the ungameable anchor** — mutation testing for the verification
  loop itself. Two layers, different rot: (a) deterministic planted-false-claim / planted-wasteful-
  cycle FIXTURES in the suite, every CI run — proves the verifier's code works; (b) a small
  SCHEDULED live calibration (weekly, pennies) through the real seam/config — proves it's still
  WIRED and engaged (config drift, aux-model swaps, intent rerouting; built ≠ wired applies to the
  loop itself). A planted error surviving to publication is a BLOCKING failure; the floor only
  rises. A verification loop that never fails a planted error is theater.
- **A guard's claim about ITSELF is an unverified claim — in BOTH directions.** Verification
  machinery (a guard, a scanner, a conftest block, a fixture) states its own coverage in a
  docstring, and that claim is the one nobody re-checks, because checking it feels like
  distrusting the safety net. So every blocking guard ships a two-directional calibration table:
  it must BLOCK what it claims to block **and ALLOW what it claims to allow**. Both halves have
  bitten. Block-direction: a "block privileged commands" guard matched program basenames
  case-sensitively while the only copy on the host lived in a capitalised app bundle — so running
  the suite reconfigured the developer's machine for months, and the guard's docstring, the project
  handoff and three later docstrings all repeated the false claim. Allow-direction: this repo's
  TEST-LOCK guard promised "reads are always fine" and blocked a read, because its write-verb list
  matched a Python loop variable named `ln`. Freeze each real false positive AND each real bypass
  as a dated fixture; narrowing a guard is not amnesty, so the block rows must survive every
  narrowing.
- **Guard calibration — a guard born from a specific defect is not trusted until it has been
  REPLAYED against the motivating artifact.** Red-first proves a test CAN fail; it does not prove
  it fails for the reason it was built — the documented case (Cheliped, 2026-08) is a guard that
  passed the pre-fix shape of the very bug it existed to catch: red-first in ritual, never failed
  for the right reason. The replay is one command — `git show <pre-fix-rev>:<file>` through the
  new guard; a sweep that reports zero offenders on the historical bug is decorative. Then §1's
  regression iron rule applies with the GUARD as the code under test: freeze the defect shape as a
  planted fixture, and cite the pre-fix rev/blob sha in the fixture's docstring — the sha is the
  anchor that keeps repo fixtures, corpus plants, and any engine-side replay recipe pointing at
  the SAME defect instead of three drifting transcriptions. This generalizes the planted-error
  rule from the verification loop to every individual guard; the
  cheapest plant is the bug already in git history.
- **Verifier-strength policy (co-evolution made mechanical):** calibration measures verifier
  recall against the CURRENT doer model; new plants are authored by an adversary on ≥ the
  doer's model tier (`calibration/author_plants.py` — human-reviewed, corpus only grows, each
  plant records its authoring model); a doer-model upgrade REQUIRES a calibration run before
  its work is trusted. Never let the thing generating code outrun the thing checking it.
  **The floor is now MECHANICAL, not a hope:** the judgment/adversary verifiers
  (`claims-verifier`, `tripwire-auditor`, `architecture-adversary`, `integration-adversary`,
  `edge-case-adversary`, `mutation-runner`, `script-adversary`) pin `model: opus` in their frontmatter, so live
  dispatch never silently floats down to a cheap session model — the verifier's strength is
  decoupled from whatever tier the doer happens to run on (audit finding F3: a verifier that
  inherits the session model is the same mind it's checking, on the same tier). The mechanical
  test-runners (`red-first-verifier`, `planted-error-probe`, `ux-probe-calibrator`) stay
  inherit — they run suites, not judgment, so tier barely moves them. Two rules follow: (1) if
  the DOER routinely runs ABOVE the pinned tier, RAISE the pins — a floor below the doer
  violates the policy, and the scoreboard's verifier-vs-adversary column surfaces the lag; (2)
  calibration deliberately runs the verifiers at a CHEAP tier (`haiku`) as a CONSERVATIVE lower
  bound — a plant a weak verifier catches, the pinned production verifier catches too; the pin
  is not tested by calibration (frontmatter is stripped), it is the production guarantee ON TOP.
- **Retro proposes the SMALLEST tweak** (one config knob / prompt line / threshold), human-reviewed.
  A healthy loop's proposals shrink toward noise over time; report-only grades nobody must act on
  are theater (§4's rule, same teeth).

## Markers (register in pytest.ini / equivalent)
`edge` · `ux` · `ux_probe` (non-blocking lane, §5a) · `eval` (§5b blocking lane — agent-path-
INDEPENDENT invariants only) · `eval_judge` (§5b trend lane, NEVER gates) · `tripwire` · `assembly`
(standing wiring suite, §6a) · `flaky` (quarantine). Two eval markers, not one: a single marker
cannot carry two gate semantics, exactly as `ux`/`ux_probe` split. Audit with
`pytest -m <marker>`. Markers aid navigation
and audit; a marker COUNT is never a quality metric — §4 (mutation) is.
