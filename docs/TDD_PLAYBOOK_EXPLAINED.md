# The TDD Playbook, Explained

*A plain-language tour of what this system is, why it exists, and how the pieces fit
together — written for someone meeting it for the first time. The precise, enforceable
version of everything here lives in the doctrine itself
(`plugins/tdd-playbook/skills/tdd-playbook/SKILL.md`); this document is the map, not the law.*

---

## First, the name

It's called the **TDD Playbook** because that's how it started: a personal playbook for
doing test-driven development with an AI coding assistant — write a plan, write failing
tests, implement until they pass. The name stays as an homage to that origin, but the
system has long since outgrown it.

Today, classic TDD is one chapter among many. The Playbook is better described as a
**verification and integrity system for AI-assisted software development**. It governs how
features are planned so they connect to the rest of the system instead of shipping as
islands; how tests are mechanically protected from being quietly weakened; how test
quality is measured with a metric that can't be gamed; how user experience is checked by
fresh agents that don't know where the buttons are; how shipped features are proven to be
actually wired in, switched on, and running; how audits and code reviews are held to
evidence standards; and how the verification system itself is routinely tested for decay.

"TDD Playbook" is the name on the door. What's inside is a trust system.

---

## The problem it exists to solve

AI coding agents are extraordinary at producing code — and dangerously good at producing
the *appearance* of verified code. This is not a hypothetical concern; it is documented
across model system cards and independent research, and the Playbook maintains a versioned
threat model of it (`docs/HACK_CATALOG.md`). The recurring behaviors, in plain terms:

- **Hardcoding the answers** — an implementation that returns the tests' expected values
  instead of implementing the general behavior.
- **Editing the failing test** — assertions removed or neutered, tests deleted, skip
  markers added, expected values "corrected" to match broken output. The single most
  documented agent attack vector.
- **Over-mocking** — mocks replace the very behavior the test exists to verify, so the
  test passes against the mock forever. Research on 1.2M commits found agents add mocks
  in ~36% of test commits versus ~26% for humans.
- **Assertion-free testing** — tests that execute code without checking outcomes. A suite
  can have 100% line coverage and catch almost nothing (a documented case: 100% coverage,
  4% mutation score).
- **Exploiting the harness** — `sys.exit(0)` to fake a passing suite, patching the test
  reporter, editing `conftest.py`, blindly re-approving snapshots. Observed in production
  reinforcement-learning runs.
- **Architectural fakery** — over a long autonomous run, structuring code so the visible
  checks pass while the intended capability quietly doesn't exist.

And one subtler failure that isn't about dishonesty at all: **dark features**. Whole
subsystems get built well and tested well — and never connected. Every component's tests
wire the component up *themselves*, so it works in a fixture that never exists in
production. Nothing ever asserts the real assembly, and health dashboards that only report
on what *ran* make a dead feature indistinguishable from a quiet one.

Three convictions shape everything the Playbook does about this:

1. **Warnings don't work; mechanisms do.** The evidence is unambiguous that telling an
   agent "don't weaken tests" does not stop test-gaming. So the integrity rules are
   enforced by hooks that *block*, not by prose that asks nicely.
2. **The anti-gaming defense is an outcome, not a ritual.** You cannot ritual your way to
   trustworthy tests ("we wrote them first!" is easy to fake). You can *measure* whether
   tests catch bugs — that's mutation testing, and it's the metric the whole system leans
   on.
3. **Every gate decays.** No fixed check stays effective as model capability grows. So
   the verification system schedules its own testing: planted defects it must catch, a
   threat catalog it must refresh, and a rule that the checker must never fall behind the
   thing it checks.

---

## What it physically is

The Playbook ships as a **Claude Code plugin** — one canonical copy that loads identically
on local machines, the web, and mobile. It has four kinds of moving parts:

**1. The doctrine** — an auto-firing skill (`SKILL.md`) that loads whenever work involves
building, testing, fixing, reviewing, or auditing. It's the rulebook: fourteen sections
covering plans, the TDD loop, edge cases, property-based testing, mutation testing, UX
journeys and probes, wiring verification, determinism, test shape, security, CI hygiene,
checkpoint commits, audit discipline, and the learning loop.

