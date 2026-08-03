# Plan — 2026-08-03-dataflow-liveness

Authored 2026-08-03 via plan_block.py. Status lives in the block; `satisfied` is cosmetic to
the engine and `abandoned` is the ratifier's word alone (root-owned store on the box).

## Spec integrity

Full plan: `docs/plans/dataflow-liveness-implementation-plan-2026-08.md` (§B carries the
stated assumptions, the rejected doctrine-only alternative, and the three open questions
David answered on the defaults 2026-08-03). The upstream review doc was never committed;
T1–T7 are grounded inline in the plan header from the Cheliped excavation table.

## Deliverables

D1–D19 per the full plan. The gated slice here is the Tier-1 mechanism (D10/D14): the
stdlib-only `dataflow_sweeps.py` (render-pairing blocking · ghost-gates advisory-by-default
Tier 2 · exemption-prose · exit 0/1/2/3 with vacuous=3) and its planted/paired-control
suite. Doctrine (D1–D6), gate-surface additions (D7–D9), installer/registry/self-sweep
wiring (D11–D13) are pinned by `test_agents.py` v1.24 needles, `test_installer.py`'s
vendored-equality assertion, and the blocking self-sweep in `scripts/civerd_gate.sh` —
all inside the same suites the `suite_cmd` already runs.

## Unenforceable deliverables (prose)

- D15 corpus authoring (proposals require David's `--approve`) and D16 live calibration of
  the changed gate surfaces (~2026-08-10 run) — external state, tracked as registry debt.
- D19 Cheliped pilot dispatch + the CIVerd upgrade-proposal forwarding
  (`docs/recommendations/civerd-dataflow-liveness-upgrades-2026-08.md`) — cross-repo human
  handoffs, each carried by a dated debt entry on `dataflow-sweeps` (expiry 2026-09-15).

## Predicates

The engine evaluates these against the tree it judges — see the weaker-truth semantics in
plan_block.py's header before reading them as stronger promises than they are.

```civerd-plan
version: 1
repo: tdd-playbook
status: active
predicates:
  - file_exists: plugins/tdd-playbook/bin/dataflow_sweeps.py
  - test_passes: plugins/tdd-playbook/tests/test_dataflow_sweeps.py::test_render_pairing
  - test_passes: plugins/tdd-playbook/tests/test_dataflow_sweeps.py::test_exit_codes_and_vacuity
  - test_passes: plugins/tdd-playbook/tests/test_dataflow_sweeps.py::test_exemptions
```
