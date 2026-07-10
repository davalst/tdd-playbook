---
name: tdd-playbook
description: David's universal TDD/QA workflow — use whenever building or changing a feature, fixing a bug, writing or reviewing tests, or planning test coverage, in ANY repo. ALSO fires for ANALYSIS work — audits, code review, diagnosis/root-cause, "investigate/verify/grade X", and self-improvement/grading loops. Covers the reviewable TDD plan, edge-case rigor, property-based + mutation testing, interface-agnostic UX journeys (web/Telegram/TUI/MCP), intent-only UX probes (agent-driven, oracle-split, never a gate), the Tripwire wiring check (BUILT + WIRED + ACTIVATED + EXERCISED), the integration surface + capability registry + wiring-liveness discipline (assembly suite, darkness doctor, integration audits), determinism/flaky policy, security tests, test shape, CI hygiene, the claims discipline (cite-or-refuse, exhaustive negatives, Claims N/N), and the learning loop (process grading + planted-error calibration). The collective handle is "the TDD Playbook"; named pieces are the Tripwire, UX journeys, UX probes, edge-case rigor, the TDD plan, the integration surface, the capability registry, the claims discipline, the learning loop.
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
  - *Emits → named consumer:* everything this produces names WHO reads it. A write-only loop is not
    a design; "nobody yet" becomes an integration-debt entry with an OWNER and an EXPIRY (§7's
    quarantine rules — a loan, not a landfill).
  - *Surface parity:* which interfaces (web/Telegram/TUI/MCP/CLI) get this behavior. Divergence is
    STATED at plan time, not discovered by a user later.
  - *Reverse sweep:* which EXISTING features should now use this new capability. Each hit becomes a
    deliverable in this plan or a dated debt entry — silent deferral is how old features go blind
    to new capabilities.
  Close the plan by dispatching the `integration-adversary` (fresh context, refute-framed: "name
  what this plan should touch but doesn't"); a confirming reviewer rubber-stamps islands.
And ONCE per plan, BEFORE the deliverables — **spec integrity**. Everything downstream (§§1–6)
rigorously verifies what the PLAN says; a wrong reading of the request here passes every gate. So:
- **Assumptions stated explicitly.** If the request supports multiple readings, present them and say
  which one the plan follows — never pick silently.
- **If a materially simpler approach would satisfy the request, say so** and let the review choose —
  don't build the bigger one by default.
- **If something is genuinely unclear, name the confusion as a question for David** — don't plan
  around it. Plan review is the cheap place to be wrong; §4 is the expensive place.
This reviewed plan is the SINGLE upstream spec for the unit/edge/property tests, UX journeys, and the
Tripwire. Default to a one-liner for small work; don't make David review ceremony he didn't ask for.

## 1. The TDD loop
- Author tests from the spec, run RED, then implement to green. **Never weaken/delete a test to pass.**
- Test BEHAVIOR and OUTCOMES, not implementation details or "did the route fire."
- **Built ≠ wired-in ≠ usable.** Verify the user-visible outcome AND reachability (nav/button/CLI/tool)
  AND second-order effects (what list it leaves/joins; consistency across surfaces). Report "route
  exists + unit-tested" separately from "reachable + behaviorally verified." Don't round up.
- **Regression is an IRON RULE — non-negotiable, no approval prompt, highest priority.** On every bug,
  write the failing test that reproduces it FIRST, then fix; pin it so it can't silently come back (e.g.
  the Postgres GROUP BY bug → a test that fails on the old query). A regression = any bug in behavior a
  prior test covered, or in a path once known-good. Never skip it or defer it to "later."
