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
| 2026-07-27 | testlock | 1 | 0 | 1 | 0 |
| 2026-07-27 | testweaken | 2 | 0 | 2 | 0 |
| 2026-08-10 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-07-27 | testlock | 1 | 0 | 1 | 0 |
| 2026-07-27 | testweaken | 2 | 0 | 2 | 0 |
| 2026-08-10 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-07-27 | testlock | 1 | 0 | 1 | 0 |
| 2026-07-27 | testweaken | 2 | 0 | 2 | 0 |
| 2026-08-10 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-07-27 | testlock | 1 | 0 | 1 | 0 |
| 2026-07-27 | testweaken | 2 | 0 | 2 | 0 |
| 2026-08-10 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-07-27 | testlock | 1 | 0 | 1 | 0 |
| 2026-07-27 | testweaken | 2 | 0 | 2 | 0 |
| 2026-08-10 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-08-06 | testlock | 6 | 0 | 6 | 0 |
| 2026-08-06 | testweaken | 1 | 0 | 1 | 0 |
| 2026-07-27 | testlock | 1 | 0 | 1 | 0 |
| 2026-07-27 | testweaken | 2 | 0 | 2 | 0 |
| 2026-08-10 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-07-27 | testlock | 1 | 0 | 1 | 0 |
| 2026-07-27 | testweaken | 2 | 0 | 2 | 0 |
| 2026-08-10 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-01 | testlock | 1 | 0 | 1 | 0 |
| 2026-09-02 | testlock | 1 | 0 | 1 | 0 |
