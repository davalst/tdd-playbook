# Generated current state

> DO NOT EDIT. This output contains machine-owned facts only; rationale and history stay in authored documents.

## Provenance

- `gate-manifest.json` — `c2882586e27a5ab32ce6444452baab83a2a28dc406de88e1e61361e16e43eb73`
- `plugins/tdd-playbook/bin/gate_plan.py` — `e51338c374f95617eef22e22b9b99ec27e1f6b23ae1a8db3103523dfe7848fda`
- `docs/architecture/host-parity-policy.json` — `37c62ad37f395681635807c1a0f3e3d9370ff20a9d3431d16b4cfaab9b42b01e`
- `docs/architecture/host-parity.json` — `ac5a9b1c6d649c862677bbed993d0dfb6dd05d0a1a0732d0d044b6a523615fd3`
- `plugins/tdd-playbook/bin/host_parity.py` — `b468b1f80d24ff0c6cce8ddf9b75c8c2de9bbe6c79fe464cff8db810b275eda8`
- `capabilities.json` — `2fa8d95041ac04924d3250c7c7d86885b0cb196be07fb4890c35d5c3e5beb3e6`
- `docs/reviews/2026-08-07-assurance-pipeline-implementation.json` — `5d3649dcb949fa820f87834db896cc69db664e5a82eadd3617cb342fcf03aace`
- `docs/reviews/2026-08-07-assurance-pipeline-plan.json` — `1f723b5524d6746f4da06b565e81f62758796e32f1cfcefc2d9a6baa64474bbd`
- `docs/reviews/2026-08-07-v1.31.0-release-implementation.json` — `77785271eddb17ba1ae19789c01e4b546ac246b52cdd18bd5272eaee9d3911fa`
- `docs/reviews/2026-08-09-calibration-opt-in.json` — `cfd934054dbb123172d51731b5bc835aa71515b46ca18658b6f879d487a08661`
- `docs/reviews/2026-08-09-debt-sweep.json` — `262c1c539593868bbfa3ec02bdb3244748d14cbde647dba1937fb7ad7720371b`
- `docs/reviews/2026-08-09-owner-control-phase1-implementation.json` — `39a5d273cfe18341231d740afce2201fddc051df8caf479e37b63e1dce2cdb59`
- `docs/reviews/2026-08-09-owner-control-phase2-implementation.json` — `69b66b6a969793d3bf751d4edc9ff3029c3c13dfb053bc9b44d36107dcc0cc3f`
- `docs/reviews/2026-08-09-owner-control-phase3-implementation.json` — `0f5f404e73fd6e7d14f772230d1c4ea9fde2d82ebe3797cfb65c9baaeab4b0fc`
- `docs/reviews/2026-08-09-owner-control-phase4-implementation.json` — `f632925f007e6ece0b3ee6b0fa9b990aff7df570792a12796d1d99c40381185c`
- `docs/reviews/2026-08-09-owner-control-phase5-release.json` — `2322c48835121a967742acaed15a3a01cd42445e0dff5de818e009d33455eea7`
- `docs/reviews/2026-08-10-v1.33.0-release.json` — `f7597223da1661f5058949cdc53f683e818237b86e516ec6f20323eb74f1e688`
- `docs/reviews/2026-08-12-v1.33.1-hotfix.json` — `918b7cdb9ec9414effab66f57980c342c8183fd02a339595246c30ecd387be57`
- `docs/reviews/2026-08-12-v1.34.0-release.json` — `f4ddc2db927182b70234e08d4427f497a5805830fbc5d028127dd9ec1f56d294`
- `docs/reviews/2026-08-13-cheliped-proposals-adjudication.json` — `e236a759abbaec1d48847386e8e05827f22a00f400a3ea3fd9ea97a7219b6d9b`
- `docs/reviews/2026-08-13-readable-first-read-response.json` — `5d2071a44635918d54d84e205294f53d16d3568180bfc5691631a0651dc77156`
- `docs/reviews/2026-08-14-review-as-judgment-surface.json` — `013879179a2bcb26b44eab09064ff0c0b7311a387536fd78ebe66f951e6ddf0f`
- `docs/reviews/2026-08-15-holdout-authoring-baseline-isolation.json` — `4d4ef49f6483df09c5bf23784d5701884793c4be23aea90c31a8cc6ded3d4a93`
- `docs/reviews/2026-08-15-holdout-authoring-live-usability.json` — `9f1a3aa04e569fc40ebfc71f0c7f40465a6922330e8297c6c2215c808fbfd317`
- `docs/reviews/2026-08-15-two-tier-calibration-part1.json` — `e136a85d87ce608c43177953945d2349574508528733f962e4ea9629336231a5`
- `docs/reviews/2026-08-15-two-tier-calibration-part2-controller.json` — `2451276d4660eb33254f542ea4e04df2f18114ccb302e9d001da4f17af79278c`
- `docs/reviews/index.json` — `e89446a37ecc777d424721765ca98994b1f04310209d29fbd1aa0e2a3a9603b9`

