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

### Run 2026-07-30 — model haiku · repo 1cf99f2 · selected 4 of 30 (26 shipped + 4 corpus · 13 controls) · recall 0/2 [0.00–0.66] · FP 2/2 [0.34–1.00]
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-07-30 | haiku | never-red-test | red-first-verifier | 2/3 | missed-entirely | AMBER |
| 2026-07-30 | haiku | red-first-symmetric-break | red-first-verifier | 0/3 | missed-entirely | **BLOCKING FAIL** |
| 2026-07-30 | haiku | control-assert-red-then-green | red-first-verifier | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-07-30 | haiku | control-genuine-red-first | red-first-verifier | 0/3 | missed-entirely | **BLOCKING FAIL** |

### Run 2026-07-30 — model haiku · repo 1cf99f2 · selected 9 of 30 (26 shipped + 4 corpus · 13 controls) · recall 4/5 [0.38–0.96] · FP 4/4 [0.51–1.00]
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-07-30 | haiku | vacuous-mutation-scope | mutation-runner | 3/3 | — | PASS |
| 2026-07-30 | haiku | red-baseline-false-green | mutation-runner | 2/3 | found-but-hedged | AMBER |
| 2026-07-30 | haiku | unmeasured-not-certified | mutation-runner | 3/3 | — | PASS |
| 2026-07-30 | haiku | mutation-phantom-run | mutation-runner | 3/3 | — | PASS |
| 2026-07-30 | haiku | control-cachebusted-run | mutation-runner | 1/3 | missed-entirely | AMBER |
| 2026-07-30 | haiku | control-real-scope-measured | mutation-runner | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-07-30 | haiku | control-green-baseline-measured | mutation-runner | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-07-30 | haiku | control-accounting-reconciles | mutation-runner | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-07-30 | haiku vs claude-fable-5 | shadowed-import-vacuous-suite | mutation-runner | 3/3 | — | PASS |

### Run 2026-07-30 — model haiku · repo 1cf99f2 · selected 4 of 30 (26 shipped + 4 corpus · 13 controls) · recall 0/2 [0.00–0.66] · FP 2/2 [0.34–1.00]
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-07-30 | haiku | unwired-deliverable | tripwire-auditor | 2/3 | missed-entirely | AMBER |
| 2026-07-30 | haiku | roadmap-laundering | tripwire-auditor | 0/3 | missed-entirely | **BLOCKING FAIL** |
| 2026-07-30 | haiku | control-parked-deferral | tripwire-auditor | 0/3 | missed-entirely | **BLOCKING FAIL** |
| 2026-07-30 | haiku | control-export-wired | tripwire-auditor | 1/3 | wrong-verdict-line | AMBER |

### Run 2026-07-30 — model haiku · repo 1cf99f2 · selected 3 of 30 (26 shipped + 4 corpus · 13 controls) · recall 1/2 [0.09–0.91] · FP 0/1 [0.00–0.79]
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-07-30 | haiku | false-negative-claim | claims-verifier | 1/3 | found-but-hedged | AMBER |
| 2026-07-30 | haiku | control-true-dead-code | claims-verifier | 3/3 | — | PASS |
| 2026-07-30 | haiku vs claude-fable-5 | dead-export-claim-cmd-indirection | claims-verifier | 3/3 | — | PASS |

### Run 2026-07-30 — model haiku · repo 1cf99f2 · selected 4 of 30 (26 shipped + 4 corpus · 13 controls) · recall 3/3 [0.44–1.00] · FP 0/1 [0.00–0.79]
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-07-30 | haiku | band-aid-parallel-list | architecture-adversary | 3/3 | — | PASS |
| 2026-07-30 | haiku | good-fix-single-source | architecture-adversary | 3/3 | — | PASS |
| 2026-07-30 | haiku vs claude-fable-5 | csv-escape-fixed-at-call-site | architecture-adversary | 3/3 | — | PASS |
| 2026-07-30 | haiku vs claude-fable-5 | special-case-bypasses-both-copies | architecture-adversary | 3/3 | — | PASS |

### Run 2026-07-30 — model haiku · repo 1cf99f2 · selected 2 of 30 (26 shipped + 4 corpus · 13 controls) · recall 1/1 [0.21–1.00] · FP 0/1 [0.00–0.79]
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-07-30 | haiku | script-unsafe-probe | script-adversary | 3/3 | — | PASS |
| 2026-07-30 | haiku | control-script-safe-probe | script-adversary | 3/3 | — | PASS |

