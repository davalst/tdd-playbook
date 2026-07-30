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
| 2026-07-27 | haiku | csv-escape-fixed-at-call-site | architecture-adversary | **BLOCKING FAIL** |
| 2026-07-27 | haiku | special-case-bypasses-both-copies | architecture-adversary | PASS |
| 2026-07-27 | haiku | shadowed-import-vacuous-suite | mutation-runner | **BLOCKING FAIL** |
| 2026-07-27 | haiku | dead-export-claim-cmd-indirection | claims-verifier | PASS |
| 2026-07-27 | haiku | csv-escape-fixed-at-call-site | architecture-adversary | **BLOCKING FAIL** |
| 2026-07-27 | haiku | shadowed-import-vacuous-suite | mutation-runner | **BLOCKING FAIL** |
| 2026-07-27 | haiku | csv-escape-fixed-at-call-site | architecture-adversary | PASS |
| 2026-07-27 | haiku | shadowed-import-vacuous-suite | mutation-runner | **BLOCKING FAIL** |
| 2026-07-27 | haiku | shadowed-import-vacuous-suite | mutation-runner | PASS |

### Run 2026-07-30 — model haiku · repo b5b30aa · selected 2 of 30 (26 shipped + 4 corpus · 13 controls) · recall 1/1 [0.21–1.00] · FP 1/1 [0.21–1.00]
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-07-30 | haiku | island-write-only-plan | integration-adversary | 3/3 | — | PASS |
| 2026-07-30 | haiku | control-connected-plan | integration-adversary | 2/3 | wrong-verdict-line | AMBER |

### Run 2026-07-30 — model haiku · repo b5b30aa · selected 2 of 30 (26 shipped + 4 corpus · 13 controls) · recall 1/1 [0.21–1.00] · FP 1/1 [0.21–1.00]
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-07-30 | haiku | missing-boundary-test | edge-case-adversary | 3/3 | — | PASS |
| 2026-07-30 | haiku | control-boundary-covered | edge-case-adversary | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
