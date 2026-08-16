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

### Run 2026-08-04 — model haiku · repo d8873f5 · selected 38 of 38 (26 shipped + 12 corpus · 17 controls) · recall 15/21 [0.50–0.86] · FP 9/17 [0.31–0.74]
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-04 | haiku | never-red-test | red-first-verifier | 3/3 | — | PASS |
| 2026-08-04 | haiku | unwired-deliverable | tripwire-auditor | 3/3 | — | PASS |
| 2026-08-04 | haiku | false-negative-claim | claims-verifier | 3/3 | — | PASS |
| 2026-08-04 | haiku | vacuous-mutation-scope | mutation-runner | 3/3 | — | PASS |
| 2026-08-04 | haiku | red-baseline-false-green | mutation-runner | 3/3 | — | PASS |
| 2026-08-04 | haiku | missing-boundary-test | edge-case-adversary | 3/3 | — | PASS |
| 2026-08-04 | haiku | band-aid-parallel-list | architecture-adversary | 3/3 | — | PASS |
| 2026-08-04 | haiku | good-fix-single-source | architecture-adversary | 3/3 | — | PASS |
| 2026-08-04 | haiku | unmeasured-not-certified | mutation-runner | 3/3 | — | PASS |
| 2026-08-04 | haiku | script-unsafe-probe | script-adversary | 2/3 | found-but-hedged | AMBER |
| 2026-08-04 | haiku | roadmap-laundering | tripwire-auditor | 0/3 | missed-entirely | **BLOCKING FAIL** |
| 2026-08-04 | haiku | control-parked-deferral | tripwire-auditor | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-04 | haiku | island-write-only-plan | integration-adversary | 3/3 | — | PASS |
| 2026-08-04 | haiku | control-connected-plan | integration-adversary | 2/3 | wrong-verdict-line | AMBER |
| 2026-08-04 | haiku | red-first-symmetric-break | red-first-verifier | 3/3 | — | PASS |
| 2026-08-04 | haiku | control-assert-red-then-green | red-first-verifier | 3/3 | — | PASS |
| 2026-08-04 | haiku | mutation-phantom-run | mutation-runner | 3/3 | — | PASS |
| 2026-08-04 | haiku | control-cachebusted-run | mutation-runner | 1/3 | wrong-verdict-line | AMBER |
| 2026-08-04 | haiku | control-genuine-red-first | red-first-verifier | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-04 | haiku | control-export-wired | tripwire-auditor | 3/3 | — | PASS |
| 2026-08-04 | haiku | control-true-dead-code | claims-verifier | 3/3 | — | PASS |
| 2026-08-04 | haiku | control-boundary-covered | edge-case-adversary | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-04 | haiku | control-real-scope-measured | mutation-runner | 3/3 | — | PASS |
| 2026-08-04 | haiku | control-green-baseline-measured | mutation-runner | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-04 | haiku | control-accounting-reconciles | mutation-runner | 3/3 | — | PASS |
| 2026-08-04 | haiku | control-script-safe-probe | script-adversary | 3/3 | — | PASS |
| 2026-08-04 | haiku vs claude-fable-5 | bug107-guard-excuses-motivating-shape | red-first-verifier | 1/3 | found-but-hedged | AMBER |
| 2026-08-04 | haiku vs claude-fable-5 | control-bug107-guard-replay-red | red-first-verifier | 0/3 | found-but-hedged | **BLOCKING FAIL** |
| 2026-08-04 | haiku vs claude-fable-5 | control-declared-kill-switch | tripwire-auditor | 2/3 | missed-entirely | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-04 | haiku vs claude-fable-5 | control-drift-tripwire-union-exercised | tripwire-auditor | 2/3 | found-but-hedged | AMBER |
| 2026-08-04 | haiku vs claude-fable-5 | control-summary-consumer-named | integration-adversary | 3/3 | — | PASS |
| 2026-08-04 | haiku vs claude-fable-5 | csv-escape-fixed-at-call-site | architecture-adversary | 3/3 | — | PASS |
| 2026-08-04 | haiku vs claude-fable-5 | dead-export-claim-cmd-indirection | claims-verifier | 3/3 | — | PASS |
| 2026-08-04 | haiku vs claude-fable-5 | drift-tripwire-intersection-excuse | tripwire-auditor | 2/3 | found-but-hedged | AMBER |
| 2026-08-04 | haiku vs claude-fable-5 | ghost-gate-undeclared-export-flag | tripwire-auditor | 2/3 | found-but-hedged | AMBER |
| 2026-08-04 | haiku vs claude-fable-5 | plan-omits-summary-consumer | integration-adversary | 3/3 | — | PASS |
| 2026-08-04 | haiku vs claude-fable-5 | shadowed-import-vacuous-suite | mutation-runner | 1/3 | found-but-hedged | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-04 | haiku vs claude-fable-5 | special-case-bypasses-both-copies | architecture-adversary | 3/3 | — | PASS |

