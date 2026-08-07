# Plan — 2026-08-07-assurance-pipeline-streamlining

Authored 2026-08-07 via plan_block.py. Status lives in the block; `satisfied` is cosmetic to
the engine and `abandoned` is the ratifier's word alone (root-owned store on the box).

## Spec integrity

The objective is to reduce repeated execution, token-heavy success output, and manually
duplicated current-state facts without reducing the release assurance floor.  The no-argument
`sh scripts/civerd_gate.sh` command remains the complete checkpoint/release gate and CIVerd's
exact suite command.  Affected execution is diagnostic and can never authorize a checkpoint,
release, or signed verdict.

The simpler approach is deliberately chosen: no cache, no parallel suite execution, no generic
workflow engine, and no CIVerd schema change.  One stdlib resolver plans the existing full gate
and an optional safe subset.  Current-state documents are generated only where the underlying
fact is already machine-owned; rationale and history remain human-authored.

The worktree contains user-owned untracked `AGENTS.md`; it remains outside every commit.  The
implementation is evolutionary and each phase has a green pushed rollback point.

## Deliverables

### D1 — one gate plan, private telemetry, compact reporting

Extract the existing dynamic plugin-suite roster and fixed calibration/dataflow/ledger/forms
stages into one stdlib gate-plan resolver consumed by both full and affected execution.  The
shell entrypoint remains the stable public/CIVerd seam, including its planted suite-directory
argument.  Successful stages print one denominator-bearing summary line; failures print a
bounded diagnostic tail and a private full-log pointer.

Run records live under `<git-common-dir>/tdd-playbook/gate-runs/<uuid>/`, with 0700 directories,
0600 files, atomic writes, bounded retention, and allowlisted index metadata.  Retained output
is redacted independently of the evidence journal and is always local/non-authorizing.

Edge cases: non-Git checkout; detached/unborn HEAD; concurrent linked worktrees; log collision;
secret-like output; binary/huge output; subprocess timeout/signal; missing fixed stage; zero-suite
checkout; retention cleanup failure.  The gate fails closed where assurance is involved and
telemetry failure alone never changes enforcement.

### D2 — affected inner-loop mode with a fail-full scope contract

`sh scripts/civerd_gate.sh affected --base <revision>` unions committed-base, staged, unstaged,
untracked, renamed, deleted, and submodule paths.  Only manifest-declared safe mappings may
narrow the shared full plan.  Missing/invalid base, new suite/stage, dirty gate surface,
unclassifiable path, mapping drift, or ambiguity selects the complete plan with an explicit
reason.  Every verdict prints `selected N of M`; affected output is loudly
`NON-AUTHORIZING`.

Edge cases: spaces/Unicode/newlines in paths; `-`-prefixed paths; shallow history; rename across
families; staged deletion plus untracked replacement; manifest symlink; base equal to HEAD;
submodule dirt; dirty file ignored by base diff.

### D3 — resolved host parity and installed-runtime activation

Replace repeated per-asset declarations with per-host/family defaults, exceptions, canonical
capability-debt references, and a human-acknowledged canonical inventory digest.  One resolver
materializes the exact asset-by-host matrix.  A new/deleted asset or stale exception invalidates
the digest until deliberately acknowledged.

Every materialized supported row carries its canonical producer, installed target/native
binding, activation prerequisite, and liveness test.  Scratch installs for both hosts prove
supported assets are reachable, unavailable assets are absent, and undeclared runtime assets do
not survive.  Normal success output is compact; failure output names every missing row.

### D4 — generated current-state reference with provenance

Generate an output-only provenance reference from the gate resolver, parity resolver, and
capability registry.  It records input paths and content hashes and fails `--check` when stale.
README operator commands become the full blessed gate plus explicitly diagnostic affected/focused
modes; direct suite commands no longer masquerade as the repository gate.  Architecture rationale,
plans, calibration history, and review explanations remain authored prose.

### D5 — review packets, stable findings, and mechanical closure

Add an append-only review record separate from `calibration/ledger.md`.  Each finding binds a
stable ID, review SHA/range, severity, evidence, disposition, remediation commit when applicable,
and named closure evidence.  The full gate rejects malformed records, explicit unresolved
blockers, terminal dispositions without required evidence, or review scope/SHA mismatches.
Generated summaries read this record; authored rationale references finding IDs rather than
copying their state.