## Gate surface

- `sh scripts/civerd_gate.sh` — **AUTHORIZING** complete local gate and CIVerd suite command.
- `sh scripts/civerd_gate.sh affected --base <revision>` — **NON-AUTHORIZING** diagnostic subset; ambiguous scope falls back to full.
- Discovered suites: 27. Fixed stages: 4. Total stages: 31.
- Suite IDs: `test_aaa_suites_via_main`, `test_agents`, `test_capability_registry`, `test_capture`, `test_codex_adapter`, `test_dataflow_sweeps`, `test_ed25519_verify`, `test_gate_runner`, `test_gate_yield`, `test_grade_from_otel`, `test_holdout_confinement`, `test_hooks`, `test_host_adapters`, `test_host_doctor`, `test_host_parity`, `test_host_runner`, `test_installer`, `test_portable_core`, `test_readable_surface`, `test_red_lock_portable`, `test_reference_docs`, `test_review_ledger`, `test_tdd_lock`, `test_vendoring`, `test_verify_citations`, `test_verify_verdict`, `test_with_snapshot`
- Fixed IDs: `calibration`, `dataflow`, `ledger`, `plant-forms`
- Acknowledged roster digest: `6239dbea0fcb7fb6e01227fd5d0b1e74999deef8b1b24d9dbce0a5d7f1be79bb`
- Acknowledged execution-manifest digest: `4bfd3e672c92d0f32eead8d39bcadb2a68f71065d5a4903f47454eff439d634e`

## Host parity

- Canonical assets: 39. Exact host dispositions: 78.
- Claude: 39 supported, 0 unavailable, 0 debt.
- Codex: 1 supported, 38 unavailable, 0 debt.
- Acknowledged inventory digest: `66b4fec8b40a730b62a46362f9228d5a661297ed3cdfe6e46f17be7d94f8d9f8`

## Capability registry

