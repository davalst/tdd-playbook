# Calibration scoreboard

Public record of the Playbook's own planted-defect calibration (see `calibration/` for the
harness). Each run appends a **run block** to `history.md`: a header with the repo SHA, the
DERIVED suite composition (`selected N of M — shipped + corpus · controls`), and **two
numbers, not one** — recall (plants caught) and false-positive rate (clean controls wrongly
flagged) — followed by one row per scenario with its `k/n` repeat count, failure mode, and a
three-state verdict (`PASS` at k/k, `AMBER` on a partial catch, `**BLOCKING FAIL**` at 0/k;
`INVALID` rows mean nothing was measured and never extend freshness).

Since v1.17 each scenario runs **3× by default** (§5a — one roll of a probabilistic verifier
is a coin flip, not a measurement), an AMBER on consecutive runs promotes to BLOCKING
mechanically, and `gate_yield.md` (same directory) records the mirror question: which gates
still earn their friction.

The claim this backs: *our verifiers are tested on a schedule against plants — including
plants they have never seen — and here are BOTH numbers.* A gap in the history is itself a
finding (the schedule is part of the product — §13). The scoreboard's own integrity is
mechanical: `calibration/check_scoreboard_integrity.py` proves history append-only, the
approved corpus immutable, and oracles never weakened without a journaled reason.
