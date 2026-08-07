# Portable host contracts

Status: evolutionary migration, 2026-08-07.  CIVerd remains the only independent
release-certification authority; every host observation below is local and forgeable.

## Capability outcome matrix

| Capability / route | Claude adapter | Codex adapter | Current assurance | Liveness proof |
|---|---|---|---|---|
| TEST-LOCK structured edit | `PreToolUse` Edit/Write fields | `PreToolUse` `apply_patch` command | host-prevented when a fresh per-host probe exists | planted locked edit + clean source control |
| TEST-LOCK shell | `PreToolUse` Bash command | `PreToolUse` Bash/unified exec command | host-prevented when a fresh per-host probe exists | planted `sed -i` + read-only command control |
| Post-edit integrity guards | PostToolUse | not migrated | unavailable | dated parity work, never inferred from TEST-LOCK |
| Prompt capture/nudge | UserPromptSubmit | not migrated | unavailable | event-specific plant/control required |
| Stop/Tripwire reminder | Stop | not migrated | unavailable | continuation and re-entry plant required |
| Subagent lifecycle | no current Playbook mapping | available host event, not mapped | unavailable | SubagentStart/Stop plant required |
| Release certification | none | none | CIVerd-signed only | fresh signed GREEN exact-SHA verdict |

The exact command/agent/guard inventory and each host's supported/unavailable disposition live in
`host-parity.json`. A family-parity test derives the canonical roster from the real directories and
Claude hook registry, so a newly added asset cannot silently disappear from one host. Codex packaging
does not copy command/agent Markdown until a native discovery consumer exists.

## Codex contract discovery

The implementation is grounded in the official OpenAI Hooks contract, not the Claude wire
shape.  As observed with installed `codex-cli 0.147.0`, Codex discovers trusted repo-local
`.codex/hooks.json`, exposes `PreToolUse` for `apply_patch` and Bash/unified exec, supplies
patches as `tool_input.command`, and treats exit code 2 plus stderr as a pre-execution deny.
The official contract also says some specialized tools may opt out, so hooks remain a
guardrail rather than certification.

Official reference: <https://developers.openai.com/codex/hooks/>.

Project trust and hook-definition trust are separate gates.  A package on disk is not live
until the project layer is trusted and the exact hook definition is reviewed.  The one-shot
`--dangerously-bypass-hook-trust` flag is used only by a probe that already vets its scratch
configuration; it does not replace ordinary user review.

## Installation ownership

- Default `install_into_repo.py` behavior remains Claude-only.
- `--host codex` owns `.codex/tdd-playbook/`, its two groups in `.codex/hooks.json`, and
  `.codex/.tdd-playbook-version`.
- `--host all` invokes both independent reconcilers.
- A reconciler removes only groups whose every command points into its adapter-owned
  namespace.  It preserves unrelated hook groups and top-level host metadata.
- Runtime lock/evidence state never lives in either vendor directory; both consume the
  Git-common-dir authority.

## Shared state and local evidence

Lock creation/extension/clear uses one interprocess transaction file around the complete
read/validate/mutate operation. Ownership is the worktree+session composite: a matching owner can
extend its protected set, while another worktree is refused even if a host reuses a fallback session
label. Unlock compares immutable lock ID, generation and session before removal, and journals only
after that conditional clear succeeds; the full worktree+session owner is checked, and a lock that
disappears after the read is a refusal rather than success. Stale/non-owner/ABA clears cannot delete a replacement or
claim an unlock that did not occur. HEAD/worktree binding is retained for classification: another worktree can enforce the shared
lock, but a changed HEAD is `stale_revision` evidence rather than current red-first proof.

Both live adapters are production producers for the doctor's local event consumer. While TEST-LOCK
is active they append only redacted `blocked`/`allowed` route observations. Doctor requires a block
and its clean control from the same run for every required route and exact SHA before reporting the
manifest's declared assurance. Evidence from another worktree at the same SHA is listed separately
but not promoted. Missing, partial, stale, cross-worktree or wrong-SHA data remains `unmeasured`; the
journal is still locally forgeable and cannot authorize release.

## Known bounded debt

The Codex adapter deliberately contains only the TEST-LOCK vertical slice.  PostToolUse,
prompt, Stop, and subagent behavior stay unavailable until each has its own real-host plant
and clean control.  The current Codex shell route temporarily imports the already-calibrated
Claude shell classifier; extracting that classifier requires a parity suite first so this
migration does not fork or silently weaken the live policy.
