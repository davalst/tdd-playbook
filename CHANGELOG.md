# Changelog

All notable changes to the TDD Playbook plugin. Versions are the plugin `version` in
`plugins/tdd-playbook/.claude-plugin/plugin.json` (and the matching marketplace entry).

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
