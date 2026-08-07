# Portable host adapter adversary disposition — 2026-08-07

Scope reviewed: `b9bfefd..2fd9e35`. Both adversaries ran the blessed gate and reviewed production
consumers. CIVerd's independent signed exact-SHA boundary was a verified non-finding.

| Review | Finding | Disposition |
|---|---|---|
| Architecture P1 / Integration P1 | Doctor consumed `capability_probe` events with no production producer. | Incorporated. Both native TEST-LOCK adapters now emit redacted local observations; doctor requires a same-run block+control pair on every route. Adapter-to-doctor planted test added. |
| Architecture P1 / Integration P1 | Lock read/merge/replace could lose a concurrent worktree's protection. | Incorporated. Complete lock mutation is interprocess-serialized; competing owners are refused, same-run extension merges, and unlock is generation-conditional. Concurrent plant added. |
| Architecture P2 | HEAD/worktree fields were recorded but not validated/classified. | Incorporated. Required structurally and exposed as current/shared/stale/missing binding; HEAD-advance plant added. Enforcement remains shared while stale evidence is not promoted. |
| Integration P2 | Codex copied canonical commands/agents without a native consumer or parity inventory. | Incorporated. Exact generated-roster parity manifest/test added; unavailable assets carry owner+expiry and are no longer copied into the Codex runtime. |
| Architecture P2 | Fresh Claude real-host calibration is unmeasured and unowned. | Incorporated as dated debt in `capabilities.json` (owner `david`, expires 2026-08-17). The plan remains active until the live paired host run lands; no subprocess fixture is rounded up. |

The Codex verifier-agent calibration and remaining guard-family parity were already explicit dated
debt and remain so. Neither changes CIVerd schemas, signing, plant ownership, baselines or release
ratification.
