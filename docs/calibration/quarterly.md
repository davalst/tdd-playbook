# Quarterly bundle record — the ~100-day clock (lift/ratchet D6)

One dated row per completed quarterly bundle. The bundle: **HACK_CATALOG refresh ritual** ·
**lift diagnostic read** (once unblocked by the holdout split + stub-freeze — see the
`calibration-loop` quarterly debt entry) · **cross-tier calibration row** (once funded).

This file IS the trigger: `check_staleness.py --history docs/calibration/quarterly.md
--max-age-days 100 --warn-only` runs in the release gate (CLAUDE.md), so a lapsed quarter is
loud on every release — replacing the earlier idea of a reminder clause inside a
calibration-run print (a reminder inside a run someone must remember to run is decoration,
and refreshing the catalog would have silenced an unrelated reminder). The registry debt
entry (expires 2026-11-01) is the hard backstop.

| date | bundle | item | owner | status |
|---|---|---|---|---|
| 2026-07-01 | quarterly | HACK_CATALOG refresh — catalog 2026.07 (month-granularity per the catalog's own clock, day-1 convention, matches catalog_staleness()) | david | DONE |