- **TEST-LOCK — make the iron rule mechanical (default for feature/multi-deliverable work):**
  once the plan's tests are authored, RED for the right reason, and COMMITTED, lock them
  (`/tdd-lock`) — the `test_lock_guard` hook then BLOCKS edits to the locked tests AND the
  verifier surface (conftest, test configs) until `/tdd-unlock` with a JOURNALED reason. The
  strongest validated defense against the documented top agent attack vector (editing the
  failing test — HACK_CATALOG H2/H5; prompts don't stop it, mechanisms do). Unlock reasons
  are reviewed by §13's `/grade`; "adjusted test to match output" is the move the lock exists
  to stop. Snapshots are the same rule (H5): agents NEVER auto-update snapshots
  (`-u`/`--update-snapshots` is blocked); a snapshot diff is a human review artifact.
- **Every new mock needs a one-line justification** — what real behavior it stands in for and
  where that behavior IS tested for real. Over-mocking is the most common agent weakening
  (H3: agents add mocks ~36% of test commits vs ~26% for humans); the `overmock` guard reminds.
- Red-first is a helpful habit but it is an HONOR SYSTEM and easy to fake; do not lean on it as the
  guarantee of test quality. The guarantee is §3–§4 (+ the TEST-LOCK above).

## 2. Edge cases — a never-skipped category (`@pytest.mark.edge`)
Run each deliverable methodically through this checklist; write tests for the ones that genuinely apply:
boundaries/limits · empty/null/missing · malformed/invalid/wrong-type input · permission & auth NEGATIVE
cases · state/lifecycle transitions + idempotency/double-submit/re-entry · concurrency/ordering/retries/
duplicates · failure & error paths + rollback/cleanup · scale/large input · second-order/cross-surface.
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
- Run a mutation pass on CRITICAL modules only (auth, money, permissions, lifecycle, core algorithms) —
  not the whole repo (mutant explosion). Tools: `mutmut`/`cosmic-ray` (Python), `Stryker` (JS/TS).
- **Roster admission — anti-creep teeth for "critical only":** a module enters the mutation roster
  ONLY with a one-line justification IN the roster stating "a survivor here costs ___"
  (an irreversible/security/money/data-integrity/loop-safety consequence). Rendering,
  presentation, and formatting modules are explicitly OUT — a survivor there is a cosmetic glitch,
  and the ceremony costs the same as on an audit chain. Re-audit the roster at feature end (origin:
  doctrine said "critical only" and practice still drifted to 44 rostered modules, 5 of them TUI
  renderers — the rule is only real when every entry carries its cost line).
- **Surviving mutants = weak/missing tests.** Triage survivors on critical paths first; add the test that
  kills each. Aim ~80%+ EFFECTIVE mutation score on critical modules.
- **Equivalent mutants are real and UN-KILLABLE — don't chase them (that's performative gaming).** On
  DB/SQL-heavy code, tools (e.g. mutmut, no toggle to disable string mutation) case-mutate SQL keywords +
  dict/`Row` subscript keys, which SQL/SQLite treat identically — these survive forever. Exclude them with
  a CONSERVATIVE automated filter: a survivor whose single changed line differs by CASE ONLY *and* sits in
  a SQL statement or a string-subscript (never excludes a free-text/user-facing string mutation). Gate on
  the EFFECTIVE score = killed / non-equivalent; print raw + effective + the count excluded (transparent).
  (Real example: reconcile went 62.8% raw → 67% → 89.7% effective once equivalents were filtered AND
  real `reconcile()` contract tests were added.)
- **Equivalents the heuristic can't classify go in an audited equivalence ledger**, never into a
  widened filter. One entry per mutant, with (a) a WRITTEN equivalence proof in the entry itself,
  (b) EXACT-substitution matching — the changed line must be exactly the documented before→after,
  so an entry can never swallow a neighboring real mutant — and (c) its own can't-overmatch test
  asserting a nearby DIFFERENT mutation is still kept. Ledger entries match by line TEXT, not
  location: before adding one, check the same line doesn't recur elsewhere in scope. Keep the
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
- **Gate it (close the loop):** a small script parses the tool's machine-readable stats, prints
  `Mutation: N%`, and FAILS under a no-regression FLOOR — BLOCKING in CI. Raise the floor as genuine
  survivors are killed; never lower it. Report-only mutation that nobody must act on is theater.
- **When a critical file mixes eras, scope the gate by FUNCTION (two-tier policy):** new/core work
  gates at ZERO real survivors on its NAMED functions (nothing to lower); pre-Playbook debt paths in
  the same file are named as tracked debt next to the roster entry, with an instruction not to widen
  the gated list until their survivors die. A whole-file floor either flatters the debt or lets the
  debt dilute the new floor — function-scoped gating keeps the strong floor undiluted and the debt
  visible.
