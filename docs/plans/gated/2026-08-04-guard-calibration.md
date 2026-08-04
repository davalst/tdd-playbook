# Plan — 2026-08-04-guard-calibration

Authored 2026-08-04 via plan_block.py. Status lives in the block; `satisfied` is cosmetic to
the engine and `abandoned` is the ratifier's word alone (root-owned store on the box).

## Spec integrity

Adopts the Cheliped guard-calibration proposal (2026-08-04): a guard born from a defect is
replayed against the motivating artifact and the defect shape frozen as a sha-cited planted
fixture. Failure CLASSES adopted, not the self-reported counts (§12). Both plan-review
adversaries dispatched; all 14 findings folded — including two live v1.24 sweep bugs their
probes proved (vacuity accounting, advisory swallowing exemption violations). David's
decisions: stale exemptions fail closed; plant class authored live; CIVerd asks delivered as
a chat prompt he tracks himself (explicit choice, stated).

## Deliverables

G1 §13 guard-calibration rule + §6/§6c reachability cross-refs; G1b brief adoptions
(red-first-verifier / tripwire-auditor / planted-error-probe); G2 §1 single-home additions
(generalized trigger question, state-not-action, silent-failure corollary, seam-fabrication
rule); G2e overmock_guard H9 pattern + create_autospec de-listing; G3 §12 line; G4 sweep
fixes (honest vacuity accounting, kind-partitioned advisory, stale-vs-unmatched exemptions,
per-site <dyn:EXPR> targets, layer_10 reconstruction fixture); G5 H10 corpus plants;
G6 ADOPT bullet + HACK_CATALOG H9/H10; G8 release 1.25.0 with V1.25 registry debt rows.

## Unenforceable deliverables (prose)

- G7 CIVerd prompt: chat-only per David's explicit decision — he tracks the handoff (the
  flow table records it as unowned by this repo; never dressed as covered).
- G5 approvals (`--approve` is David's), the ~2026-08-10 live calibration of the changed
  surfaces, and the Cheliped layer_10 pre-fix sha report-back — external state, carried by
  the V1.25 registry debt rows (2026-08-17) and the existing pilot debt (2026-09-15).

## Predicates

The engine evaluates these against the tree it judges — see the weaker-truth semantics in
plan_block.py's header before reading them as stronger promises than they are.

```civerd-plan
version: 1
repo: tdd-playbook
status: active
predicates:
  - test_passes: plugins/tdd-playbook/tests/test_agents.py::test_v125_doctrine
  - test_passes: plugins/tdd-playbook/tests/test_dataflow_sweeps.py::test_render_vacuity_all_dynamic
  - test_passes: plugins/tdd-playbook/tests/test_dataflow_sweeps.py::test_exemption_kind_survives_advisory
  - test_passes: plugins/tdd-playbook/tests/test_dataflow_sweeps.py::test_stale_vs_unmatched_exemptions
  - test_passes: plugins/tdd-playbook/tests/test_hooks.py::test_overmock
```
