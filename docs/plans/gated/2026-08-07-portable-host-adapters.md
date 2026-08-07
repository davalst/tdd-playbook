# Plan — 2026-08-07-portable-host-adapters

Authored 2026-08-07 via plan_block.py. Status lives in the block; `satisfied` is cosmetic to
the engine and `abandoned` is the ratifier's word alone (root-owned store on the box).

## Spec integrity

This is an evolutionary extraction, not a rewrite.  The current Claude plugin remains the
reference implementation until each neutral seam has a planted parity test and a live-host
control.  Codex support means the same policy outcomes and evidence contract; it does not
mean pretending the two hosts expose identical events, JSON, exit semantics, installation
paths, or lifecycle coverage.

CIVerd remains an independent verifier.  This repository continues to send only the paths
and blessed `suite_cmd` in `civerd-integrity.yml`; CIVerd continues to own plants, baselines,
ratification, signing, and the exact-SHA release verdict.  Local host evidence is never
allowed to manufacture certification.

The smallest safe extraction is repository/worktree identity, lock record validation, and
a pure policy decision.  A universal lifecycle framework or linear
`draft -> tested -> certified` state machine was rejected: concurrent worktrees and runs
form an evidence graph, and the current live Claude prevention path is stronger than an
unproven abstraction.

## Deliverables

### D0 — isolate the existing work

The unrelated H15 real-config detection work is gated, committed, and pushed before this
branch starts.  `AGENTS.md` remains user-owned workspace configuration and is neither
deleted nor swept into feature commits.

### D1 — versioned core contract and canonical state

Add a stdlib-only core that resolves canonical repository, Git common-dir, worktree git-dir,
HEAD, and a stable local repository identity.  Runtime state lives under Git metadata, not
tracked `.tdd-playbook/` policy and not a vendor directory.  There is exactly one canonical
active-lock source.  A one-shot importer consumes the legacy `.claude/tdd-lock.json`; there
is no indefinite dual read/write mode.

Lock records bind schema version, canonical repo and worktree identity, HEAD, session/run,
protected relative paths, hashes, and timestamp.  Writes are atomic; journal appends are
serialized.  Reject traversal, symlink escape, root mismatch, malformed/stale records, and
competing ownership.  The pure policy accepts normalized write targets and returns a
versioned allow/block decision.  Shell parsing remains adapter-owned.

### D2 — Claude compatibility migration

Keep Claude event parsing, shell heuristics, exit-code-2 blocking, messages, and hook config
in its adapter.  Route Claude through D1 behind compatibility fixtures, then run planted
allow/block attempts through a real Claude Code process before retiring the legacy seam.
The old prevention path is the rollback switch until parity is proven.

### D3 — evidence and doctor

Normalize local events with schema version, host + host version, adapter version,
repo/worktree/run identity, SHA, event, decision, timestamp, scope, and assurance.  The
closed assurance vocabulary is `unmeasured`, `local_claim`, `host_observed`,
`host_prevented`, `ci_verified`, and `civerd_signed`.  Local files and agent-authored
reports are explicitly forgeable claims; only a fresh signed CIVerd verdict for the exact
SHA authorizes release.  Arguments/prompts are allowlisted and redacted by default.

`doctor` reports declared, observed, stale, degraded, or unavailable capabilities and
version skew.  It never rounds an unprobed host into support.

### D4 — Codex adapter and packaging

Discover the installed/official Codex hook contract first.  Implement a thin adapter for
observed native events, beginning with TEST-LOCK over both structured patch and shell paths.
Installation is a host contract: install, reconcile/prune adapter-owned entries only,
version stamp, doctor, and ignores.  Codex config and Claude config remain separate; a
scratch-repo reinstall must preserve unrelated user entries byte-for-byte/semantically.

### D5 — calibration and parity

Extract calibration invocation behind a runner interface that normalizes prompt delivery,
cwd/worktree, timeout/exit, transcript, model identity, and capability probes.  Record
recall and false positives separately per host; never merge host scores.  Codex starts
`unmeasured` and cannot be advertised as prevented until real-host planted violation plus
paired clean control runs pass.

