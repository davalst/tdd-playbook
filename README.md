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
- **Enforcement hooks** — four block by default (test weakening, the TEST-LOCK, snapshot
  re-approval, release tags); five more are opt-in. See **Hook controls** below.
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
the four blocking guards (`test_weakening_guard`, `test_lock_guard`, `snapshot_guard`,
`tag_guard`) plus the opt-in ones (`exitcode_guard`, `exhaustive_claim_guard`, `overmock_guard`,
`flaky_guard`, `red_lock`) — so a refresh
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

## Leaving — reset & uninstall
The ability to leave is what makes adopting safe, so both verbs ship with the Playbook and
both are **dry-run by default**.

```bash
python3 <plugin>/bin/tdd.py reset --repo          # prints every path; changes nothing
python3 <plugin>/bin/tdd.py reset --repo --yes    # ...now actually do it
python3 <plugin>/bin/tdd.py uninstall --apply     # the true inverse of the installer
python3 <plugin>/bin/tdd.py doctor --only clone --fix   # e.g. repair a shallow clone
```

Scopes are separate because their blast radii are: `--repo` (this worktree's vendored install
+ local exhaust) · `--shared` (git common-dir state — **shared by every worktree of the repo**,
so it is never implied by `--repo`) · `--machine` (the capture store, all repos) · `--plugin`
(the user-scope plugin cache, stale versions only — the newest installed copy is kept because
deleting the one a live session runs from darkens guards everywhere, silently). `--all` covers
those four. **Evidence is never in scope**: `docs/calibration/` and `calibration/corpus/` need
an explicit `--burn-evidence` plus `--yes` and `--reason`, because they are append-only and
immutable under `check_scoreboard_integrity` — deleting them makes the repo permanently RED
against every baseline, which is worse than losing data.

Two safety properties are asserted by tests rather than promised: the set of paths a dry run
PRINTS equals the set a real run DELETES, and a linked git worktree is never touched (this
repo carries five, one locked and several on unpushed branches).

`uninstall` deletes **by name** in `.claude/commands/`, `.claude/agents/` and `.claude/bin/` —
your own files live in those namespaces — and prunes only Playbook hook groups from
`settings.json`. Two known irreversibilities are reported rather than hidden: install drops
`extraKnownMarketplaces`/`enabledPlugins` and records them nowhere, and `.gitignore` lines it
added cannot be told apart from lines you already had.

## Hook controls
Three tiers, and the tiers are set by **measured yield**, not by how important a guard sounds
(`docs/calibration/gate_yield.md`; §13's decay principle runs in both directions — a gate can
become more expensive than the risk it retires).

**BLOCKING by default** — `TDD_PLAYBOOK_HOOK_TESTWEAKEN`, `_TESTLOCK`, `_SNAPSHOTGUARD`,
`_TAGGUARD`. These defend the documented agent attack vectors (`docs/HACK_CATALOG.md`; the
research is unambiguous that warnings don't stop test-gaming) and the release tag. `testweaken`
has 4 blocks and 0 adjudicated false positives; `testlock` has 16 blocks and **zero** unlocks
classed `gate-wrong`.

**OPT-IN since v1.32.0** — `_EXITCODE`, `_OVERMOCK`, `_EXHAUSTIVE`, `_FLAKY`, `_REDLOCK`.
31 warnings and zero blocks across all recorded history, so they ship off. Nothing was deleted:
turn any of them back on with `TDD_PLAYBOOK_HOOK_<NAME>=warn` and its yield rows resume.

**Break-glass** — `TDD_PLAYBOOK_BREAK_GLASS="<reason>"` demotes **every** blocking gate to warn
for the session. The reason is required (empty does not demote) and is recorded in the yield log
alongside the block it demoted, so a bypass stays visible rather than becoming a clean record.
It can only turn `block` into `warn` — never into silence.

Precedence: per-hook env > global env > per-hook default; break-glass is a clamp applied on top.
`TDD_PLAYBOOK_HOOK_MODE=off` is **refused out loud** — a global off would silence integrity
gates too, which is the kill switch these guards exist to prevent; use break-glass, or
`TDD_PLAYBOOK_HOOK_<NAME>=off` for one specific gate. Any unrecognised value is reported rather
than swallowed. `TDD_PLAYBOOK_NUDGE=off` disables the build-intent reminder.

A standing demotion in a committed `settings.json` env block — including break-glass — is
flagged by `python3 scripts/install_into_repo.py --doctor <repo>`.

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

**Releasing.** Blessed gate green → version bump → **push `main`** → wait for the `gate` check
to go green on that sha → the maintainer tags → push the tag. The push-before-tag order is
load-bearing: CI triggers on push, so tagging first would mean the check has never run on the
commit being tagged.

No release script exists, by design: `test_installer.py::test_no_script_creates_a_release_tag`
parses every TRACKED `.py`/`.sh`/`.yml` — the roster is derived from `git ls-files`, so a new
tool directory or a workflow cannot fall outside it — and fails the gate if one creates or pushes
a tag. `hooks/scripts/tag_guard.py` (BLOCKING) stops a session doing the same at the Bash seam. `bin/verify_verdict.py` (stdlib-only, pure-Python Ed25519) is retained
**unwired** to read historical signed verdicts from the retired CIVerd engine; nothing in the
release path consults it. See CLAUDE.md for the full procedure.
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
`docs/calibration/history.md`'s latest run is missing or stale. It runs inside the blessed gate, so it is
re-run off-box on every push by `.github/workflows/gate.yml` (the CIVerd engine that used to do
this was retired in v1.32.0).

## Layout
```
.claude-plugin/marketplace.json     # this repo is a marketplace ("david-tools")
plugins/tdd-playbook/
  .claude-plugin/plugin.json
  skills/tdd-playbook/SKILL.md       # the doctrine (auto-fires)
  commands/                          # /tdd-plan /tripwire /edge /mutate /claims /grade
  agents/                            # the verification agents
  hooks/                             # enforcement hooks (4 blocking, 5 opt-in)
  tests/                             # planted-input calibration
```