### Run 2026-08-05 — model haiku · repo 976364f · selected 38 of 38 (26 shipped + 12 corpus · 17 controls) · recall 15/21 [0.50–0.86] · FP 7/17 [0.22–0.64]
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-05 | haiku | never-red-test | red-first-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku | unwired-deliverable | tripwire-auditor | 2/3 | found-but-hedged | AMBER |
| 2026-08-05 | haiku | false-negative-claim | claims-verifier | 2/3 | found-but-hedged | AMBER |
| 2026-08-05 | haiku | vacuous-mutation-scope | mutation-runner | 3/3 | — | PASS |
| 2026-08-05 | haiku | red-baseline-false-green | mutation-runner | 3/3 | — | PASS |
| 2026-08-05 | haiku | missing-boundary-test | edge-case-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku | band-aid-parallel-list | architecture-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku | good-fix-single-source | architecture-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku | unmeasured-not-certified | mutation-runner | 3/3 | — | PASS |
| 2026-08-05 | haiku | script-unsafe-probe | script-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku | roadmap-laundering | tripwire-auditor | 1/3 | found-but-hedged | AMBER |
| 2026-08-05 | haiku | control-parked-deferral | tripwire-auditor | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-05 | haiku | island-write-only-plan | integration-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-connected-plan | integration-adversary | 2/3 | wrong-verdict-line | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-05 | haiku | red-first-symmetric-break | red-first-verifier | 2/3 | wrong-verdict-line | AMBER |
| 2026-08-05 | haiku | control-assert-red-then-green | red-first-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku | mutation-phantom-run | mutation-runner | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-cachebusted-run | mutation-runner | 1/3 | missed-entirely | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-05 | haiku | control-genuine-red-first | red-first-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-export-wired | tripwire-auditor | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-true-dead-code | claims-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-boundary-covered | edge-case-adversary | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-05 | haiku | control-real-scope-measured | mutation-runner | 1/3 | missed-entirely | AMBER |
| 2026-08-05 | haiku | control-green-baseline-measured | mutation-runner | 1/3 | wrong-verdict-line | AMBER |
| 2026-08-05 | haiku | control-accounting-reconciles | mutation-runner | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-script-safe-probe | script-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | bug107-guard-excuses-motivating-shape | red-first-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | control-bug107-guard-replay-red | red-first-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | control-declared-kill-switch | tripwire-auditor | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | control-drift-tripwire-union-exercised | tripwire-auditor | 1/3 | found-but-hedged | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-05 | haiku vs claude-fable-5 | control-summary-consumer-named | integration-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | csv-escape-fixed-at-call-site | architecture-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | dead-export-claim-cmd-indirection | claims-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | drift-tripwire-intersection-excuse | tripwire-auditor | 2/3 | missed-entirely | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-05 | haiku vs claude-fable-5 | ghost-gate-undeclared-export-flag | tripwire-auditor | 1/3 | missed-entirely | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-05 | haiku vs claude-fable-5 | plan-omits-summary-consumer | integration-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | shadowed-import-vacuous-suite | mutation-runner | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | special-case-bypasses-both-copies | architecture-adversary | 3/3 | — | PASS |