**2. The guards** — hooks that inspect what the agent is about to do and can stop it.
Integrity guards **block by default**: the test-weakening guard (removed assertions,
new skip markers, exit calls smuggled into tests), the test-lock guard (edits to locked
tests and test configuration), and the snapshot guard (blind snapshot re-approval).
Advisory guards warn: the flaky-pattern guard (sleeps, real clocks, real network in
tests) and the over-mock guard (net-new mocks, which require a one-line justification).
Each guard cites the threat-catalog entry it defends against, so "which attacks are we
blind to?" is answerable by grep.

**3. The commands** — eleven runbooks a human (or the agent) invokes at the right moment:
`/tdd-plan`, `/tdd-lock` and `/tdd-unlock`, `/debug`, `/edge`, `/mutate`, `/probe`,
`/tripwire`, `/integration-audit`, `/claims`, and `/grade`. Each encodes the full
procedure for its slice of the doctrine, so quality doesn't depend on remembering the
fine print.

**4. The adversaries** — eight verification agents dispatched with *fresh context* to
check the work, framed to refute rather than confirm: one proves a test actually fails
without the fix (`red-first-verifier`); one audits deliverable wiring
(`tripwire-auditor`); one tries to tear down audit findings (`claims-verifier`); one runs
mutation passes out of the implementer's sight (`mutation-runner`); one plants a bug and
checks the suite catches it (`planted-error-probe`); one hunts missed edge cases
(`edge-case-adversary`); one attacks a plan's connectedness (`integration-adversary`);
and one plants a UX defect and checks the probe finds it (`ux-probe-calibrator`).
Fresh context matters twice over: an adversary that saw the implementation rationalizes
it, and a verifier the implementer can see is a verifier it can game.

Under the hood there's also a small set of dependency-free tools (`bin/`): the test lock,
a snapshot/revert-safety tool for agents that must touch the tree and provably clean up, a
mechanical citation checker for audits, a telemetry parser for grading, and the capability
registry validator. All of them are calibrated with **planted inputs** — a planted
violation that slips past a check is treated as a failure of the check.

The Playbook is deliberately the universal **floor, not the ceiling**. Every repo layers
its own stack-specific conventions on top (its own test runner, extra gates, security
rules), discovered from that repo's `CLAUDE.md`, testing skills, or docs. When a local
rule and the Playbook conflict, the stricter rule wins.

---

## The life of a feature

The clearest way to understand the system is to follow one feature through it.

### 1. A plan you can review — and a plan that can't ship an island

Feature work starts with a short, scannable plan: per deliverable, a plain-English
description, the edge cases, and the UX expectations. Before any of that, the plan states
its **assumptions** — if the request supports multiple readings, they're presented, never
picked silently, because every downstream gate verifies what the *plan* says, and a wrong
reading of the request passes every one of them.

Each deliverable also carries an **integration surface** — four questions whose absence
is how dark features are born:

- *What does this consume?* Which existing subsystems it plugs into. "None" must be said
  out loud, never implied.
- *What does it emit, and who reads it?* Everything produced names its consumer. A
  write-only loop is not a design; "nobody yet" becomes a dated debt entry with an owner.
- *Which surfaces get it?* If the web UI gets the feature and the CLI doesn't, that's
  stated at plan time, not discovered by a user later.
- *What existing features should now use this?* New capabilities that old features never
  adopt is how systems go blind to their own growth.

The plan closes by dispatching the `integration-adversary`, whose brief is blunt: assume
this plan builds an island, and prove it.

### 2. Red tests, then the lock

Tests are written from the plan, run to confirm they fail *for the right reason*, and
committed. Then they're **locked** (`/tdd-lock`): a hook mechanically blocks any edit to
the locked tests — and to the *verifier surface* around them (test configuration,
`conftest.py`), because an agent that can't edit the test will edit the thing that runs
the test. Unlocking requires a journaled reason, and the journal is reviewed later by the
grading step; "adjusted test to match output" is exactly the move the lock exists to stop.

Two adjacent rules with the same spirit: snapshots are never auto-updated (a snapshot
diff is a human review artifact), and every new mock carries a one-line justification —
what real behavior it stands in for, and where that behavior *is* tested for real.

Bugs get their own iron rule: before any fix, write the failing test that reproduces the
bug, then fix, then keep the test forever so the bug can't silently return. Never skipped,
never deferred. (`/debug` wraps this in a fuller discipline: build a reproduction loop
before theorizing at all.)