### Run 2026-08-03 — model haiku · repo a3277eb · selected 34 of 34 (26 shipped + 8 corpus · 15 controls) · recall 12/19 [0.41–0.81] · FP 12/15 [0.55–0.93]
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-03 | haiku | never-red-test | red-first-verifier | 2/3 | missed-entirely | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-03 | haiku | unwired-deliverable | tripwire-auditor | 3/3 | — | PASS |
| 2026-08-03 | haiku | false-negative-claim | claims-verifier | 3/3 | — | PASS |
| 2026-08-03 | haiku | vacuous-mutation-scope | mutation-runner | 2/3 | missed-entirely | AMBER |
| 2026-08-03 | haiku | red-baseline-false-green | mutation-runner | 3/3 | — | PASS |
| 2026-08-03 | haiku | missing-boundary-test | edge-case-adversary | 3/3 | — | PASS |
| 2026-08-03 | haiku | band-aid-parallel-list | architecture-adversary | 3/3 | — | PASS |
| 2026-08-03 | haiku | good-fix-single-source | architecture-adversary | 2/3 | found-but-hedged | AMBER |
| 2026-08-03 | haiku | unmeasured-not-certified | mutation-runner | 3/3 | — | PASS |
| 2026-08-03 | haiku | script-unsafe-probe | script-adversary | 3/3 | — | PASS |
| 2026-08-03 | haiku | roadmap-laundering | tripwire-auditor | 1/3 | missed-entirely | AMBER |
| 2026-08-03 | haiku | control-parked-deferral | tripwire-auditor | 0/3 | missed-entirely | **BLOCKING FAIL** |
| 2026-08-03 | haiku | island-write-only-plan | integration-adversary | 3/3 | — | PASS |
| 2026-08-03 | haiku | control-connected-plan | integration-adversary | 1/3 | wrong-verdict-line | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-03 | haiku | red-first-symmetric-break | red-first-verifier | 2/3 | missed-entirely | AMBER |
| 2026-08-03 | haiku | control-assert-red-then-green | red-first-verifier | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-03 | haiku | mutation-phantom-run | mutation-runner | 3/3 | — | PASS |
| 2026-08-03 | haiku | control-cachebusted-run | mutation-runner | 1/3 | wrong-verdict-line | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-03 | haiku | control-genuine-red-first | red-first-verifier | 0/3 | missed-entirely | **BLOCKING FAIL** |
| 2026-08-03 | haiku | control-export-wired | tripwire-auditor | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-03 | haiku | control-true-dead-code | claims-verifier | 3/3 | — | PASS |
| 2026-08-03 | haiku | control-boundary-covered | edge-case-adversary | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-03 | haiku | control-real-scope-measured | mutation-runner | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-03 | haiku | control-green-baseline-measured | mutation-runner | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-03 | haiku | control-accounting-reconciles | mutation-runner | 1/3 | wrong-verdict-line | AMBER |
| 2026-08-03 | haiku | control-script-safe-probe | script-adversary | 3/3 | — | PASS |
| 2026-08-03 | haiku vs claude-fable-5 | control-declared-kill-switch | tripwire-auditor | 1/3 | missed-entirely | AMBER |
| 2026-08-03 | haiku vs claude-fable-5 | control-summary-consumer-named | integration-adversary | 3/3 | — | PASS |
| 2026-08-03 | haiku vs claude-fable-5 | csv-escape-fixed-at-call-site | architecture-adversary | 2/3 | found-but-hedged | AMBER |
| 2026-08-03 | haiku vs claude-fable-5 | dead-export-claim-cmd-indirection | claims-verifier | 3/3 | — | PASS |
| 2026-08-03 | haiku vs claude-fable-5 | ghost-gate-undeclared-export-flag | tripwire-auditor | 3/3 | — | PASS |
| 2026-08-03 | haiku vs claude-fable-5 | plan-omits-summary-consumer | integration-adversary | 3/3 | — | PASS |
| 2026-08-03 | haiku vs claude-fable-5 | shadowed-import-vacuous-suite | mutation-runner | 2/3 | found-but-hedged | AMBER |
| 2026-08-03 | haiku vs claude-fable-5 | special-case-bypasses-both-copies | architecture-adversary | 2/3 | found-but-hedged | AMBER |
