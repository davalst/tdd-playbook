# Gate yield record (R4 — derived from telemetry, never self-report)

One committed row per gate per calibration cycle. blocks/warns = frictions fired; overrides = ALL journaled unlocks; fp = the subset whose journaled reason-class is `gate-wrong` — the only kind that adjudicates a block as a false positive; suppressed = findings that fired while the gate was demoted to off (a muzzled gate, never a quiet one). Candidates need >=2 cycles and are computed from fp, never from overrides — see gate_yield.py.

DATED CORRECTION (v1.27, pre-fix sha 119e2de): rows on or before 2026-08-05 have NO fp cell. Before that fix `overrides` was read as 'blocks adjudicated false-positive', so four cycles of the normal red-first lock/implement/unlock rhythm printed RETIREMENT CANDIDATE: testlock with zero real false positives. Those rows mix phase/feature-end/test-wrong/gate-wrong in unknown proportion and are UNMEASURED — they are left byte-identical and are never reinterpreted, because inferring a class into a durable record is the fabrication this fix exists to end.

| date | gate | blocks | warns | overrides | suppressed | fp |
|---|---|---|---|---|---|---|
| 2026-07-30 | testlock | 2 | 0 | 7 | 0 |
| 2026-07-30 | testweaken | 1 | 0 | 0 | 0 |
| 2026-08-03 | flaky | 0 | 1 | 0 | 0 |
| 2026-08-03 | testlock | 3 | 0 | 5 | 0 |
| 2026-08-03 | testweaken | 2 | 0 | 0 | 0 |
| 2026-08-04 | overmock | 0 | 3 | 0 | 0 |
| 2026-08-04 | testlock | 3 | 0 | 2 | 0 |
| 2026-08-05 | testlock | 1 | 0 | 0 | 0 |
| 2026-08-05 | testlock | 1 | 0 | 2 | 0 |
| 2026-08-06 | testlock | 6 | 0 | 4 | 0 | 0 |
| 2026-08-06 | testweaken | 1 | 0 | 0 | 0 | 0 |
| 2026-08-06 | exhaustive | 0 | 2 | 0 | 0 | 0 |
| 2026-08-06 | exitcode | 0 | 24 | 0 | 0 | 0 |
| 2026-08-06 | redlock | 0 | 1 | 0 | 0 | 0 |
| 2026-08-12 | exhaustive | 0 | 1 | 0 | 1 | 0 |
| 2026-08-12 | exitcode | 0 | 196 | 0 | 43 | 0 |
| 2026-08-12 | tagguard | 7 | 0 | 0 | 0 | 0 |
| 2026-08-12 | testlock | 1 | 0 | 1 | 0 | 0 |
| 2026-08-12 | exitcode | 0 | 0 | 0 | 1 | 0 |
| 2026-08-12 | exitcode | 0 | 0 | 0 | 1 | 0 |
| 2026-08-13 | exitcode | 0 | 0 | 0 | 2 | 0 |
| 2026-08-13 | exitcode | 0 | 0 | 0 | 1 | 0 |
| 2026-08-13 | exitcode | 0 | 0 | 0 | 2 | 0 |
