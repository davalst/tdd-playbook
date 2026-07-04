# Changelog

All notable changes to the TDD Playbook plugin. Versions are the plugin `version` in
`plugins/tdd-playbook/.claude-plugin/plugin.json` (and the matching marketplace entry).

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