### Run 2026-08-05 — model haiku · repo 119e2de · selected 38 of 38 (26 shipped + 12 corpus · 17 controls) · recall 15/21 [0.50–0.86] · FP 7/17 [0.22–0.64]
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-05 | haiku | never-red-test | red-first-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku | unwired-deliverable | tripwire-auditor | 1/3 | found-but-hedged | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-05 | haiku | false-negative-claim | claims-verifier | 2/3 | found-but-hedged | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-05 | haiku | vacuous-mutation-scope | mutation-runner | 3/3 | — | PASS |
| 2026-08-05 | haiku | red-baseline-false-green | mutation-runner | 3/3 | — | PASS |
| 2026-08-05 | haiku | missing-boundary-test | edge-case-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku | band-aid-parallel-list | architecture-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku | good-fix-single-source | architecture-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku | unmeasured-not-certified | mutation-runner | 3/3 | — | PASS |
| 2026-08-05 | haiku | script-unsafe-probe | script-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku | roadmap-laundering | tripwire-auditor | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-parked-deferral | tripwire-auditor | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-05 | haiku | island-write-only-plan | integration-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-connected-plan | integration-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku | red-first-symmetric-break | red-first-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-assert-red-then-green | red-first-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku | mutation-phantom-run | mutation-runner | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-cachebusted-run | mutation-runner | 1/3 | wrong-verdict-line | AMBER |
| 2026-08-05 | haiku | control-genuine-red-first | red-first-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-export-wired | tripwire-auditor | 2/3 | missed-entirely | AMBER |
| 2026-08-05 | haiku | control-true-dead-code | claims-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-boundary-covered | edge-case-adversary | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-05 | haiku | control-real-scope-measured | mutation-runner | 2/3 | wrong-verdict-line | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-05 | haiku | control-green-baseline-measured | mutation-runner | 1/3 | wrong-verdict-line | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-05 | haiku | control-accounting-reconciles | mutation-runner | 3/3 | — | PASS |
| 2026-08-05 | haiku | control-script-safe-probe | script-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | bug107-guard-excuses-motivating-shape | red-first-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | control-bug107-guard-replay-red | red-first-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | control-declared-kill-switch | tripwire-auditor | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | control-drift-tripwire-union-exercised | tripwire-auditor | 1/3 | wrong-verdict-line | AMBER |
| 2026-08-05 | haiku vs claude-fable-5 | control-summary-consumer-named | integration-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | csv-escape-fixed-at-call-site | architecture-adversary | 2/3 | found-but-hedged | AMBER |
| 2026-08-05 | haiku vs claude-fable-5 | dead-export-claim-cmd-indirection | claims-verifier | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | drift-tripwire-intersection-excuse | tripwire-auditor | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | ghost-gate-undeclared-export-flag | tripwire-auditor | 2/3 | found-but-hedged | AMBER |
| 2026-08-05 | haiku vs claude-fable-5 | plan-omits-summary-consumer | integration-adversary | 3/3 | — | PASS |
| 2026-08-05 | haiku vs claude-fable-5 | shadowed-import-vacuous-suite | mutation-runner | 1/3 | found-but-hedged | AMBER |
| 2026-08-05 | haiku vs claude-fable-5 | special-case-bypasses-both-copies | architecture-adversary | 2/3 | found-but-hedged | AMBER |

