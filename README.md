# TDD Playbook — portable quality control for Claude Code and Codex

A universal test-driven-development / QA workflow with one canonical doctrine and thin host
adapters. Claude Code remains the established plugin surface; Codex support begins with the
real-host-calibrated TEST-LOCK prevention slice. Unsupported host capabilities are reported as
unavailable or unmeasured, never rounded up. It ships:

- **The doctrine** — an auto-firing `tdd-playbook` skill: reviewable TDD plan (with an
  integration surface, so features don't ship as islands) → red-first
  behavioral tests → edge-case rigor → property-based + mutation testing → interface-agnostic
  UX journeys → intent-only UX probes (agent-driven, oracle-split, never a gate) → the Tripwire
  wiring check (BUILT + WIRED + ACTIVATED + EXERCISED) → wiring liveness (capability registry,
  assembly suite, darkness doctor) → determinism/flaky policy → security tests →
  a claims discipline for audits → a learning loop. The anti-gaming defense is an OUTCOME
  (mutation score), not a ritual — scoped honestly: the score grades tests WITHIN a seam;
  §1's "test at the seam you don't own" covers what it structurally cannot (SKILL §4).
- **Enforcement hooks** (warn-first) — guard against weakened tests, non-deterministic tests,
  and shipping source with no test.
- **Scaffolding commands** — `/tdd-plan` `/debug` `/tripwire` `/integration-audit` `/edge` `/mutate` `/probe` `/claims` `/grade`.
- **Verification agents** — independent/adversarial checkers: `red-first-verifier`,
  `tripwire-auditor`, `claims-verifier`, `mutation-runner`, `planted-error-probe`,
  `edge-case-adversary`, `integration-adversary`, `ux-probe-calibrator`.

It is the universal **floor**: each repo's own stack-specific testing (a different test
runner, extra gates, security rules) layers on top, discovered from that repo's
`CLAUDE.md`/`AGENTS.md`, a `.claude/skills` testing addendum, or `docs/TESTING*`.

### Which command when
| Situation | Reach for |
|---|---|
| Starting new functionality | `/tdd-plan` — reviewable plan before code |
| Red tests committed, implementing to green | `/tdd-lock` — tests mechanically read-only (unlock is journaled: `/tdd-unlock`) |
| A bug / failing behavior | `/debug` — reproduction loop first, then a pinned regression test |
| Hardening one function/endpoint | `/edge` — walk the edge-case checklist |
| Before merging critical logic | `/mutate` — mutation score, the real anti-gaming metric |
| Can a first-time user actually do it? | `/probe` — intent-only agent probe; deterministic oracles block, agent signals trend |
| Finishing a multi-deliverable plan | `/tripwire` — every deliverable BUILT + WIRED + ACTIVATED + EXERCISED |
| "I built it but never see it running" | `/integration-audit` — sweep for the four darkness classes, adversarially verified |
| An audit / review / diagnosis | `/claims` — cite-or-refuse, mechanically verified citations |
| After a sprint / batch of commits | `/grade` — learning-loop retro from telemetry |

The agents are dispatched for independent second opinions (e.g. `red-first-verifier` to prove
a test fails without the fix; `claims-verifier` for a fresh-context refute pass;
`ux-probe-calibrator` to plant a UX defect and prove the probe catches it).

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
That vendors the skill + commands + agents + hooks + bins (`tdd_lock`, `with_snapshot`,
`grade_from_otel`, `capability_registry`, `verify_citations`) into the repo's `.claude/`, rewriting
`${CLAUDE_PLUGIN_ROOT}` → `$CLAUDE_PROJECT_DIR/.claude`. The installer is **reconciling**: it prunes
every stale Playbook hook group from `.claude/settings.json` and re-adds the current ones — the
three integrity guards (`test_lock_guard`, `snapshot_guard`, `overmock_guard`) plus the advisory
ones (`exitcode_guard`, `exhaustive_claim_guard`, `flaky_guard`, `red_lock`, …) — so a refresh
can't leave dead hook references behind. **Your own non-Playbook hooks are
preserved** (verify that before committing). Open a cloud session and it loads — guaranteed, no
marketplace fetch. Having both the user-scope plugin and the vendored copy is harmless — Claude Code
de-dupes by name.

## Install — Codex (per repo)

Codex configuration is a separate adapter-owned surface. The installer never rewrites user-global
Codex configuration and preserves non-Playbook project hooks:

```bash
python3 scripts/install_into_repo.py --host codex /path/to/your/repo
# Install both independent host packages when a repo is used from both hosts:
python3 scripts/install_into_repo.py --host all /path/to/your/repo
```

The legacy command without `--host` still installs Claude only. Codex project configuration is
trust-gated by the host: review the generated project hook, trust the repository and hook when
prompted, then run `python3 .codex/tdd-playbook/bin/tdd.py doctor`. A source file or static config
match is not proof of activation; the adapter reports prevention only after a real-host planted
block and paired clean control have been recorded for the installed host version.

