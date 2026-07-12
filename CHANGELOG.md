# Changelog

All notable changes to the TDD Playbook plugin. Versions are the plugin `version` in
`plugins/tdd-playbook/.claude-plugin/plugin.json` (and the matching marketplace entry).

## 1.6.4 — 2026-07-12

**§9 SBOM planted-input bullet** (scoped to repos that ship container images): generate the
SBOM in CI (syft/trivy) and assert known-must-be-present components (base OS entry,
openssl/ca-certificates/libc, the pinned app framework) — a missing known-present component
means the scan layer failed, and an incomplete SBOM is worse than none (false confidence
during CVE response). Extends §10's pinning rule to `FROM` lines (digests, not floating
tags). Doc-only; deliberately NOT a HACK_CATALOG entry — vendor/tooling SBOM omissions are
a supplier-trust failure, not an agent test-gaming behavior, and the catalog's scope stays
agent hacks only.

## 1.6.3 — 2026-07-10

**SKILL description trimmed 1136 → 958 chars** (system-prompt tax, every session, every
surface) by removing ONLY the trailing "named pieces are…" list — a verbatim duplicate of
terms already present earlier in the description. Mechanically verified zero vocabulary
loss, so trigger coverage is unchanged. Live probe checklist for the next few sessions
(planted-trigger spirit): "run the tripwire", "grade that last cycle", "is X dead code?"
must each still fire the skill.

## 1.6.2 — 2026-07-10

**§10 CI integrity/determinism split** (from the "do we need GitHub Actions?" evaluation):
determinism comes from PINNING (SHA-pinned actions, pinned container images — hosted
runner images churn monthly), while the hosted vendor's unique contribution is THIRD-PARTY
INTEGRITY (results the working session can't edit) — weigh CI alternatives on those two
properties separately. And **workflow files ARE risky paths**: a diff touching
`.github/workflows/` or the pre-push hook can silently disable a blocking gate (H2 aimed
at the harness) — path-filter gate-file edits into the fast local gates and review them
like auth code. Three structural pins.

## 1.6.1 — 2026-07-10

**Doctrine hardening from downstream implementation** (cheliped's masker, red-first
tested there): the §4 informational string class exempts LITERAL STRING CONTENT only —
a logic mutant on a display line (True→False, and/or flip, dropped guard) and anything
inside an f-string `{expression}` is CODE and stays real/blocking. Mask the string's
characters, never the line it sits on. Carried in SKILL §4, mutation-runner, and /mutate,
with three structural pins.

## 1.6.0 — 2026-07-10

**The ROI release** — origin: downstream telemetry from a production repo (cheliped) showed
the Playbook's own drift modes: the TDD reminder firing TWICE per message (plugin + vendored
registration, version-skewed for weeks), a mutation roster crept to 44 modules against a
"critical only" doctrine, zero-survivor gates forcing verbatim prose-pin tests, and
auto-checkpoints entangling a mutation runner's transients. Same release adopts the
gate-quality patterns that repo built on its tamper-evident audit chain. Theme: **the honest
path must also be the cheap path — ceremony that outlives its justification is a tax, and
scoped gates need anti-vacuity teeth.**

### Added
- **§4 roster admission rule** — a module enters the mutation roster only with a one-line
  "a survivor here costs ___" justification (irreversible/security/money/data-integrity/
  loop-safety); rendering/presentation modules explicitly OUT; re-audit at feature end.
- **§4 string-mutant role classes** — DATA strings (SQL, keys, hash inputs, persisted
  audit/forensic content) stay zero-survivor; operator-facing DISPLAY prose is an
  informational class, never resolved by verbatim prose-pinning (named anti-pattern).
- **§4 function-scoped two-tier gating** — new/core work gates at zero real survivors on
  named functions; same-file pre-Playbook debt is tracked visibly, never diluted into or
  flattered by a whole-file floor.
- **§4 vacuity guard** — any scoped gate must fail loudly on a scope matching zero
  GENERATED mutants ("refusing a vacuous pass"); denominator from generated mutants, not
  the survivors report (a fully-killed scope looks empty there).
- **§4 audited equivalence ledger** — for equivalents the conservative filter can't
  classify: written proof per entry, exact-substitution matching, a can't-overmatch test
  per entry, text-not-location caution, keep-it-short smell rule.
