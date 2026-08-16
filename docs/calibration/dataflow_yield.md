# Dataflow-sweep yield record (§6c D13b — committed rows, mechanical trend)

One committed row per sweep per calibration cycle, parsed from dataflow_sweeps.py's pinned summary line. The excluded share (exempted/checked) is a TREND claim — undetectable from one run; `gate_yield.py dataflow-trend` is the comparator.

schema: 2

SERIES MIGRATION 2026-08-04 (v1.25, arch-F4): counting semantics changed — `checked` now
credits only sites actually VERIFIED, and `exempted` may include NAMED dynamic-site
exemptions. The schema stamp above is MECHANICAL: `gate_yield.py dataflow-rollup` refuses
to append when the producer's schema differs, so a future semantics change forces this
same conscious migration instead of a prose note. The pre-change row is retired below
(kept for the human record, invisible to the comparator).

| date | sweep | checked | violations | exempted | unresolvable |
|---|---|---|---|---|---|
retired (schema 1): 2026-08-03 · render-pairing · 152 · 0 · 0 · 0
| 2026-08-04 | render-pairing | 159 | 0 | 0 | 0 |
| 2026-08-05 | render-pairing | 159 | 0 | 0 | 0 |
| 2026-08-05 | render-pairing | 159 | 0 | 0 | 0 |
| 2026-08-06 | render-pairing | 173 | 0 | 0 | 0 |
| 2026-08-12 | render-pairing | 316 | 0 | 0 | 2 |
| 2026-08-12 | render-pairing | 316 | 0 | 0 | 2 |
| 2026-08-12 | render-pairing | 316 | 0 | 0 | 2 |
| 2026-08-13 | render-pairing | 316 | 0 | 0 | 2 |
| 2026-08-13 | render-pairing | 316 | 0 | 0 | 2 |
| 2026-08-13 | render-pairing | 316 | 0 | 0 | 2 |
| 2026-08-13 | render-pairing | 316 | 0 | 0 | 2 |
| 2026-08-13 | render-pairing | 316 | 0 | 0 | 2 |
| 2026-08-13 | render-pairing | 316 | 0 | 0 | 2 |
| 2026-08-13 | render-pairing | 316 | 0 | 0 | 2 |
| 2026-08-13 | render-pairing | 316 | 0 | 0 | 2 |
| 2026-08-15 | render-pairing | 323 | 0 | 0 | 2 |
| 2026-08-16 | render-pairing | 323 | 0 | 0 | 2 |
| 2026-08-16 | render-pairing | 323 | 0 | 0 | 2 |
| 2026-08-16 | render-pairing | 323 | 0 | 0 | 2 |
| 2026-08-16 | render-pairing | 323 | 0 | 0 | 2 |
| 2026-08-16 | render-pairing | 323 | 0 | 0 | 2 |
| 2026-08-16 | render-pairing | 323 | 0 | 0 | 2 |
