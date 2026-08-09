# Generated current state

> DO NOT EDIT. This output contains machine-owned facts only; rationale and history stay in authored documents.

## Provenance

- `gate-manifest.json` — `8903bc05b0a9aebdefaffa85d4303b31a272eabc76815bc36b10abdd774dfad5`
- `plugins/tdd-playbook/bin/gate_plan.py` — `e51338c374f95617eef22e22b9b99ec27e1f6b23ae1a8db3103523dfe7848fda`
- `docs/architecture/host-parity-policy.json` — `9b97797bcdbd9885f645e2d4791c28711f05ba1439d0060139fd771980fda755`
- `docs/architecture/host-parity.json` — `986d406d24b8529c7426be2f10c54f7f3da5817f36033a7791a6cfbd069303d8`
- `plugins/tdd-playbook/bin/host_parity.py` — `270d33a6dfbcc291be57c80004a2e39f52ea875d7e8b799328df6b69114cfb03`
- `capabilities.json` — `936cb184642ee3c53307a0361da680b3d71245dab65b2abd0559243394b183e2`
- `docs/reviews/2026-08-07-assurance-pipeline-implementation.json` — `5d3649dcb949fa820f87834db896cc69db664e5a82eadd3617cb342fcf03aace`
- `docs/reviews/2026-08-07-assurance-pipeline-plan.json` — `1f723b5524d6746f4da06b565e81f62758796e32f1cfcefc2d9a6baa64474bbd`
- `docs/reviews/2026-08-07-v1.31.0-release-implementation.json` — `77785271eddb17ba1ae19789c01e4b546ac246b52cdd18bd5272eaee9d3911fa`
- `docs/reviews/2026-08-09-calibration-opt-in.json` — `cfd934054dbb123172d51731b5bc835aa71515b46ca18658b6f879d487a08661`
- `docs/reviews/2026-08-09-owner-control-phase1-implementation.json` — `39a5d273cfe18341231d740afce2201fddc051df8caf479e37b63e1dce2cdb59`
- `docs/reviews/2026-08-09-owner-control-phase2-implementation.json` — `69b66b6a969793d3bf751d4edc9ff3029c3c13dfb053bc9b44d36107dcc0cc3f`
- `docs/reviews/2026-08-09-owner-control-phase3-implementation.json` — `0f5f404e73fd6e7d14f772230d1c4ea9fde2d82ebe3797cfb65c9baaeab4b0fc`
- `docs/reviews/2026-08-09-owner-control-phase4-implementation.json` — `f632925f007e6ece0b3ee6b0fa9b990aff7df570792a12796d1d99c40381185c`
- `docs/reviews/2026-08-09-owner-control-phase5-release.json` — `2322c48835121a967742acaed15a3a01cd42445e0dff5de818e009d33455eea7`
- `docs/reviews/index.json` — `323374e81723298128c281b0fb6cba562a9552ff92f9a300462c9d85358d3af9`

## Gate surface

- `sh scripts/civerd_gate.sh` — **AUTHORIZING** complete local gate and CIVerd suite command.
- `sh scripts/civerd_gate.sh affected --base <revision>` — **NON-AUTHORIZING** diagnostic subset; ambiguous scope falls back to full.
- Discovered suites: 25. Fixed stages: 4. Total stages: 29.
- Suite IDs: `test_aaa_suites_via_main`, `test_agents`, `test_capability_registry`, `test_capture`, `test_codex_adapter`, `test_dataflow_sweeps`, `test_ed25519_verify`, `test_gate_runner`, `test_gate_yield`, `test_grade_from_otel`, `test_hooks`, `test_host_adapters`, `test_host_doctor`, `test_host_parity`, `test_host_runner`, `test_installer`, `test_portable_core`, `test_red_lock_portable`, `test_reference_docs`, `test_review_ledger`, `test_tdd_lock`, `test_vendoring`, `test_verify_citations`, `test_verify_verdict`, `test_with_snapshot`
- Fixed IDs: `calibration`, `dataflow`, `ledger`, `plant-forms`
- Acknowledged roster digest: `cfec9a3908546b5d9faba994212f0f083c7549c07bae5841566426abbb22b68a`
- Acknowledged execution-manifest digest: `f987ec6a9b751e3c7f05d544a51a19344e70d9a97da67b8d323986f98f4d7e7a`

## Host parity

- Canonical assets: 33. Exact host dispositions: 66.
- Claude: 33 supported, 0 unavailable, 0 debt.
- Codex: 1 supported, 32 unavailable, 0 debt.
- Acknowledged inventory digest: `5a878b2b7b6b5918259731d831095161d65677fd5261653668afaa8c55a2a040`

## Capability registry

- Registered capabilities: 25. Owned dated integration-debt entries: 54.
- `integrity-guards/unnamed` — owner `david`, expires `2026-12-31`
- `integrity-guards/unnamed` — owner `david`, expires `2026-11-15`
- `integrity-guards/unnamed` — owner `david`, expires `2026-10-15`
- `test-lock/claude-test-lock-refresh` — owner `david`, expires `2026-09-30`
- `test-lock/codex-guard-family-parity` — owner `david`, expires `2026-09-30`
- `test-lock/shell-classifier-adapter-boundary` — owner `david`, expires `2026-09-30`
- `test-lock/codex-command-agent-discovery` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-12-31`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-15`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-30`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-15`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-15`
- `calibration-loop/unnamed` — owner `david`, expires `2026-09-15`
- `scoreboard-integrity/unnamed` — owner `david`, expires `2026-12-31`
- `scoreboard-integrity/unnamed` — owner `david`, expires `2026-11-15`
- `gate-yield/unnamed` — owner `david`, expires `2026-12-31`
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
- `state-reset/unnamed` — owner `david`, expires `2026-10-31`
- `vendor-uninstall/unnamed` — owner `david`, expires `2026-10-31`
- `advisory-guards-optin/unnamed` — owner `david`, expires `2026-11-15`

## Adversarial review records

- Review records: 9. Findings: 62.
- `incorporated`: 7
- `open`: 0
- `rejected`: 0
- `verified_closed`: 55