- **§4 killing-suite visibility** — dedicated-suite tools (mutmut `tests_mutation/`) must
  provably collect the kill tests (shim/star-import + mechanical collision check).
- **§0 numeric ceremony thresholds** — path-criticality beats line count both ways;
  <~20 lines on non-roster/non-security paths + green targeted tests skips the independent
  verifier and full Tripwire; any roster/security diff gets full ceremony.
- **§11 concurrency-aware auto-checkpoints** — skip when a subagent holds the tree, exclude
  tool transients, session-id-tagged wip commits, mutation passes in an isolated worktree.
- **`intent_nudge` anti-tax rework** — runtime O_EXCL sentinel collapses duplicate
  registrations (plugin + vendored) to one reminder on any install topology; per-session
  time damping (default 30 min, `TDD_PLAYBOOK_NUDGE_INTERVAL`, `0`=off); meta-question
  exclusion ("should we…", "what do you think…"); all state fails OPEN.
- **`install_into_repo.py --doctor`** — loud version-skew check across canonical plugin,
  vendored copy (now stamped in `.claude/.tdd-playbook-version`), and the local plugin
  cache; skew exits 1 with the exact fix to run.
- **Calibration: `vacuous-mutation-scope` scenario** — a scoped gate whose scope matches
  nothing must be refused; harness stubs prove both directions deterministically.
- **20 structural doctrine pins** (`test_agents.py::test_v16_doctrine`) so the anti-tax
  rules can't silently regress out of SKILL.md / mutation-runner / /mutate.

### Fixed
- **`build_completion_reminder` macOS path bug** — session-edited-path intersection used
  `abspath` while macOS tempdirs resolve through `/var → /private/var`, silently emptying
  the intersection; the planted "source-only session" test slipped past on macOS. Now
  `realpath` on both sides.
- **TEST-LOCK dead on macOS symlinked project dirs (same class, worse consequence)** —
  `tdd_lock.py` keyed locks off `getcwd()` (always real) against a `CLAUDE_PROJECT_DIR`
  root (possibly symlinked), producing garbage relpath keys the guard could never match:
  the H2 blocking guard silently never fired. `realpath` on both sides in `tdd_lock.py`
  and `test_lock_guard.py`; the planted H2 tests (previously red on macOS) now block.

## 1.5.0 — 2026-07-09

**The integration release** — origin: a full-platform feature-wiring audit of a production
multi-surface agent system (11/11 confirmed findings; whole subsystems built well, tested
well, and never connected). Root cause, now doctrine: *every component shipped tests that wired the component up themselves, and nothing
continuously asserted the production assembly* — plus the meta-bug that health surfaces
reporting only on what RAN make dead features invisible by construction. Two principles run
through everything below: **no wiring claim counts unless proven through the production
composition root**, and **darkness must be an enumerable state, not an invisible one**.
(Roadmap note: WS5 was reserved as v1.5.0 in `docs/plans/implementation-plan-2026-07.md`;
this release was unplanned audit-driven work, so WS5 shifts to v1.6.0.)

### Added
- **Tripwire ACTIVATED leg (§6, /tripwire)** — deliverables now prove BUILT + WIRED +
  **ACTIVATED** + EXERCISED. Activated = on in the shipped default config, or off behind a
  NAMED user-reachable switch; "off with no on-switch" trips RED; a gate depending on another
  disabled gate must report itself dark, never silently no-op. The largest darkness class in
  the origin audit (a whole verify-oracle stack behind a switchless config gate, a delivery
  target shipping as "none") passed the old three-leg check.
- **Production composition root rule (§6, /tripwire)** — the WIRED proof must construct the
  REAL object graph (actual daemon/app factory, actual per-platform agent build), never a
  self-assembling test fixture; reachability checks must be SYMMETRIC (registered → reachable
  AND reachable → registered).
- **§6a Wiring liveness** — the standing (not per-plan) discipline: the **capability registry**
  (`capabilities.json`: surfaces, activation default + on-switch, `wired_by` production site,
  `exercised_by` assembly test, emits → named consumers, integration debt with owner + expiry;
  the registry only GROWS), the **assembly suite** (`@pytest.mark.assembly`, every CI push),
  **liveness canaries** (planted event through the production seam, scheduled) + **staleness
  sweep** (zero runs in N days), and **decide-or-park** (half-built-and-silent is the worst
  state).