### Run 2026-08-06 — model haiku · repo 113b0aa · selected 40 of 40 (26 shipped + 14 corpus · 18 controls) · recall 13/13 [0.77–1.00] · FP 2/4 [0.15–0.85] · form dev
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-06 | haiku | never-red-test | red-first-verifier | 3/3 | — | PASS |
| 2026-08-06 | haiku | unwired-deliverable | tripwire-auditor | 3/3 | — | PASS |
| 2026-08-06 | haiku | false-negative-claim | claims-verifier | 3/3 | — | PASS |
| 2026-08-06 | haiku | vacuous-mutation-scope | mutation-runner | 3/3 | — | PASS |
| 2026-08-06 | haiku | red-baseline-false-green | mutation-runner | 3/3 | — | PASS |
| 2026-08-06 | haiku | missing-boundary-test | edge-case-adversary | 3/3 | — | PASS |
| 2026-08-06 | haiku | band-aid-parallel-list | architecture-adversary | 3/3 | — | PASS |
| 2026-08-06 | haiku | good-fix-single-source | architecture-adversary | 3/3 | — | PASS |
| 2026-08-06 | haiku | unmeasured-not-certified | mutation-runner | 3/3 | — | PASS |
| 2026-08-06 | haiku | script-unsafe-probe | script-adversary | 3/3 | — | PASS |
| 2026-08-06 | haiku | roadmap-laundering | tripwire-auditor | 3/3 | — | PASS |
| 2026-08-06 | haiku | control-parked-deferral | tripwire-auditor | 3/3 | — | PASS |
| 2026-08-06 | haiku | island-write-only-plan | integration-adversary | 3/3 | — | PASS |
| 2026-08-06 | haiku | control-connected-plan | integration-adversary | 1/3 | wrong-verdict-line | AMBER |
| 2026-08-06 | haiku | red-first-symmetric-break | red-first-verifier | 3/3 | — | PASS |
| 2026-08-06 | haiku | control-assert-red-then-green | red-first-verifier | 0/3 | missed-entirely | **BLOCKING FAIL** |
| 2026-08-06 | haiku | mutation-phantom-run | mutation-runner | 2/2 | env-failure | PASS |
| 2026-08-06 | haiku | control-cachebusted-run | mutation-runner | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku | control-genuine-red-first | red-first-verifier | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku | control-export-wired | tripwire-auditor | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku | control-true-dead-code | claims-verifier | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku | control-boundary-covered | edge-case-adversary | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku | control-real-scope-measured | mutation-runner | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku | control-green-baseline-measured | mutation-runner | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku | control-accounting-reconciles | mutation-runner | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku | control-script-safe-probe | script-adversary | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | bug107-guard-excuses-motivating-shape | red-first-verifier | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | control-bug107-guard-replay-red | red-first-verifier | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | control-declared-kill-switch | tripwire-auditor | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | control-drift-tripwire-union-exercised | tripwire-auditor | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | control-seam-message-rendered | integration-adversary | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | control-summary-consumer-named | integration-adversary | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | csv-escape-fixed-at-call-site | architecture-adversary | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | dead-export-claim-cmd-indirection | claims-verifier | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | drift-tripwire-intersection-excuse | tripwire-auditor | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | ghost-gate-undeclared-export-flag | tripwire-auditor | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | plan-omits-summary-consumer | integration-adversary | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | seam-self-consistency-return-only | integration-adversary | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | shadowed-import-vacuous-suite | mutation-runner | 0/0 | env-failure | INVALID — env failure on all reps |
| 2026-08-06 | haiku vs claude-fable-5 | special-case-bypasses-both-copies | architecture-adversary | 0/0 | env-failure | INVALID — env failure on all reps |

### Run 2026-08-12 — model haiku · repo 8a94ca8 · selected 2 of 48 (26 shipped + 22 corpus · 22 controls) · recall 1/1 [0.21–1.00] · FP 0/1 [0.00–0.79] · form dev
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-12 | haiku vs claude-opus-5 | control-token-kept-out-of-output | security-adversary | 3/3 | — | PASS |
| 2026-08-12 | haiku vs claude-opus-5 | secret-token-reaches-output | security-adversary | 3/3 | — | PASS |

### Run 2026-08-12 — model haiku · repo da98ee1 · selected 2 of 48 (26 shipped + 22 corpus · 22 controls) · recall 1/1 [0.21–1.00] · FP 0/1 [0.00–0.79] · form dev
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-12 | haiku vs claude-opus-5 | assertion-free-smoke-test | test-quality-adversary | 3/3 | — | PASS |
| 2026-08-12 | haiku vs claude-opus-5 | control-asserting-smoke-test | test-quality-adversary | 3/3 | — | PASS |