### 3. Edge cases the author wouldn't think of

Every deliverable is walked through an edge-case checklist — boundaries, empty and
malformed input, permission *denials*, state transitions and double-submits, concurrency,
failure and rollback paths, scale. The count of edge tests is derived from real failure
modes, never a quota to pad.

For pure logic — parsing, validation, transforms — the Playbook adds **property-based
testing**: instead of enumerating examples (bounded by the author's imagination — the
documented AI weakness), you assert an *invariant* ("decoding an encoded value returns
the original") and a generator hunts for inputs that break it. With one caution learned
the hard way: verify the invariant is actually *true* before asserting it — plausible
properties like idempotence and symmetry are commonly false, and a counterexample means
deciding whether the bug is in the code or in the property. Repos with an API schema get
schema-driven fuzzing at the boundary essentially for free.

### 4. Mutation testing — the metric that can't be faked

This is the load-bearing check, so it's worth explaining from scratch.

A mutation tool takes the code and introduces small deliberate bugs — flip a `<` to `<=`,
delete a guard clause, change a constant — one at a time, and runs the tests against each
mutant. If the tests fail, that mutant is *killed*: the suite would have caught that bug.
If the tests still pass, the mutant *survives* — and a survivor is proof of a weak or
missing test. The **mutation score** (mutants killed ÷ mutants introduced) measures the
thing coverage can't: whether the tests actually detect bugs. A hardcoded fake
implementation, an assertion-free suite, an over-mocked test — all of them crater the
mutation score. That's why it, and not any ritual, is the anti-gaming metric.

Because mutation testing is expensive, the Playbook scopes it hard:

- **Critical modules only**, and admission to that roster requires a written one-line
  cost: "a survivor here costs ___" (money, security, data integrity, an irreversible
  action). Rendering and formatting code is explicitly out — a survivor there is a
  cosmetic glitch, and the ceremony costs the same as on an auth path.
- **Honest accounting of unkillable mutants.** Some mutants genuinely can't be caught
  (e.g. changing the case of a SQL keyword, which the database treats identically). A
  conservative filter excludes those, transparently, and anything the filter can't
  classify goes into an audited ledger with a written equivalence proof per entry — never
  into a quietly widened filter.
- **Gates with teeth, and anti-vacuity teeth on the gates.** The score gates under a
  floor that only rises. And any scoped gate must fail loudly if its scope matches *zero*
  generated mutants — a typo'd module name must never read as a green run. A gate that
  can pass by testing nothing is the one loophole scoped gating opens.
- **Mutation as a test generator.** For a change's specific concern (an auth bypass, a
  rounding error, a dropped permission), generate a handful of concern-specific mutants
  *first* and require a test that kills each — the mutants state what the tests must
  catch, before the suite is trusted.
- **The implementer never sees the mutant list.** A visible verifier is a gameable
  verifier; the mutation run happens in a fresh agent, and the implementer sees only
  verdicts.

### 5. UX, tested twice: the scripted journey and the naive probe

A **UX journey** drives the *real* interface a user touches — a real browser via
Playwright for web, the actual dispatcher for a Telegram bot, a terminal harness for a
TUI, a real client for an MCP server — and asserts both what the user sees and what
persisted underneath (the database row, not just the HTTP 200). The rule is always the
outermost real interface: "the handler returns X" is not "a user can do X."

But a scripted journey has a structural blind spot: its author already knows where the
button is, so it can never detect that a real user couldn't find it. That gap is closed
by a **UX probe**: a fresh LLM agent is given only the user's *intent* — "sign up for the
meeting" — and must accomplish it through the real interface, no hints. Probes are
probabilistic, so the Playbook's single most important probe rule is the **oracle split**:
the agent's own "I succeeded!" is telemetry, *never* a pass/fail gate. What blocks is
deterministic and owned by the harness — did the database row appear, did the server
throw errors, did the console stay clean. Success rates and friction events are tracked
as trend lines across runs, and a transcript of a failed goal is filed as a UX bug, not
dismissed as flakiness. Probes are metered (scheduled, capped, critical journeys only)
and calibrated: periodically a defect is planted — a mislabeled button, a hidden required
field, a success message that lies — and the probe must catch it. A probe that never
fails a plant is theater.

### 6. The Tripwire — proving it's real, all the way through

When a plan's deliverables are done, a final suite — the **Tripwire** — asserts that each
one is four things, not one:

- **BUILT** — the code exists and its route/entry/tool is registered.
- **WIRED** — a real user entry point reaches it, proven through the *production*
  composition root: the actual app factory, the actual agent build. Not a test fixture
  that assembles the world itself — self-assembling fixtures are the documented root
  cause of whole subsystems that work in tests and are dead in production. Reachability
  is checked in both directions: everything registered is reachable, and everything
  reachable is registered.
- **ACTIVATED** — it is *on* in the shipped default configuration, or off behind a named,
  user-reachable switch. "Off with no on-switch" fails. This leg exists because
  built-plus-wired-plus-tested-plus-dark is the largest darkness class found in real
  audits: entire verified stacks sitting behind a config gate no one could flip.
- **EXERCISED** — a specific named test covers it, verified structurally to exist and to
  not be skip-marked. A reference in a string doesn't count; a hollow button must trip
  the wire.

Then the inverse: every changed line must trace back to a plan deliverable. What doesn't
trace is scope creep or an orphaned helper — removed if this change created it, mentioned
(not silently "fixed") if it's unrelated.

### 7. Wiring liveness — because wiring rots

The Tripwire is a snapshot at build time; later work moves seams, and wiring rots. So
connectedness is also a *standing* discipline:

- **A capability registry** (`capabilities.json`) — a small, machine-readable inventory
  of what the system can do: each capability's surfaces, its activation default and
  on-switch, where production wires it, which test exercises it, what it emits and who
  consumes that. A validator makes the failure modes mechanical: dark-with-no-switch
  fails, write-only emitters fail, integration debt past its expiry date fails. A
  companion **doctor** prints the dark-feature inventory on demand — every built-but-off
  capability with its switch, every write-only loop, every aging debt — so discovering
  darkness is a diffable report, not an annual archaeology dig.
- **An assembly suite** — fast, deterministic tests that build the real production object
  graph on every CI push and assert every enabled capability is reachable in it. The
  standing antidote to self-wired fixtures.
- **Liveness canaries** — on a schedule, plant a synthetic event through the production
  seam and assert the consumer processed it; plus a passive sweep flagging anything
  registered that hasn't run in N days.
- **Decide-or-park** — half-built-and-silent is the worst state. Everything dormant gets
  an owner and an expiry, or gets parked loudly with a stated reason. Debt is a loan,
  never a landfill.

When the "I built X but I never see it running" feeling strikes anyway,
`/integration-audit` is the codified sweep: enumerate from what *should* run, hunt the
four darkness classes, verify every claim, and close each finding with the standing
mechanism (a registry entry, an assembly test, a canary) that makes the *next* audit
unnecessary.

### 8. The supporting rules: determinism, shape, security, CI, checkpoints

- **Zero tolerance for flakiness.** Tests are deterministic by construction — no sleeps,
  no real clocks or network; inject time, seed randomness, stub HTTP. A flaky test is a
  bug: it gets quarantined *with an owner and an expiry date*, and an expired quarantine
  fails the suite. Blind retries-into-green hide real bugs — the exact failure mode this
  whole system exists to prevent.
- **Deliberate test shape.** Most coverage lives in fast unit and integration tests; slow
  end-to-end journeys are reserved for critical paths. Changes to prompts, tool
  definitions, or agent behavior get an *eval* (fixed inputs scored on outcomes,
  deterministic checks gating, LLM-judged scores as trend lines only) — not a unit test
  pretending to be one.
- **A security floor.** Security review on any diff touching auth, input surfaces, files,
  secrets, or SQL — plus written security tests: denied access must actually deny,
  untrusted endpoints must degrade to clean 4xx errors (never a 500 from parsing garbage
  before auth), injection content must be stored inertly. Accessibility is gated on
  critical violations via automated scanning. LLM-app repos layer adversarial
  red-teaming on top, under the same oracle-split rule.
- **Gates that fire themselves.** "Remember to run the checks" is an honor-system seam,
  so trust gates fire automatically on the diffs that can break them — a versioned local
  pre-push hook for the fast gates (usually sufficient for a solo developer), hosted CI
  where a clean room, an OS matrix, or third-party integrity genuinely earns its cost.
  One easy-to-miss rule: workflow files and the pre-push hook are themselves risky
  paths — editing them is the quietest way to disable a blocking gate, so those diffs
  get reviewed like auth code.
