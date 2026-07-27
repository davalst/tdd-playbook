# Calibration history

| date | model | scenario | agent | verdict |
|---|---|---|---|---|
| 2026-07-09 | haiku | never-red-test | red-first-verifier | INVALID — env failure: `--dangerously-skip-permissions` refused under root; doer never ran |
| 2026-07-09 | haiku | unwired-deliverable | tripwire-auditor | INVALID — env failure: `--dangerously-skip-permissions` refused under root; doer never ran |
| 2026-07-09 | haiku | false-negative-claim | claims-verifier | INVALID — env failure: `--dangerously-skip-permissions` refused under root; doer never ran |
| 2026-07-09 | haiku | missing-boundary-test | edge-case-adversary | INVALID — env failure: `--dangerously-skip-permissions` refused under root; doer never ran |
| 2026-07-09 | haiku | never-red-test | red-first-verifier | PASS |
| 2026-07-09 | haiku | unwired-deliverable | tripwire-auditor | **BLOCKING FAIL** |
| 2026-07-09 | haiku | false-negative-claim | claims-verifier | **BLOCKING FAIL** |
| 2026-07-09 | haiku | missing-boundary-test | edge-case-adversary | PASS |
| 2026-07-09 | haiku | unwired-deliverable | tripwire-auditor | **BLOCKING FAIL** |
| 2026-07-09 | haiku | false-negative-claim | claims-verifier | **BLOCKING FAIL** |
| 2026-07-09 | haiku | unwired-deliverable | tripwire-auditor | PASS |
| 2026-07-09 | haiku | false-negative-claim | claims-verifier | PASS |
| 2026-07-09 | haiku | never-red-test | red-first-verifier | PASS |
| 2026-07-09 | haiku | unwired-deliverable | tripwire-auditor | PASS |
| 2026-07-09 | haiku | false-negative-claim | claims-verifier | PASS |
| 2026-07-09 | haiku | missing-boundary-test | edge-case-adversary | PASS |
| 2026-07-27 | haiku | never-red-test | red-first-verifier | PASS |
| 2026-07-27 | haiku | unwired-deliverable | tripwire-auditor | PASS |
| 2026-07-27 | haiku | false-negative-claim | claims-verifier | PASS |
| 2026-07-27 | haiku | vacuous-mutation-scope | mutation-runner | **BLOCKING FAIL** |
| 2026-07-27 | haiku | red-baseline-false-green | mutation-runner | PASS |
| 2026-07-27 | haiku | missing-boundary-test | edge-case-adversary | PASS |
| 2026-07-27 | haiku | band-aid-parallel-list | architecture-adversary | PASS |
| 2026-07-27 | haiku | good-fix-single-source | architecture-adversary | PASS |
| 2026-07-27 | haiku | unmeasured-not-certified | mutation-runner | PASS |
| 2026-07-27 | haiku | vacuous-mutation-scope | mutation-runner | PASS |