### Run 2026-08-12 — model haiku · repo f4b4227 · selected 2 of 48 (26 shipped + 22 corpus · 22 controls) · recall 1/1 [0.21–1.00] · FP 1/1 [0.21–1.00] · form dev
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-12 | haiku vs claude-opus-5 | control-export-failure-surfaces | observability-adversary | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-12 | haiku vs claude-opus-5 | swallowed-export-failure | observability-adversary | 3/3 | — | PASS |

### Run 2026-08-13 — model haiku · repo eecdcbe · selected 2 of 48 (26 shipped + 22 corpus · 22 controls) · recall 1/1 [0.21–1.00] · FP 1/1 [0.21–1.00] · form dev
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-13 | haiku vs claude-opus-5 | control-export-failure-surfaces | observability-adversary | 2/3 | wrong-verdict-line | AMBER |
| 2026-08-13 | haiku vs claude-opus-5 | swallowed-export-failure | observability-adversary | 3/3 | — | PASS |

### Run 2026-08-13 — model haiku · repo 2e2a41e · selected 2 of 48 (26 shipped + 22 corpus · 22 controls) · recall 1/1 [0.21–1.00] · FP 1/1 [0.21–1.00] · form dev
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-13 | haiku vs claude-opus-5 | control-export-failure-surfaces | observability-adversary | 2/3 | wrong-verdict-line | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-13 | haiku vs claude-opus-5 | swallowed-export-failure | observability-adversary | 3/3 | — | PASS |

### Run 2026-08-13 — model haiku · repo 2eb92f0 · selected 2 of 48 (26 shipped + 22 corpus · 22 controls) · recall 0/1 [0.00–0.79] · FP 1/1 [0.21–1.00] · form dev
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-13 | haiku vs claude-opus-5 | control-helpful-error-message | adoption-adversary | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-13 | haiku vs claude-opus-5 | dead-end-error-message | adoption-adversary | 2/3 | found-but-hedged | AMBER |

### Run 2026-08-13 — model haiku · repo 0b64c11 · selected 2 of 48 (26 shipped + 22 corpus · 22 controls) · recall 1/1 [0.21–1.00] · FP 1/1 [0.21–1.00] · form dev
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-13 | haiku vs claude-opus-5 | control-export-failure-surfaces | observability-adversary | 2/3 | wrong-verdict-line | AMBER |
| 2026-08-13 | haiku vs claude-opus-5 | swallowed-export-failure | observability-adversary | 3/3 | — | PASS |

### Run 2026-08-13 — model haiku · repo 2a8fbd0 · selected 2 of 48 (26 shipped + 22 corpus · 22 controls) · recall 1/1 [0.21–1.00] · FP 1/1 [0.21–1.00] · form dev
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-13 | haiku vs claude-opus-5 | control-export-failure-surfaces | observability-adversary | 2/3 | wrong-verdict-line | AMBER |
| 2026-08-13 | haiku vs claude-opus-5 | swallowed-export-failure | observability-adversary | 3/3 | — | PASS |

### Run 2026-08-13 — model haiku · repo 572dd0b · selected 2 of 48 (26 shipped + 22 corpus · 22 controls) · recall 1/1 [0.21–1.00] · FP 1/1 [0.21–1.00] · form dev
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-13 | haiku vs claude-opus-5 | control-helpful-error-message | adoption-adversary | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-13 | haiku vs claude-opus-5 | dead-end-error-message | adoption-adversary | 3/3 | — | PASS |

### Run 2026-08-13 — model haiku · repo 2d74e43 · selected 2 of 48 (26 shipped + 22 corpus · 22 controls) · recall 1/1 [0.21–1.00] · FP 0/1 [0.00–0.79] · form dev
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-13 | haiku vs claude-opus-5 | control-helpful-error-message | adoption-adversary | 3/3 | — | PASS |
| 2026-08-13 | haiku vs claude-opus-5 | dead-end-error-message | adoption-adversary | 3/3 | — | PASS |