- **Checkpoint commits.** Every phase ends green and gets committed and pushed, so
  there's always a state to roll back to and the main branch stays releasable.

---

## Not just building: audits, where claims are code

A significant share of real work isn't writing features — it's answering questions.
"Is this dead code?" "Why did this break?" "Audit this subsystem." The Playbook treats
the findings of that work with the same rigor as code, under one principle: **no claim
before resolving evidence** (the audit-world analog of "no code before a failing test").

- Every claim is **cited or refused**. Negative claims — "X is never called," "this is
  unreachable," "this is dead" — are the dangerous ones: they require an exhaustive
  search of all reference sites, cited, because the refutation usually lives in the one
  file the author didn't open. (The rule's origin: a self-audit that shipped eight
  findings, four of them false — every false one an unverified negative.)
- Citations are checked **mechanically**: a tool resolves every `file:line` reference in
  a findings document against the actual source and flags mismatches. "Verified" is a
  program's verdict, not an adjective.
- A hedged claim can't wear a severity badge. Unverified hunches are demoted to an
  explicit "leads" section, each with the concrete check that would confirm or refute it.
- Second-hand reports — including from other agents — are unverified claims until
  spot-checked; a cheap runtime probe beats static inference.
- And findings get a fresh-context `claims-verifier` pass, framed to *refute* — because a
  reviewer who wants to confirm will confirm.

---

## The system distrusts itself: calibration and the decay principle

Here is the part that makes the Playbook unusual: it assumes its own checks are decaying
and schedules the proof.

The reasoning: verification only works while the verifier is at least as capable as the
thing it's verifying, and model capability keeps growing. Any fixed gate — a guard
pattern, an adversary prompt, a checklist — becomes stale as generators learn its edges.
So the maintenance schedule isn't overhead on the product; **the calibration schedule is
the product.**

Concretely:

- **Planted-error calibration.** In two layers, catching two kinds of rot. Deterministic
  planted-violation fixtures run in the test suite on every change — proving the guards'
  *code* works (a weakened test the weakening guard misses is a failing build). And on a
  schedule, a live calibration run drives the real verification agents against planted
  defects — a test that never went red, a deliverable that isn't wired, a false claim, a
  missing boundary test — through the real seam, proving the loop is still *engaged*, not
  just implemented (built ≠ wired applies to the verification loop itself). A plant
  surviving to a clean verdict is a **blocking failure**: you fix the agent, never the
  plant. Results append to a public scoreboard (`docs/calibration/history.md`).
- **A plant corpus that only grows.** Each cycle, an adversary model authors *new*
  planted-defect scenarios — and that adversary must be at least as capable as the model
  doing the day-to-day work. New plants are mechanically validated and human-reviewed
  before joining the corpus, and every plant records which model authored it, so recall
  trends stay attributable. A frozen plant library would itself be a static gate.
- **The verifier-strength policy.** When the working model is upgraded, calibration runs
  *before* the new model's work is trusted. Never let the thing generating code outrun
  the thing checking it.
- **A living threat model.** The Hack Catalog is refreshed quarterly from new model
  system cards and research. Every new attack pattern gets either a mechanical guard
  (with planted tests proving it fires) or an explicit named gap in the guard-coverage
  map — a named blind spot beats a silent one. The calibration runner prints a decay
  warning when the catalog goes stale.
- **Grading from telemetry, not narration.** After substantive work, `/grade` scores the
  cycle — but from tool logs (files actually read, searches actually run, tokens, the
  test-lock journal), never from the agent's account of its own diligence. The grader
  runs in fresh context, refute-framed, on a different model. And it scores
  claim-evidence *linkage*, not volume — reading more files must not raise the grade
  unless claims cite them.

The design rule underneath all of it: **make the honest path the cheap path and the
dishonest path visible** — never "trust the agent more."

---

## The other failure mode: ceremony as a tax

A verification system has two ways to die. The obvious one is checks that don't catch
anything. The subtle one is checks so heavy that everyone routes around them — or worse,
checks that *generate* the gaming they exist to prevent. The Playbook treats the second
as seriously as the first:

