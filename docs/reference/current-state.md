# Generated current state

> DO NOT EDIT. This output contains machine-owned facts only; rationale and history stay in authored documents.

## Provenance

- `gate-manifest.json` — `cc0a49b156132f347eead42f80936c317c2197299d5f57ab2bfa54d9840fc878`
- `plugins/tdd-playbook/bin/gate_plan.py` — `e51338c374f95617eef22e22b9b99ec27e1f6b23ae1a8db3103523dfe7848fda`
- `docs/architecture/host-parity-policy.json` — `93de437fe4a5c9caadf5350d0bc0a600b4bd6548b6c809c63a89eceedffdc868`
- `docs/architecture/host-parity.json` — `677f89b9f93c8316387b4fb9cf75a00e136b58594db7dbd6659ff452643641cf`
- `plugins/tdd-playbook/bin/host_parity.py` — `270d33a6dfbcc291be57c80004a2e39f52ea875d7e8b799328df6b69114cfb03`
- `capabilities.json` — `fe1863d8a7b4776dd81afadf4b0376c92a265db96a14353089510764d317c4f1`
- `docs/reviews/2026-08-07-assurance-pipeline-implementation.json` — `5d3649dcb949fa820f87834db896cc69db664e5a82eadd3617cb342fcf03aace`
- `docs/reviews/2026-08-07-assurance-pipeline-plan.json` — `1f723b5524d6746f4da06b565e81f62758796e32f1cfcefc2d9a6baa64474bbd`
- `docs/reviews/2026-08-07-v1.31.0-release-implementation.json` — `77785271eddb17ba1ae19789c01e4b546ac246b52cdd18bd5272eaee9d3911fa`
- `docs/reviews/index.json` — `a4e6e737665e627443c446b7a9d347449fbf4f2566e839d462a3552b082641e5`

## Gate surface

- `sh scripts/civerd_gate.sh` — **AUTHORIZING** complete local gate and CIVerd suite command.
- `sh scripts/civerd_gate.sh affected --base <revision>` — **NON-AUTHORIZING** diagnostic subset; ambiguous scope falls back to full.
- Discovered suites: 26. Fixed stages: 4. Total stages: 30.
- Suite IDs: `test_aaa_suites_via_main`, `test_agents`, `test_capability_registry`, `test_capture`, `test_codex_adapter`, `test_dataflow_sweeps`, `test_ed25519_verify`, `test_gate_runner`, `test_gate_yield`, `test_grade_from_otel`, `test_hooks`, `test_host_adapters`, `test_host_doctor`, `test_host_parity`, `test_host_runner`, `test_installer`, `test_plan_block`, `test_portable_core`, `test_red_lock_portable`, `test_reference_docs`, `test_release_verify`, `test_review_ledger`, `test_tdd_lock`, `test_verify_citations`, `test_verify_verdict`, `test_with_snapshot`
- Fixed IDs: `calibration`, `dataflow`, `ledger`, `plant-forms`
- Acknowledged roster digest: `aa77e0a6e7beaafe6b96daf23ae9d7029681c15745223cbd77b4a2b2a6e70062`
- Acknowledged execution-manifest digest: `e44abf2e54655f461df615f79d8fd1baed615db1cdf2be5416f0a7b8b333f3e4`

## Host parity

- Canonical assets: 32. Exact host dispositions: 64.
- Claude: 32 supported, 0 unavailable, 0 debt.
- Codex: 1 supported, 31 unavailable, 0 debt.
- Acknowledged inventory digest: `20556de9925685d7d9061158d3d9f4b722116a7d5e438ba3fc53ebc657a96861`

## Capability registry

- Registered capabilities: 21. Owned dated integration-debt entries: 47.
- `integrity-guards/unnamed` — owner `david`, expires `2026-09-15`
- `test-lock/claude-test-lock-refresh` — owner `david`, expires `2026-08-17`
- `test-lock/codex-guard-family-parity` — owner `david`, expires `2026-09-30`
- `test-lock/shell-classifier-adapter-boundary` — owner `david`, expires `2026-09-30`
- `test-lock/codex-command-agent-discovery` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-08-17`
- `calibration-loop/unnamed` — owner `david`, expires `2026-08-17`
- `calibration-loop/unnamed` — owner `david`, expires `2026-11-01`
- `calibration-loop/unnamed` — owner `david`, expires `2026-08-17`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-15`
- `calibration-loop/unnamed` — owner `david`, expires `2026-08-17`
- `calibration-loop/unnamed` — owner `david`, expires `2026-08-17`
- `calibration-loop/unnamed` — owner `david`, expires `2026-08-17`
- `calibration-loop/unnamed` — owner `david`, expires `2026-08-17`
- `calibration-loop/unnamed` — owner `david`, expires `2026-08-17`
- `calibration-loop/unnamed` — owner `david`, expires `2026-08-17`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-15`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-15`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-15`
- `scoreboard-integrity/unnamed` — owner `david`, expires `2026-09-15`
- `scoreboard-integrity/unnamed` — owner `david`, expires `2026-11-15`
- `gate-yield/unnamed` — owner `david`, expires `2026-10-15`
- `gate-yield/unnamed` — owner `david`, expires `2026-11-15`
- `gate-yield/unnamed` — owner `david`, expires `2026-11-15`
- `civerd-release-gate/unnamed` — owner `david`, expires `2026-09-15`
- `civerd-release-gate/unnamed` — owner `david`, expires `2026-09-15`
- `plan-authoring/unnamed` — owner `david`, expires `2026-09-15`
- `deliberation-capture/unnamed` — owner `david`, expires `2026-08-31`
- `deliberation-capture/unnamed` — owner `david`, expires `2026-10-31`
- `dataflow-sweeps/unnamed` — owner `david`, expires `2026-09-15`
- `dataflow-sweeps/unnamed` — owner `david`, expires `2026-09-15`
- `dataflow-sweeps/unnamed` — owner `david`, expires `2026-09-15`
- `dataflow-sweeps/unnamed` — owner `david`, expires `2026-09-30`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-05`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-05`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-05`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-05`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-05`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-05`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-05`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-05`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-05`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-05`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-09-15`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-31`
- `plant-forms/unnamed` — owner `david`, expires `2026-10-15`
- `plant-vitality/unnamed` — owner `david`, expires `2026-11-01`

## Adversarial review records

- Review records: 3. Findings: 19.
- `incorporated`: 7
- `open`: 0
- `rejected`: 0
- `verified_closed`: 12