- Registered capabilities: 30. Owned dated integration-debt entries: 73.
- `integrity-guards` — RETIRED OBSOLETE 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-12-31`)
- `integrity-guards` — RETIREMENT IS A HYPOTHESIS, NOT A VERDICT (v1.32.0)… (owner `david`, expires `2026-11-15`)
- `integrity-guards` — BREAK-GLASS USAGE IS UNREAD (v1.32.0)… (owner `david`, expires `2026-10-15`)
- `fixture-data-guard/fixtureguard-warn-tier-decision` — WARN-TIER PROMOTE/KILL (A, 2026-08-15)… (owner `david`, expires `2026-11-15`)
- `fixture-data-guard/lock-surface-fixturedata-kind` — RESIDUAL HOLE, stated not assumed (arch-F8)… (owner `david`, expires `2026-10-31`)
- `test-lock/claude-test-lock-refresh` — RE-DATED 2026-08-09 -> 2026-09-30 in the v1.32.0 debt sweep… (owner `david`, expires `2026-09-30`)
- `test-lock/codex-guard-family-parity` — CODEX GUARD-FAMILY PARITY… (owner `david`, expires `2026-09-30`)
- `test-lock/shell-classifier-adapter-boundary` — SHELL CLASSIFIER ADAPTER BOUNDARY… (owner `david`, expires `2026-09-30`)
- `test-lock/codex-command-agent-discovery` — CODEX COMMAND/AGENT DISCOVERY… (owner `david`, expires `2026-09-30`)
- `capability-registry/consumer-reference-typed-schema-decision` — H2 FOLLOW-THROUGH… (owner `david`, expires `2026-11-30`)
- `calibration-loop` — RE-DATED 2026-08-09 -> 2026-09-30 in the v1.32.0 debt sweep… (owner `david`, expires `2026-09-30`)
- `calibration-loop` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-09-30`)
- `calibration-loop` — RETIRED OBSOLETE 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-12-31`)
- `calibration-loop` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-09-30`)
- `calibration-loop` — APPLY_EDITS CREATE capability (v1.24 §6c D15 — promoted from the corpus README's 'possible future enhancement' to owned… (owner `david`, expires `2026-09-15`)
- `calibration-loop` — RE-SCOPED 2026-08-09 (v1.32.0, calibration is now OPT-IN AND REACTIVE)… (owner `david`, expires `2026-09-30`)
- `calibration-loop` — RE-SCOPED 2026-08-09 (v1.32.0, calibration is now OPT-IN AND REACTIVE)… (owner `david`, expires `2026-09-30`)
- `calibration-loop` — RE-SCOPED 2026-08-09 (v1.32.0, calibration is now OPT-IN AND REACTIVE)… (owner `david`, expires `2026-09-30`)
- `calibration-loop` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-09-15`)
- `calibration-loop` — MUTATION-RUNNER CLEAN-RUN DESCRIPTION (CIVerd calibration analysis 2026-08-05, their finding F — the one substantive ite… (owner `david`, expires `2026-09-15`)
- `calibration-loop` — ORACLE NORMALISATION PASS (CIVerd calibration analysis 2026-08-05, their general point)… (owner `david`, expires `2026-09-15`)
- `calibration-loop` — BASELINE ISOLATION EFFECT-PROOF IS DEPLOY-GATED (B1, 2026-08-15)… (owner `david`, expires `2026-11-15`)
- `scoreboard-integrity` — RETIRED OBSOLETE 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-12-31`)
- `scoreboard-integrity` — SUBSTRING AUTHORIZATION IN THE INTEGRITY CHECKER (H15/D8, v1.30 — DEFERRED, stated not dropped)… (owner `david`, expires `2026-11-15`)
- `gate-yield` — PAID 2026-08-09 — VERIFIED, not assumed… (owner `david`, expires `2026-12-31`)
- `gate-yield` — PER-GATE ADJUDICATION SEAM (v1.27, found by integration-adversary)… (owner `david`, expires `2026-11-15`)
- `gate-yield` — DOWNSTREAM WRITE-ONLY EMITTER (v1.27 surface-parity boundary, stated not hidden)… (owner `david`, expires `2026-11-15`)
- `install-doctor/bin-roster-prose-divergence` — CLAUDE.md step-2 and README.md name DIFFERENT partial bin lists (README… (owner `david`, expires `2026-10-13`)
- `civerd-release-gate` — ARCHIVAL-ONLY, NO CONSUMER (v1.32.0)… (owner `david`, expires `2027-02-01`)
- `deliberation-capture` — ENROLLMENT SWEEP (David's nothing-ships-dark directive, 2026-07-30)… (owner `david`, expires `2026-08-31`)
- `deliberation-capture` — CONSUMER… (owner `david`, expires `2026-10-31`)
- `dataflow-sweeps` — TIER-2 FIELD-PAIRING SWEEP (v1.26 F3 deferral, David's call 2026-08-05)… (owner `david`, expires `2026-09-15`)
- `dataflow-sweeps` — CHELIPED TIER-2 PILOT VERDICT… (owner `david`, expires `2026-09-15`)
- `dataflow-sweeps` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-09-15`)
- `dataflow-sweeps` — ARM THE TWO DARK SWEEPS (H15, v1.30)… (owner `david`, expires `2026-09-30`)
- `gate-surface-ledger` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-10-05`)
- `gate-surface-ledger` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-10-05`)
- `gate-surface-ledger` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-10-05`)
- `gate-surface-ledger` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-10-05`)
- `gate-surface-ledger` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-10-05`)
- `gate-surface-ledger` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-10-05`)
- `gate-surface-ledger` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-10-05`)
- `gate-surface-ledger` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-10-05`)
- `gate-surface-ledger` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-10-05`)
- `gate-surface-ledger` — RE-SCOPED 2026-08-09 (v1.32.0)… (owner `david`, expires `2026-10-05`)
- `gate-surface-ledger` — PRE-COMMIT GATE BLIND SPOT (found live 2026-08-05)… (owner `david`, expires `2026-09-15`)
- `gate-surface-ledger` — SELF-REFERENTIAL DENOMINATORS (H15, v1.30)… (owner `david`, expires `2026-10-31`)
- `gate-surface-ledger` — WRITE-ONLY GATED PLANS + LOST SLUG-COLLISION CHECK (v1.32.0)… (owner `david`, expires `2026-10-15`)
- `gate-surface-ledger` — DOCTRINE SHRINK NOT DONE (v1.32.0)… (owner `david`, expires `2026-10-31`)
- `gate-surface-ledger/ledger-L-20260812-06-followup` — REFUTATION OWNED (L-20260812-06)… (owner `david`, expires `2026-09-30`)
- `gate-surface-ledger/ledger-L-20260813-01-followup` — REFUTATION OWNED (L-20260813-01)… (owner `david`, expires `2026-11-30`)
- `plant-forms` — FIRST HOLDOUT ASSIGNMENT (v1.29, David's ships-on-or-triggered rule)… (owner `david`, expires `2026-10-15`)
- `plant-vitality` — SATURATION K IS PROVISIONAL (v1.29)… (owner `david`, expires `2026-11-01`)
- `release-tag-authority` — SERVER-SIDE TAG PROTECTION NOT ARMED… (owner `david`, expires `2026-09-30`)
- `release-tag-authority` — NO SIGNING KEY CONFIGURED… (owner `david`, expires `2026-09-30`)
- `release-tag-authority` — TAG-CADENCE COUPLING IS NOW MANUAL (v1.32.0)… (owner `david`, expires `2026-10-15`)
- `release-tag-authority` — CODEX SURFACE DIVERGENCE (stated, not discovered)… (owner `david`, expires `2026-09-30`)
- `release-tag-authority/liveness-probe-missing` — NO HEARTBEAT (anti-dark sweep, David's challenge 2026-08-13)… (owner `david`, expires `2026-10-31`)
- `independent-gate-rerun` — PAID 2026-08-09 — first green run observed on the real runner… (owner `david`, expires `2026-11-15`)
- `independent-gate-rerun/liveness-probe-missing` — NO HEARTBEAT (anti-dark sweep, David's challenge 2026-08-13)… (owner `david`, expires `2026-10-31`)
- `state-reset` — --shared HAS NO CROSS-WORKTREE JOURNAL (v1.32.0)… (owner `david`, expires `2026-10-31`)
- `state-reset/liveness-probe-missing` — NO HEARTBEAT (anti-dark sweep, David's challenge 2026-08-13)… (owner `david`, expires `2026-10-31`)
- `vendor-uninstall` — INSTALL IS LOSSY AND UNINSTALL INHERITS IT (v1.32.0)… (owner `david`, expires `2026-10-31`)
- `vendor-uninstall/liveness-probe-missing` — NO HEARTBEAT (anti-dark sweep, David's challenge 2026-08-13)… (owner `david`, expires `2026-10-31`)
- `advisory-guards-optin` — RE-READ THE YIELD BEFORE MAKING THIS PERMANENT (v1.32.0)… (owner `david`, expires `2026-11-15`)
- `advisory-guards-optin/liveness-probe-missing` — NO HEARTBEAT (anti-dark sweep, David's challenge 2026-08-13)… (owner `david`, expires `2026-10-31`)
- `generated-agents-md` — HOST_NOTES IS HAND-MAINTAINED AND UNPINNED (v1.33.0)… (owner `david`, expires `2026-11-30`)
- `generated-agents-md/liveness-probe-missing` — NO HEARTBEAT (anti-dark sweep, David's challenge 2026-08-13)… (owner `david`, expires `2026-10-31`)
- `role-adversaries/observability-haiku-flakiness` — PAID 2026-08-13 on evidence, then RE-SCOPED… (owner `david`, expires `2026-09-30`)
- `role-adversaries/role-adversaries-codex-unavailable` — CLAUDE-ONLY BY PARITY… (owner `david`, expires `2026-09-30`)
- `scenario-inventory/scenario-inventory-not-vendored` — THIS REPO ONLY, BY DECISION (dissolves the parity exception both reviewers flagged)… (owner `david`, expires `2026-11-30`)
- `readable-surface/readable-surface-keep-kill` — THE R&D DECISION… (owner `david`, expires `2026-09-30`)
- `readable-surface/readable-surface-downstream-inert-emitter` — JOINS THE EXISTING gate-yield DOWNSTREAM WRITE-ONLY DEBT (capabilities.json gate-yield entry)… (owner `david`, expires `2026-12-31`)

## Adversarial review records

- Review records: 20. Findings: 126.
- `incorporated`: 42
- `open`: 6
- `rejected`: 3
- `verified_closed`: 75