Every canonical command, agent, and guard policy is either supported, explicitly
unavailable with an assurance downgrade, or owned dated debt.  Expand from TEST-LOCK to
the remaining PreToolUse/PostToolUse/prompt/stop behaviors only after each event is probed.

### Flow and liveness

| flow | producer | named consumer | liveness test |
|---|---|---|---|
| host package/config | host installer | native Claude/Codex runtime | scratch install + real-host probe |
| canonical lock state | `tdd_lock.py`/core | both host guards | main/worktree planted write attempt |
| local event | host adapter | local evidence + doctor | schema/consumer seam test |
| calibration request | runner | per-host history | paired real-host plant/control |
| blessed gate | `scripts/civerd_gate.sh` | CIVerd run | engine suite command probe |
| signed exact-SHA verdict | CIVerd | `release_verify.py` | golden corpus + no-tag-on-red test |

### Edge, security, and concurrency matrix

Cover nested repos, detached HEAD, unborn branches, missing Git, spaces and Unicode, case
aliases, symlinks, traversal, deleted worktrees, stale locks, two simultaneous agents,
lost-journal updates, lock-owner death, disabled/demoted hooks, adapter reinstall/version
skew, offline or missing host CLI, missing CI, stale/cross-worktree evidence, secret-bearing
commands, structured edits, shell redirects, and whole-tree Git restore.  Every planted
block has a paired clean control.

### Sequencing and rollback

Each phase lands green and is pushed separately.  D1 adds neutral APIs without switching
hosts; D2 has a compatibility toggle back to the legacy Claude path; D3 is advisory until
its detector has plants; D4 ships Codex as `unmeasured` until live calibration; D5 can
disable one adapter without touching the core or CIVerd.  No CIVerd schema or signed-field
change is included in the initial migration.  A later release-authorizing checker joins
`plant_targets` only after motivating-artifact replay, planted coverage, and live proof.

### Acceptance criteria

- Claude's existing allow/block behavior remains green and real-host calibrated.
- Main checkout and linked worktrees consume one validated lock authority without
  split-brain, journal loss, or cross-repo leakage.
- Codex structured-patch and shell attempts against a locked test are observed at the real
  host boundary; the result is labelled at its measured assurance, never inferred.
- Both installers are idempotent and preserve non-Playbook host configuration.
- Per-host recall/FP denominators, capability probe date/version/scope, and stale state are
  visible.
- Local evidence cannot authorize a release; a wrong/stale/unsigned/non-exact-SHA CIVerd
  verdict still creates no tag.
- The blessed gate is green, all new mechanical controls have planted inputs and controls,
  and the final Tripwire is BUILT + WIRED + ACTIVATED + EXERCISED.
- Integration- and architecture-adversary findings are each incorporated or explicitly
  dispositioned before completion.

## Unenforceable deliverables (prose)

- Official host-contract research and the dated capability-probe record.
- Live Claude/Codex calibration runs, which require installed authenticated CLIs and budget.
- Any jointly versioned CIVerd schema proposal; it is deliberately outside this initial
  repository migration and requires CIVerd-owned signing/ratification changes.

## Predicates

The engine evaluates these against the tree it judges — see the weaker-truth semantics in
plan_block.py's header before reading them as stronger promises than they are.

```civerd-plan
version: 1
repo: tdd-playbook
status: active
predicates:
  - file_exists: plugins/tdd-playbook/bin/host_contract.py
  - test_passes: plugins/tdd-playbook/tests/test_portable_core.py::test_worktree_state_identity
  - test_passes: plugins/tdd-playbook/tests/test_portable_core.py::test_lock_policy
  - test_passes: plugins/tdd-playbook/tests/test_host_adapters.py::test_adapter_parity
  - test_passes: plugins/tdd-playbook/tests/test_installer.py::test_codex_install_preserves_user_config
```
