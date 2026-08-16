# Guard-response record (§12 v1.28 — was the block complied with, or routed around?)

One committed row per gate per cycle. `blocks` is written by the HOOKS (mechanical, via
_common.emit); `accounted` counts the agent's own three-clause responses recorded with
`bin/guard_note.py`. Self-report can move `accounted`; it cannot touch `blocks` — so an
agent that simply stays quiet produces a visible `unaccounted`, not a clean record.
`elsewhere` counts responses admitting the blocked action was performed by another
route: that column should be 0 forever, and any other value is a finding.

schema: 1

| date | gate | blocks | accounted | unaccounted | elsewhere |
|---|---|---|---|---|---|
| 2026-08-06 | testlock | 6 | 0 | 6 | 0 |
| 2026-08-06 | testweaken | 1 | 0 | 1 | 0 |


**DATED CORRECTION 2026-08-06 (v1.29).** 88 rows were removed from this record: they were test exhaust, not measurements.
`test_gate_yield.py` drove the real `gate_yield.py rollup` seven times, and only two of
those call sites passed `--response-md`, so `default_response_md()` fell through to THIS
file and wrote fixture-dated rows (2026-07-27, 2026-08-10, 2026-09-0x) into a committed
instrument record. Same class as the 2026-07-28 G5 incident one file over; it survived
because nothing asserted this file was untouched by a suite run. The leak is now closed
at the source (`run_gy` redirects `TDD_PLAYBOOK_RESPONSE_MD` unconditionally) and pinned
by a byte-identity check at the end of that suite. The two rows above are the real ones —
the first genuine guard-response cycle, and its honest reading is 0 of 7 accounted.
| 2026-08-12 | tagguard | 7 | 3 | 4 | 1 |
| 2026-08-12 | testlock | 1 | 1 | 0 | 0 |
| 2026-08-16 | testweaken | 1 | 0 | 1 | 0 |