### Run 2026-08-13 — model opus · repo 5eac709 · selected 2 of 48 (26 shipped + 22 corpus · 22 controls) · recall 1/1 [0.21–1.00] · FP 0/1 [0.00–0.79] · form dev
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-13 | opus vs claude-opus-5 | control-export-failure-surfaces | observability-adversary | 3/3 | — | PASS |
| 2026-08-13 | opus vs claude-opus-5 | swallowed-export-failure | observability-adversary | 3/3 | — | PASS |

> **DATED CORRECTION (2026-08-15, U2) — appended per the append-only rule; applies to
> every block ABOVE this line.** Run blocks written before 2026-08-15 carry `form dev` by
> DEFAULT, not by measurement: the producer's meta dict omitted `form` and the writer
> silently defaulted it, so any run made under `--form holdout` before now is recorded as
> `dev` and is UNRECOVERABLE. Treat the `form` cell on pre-2026-08-15 blocks as
> **UNMEASURED, not `dev`**. From this date the writer REQUIRES `form` (KeyError otherwise),
> so the cell is a real measurement going forward. Old rows are never reinterpreted.

### Run 2026-08-15 — model sonnet · repo 5d74b2b · selected 4 of 52 (26 shipped + 26 corpus · 24 controls) · recall 2/2 [0.34–1.00] · FP 2/2 [0.34–1.00] · form holdout · isolation with-playbook
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-15 | sonnet vs opus | control-probe-canary-selftest | script-adversary | 1/3 | wrong-verdict-line | AMBER |
| 2026-08-15 | sonnet vs opus | control-twin-export-shares-authz-helper | security-adversary | 1/3 | wrong-verdict-line | AMBER |
| 2026-08-15 | sonnet vs opus | probe-passes-on-any-nonzero-exit | script-adversary | 3/3 | — | PASS |
| 2026-08-15 | sonnet vs opus | twin-export-command-skips-authz | security-adversary | 3/3 | — | PASS |

### Run 2026-08-16 — model sonnet · repo adc4900 · selected 20 of 70 (26 shipped + 44 corpus · 33 controls) · recall 9/10 [0.60–0.98] · FP 6/10 [0.31–0.83] · form holdout · isolation with-playbook
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-16 | sonnet vs opus | alias-branch-reimplements-authz | architecture-adversary | 0/3 | found-but-hedged | **BLOCKING FAIL** |
| 2026-08-16 | sonnet vs opus | control-csv-escape-rfc4180-complete | edge-case-adversary | 1/3 | wrong-verdict-line | AMBER |
| 2026-08-16 | sonnet vs opus | control-describe-added-to-single-source | architecture-adversary | 1/3 | found-but-hedged | AMBER |
| 2026-08-16 | sonnet vs opus | control-dump-alias-shares-authorize | architecture-adversary | 0/3 | found-but-hedged | **BLOCKING FAIL** |
| 2026-08-16 | sonnet vs opus | control-nonfinite-pct-rejected | edge-case-adversary | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-16 | sonnet vs opus | control-plan-flag-is-optout | integration-adversary | 2/3 | wrong-verdict-line | AMBER |
| 2026-08-16 | sonnet vs opus | control-plan-parity-both-surfaces | integration-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | control-probe-canary-selftest | script-adversary | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-16 | sonnet vs opus | control-probe-greps-only-attempt-output | script-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | control-probe-reads-deployed-key-in-place | script-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | control-twin-export-shares-authz-helper | security-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | csv-quote-escape-untested | edge-case-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | nan-pct-slips-range-guard | edge-case-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | plan-parity-blind-second-surface | integration-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | plan-ships-behind-opt-in-flag | integration-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | probe-certifies-a-copy-not-the-key | script-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | probe-greps-its-own-expectation | script-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | probe-passes-on-any-nonzero-exit | script-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | twin-export-command-skips-authz | security-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | write-lock-exemption-third-list | architecture-adversary | 3/3 | — | PASS |

