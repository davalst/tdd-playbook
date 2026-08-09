# Generated current state

> DO NOT EDIT. This output contains machine-owned facts only; rationale and history stay in authored documents.

## Provenance

- `gate-manifest.json` — `e8ac04bfb58f504984e7247b36955960667730e3da17ade9a7b1da947489385b`
- `plugins/tdd-playbook/bin/gate_plan.py` — `e51338c374f95617eef22e22b9b99ec27e1f6b23ae1a8db3103523dfe7848fda`
- `docs/architecture/host-parity-policy.json` — `9b97797bcdbd9885f645e2d4791c28711f05ba1439d0060139fd771980fda755`
- `docs/architecture/host-parity.json` — `986d406d24b8529c7426be2f10c54f7f3da5817f36033a7791a6cfbd069303d8`
- `plugins/tdd-playbook/bin/host_parity.py` — `270d33a6dfbcc291be57c80004a2e39f52ea875d7e8b799328df6b69114cfb03`
- `capabilities.json` — `2fe48e75f197c718bb76add0381c1650134f96e590d310769f9a8f7abaef1482`
- `docs/reviews/2026-08-07-assurance-pipeline-implementation.json` — `5d3649dcb949fa820f87834db896cc69db664e5a82eadd3617cb342fcf03aace`
- `docs/reviews/2026-08-07-assurance-pipeline-plan.json` — `1f723b5524d6746f4da06b565e81f62758796e32f1cfcefc2d9a6baa64474bbd`
- `docs/reviews/2026-08-07-v1.31.0-release-implementation.json` — `77785271eddb17ba1ae19789c01e4b546ac246b52cdd18bd5272eaee9d3911fa`
- `docs/reviews/2026-08-09-owner-control-phase1-implementation.json` — `39a5d273cfe18341231d740afce2201fddc051df8caf479e37b63e1dce2cdb59`
- `docs/reviews/2026-08-09-owner-control-phase2-implementation.json` — `69b66b6a969793d3bf751d4edc9ff3029c3c13dfb053bc9b44d36107dcc0cc3f`
- `docs/reviews/index.json` — `291c71cf43510280db57b8ba5d03261937605d590476f7e449f3718a1c498642`

## Gate surface

- `sh scripts/civerd_gate.sh` — **AUTHORIZING** complete local gate and CIVerd suite command.
- `sh scripts/civerd_gate.sh affected --base <revision>` — **NON-AUTHORIZING** diagnostic subset; ambiguous scope falls back to full.
- Discovered suites: 24. Fixed stages: 4. Total stages: 28.
- Suite IDs: `test_aaa_suites_via_main`, `test_agents`, `test_capability_registry`, `test_capture`, `test_codex_adapter`, `test_dataflow_sweeps`, `test_ed25519_verify`, `test_gate_runner`, `test_gate_yield`, `test_grade_from_otel`, `test_hooks`, `test_host_adapters`, `test_host_doctor`, `test_host_parity`, `test_host_runner`, `test_installer`, `test_portable_core`, `test_red_lock_portable`, `test_reference_docs`, `test_review_ledger`, `test_tdd_lock`, `test_verify_citations`, `test_verify_verdict`, `test_with_snapshot`
- Fixed IDs: `calibration`, `dataflow`, `ledger`, `plant-forms`
- Acknowledged roster digest: `42562b24b10c4b189e339420372cc08d2e5d79424e1ed3d4a6ad6ae51ef2ffde`
- Acknowledged execution-manifest digest: `d39ebfdad74ff2c59484f4e40cb9ecacb0d08837654b022857194b49aae98aaf`

## Host parity

- Canonical assets: 33. Exact host dispositions: 66.
- Claude: 33 supported, 0 unavailable, 0 debt.
- Codex: 1 supported, 32 unavailable, 0 debt.
- Acknowledged inventory digest: `5a878b2b7b6b5918259731d831095161d65677fd5261653668afaa8c55a2a040`

## Capability registry

- Registered capabilities: 22. Owned dated integration-debt entries: 54.
- `integrity-guards/unnamed` — owner `david`, expires `2026-12-31`
- `integrity-guards/unnamed` — owner `david`, expires `2026-11-15`
- `integrity-guards/unnamed` — owner `david`, expires `2026-10-15`
- `test-lock/claude-test-lock-refresh` — owner `david`, expires `2026-09-30`
- `test-lock/codex-guard-family-parity` — owner `david`, expires `2026-09-30`
- `test-lock/shell-classifier-adapter-boundary` — owner `david`, expires `2026-09-30`
- `test-lock/codex-command-agent-discovery` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-11-01`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-15`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-15`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-15`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-15`
- `scoreboard-integrity/unnamed` — owner `david`, expires `2026-12-31`
- `scoreboard-integrity/unnamed` — owner `david`, expires `2026-11-15`
- `gate-yield/unnamed` — owner `david`, expires `2026-10-15`
- `gate-yield/unnamed` — owner `david`, expires `2026-11-15`
- `gate-yield/unnamed` — owner `david`, expires `2026-11-15`
- `civerd-release-gate/unnamed` — owner `david`, expires `2027-02-01`
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
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-15`
- `gate-surface-ledger/unnamed` — owner `david`, expires `2026-10-31`
- `plant-forms/unnamed` — owner `david`, expires `2026-10-15`
- `plant-vitality/unnamed` — owner `david`, expires `2026-11-01`
- `release-tag-authority/unnamed` — owner `david`, expires `2026-09-30`
- `release-tag-authority/unnamed` — owner `david`, expires `2026-09-30`
- `release-tag-authority/unnamed` — owner `david`, expires `2026-10-15`
- `release-tag-authority/unnamed` — owner `david`, expires `2026-09-30`
- `independent-gate-rerun/unnamed` — owner `david`, expires `2026-11-15`

## Adversarial review records

- Review records: 5. Findings: 39.
- `incorporated`: 7
- `open`: 0
- `rejected`: 0
- `verified_closed`: 32