- **Every scoped gate needs a VACUITY GUARD:** a scope pattern matching ZERO generated mutants
  (typo'd function name, module dropped from the tool config) must FAIL LOUDLY ("refusing a
  vacuous pass"), never read as green — a gate that can pass by testing nothing is the one gaming
  vector scope-based gating opens. Count the denominator from mutants the tool GENERATED, not from
  its survivors/problems report: a fully-killed scope looks empty there, and a naive guard would
  fail a perfect run.
- **Verify the gate's KILLING SUITE actually collects your kill tests.** Tools with a dedicated
  mutation suite (e.g. mutmut's `tests_mutation/`) never see kill tests written in the normal
  suite — the gate then measures the WRONG suite (red, or worse, vacuously green). Shim/star-import
  the real suites into the killing suite and assert the collected count MECHANICALLY (a star-import
  shadowing silently drops a test; a docstring claiming "collision-checked" is narration).
- **Diff-scoped on PRs; full pass at feature completion.** The full critical-module pass stays at
  feature completion, but substantive changes to critical modules get a DIFF-SCOPED run in review
  (Stryker `--incremental`/`--since`, pitest history files, mutmut on changed files) — a handful of
  survivors surfaced on the changed lines, Google-style. A repo-wide score is NOT a KPI (noise,
  arid code); per-module floors on critical code are the gate.
- **Targeted-mutant mode — mutation as test GENERATOR (Meta ACH pattern):** for the CONCERN of the
  change (auth bypass, money rounding, permission drop, lifecycle skip), generate 3–5 plausible
  concern-specific mutants and require a test that kills each, BEFORE trusting the suite. Inverts
  the workflow: instead of only grading tests after the fact, mutants state what the tests must
  catch. (Validated at 10k-class scale, 73% engineer acceptance.)
- **Mutants stay OUT of the implementing agent's context.** A visible verifier is a gameable
  verifier (METR: models introspect graders when they can see them). Dispatch `mutation-runner`
  fresh; the implementer sees killed/survived VERDICTS, never the mutant list it could special-case.
- Frame the anti-gaming story around mutation score, not the red-first ritual.

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
  - **MCP server** → the probe is an agent-SDK client given only the tool list (converges with the
    pending agent-eval upgrade below).
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
  deliverable's entry is part of this proof — `capability_registry.py validate` must pass; AND
- **EXERCISED** — point at a SPECIFIC `file::test_name`; assert (via `ast`) that the test is DEFINED and
  NOT skip-marked (`@pytest.mark.skip`/`skipif` or a module-level `pytestmark` skip). A string-token grep
  only proves a *reference*; a hollow button or a `@skip`'d test must trip the Tripwire.
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
- Author it red-first, drive to green; report `Tripwire: N/N`. It's a FLOOR, not a target — never add a
  hollow button/stub to go green. Anchor it to the PLAN, not the implementation.
- Scale it: full Tripwire for multi-deliverable plans; for a 1–2 deliverable change the regular behavioral
  tests + a one-line wiring check suffice.

## 6a. Wiring liveness — darkness must be enumerable (standing, not per-plan)
The Tripwire (§6) is a snapshot at build time; wiring ROTS as later work moves seams — §13's decay
principle applies to wiring itself. And the meta-bug that lets rot hide: health surfaces that report
only on what RAN make a dead feature indistinguishable from a quiet one ("healthy, no runs recorded
yet"). Darkness is invisible by construction unless you enumerate from what SHOULD run:
- **The capability registry (`capabilities.json`)** — small, machine-readable, per repo: each
  capability's surfaces, activation default + named on-switch, production wiring site (`wired_by`),
  assembly-level test (`exercised_by`), emitted topics with NAMED consumers, and integration debt
  (owner + expiry, expired debt FAILS). Corpus rules apply: **it only grows**; registering there is
  part of a deliverable's WIRED proof. Mechanical gate:
  `python3 "${CLAUDE_PLUGIN_ROOT}/bin/capability_registry.py" validate` (BLOCKING in the release
  gate) · `… doctor` prints the dark-feature inventory — every built-but-off capability WITH its
  on-switch, write-only emitters, debt aging. The doctor makes the next archaeology audit unnecessary.
- **The ASSEMBLY suite (`@pytest.mark.assembly`)** — the standing antidote to self-wired fixtures:
  build the real production object graph per platform (real daemon factory, real agent build) and
  assert every ENABLED registry capability is reachable in it, both directions (§6's symmetric rule).
  Fast and deterministic → runs every CI push, not on a schedule.
- **Liveness canaries + staleness sweep** — §13's planted-error rule applied to wiring, two layers:
  ACTIVE — on a schedule, plant a synthetic event through the PRODUCTION seam and assert the consumer
  processed it (a subscriber-count probe would have caught the dead-bus orchestrator months early);
  PASSIVE — "registered but zero runs in N days" from telemetry (`liveness.max_quiet_days`). Weekly
  Routine, like the calibration scoreboard: a diffable line, not an annual dig.
- **Half-built-and-silent is the WORST state — decide-or-park.** A dormant package, an unactioned
  review finding, a "we'll wire it later": each gets an owner + expiry (debt entry) or gets parked
  LOUDLY (removed from the registry with a stated reason). Findings without owners rot; the registry
  makes the rot expire instead of accumulate.

## 7. Determinism & flaky tests (zero tolerance)
- Deterministic by construction: no `sleep`/hard waits (use auto-waiting/polling assertions); full test
  isolation (fresh fixtures/contexts); no real clock/`random`/network — inject time, seed, stub HTTP.
- A flaky test is a bug. **Quarantine** it (a marker that runs but doesn't block) and FIX it — never paper
  over with blind retries (`--repeat-each` is for DETECTING flakiness, not hiding it). Retry-into-green
  hides real bugs, the exact failure mode this Playbook exists to prevent.
- **Quarantine entries carry an OWNER and an EXPIRY** (e.g. `@pytest.mark.flaky(expires="2026-08-01")`
  or a dated comment the suite checks): an expired quarantine FAILS the suite. Quarantine-without-
  deadline is how flake graveyards form — the marker is a loan, not a landfill.
- **Hunt order-dependence with `pytest-randomly`** (shuffles collection order + seeds randomness each run,
  prints the seed to reproduce). A suite green across seeds is provably order-independent. Combine with
  `--count=N` (`pytest-repeat`) in a BLOCKING `flake-detect` job to surface both repeat- and order-flakiness.

## 8. Test shape (don't drift E2E-heavy)
- Use the FASTEST layer that gives real confidence: most coverage in fast unit/integration; reserve slow
  browser/E2E UX journeys for CRITICAL user paths, not every flow. (Pyramid ~70/20/10; trophy weights
  integration. Pick per architecture.) Slow + flaky E2E sprawl is a maintenance tax.
- **Pick the layer deliberately:** pure logic/transform → unit + property (§3); cross-module/IO/DB →
  integration; a real user path through the outermost interface → ONE UX journey (§5); **a prompt /
  tool-definition / model-routing / agent-behavior change → an EVAL (`[→EVAL]`), not a unit test** — a
  fixed input set scored on OUTCOMES, deterministic-oracle checks as the blocking gate, any LLM-judge
  score as a tracked trend line, never a hard gate (§7's zero-flake rule). Don't unit-test what only an
  eval can catch, or E2E what a unit covers. (The full agent-eval discipline is the open §-upgrade below.)

## 9. Security & supply chain
- Run `/security-review` (CC) on any diff touching security-relevant surfaces — auth/session, routes/tools
  accepting input, file/secret handling, external webhooks/ingest, deserialization, permissions, SQL — and
  as a final pass before merging a feature. Skip purely cosmetic/test-only diffs (noise).
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
  touch the main tree at all.

## 12. Analysis & audit discipline — claims are code
For audit / review / diagnosis / "investigate X" work the deliverable is CLAIMS, and the same
anti-performative rules apply. TDD says no code before a failing test; this says **no claim before
resolving evidence**. (Origin: a self-audit shipped 8 findings, 4 false — every false one was an
unverified NEGATIVE about a file it never read.)
- **Cite-or-refuse, and NEGATIVES need exhaustive search:** "X is never called / unreachable / not
  wired / dead" requires grepping ALL reference/assignment sites and citing the SWEEP. Citing one
  file where X *should* appear proves nothing — the refutation usually lives in a file you didn't
  open (e.g. the "unreachable" toolset that was wired via a profiles file nobody cited).
- **Built ≠ wired-in ≠ usable applies to claims too:** trace the wire end-to-end — who SETS the
  value, who CONSUMES it, which config gates it — before claiming wired or unwired. A registration,
  an export, or a comment is not a wire.
- **Subagent/secondhand reports are UNVERIFIED claims.** Spot-check load-bearing ones before
  publishing (a subagent confidently reported a whole subsystem unreachable; one runtime probe
  killed it). When a cheap runtime check exists (`python -c` import/registration probe, hit the
  route), prefer it over static inference.
- **No severity without verification.** A hedged claim cannot carry a severity or a scoreboard row.
  Demote it to an explicit "Unverified leads" section WITH its falsification path ("confirmed/
  refuted by grepping X"). Leads are first-class — the sin is uncertainty wearing a severity badge;
  demotion must cost the badge, so hedging is never the free escape from verification.
- **Report `Claims: N load-bearing · N verified (grep/runtime/cited) · N demoted to leads`** on any
  findings-bearing deliverable (NOT chat turns — a ubiquitous line is wallpaper). Each "verified"
  points at the actual grep/read/probe so the line is auditable against the transcript. Where a
  mechanical seam exists (e.g. a repo's own grounding/claims hooks), the SEAM emits the count — a
  self-reported N/N is narration with a colon in it.

## 13. The learning loop — grade the process, calibrate with planted errors
**The decay principle (why this section exists):** every gate is a DECAYING asset —
verification must co-evolve with the generator, because no fixed check stays effective as
model capability grows (Verification Horizon, arXiv 2606.26300; METR's capability-vs-hacking
trend). The calibration schedule below is not maintenance; it IS the product. Corollaries:
the plant corpus only GROWS (a frozen plant library is itself a static gate); the guards'
hack catalog (`docs/HACK_CATALOG.md`) is refreshed quarterly; a doer-model upgrade requires a
calibration run before its work is trusted (verifier-strength policy, below).
After substantive work, grade the CYCLE (spend → evidence → claims → outcome) against a NAMED
benchmark (e.g. "Claude Code on the same task"), so the system improves instead of re-learning.
The design rule for every check below: make the honest path the cheap path and the dishonest path
visible — never "trust the agent more."
- **Grade from telemetry, never self-narration:** files actually read, greps actually run, tokens
  in/out (net of cache), turn count — tool logs, not the model's account of its own diligence.
- **Score claim-evidence LINKAGE, not volume:** more files read must not raise the grade unless
  claims cite them — count-pumping is §2's marker theater wearing a new badge.
- **Grader independent of doer:** fresh context, refute-framing, a different (cheap) model.
- **Planted-error calibration is the ungameable anchor** — mutation testing for the verification
  loop itself. Two layers, different rot: (a) deterministic planted-false-claim / planted-wasteful-
  cycle FIXTURES in the suite, every CI run — proves the verifier's code works; (b) a small
  SCHEDULED live calibration (weekly, pennies) through the real seam/config — proves it's still
  WIRED and engaged (config drift, aux-model swaps, intent rerouting; built ≠ wired applies to the
  loop itself). A planted error surviving to publication is a BLOCKING failure; the floor only
  rises. A verification loop that never fails a planted error is theater.
- **Verifier-strength policy (co-evolution made mechanical):** calibration measures verifier
  recall against the CURRENT doer model; new plants are authored by an adversary on ≥ the
  doer's model tier (`calibration/author_plants.py` — human-reviewed, corpus only grows, each
  plant records its authoring model); a doer-model upgrade REQUIRES a calibration run before
  its work is trusted. Never let the thing generating code outrun the thing checking it.
- **Retro proposes the SMALLEST tweak** (one config knob / prompt line / threshold), human-reviewed.
  A healthy loop's proposals shrink toward noise over time; report-only grades nobody must act on
  are theater (§4's rule, same teeth).

## Open upgrade — circle back with David (don't silently bake in)
The Playbook itself evolves. One upgrade is **pending discussion, not yet doctrine**: generalizing the
"drive the REAL agent in an isolated package and assert on outcomes" harness (one production repo's
local agent-eval rig) into
a first-class **agent-eval** discipline — likely a new §5b. The load-bearing rule to debate: **deterministic-
oracle evals are blocking CI gates; LLM-judge evals are tracked trend lines, never hard gates** (§7 zero-flake
forbids gating on a probabilistic judge; a judge < ~65% human agreement is noise). §5a (UX probes) is the
mirror image — agents testing UXs vs evals testing agents — and already applies that oracle-split rule. **Proactively raise this
with David** when agent/LLM-eval work comes up — it's a standing investment in our deterministic-testing
tension, to be revisited as new agent surfaces ship, not a one-off. (Tracked in the origin repo's
post-build follow-ups list.)

## Markers (register in pytest.ini / equivalent)
`edge` · `ux` · `ux_probe` (non-blocking lane, §5a) · `tripwire` · `assembly` (standing wiring
suite, §6a) · `flaky` (quarantine). Audit with
`pytest -m <marker>`. Markers aid navigation
and audit; a marker COUNT is never a quality metric — §4 (mutation) is.
