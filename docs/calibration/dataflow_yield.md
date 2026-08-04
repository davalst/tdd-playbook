# Dataflow-sweep yield record (§6c D13b — committed rows, mechanical trend)

One committed row per sweep per calibration cycle, parsed from dataflow_sweeps.py's pinned summary line. The excluded share (exempted/checked) is a TREND claim — undetectable from one run; `gate_yield.py dataflow-trend` is the comparator.

SERIES NOTE 2026-08-04 (v1.25): counting semantics changed — `checked` now credits only
sites actually VERIFIED (unresolvable/dynamic sites no longer count toward it), and
`exempted` may include NAMED dynamic-site exemptions. Rows before this date used the
older accounting; compare shares across the boundary with that in mind.

| date | sweep | checked | violations | exempted | unresolvable |
|---|---|---|---|---|---|
| 2026-08-03 | render-pairing | 152 | 0 | 0 | 0 |
