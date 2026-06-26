# TDD Playbook — a Claude Code plugin

A universal test-driven-development / QA workflow for [Claude Code](https://claude.com/claude-code),
packaged as a plugin so it loads identically on local, web, and mobile. It ships:

- **The doctrine** — an auto-firing `tdd-playbook` skill: reviewable TDD plan → red-first
  behavioral tests → edge-case rigor → property-based + mutation testing → interface-agnostic
  UX journeys → the Tripwire wiring check → determinism/flaky policy → security tests →
  a claims discipline for audits → a learning loop. The anti-gaming defense is an OUTCOME
  (mutation score), not a ritual.
- **Enforcement hooks** (warn-first) — guard against weakened tests, non-deterministic tests,
  and shipping source with no test.
- **Scaffolding commands** — `/tdd-plan` `/debug` `/tripwire` `/edge` `/mutate` `/claims` `/grade`.
- **Verification agents** — independent/adversarial checkers: `red-first-verifier`,
  `tripwire-auditor`, `claims-verifier`, `mutation-runner`, `planted-error-probe`,
  `edge-case-adversary`.

It is the universal **floor**: each repo's own stack-specific testing (a different test
runner, extra gates, security rules) layers on top, discovered from that repo's
`CLAUDE.md`/`AGENTS.md`, a `.claude/skills` testing addendum, or `docs/TESTING*`.

### Which command when
| Situation | Reach for |
|---|---|
| Starting new functionality | `/tdd-plan` — reviewable plan before code |
| A bug / failing behavior | `/debug` — reproduction loop first, then a pinned regression test |
| Hardening one function/endpoint | `/edge` — walk the edge-case checklist |
| Before merging critical logic | `/mutate` — mutation score, the real anti-gaming metric |
| Finishing a multi-deliverable plan | `/tripwire` — every deliverable BUILT + WIRED + EXERCISED |
| An audit / review / diagnosis | `/claims` — cite-or-refuse, mechanically verified citations |
| After a sprint / batch of commits | `/grade` — learning-loop retro from telemetry |

The agents are dispatched for independent second opinions (e.g. `red-first-verifier` to prove
a test fails without the fix; `claims-verifier` for a fresh-context refute pass).

## Install — local (every repo on the machine)
A user-scope install makes the Playbook available in every **local** repo:
```bash
claude plugin marketplace add davalst/tdd-playbook
claude plugin install tdd-playbook@david-tools
```

## Install — cloud (per repo, all surfaces: web / mobile / desktop)
Cloud Claude Code sandboxes only load config that's **part of the repo clone** — they do *not*
reliably install an external marketplace, and never read your `~/.claude`. So the user-scope
install above does **not** reach cloud, and there is **no account-wide cloud sync**: each repo you
want in cloud must carry the Playbook in its own `.claude/`. One command does that (run it from a
clone of THIS repo, pointing at the target repo):
```bash
python3 scripts/install_into_repo.py /path/to/your/repo
cd /path/to/your/repo && git add .claude && git commit -m "chore: vendor TDD Playbook for cloud" && git push
```
That vendors the skill + commands + agents + hooks (and `verify_citations`) into the repo's
`.claude/`, rewriting `${CLAUDE_PLUGIN_ROOT}` → `$CLAUDE_PROJECT_DIR/.claude` and merging the hooks
into `.claude/settings.json` (existing hooks preserved; the unreliable marketplace block removed).
Open a cloud session and it loads — guaranteed, no marketplace fetch. **Re-run after this repo
updates** to refresh a vendored repo (idempotent). Having both the user-scope plugin and the
vendored copy is harmless — Claude Code de-dupes by name.

## Hook controls
Enforcement hooks are **warn-first**. Override per hook with env vars:
`TDD_PLAYBOOK_HOOK_TESTWEAKEN`, `_FLAKY`, `_TRIPWIRE` = `warn` (default) | `block` | `off`;
`TDD_PLAYBOOK_HOOK_MODE` sets the global default; `TDD_PLAYBOOK_NUDGE=off` disables the
build-intent reminder.

## Tests
The hooks are real logic, calibrated with planted inputs (a planted weakening/flaky pattern
that slips past a guard is a failure):
```bash
python3 plugins/tdd-playbook/tests/test_hooks.py
```

## Layout
```
.claude-plugin/marketplace.json     # this repo is a marketplace ("david-tools")
plugins/tdd-playbook/
  .claude-plugin/plugin.json
  skills/tdd-playbook/SKILL.md       # the doctrine (auto-fires)
  commands/                          # /tdd-plan /tripwire /edge /mutate /claims /grade
  agents/                            # the verification agents
  hooks/                             # warn-first enforcement + scripts
  tests/                             # planted-input calibration
```