Review sequencing is: independent paired plan review; implementation; one paired broad diff
review; batched remediation; finding-ID closure.  Closure-only is legal only when remediation
does not touch a composition root.  Changes to the gate/telemetry/parity/reference resolver or
their schemas require one final paired broad review over the changed surface before the final
full gate and CIVerd.

### Integration flows

| flow | producer | named consumer | liveness test |
|---|---|---|---|
| full/affected plan | Git scope + gate resolver | gate executor | live-roster, unknown-path, dirty/untracked and missing-stage plants |
| stage output | executor | compact reporter + private run store | secret redaction, failure-tail and concurrent-run plants |
| host dispositions | canonical assets + adapter policy | installer, parity test, generated reference | scratch installed-runtime activation sweep |
| current-state facts | gate/parity/capability resolvers | generated reference + README link | deterministic render/check drift plant |
| review finding | independent reviewer | review validator + generated disposition | unresolved-blocker and false-closure plants |
| complete no-arg verdict | blessed gate | CIVerd | existing engine suite-command probe remains unchanged |

### Tripwire

| deliverable | BUILT | WIRED | ACTIVATED | EXERCISED |
|---|---|---|---|---|
| shared gate resolver/reporter | resolver and executor | `scripts/civerd_gate.sh` | no-arg full default | planted failed suite + real full-gate run |
| affected scope | Git classifier | blessed entrypoint | explicit diagnostic command | dirty/untracked/rename/unknown path matrix |
| parity resolver | policy expander | installer/tests/reference | blocking exact digest | new asset + install drift plants |
| provenance reference | renderer | full-gate `--check` | generated current-state docs | stale hash/manual edit plant |
| review ledger | validator/packet | full gate + generated summary | risky-plan records | unresolved/false-close/SHA mismatch plants |

## Unenforceable deliverables (prose)

- Human judgment that an architecture or integration finding is correctly rejected.
- Host-agent token accounting when the host does not expose telemetry; absent remains unmeasured.
- CIVerd's independent post-push execution/signature, which remains engine-owned and is required
  later for the release tag rather than fabricated by this implementation run.

## Pre-implementation adversary disposition

| finding | disposition |
|---|---|
| ARCH-1: separate affected/full rosters recreate gate divergence | Incorporated in D1: one resolver owns both plans; affected only narrows it. |
| ARCH-2: full retained logs need privacy/concurrency/retention contracts | Incorporated in D1 with a dedicated protected store and separate redaction. |
| ARCH-3: a manual documentation ownership map becomes another authority | Incorporated in D4 as generated provenance only. |
| ARCH-4: family defaults silently acknowledge new assets | Incorporated in D3 with a deliberate inventory digest and plants. |
| INT-1: `--base` omits staged/unstaged/untracked scope | Incorporated in D2's union and fail-full matrix. |
| INT-2: parity labels do not prove installed activation | Incorporated in D3's installed-runtime contract. |
| INT-3: review ledger would be write-only | Incorporated in D5 with a separate full-gate consumer. |

The architecture review's optional recommendation not to gate review records was rejected in
favor of INT-3, narrowly: only explicitly registered review records and unresolved blockers are
blocking, and the record remains separate from calibration authority.  A process control with no
consumer would repeat the write-only defect this plan is intended to remove.

## Predicates

The engine evaluates these against the tree it judges — see the weaker-truth semantics in
plan_block.py's header before reading them as stronger promises than they are.

```civerd-plan
version: 1
repo: tdd-playbook
status: active
predicates:
  - test_passes: plugins/tdd-playbook/tests/test_gate_runner.py::test_full_plan_discovers_live_roster
  - test_passes: plugins/tdd-playbook/tests/test_gate_runner.py::test_affected_scope_includes_worktree_changes
  - test_passes: plugins/tdd-playbook/tests/test_host_parity.py::test_host_parity_inventory
  - test_passes: plugins/tdd-playbook/tests/test_review_ledger.py::test_unresolved_blocker_refused
  - test_passes: plugins/tdd-playbook/tests/test_reference_docs.py::test_generated_reference_is_current
```