### Re-vendoring / refreshing a downstream repo
Re-running the installer is idempotent and updates the files, but that alone is **not the whole
refresh** — the current mechanisms only take effect once you also verify and adopt them. After
`install_into_repo.py`:
- **Verify the vendored surface** — `.claude/bin/` has `tdd_lock.py`, `with_snapshot.py`,
  `grade_from_otel.py`, `capability_registry.py`; `.claude/settings.json` carries the PreToolUse
  integrity guards; the vendored `SKILL.md` mentions TEST-LOCK, the decay principle, the
  §1 seam rule, the §6c family parity sweep, and the
  ACTIVATED Tripwire leg.
- **Seed the capability registry** (the installer does *not* do this) — if the repo has no
  `capabilities.json`, run `python3 .claude/bin/capability_registry.py init` and register the repo's
  real entry points; then `validate` before committing. If it already exists, run `validate` + `doctor`.
- **Calibration-staleness check** — read this repo's `docs/calibration/history.md`; if its last
  entry is missing or >14 days old, the gates you just vendored have not been recently live-calibrated
  — flag it (calibration needs a real `claude` binary and is the Playbook maintainer's action, not
  something you run in the downstream repo).

The **complete, copy-pasteable refresh prompt** — including hook-mode adoption, `/tdd-lock` usage,
the four-leg Tripwire, and the registry-as-release-gate — lives in this repo's
[`CLAUDE.md`](./CLAUDE.md) under **"STANDING PROMPT — refreshing downstream repos."** Paste it into
the target repo's session; it is the authoritative revendoring checklist.

## Hook controls
Two tiers. **Integrity hooks default to `block`** — they defend the documented agent attack
vectors (see `docs/HACK_CATALOG.md`; the research is unambiguous that warnings don't stop
test-gaming): `TDD_PLAYBOOK_HOOK_TESTWEAKEN`, `_TESTLOCK`, and `_SNAPSHOTGUARD`. **Advisory hooks
default to `warn`**: `_OVERMOCK`, `_FLAKY`, `_REDLOCK`. Override per hook with `warn` | `block` |
`off`; `TDD_PLAYBOOK_HOOK_MODE` sets the global default (an explicit per-hook env wins over the
global, which wins over the per-hook default); `TDD_PLAYBOOK_NUDGE=off` disables the build-intent
reminder.

## Tests & calibration
Everything mechanical is calibrated with planted inputs (a planted violation that slips past
a check is a failure — §13 applied to ourselves):
```bash
sh scripts/civerd_gate.sh                       # complete AUTHORIZING local/CIVerd gate
sh scripts/civerd_gate.sh affected --base HEAD~1  # NON-AUTHORIZING inner-loop diagnostic
```
The affected command always reports `selected N of M` and falls back to the complete plan for
unknown or assurance-bearing paths. Focused suite runs are diagnostics, never checkpoint or release
evidence. Machine-owned gate, parity, and capability facts are rendered with provenance in
[`docs/reference/current-state.md`](docs/reference/current-state.md).

**Release verification (CIVerd, audit finding F4).** An independent CI engine on a VPS signs a
verdict for each pushed commit; `bin/verify_verdict.py` (stdlib-only, pure-Python Ed25519) checks
it, and `scripts/release_verify.py` creates the release tag only for a fresh signed GREEN verdict
of the release SHA — no bypass flag. See CLAUDE.md for the gate wiring.
The **agents** are calibrated behaviorally on a schedule — planted defects a live agent must
catch (`calibration/`, results in `docs/calibration/`):
```bash
python3 calibration/check_staleness.py             # deterministic: is the scoreboard stale? (F5)
python3 calibration/run_calibration.py --dry-run   # free validation (CI) + R2 pairing invariant
python3 calibration/run_calibration.py             # Claude history.md; weekly live calibration
python3 calibration/run_calibration.py --host codex --model <model>  # separate history-codex.md
```
Since v1.17 each scenario runs 3× (one roll is a coin flip, not a measurement): `PASS` only at
k/k, `AMBER` on a partial catch (nonzero; consecutive AMBER promotes to BLOCKING), and the run
header reports **recall and false-positive rate separately** — every plant class ships with a
paired clean control the verifier must stay quiet on. Since v1.22 both numbers carry 95%
Wilson intervals, every calibratable agent must have a plant (the coverage invariant), and
removing any gate surface — a SKILL section, an agent brief, a command — costs a journaled
`gate-changes.md` entry while adding one stays free: gate removal costs what addition costs.
`check_staleness.py` makes the 14-day cadence mechanical instead of a memory: it fails loudly when
`docs/calibration/history.md`'s latest run is missing or stale. It runs in the release gate and as a
CIVerd `staleness` check, so decay is flagged off-box on the engine's daily timer.

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