- **`bin/capability_registry.py`** — stdlib-only mechanical gate for the registry:
  `validate` (R-DARK dark-with-no-switch · R-WRITE-ONLY emitter-without-consumer · R-DEBT
  expired/ownerless debt fails · R-DUP · R-SCHEMA, BLOCKING), `doctor` (the dark-feature
  inventory: built-but-off + on-switch, write-only emitters, debt aging, missing liveness,
  consumed-but-never-emitted), `init`. Planted-input calibrated in
  `tests/test_capability_registry.py` (21 checks).
- **Integration surface in the plan (§0, /tdd-plan)** — per deliverable: *consumes* (stated,
  never implied) · *emits → named consumer* (write-only loops become owned, dated integration
  debt) · *surface parity* (divergence stated, not discovered) · *reverse sweep* (existing
  features that should adopt the new capability) · *activation* (where's the on-switch).
  Islands are cheapest to catch at plan review.
- **`integration-adversary` agent** — fresh-context, refute-framed connectedness check of a
  plan ("assume it builds an island and prove it"): consumes gaps, write-only emitters,
  surface parity, reverse islands, dark shipping. `/tdd-plan` now closes its loop by
  dispatching it (`Loop closed:` contract, same teeth as /edge /mutate /probe).
- **`/integration-audit` command** — the codified "built but is it running?" sweep: enumerate
  from what SHOULD run (registry, else entry points — a missing registry is Finding #0), hunt
  the four darkness classes (broken wiring · dark-by-default · surface drift ·
  old-blind-to-new/write-only loops), §12 claims discipline with runtime probes and a
  fresh-context `claims-verifier` pass on every trap-category negative, findings ship with
  OWNER + EXPIRY and a decide-or-park verdict, and each finding names the standing mechanism
  (registry entry / assembly test / canary) that makes the next audit unnecessary.

### Changed
- `tests/test_agents.py` — contracts extended: 8 agents, `/tdd-plan` and `/integration-audit`
  join the loop-closing set, `/tripwire` must carry ACTIVATED + the registry gate + the
  composition-root rule.
- SKILL.md frontmatter, README, and the §Markers line (`assembly` added) reflect the new
  pieces.

## 1.4.0 — 2026-07-08

**The co-evolution release** — Workstreams 3–4 of the implementation plan: the answer to
the Verification Horizon problem ("no fixed gate stays effective as model capability
grows") is now mechanical, and §13's "grade from telemetry" has a real seam.

### Added
- **Generative plant corpus (`calibration/corpus/` + `calibration/author_plants.py`)** —
  each cycle an ADVERSARY agent (>= the doer's model tier) authors NEW planted-defect
  scenarios; mechanical validation (schema, edits-apply, oracle regexes) gates acceptance;
  human review moves proposed → approved; `run_calibration` includes approved plants and
  reports corpus size. **The corpus only grows** — plants record their authoring model so
  recall trends stay attributable. Pipeline planted-calibrated in `calibration/test_harness.py`.
- **Decay principle (§13 preamble)** — every gate is a decaying asset; the calibration
  schedule IS the product. `run_calibration` now prints a DECAY WARNING when
  `docs/HACK_CATALOG.md`'s refresh log is >100 days old (the quarterly ritual's mechanical
  reminder).
- **Verifier-strength policy (§13)** — calibration measures against the CURRENT doer model;
  plants authored at >= the doer's tier; a doer-model upgrade requires recalibration before
  its work is trusted.
- **`bin/grade_from_otel.py` + `docs/telemetry.md`** — /grade's telemetry seam: parses
  Claude Code OTel exports (lenient: flat-attribute JSONL AND OTLP/JSON; gen_ai.*
  conventions still unstable so no hard schema binding) into the §13 metrics — turns,
  tokens net of cache, file reads, greps, edits, tests-vs-source touched, cost. No
  recognizable records → exit 1 and /grade must label itself "narration-grade (telemetry
  unavailable)" — an estimate never wears a telemetry badge. `/grade` also now reads the
  TEST-LOCK journal (frequent/suspect unlock reasons cap the grade, H2).
- **Mutation v2 (§4, /mutate, mutation-runner)** — diff-scoped runs on PRs (Stryker
  `--incremental`/`--since`, pitest history, mutmut changed-files; repo-wide score is NOT a
  KPI), ACH-style targeted-mutant mode (mutation as test GENERATOR for the change's
  concern), and context hygiene: mutants stay OUT of the implementing agent's context — a
  visible verifier is a gameable verifier.
- **Doctrine wins** — §3: Schemathesis at the API boundary when a schema exists; §7:
  quarantine entries carry OWNER + EXPIRY (expired quarantine fails the suite); §10:
  affected-tests inner loop with the full suite at checkpoints/merge.

## 1.3.0 — 2026-07-08

**The integrity release** — Workstreams 0–2 of the implementation plan
(`docs/plans/implementation-plan-2026-07.md`): the Playbook now mechanically practices its
own doctrine, and the two top documented agent attack vectors (edit-the-test, over-mock)
are constrained by mechanism, not warning.

### Added
- **`docs/HACK_CATALOG.md`** — the versioned threat model (H1–H6: hardcode outputs ·
  edit/delete tests · over-mock · assertion-free coverage · harness exploitation ·
  architectural fakery), seeded from the 2026 research corpus. Guards cite entry IDs;
  the guard↔entry map makes open gaps diffable; quarterly refresh ritual included.
- **TEST-LOCK (§1, H2/H5)** — `bin/tdd_lock.py` (lock/unlock/status; unlock REFUSED
  without a ≥10-char reason; append-only journal read by `/grade`),
  `test_lock_guard.py` PreToolUse hook (BLOCKS edits to locked tests AND the verifier
  surface — conftest.py, pytest/jest/vitest configs — while a lock is active), and
  `/tdd-lock` + `/tdd-unlock` commands. The strongest validated anti-gaming defense
  (Beck; TDFlow/TDAD) made mechanical.
- **`bin/with_snapshot.py`** — mechanical revert safety (begin/verify/status; catches
  un-reverted plants, stray files, content drift, stray stashes). The four tree-touching
  agents (planted-error-probe, ux-probe-calibrator, mutation-runner, red-first-verifier)
  now REQUIRE worktree isolation or a begin/verify pair — a clean revert is proven, not
  narrated.
- **`overmock_guard.py` (H3, warn)** — flags net-new mocks in test edits (agents over-mock
  36% vs 26% for humans, MSR 2026); pairs with the new §1 rule: every new mock carries a
  one-line justification.
- **`snapshot_guard.py` (H5, block)** — blocks snapshot auto-update invocations
  (`jest -u`, `--update-snapshots`, `--snapshot-update`, env forms) and direct edits to
  `.snap`/`__snapshots__` files: snapshot diffs are human review artifacts.
- **Exit-call detection in the weakening guard (H5)** — `sys.exit`/`os._exit`/
  `process.exit` added to a test or `conftest.py` (verifier surface now in scope) is
  caught: exiting early fakes a passing suite (observed in production RL).
- **Agent calibration harness (`calibration/`)** — a fixture package + 4 planted scenarios
  (never-red test, unwired deliverable, false negative claim, missing boundary tests)
  driven headlessly against the real agents with DETERMINISTIC string oracles (no LLM
  judge); `--dry-run` validates free in CI; results append to `docs/calibration/history.md`.
  The harness itself is planted-calibrated with a stub binary (it can provably fail).
- **`tests/test_agents.py`** — structural contracts for all agents/commands (tool
  sanctions, forced verdict lines, revert-safety blocks, loop-closure lines).
- **LICENSE: Apache-2.0** (was UNLICENSED) — a universal floor needs a real license.

### Changed
- **Integrity hooks now default to BLOCK** (`test_weakening_guard`, `test_lock_guard`,
  `snapshot_guard`); advisory hooks stay warn. Demote per hook
  (`TDD_PLAYBOOK_HOOK_<NAME>=warn|off`) or globally (`TDD_PLAYBOOK_HOOK_MODE=warn`).
  Rationale: the 2025–2026 evidence is unambiguous that warnings do not stop test-gaming.
- **`/edge` `/mutate` `/probe` now close their loops** — each DISPATCHES its adversary
  agent (edge-case-adversary / planted-error-probe / ux-probe-calibrator) and ends with a
  mandatory `Loop closed: yes/no — why` line.
- **`flaky_guard` suppression tightened** — per-category suppressors: a `@pytest.fixture`
  or unrelated `monkeypatch` in the block no longer silences a wall-clock warning; only
  real clock control (freeze_time/fake timers/clock monkeypatch) does.
- **`verify_citations` quote quality** — short (<10 chars) or non-unique quotes are
  flagged `weak-quote` in the summary (gate unchanged; weak evidence is now visible).
- **`install_into_repo.py` reconciles instead of appending** — plugin-namespace hook
  groups are pruned and re-added from the current hooks.json, so removed/renamed hooks no
  longer accumulate downstream; user hooks outside `.claude/hooks/scripts/` untouched.
- **Stop-hook reminder is session-aware** — with a readable transcript it narrows to the
  session's own edits, so a pre-existing test change elsewhere no longer silences a
  source-only session; falls back to whole-tree.

## 1.2.1 — 2026-07-07

Two doctrine additions adapted from the Karpathy-inspired CLAUDE.md guidelines
(Think Before Coding / Surgical Changes) — the two that guard seams the Playbook
didn't: the integrity of the plan the tests are derived from, and the integrity
of the diff against that plan.

### Added
- **SKILL.md §0 — spec integrity** (once per plan, before the deliverables): assumptions
  stated explicitly; competing readings of the request presented, never picked silently;
  a materially simpler approach surfaced if one exists; genuine confusion raised as a
  question at plan review instead of planned around. Rationale: §§1–6 verify what the
  PLAN says — a wrong reading of the request passes every downstream gate. `/tdd-plan`
  now opens with this block.
- **SKILL.md §6 — the reverse check (diff → plan):** the Tripwire proves every deliverable
  is in the diff; the inverse is now also checked — every changed line traces to a plan
  deliverable. Non-tracing lines are scope creep / drive-by refactors / orphaned helpers:
  orphans the change created get removed; unrelated cleanup and dead code get mentioned,
  not done ("dead" is a negative claim — §12's exhaustive-sweep rule applies before acting).

## 1.2.0 — 2026-07-04

New doctrine: **UX probes** — intent-only agent probes that close the gap scripted journeys
structurally can't cover (a §5 journey's author already knows where the button is; a probe's
fresh agent has to find it). Backed by a code-level evaluation of the three candidate engines
(full source clones of alibaba/page-agent, browserbase/stagehand v3, browser-use v0.13, with
file:line citations — see `docs/evaluations/ux-probe-engine-evaluation-2026-07.md`).

### Added
- **SKILL.md §5a — UX probes** (`ux_probe` marker, non-blocking lane): a fresh LLM agent gets
  only the user's INTENT and must accomplish it through the real interface. Load-bearing rule:
  the **oracle split** — agent self-reported success is telemetry, NEVER a gate; blocking
  assertions are deterministic and harness-owned (DB effect, no-5xx from harness network
  capture, console budget); success rate/steps/cost/friction are tracked trend lines (§7
  zero-flake + §8 EVAL rules applied). Engine-agnostic OBSERVE/ACT/EVIDENCE/ORACLE contract
  with a per-interface driver table mirroring §5: web → Stagehand (TS; committed act-cache =
  probabilistic discovery, deterministic replay; UI drift = cache diff in PR) or browser-use
  (Python; `cdp_url` attach, HAR oracle, custom friction action; telemetry/judge off);
  Telegram mini-app → same engines + `Telegram.WebApp` shim (native chrome stubbed into the
  action space); TUI → tmux/PTY loop (screen is already text); Telegram bot → dispatcher/test
  DC; MCP → agent-SDK client. Planted-UX-defect calibration (§13's teeth), scheduled cadence
  with step/token caps, staging-only + injection hygiene, and the a11y "free win" note.
- **`docs/evaluations/ux-probe-engine-evaluation-2026-07.md`** — the engine evaluation
  (comparison matrix + three full code reviews) that grounds the §5a driver choices, including
  why page-agent was rejected for probe duty (SPA-only, synthetic `isTrusted:false` events,
  no replay) and why the harness attaches over CDP rather than driving through Playwright
  (both blessed engines left Playwright for their own CDP stacks).
- **`/probe` command** — the §5a runbook at the same altitude as `/mutate`: guardrails first
  (staging-only, critical journeys only, keys harness-side, caps set), driver selection from
  the §5a table by repo detection, goal-phrased intents sourced from the §0 plan (UI hints
  rejected — they defeat the probe), N≥3 runs, the oracle split applied verbatim, lying-UI
  detection flagged loudly, failed-goal transcripts filed as UX bugs, and first-run-in-repo
  setup (marker registration, testing-addendum note, calibration recommendation).
- **`ux-probe-calibrator` agent** — `planted-error-probe` one layer up: plants ONE
  user-meaningful UX defect the probe's perception channel can see (mislabel / lost
  accessible name / hidden required field / dead-ended CTA / lying success message), runs
  the probe 3×, verdicts `PROBE VERIFIED` (≥2/3 detections) or `BLOCKING GAP` classified as
  PERCEPTION / ORACLE / INTENT with the smallest fix, then reverts to a clean tree. Plant
  types rotate; the lying-success plant is periodically mandatory (it exercises the oracle
  split). Forced-recommendation discipline applies.
- `backups/SKILL.md.2026-07-04.pre-ux-probe.md` — pre-change snapshot (requested backstop).

### Changed
- Skill frontmatter + markers line register `ux_probe`; the Open-upgrade note now points at
  §5a as the mirror image of the pending agent-eval discipline (agents testing UXs vs evals
  testing agents), sharing the same oracle-split rule.

## 1.1.0 — 2026-06-25

Enforcement upgrades mined from a deep-dive of `mattpocock/skills` and `garrytan/gstack`,
filtered through a CTO/QA review (ported only what *raises* the bar; kept the plugin lean and
portable; did not import coverage-% theater or stateful telemetry that belongs in a host app).

### Added
- **`bin/verify_citations.py`** — the mechanical half of the §12 claims discipline. Resolves
  every `file:line` citation in a findings doc and checks quoted snippets against the real
  source (VERIFIED / UNRESOLVED / MISMATCH). Wired into `/claims` and the `claims-verifier`
  agent so "no claim before resolving evidence" is code, not an honor system. Planted-input
  calibrated (`tests/test_verify_citations.py`, 10/10).
- **`/debug` command** — feedback-loop-first debugging: a hard gate against theorizing before
  a reproduction loop exists, ranked loop menu, falsifiable hypotheses with predictions, a
  3-strike STOP→escalate, and a pinned regression test to finish.
- **Tripwire verification-mode taxonomy** (§6 + `/tripwire` + `tripwire-auditor`): for
  multi-deliverable plans, classify each deliverable DIFF-VERIFIABLE / CROSS-REPO /
  EXTERNAL-STATE / UNVERIFIABLE and name the probe; "code that handles a deliverable is not
  the deliverable."
- **E2E/EVAL decision matrix + regression IRON RULE** (§1, §8): pick the test layer
  deliberately; route prompt/tool-definition/agent-behavior changes to an `[→EVAL]` (outcome
  scoring, deterministic-oracle gate, LLM-judge as trend only); regression tests are
  non-negotiable, no approval prompt.
- **Forced-recommendation discipline** on `edge-case-adversary`, `claims-verifier`,
  `tripwire-auditor` — each ends with `Recommendation: <action> because <specific finding>`;
  generic justifications rejected.
- README "which command when" table.

### Changed
- Doctrine audit (mattpocock `writing-great-skills`): condensed §10 (CI hygiene) and the §9
  a11y note so the three new enforcement rules land with the always-on cost staying flat.

## 1.0.0 — 2026-06-24

Initial release: the universal TDD/QA doctrine as an auto-firing skill, 6 scaffolding commands
(`/tdd-plan` `/tripwire` `/edge` `/mutate` `/claims` `/grade`), 6 verification agents, and 4
warn-first enforcement hooks (test-weakening, flaky-pattern, build-intent nudge, Tripwire
reminder). Composes with each repo's own stack-specific testing on top. Public marketplace so
cloud/mobile sandboxes load it without auth.