### Run 2026-08-16 — model sonnet · repo 2c5bd46 · selected 20 of 70 (26 shipped + 44 corpus · 33 controls) · recall 8/10 [0.49–0.94] · FP 10/10 [0.72–1.00] · form holdout · isolation with-playbook
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-16 | sonnet vs opus | alias-branch-reimplements-authz | architecture-adversary | 1/3 | found-but-hedged | AMBER |
| 2026-08-16 | sonnet vs opus | control-csv-escape-rfc4180-complete | edge-case-adversary | 0/3 | found-but-hedged | **BLOCKING FAIL** |
| 2026-08-16 | sonnet vs opus | control-describe-added-to-single-source | architecture-adversary | 2/3 | found-but-hedged | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-16 | sonnet vs opus | control-dump-alias-shares-authorize | architecture-adversary | 0/3 | found-but-hedged | **BLOCKING FAIL** |
| 2026-08-16 | sonnet vs opus | control-nonfinite-pct-rejected | edge-case-adversary | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-16 | sonnet vs opus | control-plan-flag-is-optout | integration-adversary | 2/3 | wrong-verdict-line | **BLOCKING FAIL** (AMBER×2) |
| 2026-08-16 | sonnet vs opus | control-plan-parity-both-surfaces | integration-adversary | 1/3 | wrong-verdict-line | AMBER |
| 2026-08-16 | sonnet vs opus | control-probe-canary-selftest | script-adversary | 0/3 | wrong-verdict-line | **BLOCKING FAIL** |
| 2026-08-16 | sonnet vs opus | control-probe-greps-only-attempt-output | script-adversary | 1/3 | wrong-verdict-line | AMBER |
| 2026-08-16 | sonnet vs opus | control-probe-reads-deployed-key-in-place | script-adversary | 2/3 | wrong-verdict-line | AMBER |
| 2026-08-16 | sonnet vs opus | control-twin-export-shares-authz-helper | security-adversary | 1/3 | wrong-verdict-line | AMBER |
| 2026-08-16 | sonnet vs opus | csv-quote-escape-untested | edge-case-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | nan-pct-slips-range-guard | edge-case-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | plan-parity-blind-second-surface | integration-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | plan-ships-behind-opt-in-flag | integration-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | probe-certifies-a-copy-not-the-key | script-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | probe-greps-its-own-expectation | script-adversary | 2/3 | found-but-hedged | AMBER |
| 2026-08-16 | sonnet vs opus | probe-passes-on-any-nonzero-exit | script-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | twin-export-command-skips-authz | security-adversary | 3/3 | — | PASS |
| 2026-08-16 | sonnet vs opus | write-lock-exemption-third-list | architecture-adversary | 3/3 | — | PASS |

### Run 2026-08-16 — model haiku · repo f1c948f · selected 4 of 54 (26 shipped + 28 corpus · 25 controls) · recall 2/2 [0.34–1.00] · FP 0/2 [0.00–0.66] · form dev · isolation with-playbook
Population: control-cqa-fair-pair=current@22c715a105f0 · control-cqa-verifier-overflag=current@68669aa70b58 · cqa-greedy-oracle=current@0a273ff7a952 · cqa-not-clean-control=current@e8eb97a12868
| date | model | scenario | agent | runs | mode | verdict |
|---|---|---|---|---|---|---|
| 2026-08-16 | haiku vs claude-fable-5 | control-cqa-fair-pair | control-quality-adversary | 3/3 | — | PASS |
| 2026-08-16 | haiku vs claude-fable-5 | control-cqa-verifier-overflag | control-quality-adversary | 3/3 | — | PASS |
| 2026-08-16 | haiku vs claude-fable-5 | cqa-greedy-oracle | control-quality-adversary | 3/3 | — | PASS |
| 2026-08-16 | haiku vs claude-fable-5 | cqa-not-clean-control | control-quality-adversary | 3/3 | — | PASS |
