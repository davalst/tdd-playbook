# Gate yield record (R4 — derived from telemetry, never self-report)

One committed row per gate per calibration cycle. blocks/warns = frictions fired; overrides = journaled unlocks adjudicating a block as false-positive; suppressed = findings that fired while the gate was demoted to off (a muzzled gate, never a quiet one). Candidates need >=2 cycles — see gate_yield.py.

| date | gate | blocks | warns | overrides | suppressed |
|---|---|---|---|---|---|
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
