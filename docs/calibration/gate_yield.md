# Gate yield record (R4 — derived from telemetry, never self-report)

One committed row per gate per calibration cycle. blocks/warns = frictions fired; overrides = journaled unlocks adjudicating a block as false-positive; suppressed = findings that fired while the gate was demoted to off (a muzzled gate, never a quiet one). Candidates need >=2 cycles — see gate_yield.py.

| date | gate | blocks | warns | overrides | suppressed |
|---|---|---|---|---|---|
| 2026-07-30 | testlock | 2 | 0 | 7 | 0 |
| 2026-07-30 | testweaken | 1 | 0 | 0 | 0 |
