# Readable-surface usage record (v1.34.0 D5 — the R&D instrument)

One committed row per scenario per cycle, drained from the same event log as the
gate record. `uses` is MACHINE-written (the facts CLI logging its own invocation) —
the denominator; `dispatched` / `changed_a_decision` count the agent's own
usage-note events (source: agent), the same self-report split guard_response.md
uses: a note can move its two columns and can never move `uses`. A note whose
scenario saw no machine use this cycle is an ORPHAN — reported, never counted.
Absent data is UNMEASURED, never zero. Usage measures whether the surface was
ASKED, not whether it helped — the keep/kill criterion is rows nobody asks about.

schema: 1

| date | scenario | uses | dispatched | changed_a_decision |
|---|---|---|---|---|
| 2026-08-15 | S41 | 1 | 0 | 0 |
| 2026-08-15 | full | 8 | 0 | 0 |
| 2026-08-16 | full | 1 | 0 | 0 |
| 2026-08-16 | full | 1 | 0 | 0 |
| 2026-08-16 | full | 1 | 0 | 0 |
| 2026-08-16 | full | 1 | 0 | 0 |
| 2026-08-16 | full | 1 | 0 | 0 |
| 2026-08-16 | full | 1 | 0 | 0 |