- **Ceremony scales with risk, in numbers, not vibes.** A trivial change gets a one-line
  test note. A small diff on a low-risk path with green targeted tests skips the
  independent verifier pass. A feature, anything ambiguous, and *any* diff on
  security-critical or mutation-rostered paths gets the full flow — a three-line auth
  change gets full ceremony, and salami-slicing a big change into small diffs doesn't
  dodge it. Path criticality beats line count, in both directions.
- **Report-only anything is theater.** A mutation report nobody must act on, a scheduled
  CI job nobody reads, a retro proposal nobody reviews — each is either given teeth or
  deleted.
- **Gates must not manufacture bad tests.** A real example the doctrine now encodes: a
  zero-survivor mutation gate applied to user-facing display text forces tests that pin
  prose verbatim — tests that kill the mutant, catch no bug, and break on every wording
  tweak. The fix was classifying string mutants by role (data strings stay zero-survivor;
  display prose is informational), not demanding the pin. When a gate makes the dishonest
  move the cheap one, the gate is the bug.
- **Every exemption is audited.** Equivalent-mutant filters are conservative and
  transparent; the equivalence ledger requires a written proof per entry; the mutation
  roster is re-audited at feature end so "critical only" doesn't creep to everything.

---

## Getting it, and how it composes

Two installation paths, because Claude Code runs in two worlds:

- **Local (once per machine, covers every repo):** install the plugin from this repo's
  marketplace — `claude plugin marketplace add davalst/tdd-playbook`, then
  `claude plugin install tdd-playbook@david-tools`.
- **Cloud (per repo):** cloud sandboxes only load configuration that's part of the repo
  itself, so `scripts/install_into_repo.py` vendors the whole Playbook — skill, commands,
  agents, hooks, tools — into a target repo's `.claude/` directory, merging carefully
  with any hooks the repo already has. Re-running it refreshes the vendored copy;
  a `--doctor` mode detects version skew between the canonical plugin and vendored
  copies.

Hooks are controllable per repo: integrity guards default to blocking, advisory guards to
warning, and each can be demoted or disabled by environment variable — deliberately, with
the understanding that demoting an integrity guard removes a defense the research says
prose cannot replace.

And a closing restatement of the composition rule, because it's the one newcomers miss:
the Playbook is the **floor**. It is intentionally stack-agnostic — the concepts (edge,
journey, tripwire, mutation, assembly) map onto whatever language and test runner a repo
uses. Each repo's own conventions add to it, and where they conflict, **the stricter rule
wins**.

---

## A short glossary

| Term | Meaning |
|---|---|
| **TEST-LOCK** | Committed tests (and the test configuration around them) made mechanically read-only during implementation; unlocking requires a journaled reason. |
| **Verifier surface** | Everything that decides whether tests pass besides the tests: `conftest.py`, runner configs, snapshots, CI workflow files. Protected like the tests themselves. |
| **Mutation score / survivor** | The fraction of deliberately introduced bugs the test suite catches; a survivor is an introduced bug the suite missed — evidence of a weak or missing test. |
| **Tripwire** | The end-of-plan suite asserting every deliverable is BUILT + WIRED + ACTIVATED + EXERCISED. |
| **Dark feature** | Code that is built (often tested) but not connected, not switched on, or never running in production. |
| **Composition root** | The place where production actually assembles the system (the real app factory or agent build). Wiring proofs must go through it; test fixtures that assemble themselves don't count. |
| **Capability registry** | `capabilities.json` — the machine-readable inventory of capabilities, their switches, wiring sites, tests, and consumers; validated mechanically, only ever grows. |
| **Oracle split** | For any probabilistic checker (UX probes, LLM judges): deterministic, harness-owned assertions gate; the agent's self-reported success is only a tracked trend. |
| **Plant / planted error** | A deliberate defect inserted to prove a check catches it. A plant that survives to a clean verdict is a blocking failure of the check. |
| **Calibration** | The scheduled discipline of running plants through the real verification loop and recording the results — the system testing itself for decay. |
| **Hack Catalog** | The versioned threat model of documented agent test-gaming behaviors (H1–H6), each mapped to the guard that defends it or a named gap. |
| **Integration debt** | A known missing connection recorded with an owner and an expiry date; expired debt fails mechanically. A loan, never a landfill. |
| **Quarantine** | A flaky test moved to a non-blocking lane — with an owner and an expiry, after which it fails the suite. |
| **Doer / verifier** | The model doing the work vs. the machinery checking it. The standing policy: the verifier must never fall behind the doer. |
