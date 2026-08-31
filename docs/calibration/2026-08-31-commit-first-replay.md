# D3 replay — commit-first vs anchored. SCORING RULE, WRITTEN BEFORE THE RESULTS.

Committed before any of the six agents returned. If this file is edited after the results
land, the edit is visible in git and the experiment is void.

## Design

Subject: the three plans this repo REJECTED on 2026-08-28/29, each with a documented cause
of death. `architecture-adversary` reviews each in two arms:

- **A (anchored)** — reads the plan first, commit-first step explicitly suppressed.
- **B (commit-first)** — forms its own prior from the repo, THEN reads the plan.

Six dispatches, blind: no agent was told the plans were rejected, or why.

## Ground truth — the objection that actually killed each plan

| plan | the killing objection |
|---|---|
| drift-detector | The capability already existed as doctrine; the tool's extraction caught 1 of 3 real failures, and its frozen fixtures pinned commits that exist on NO ref after a rebase, so CI could never fetch them. |
| replay-calibration | The numbers it proposed to compute were **already sitting in a committed file** — `docs/calibration/gate_yield.md` holds the suppressed counts. |
| gate-provenance | The data it needs **does not exist**: gate telemetry carries no tree identifier, the run store spans 0.7 hours rather than a week, and all three named consumers of that store were wrong (one writer, one deleter, no reader). |

Every one is the same shape: **the premise was false and one cheap look would have shown it.**
That is the shape commit-first is supposed to catch, because an agent that forms its own view
of the repo FIRST has already looked at the thing the plan mis-describes.

## Scoring — decided now

Per review, one binary: **did it name the killing objection?** Naming means identifying the
false premise (already exists / the data is not there / the fixtures cannot resolve) — not
merely rating the plan poorly, and not listing generic design criticism. Verdict wording is
NOT scored; a review that says BAND-AID for the wrong reason scores zero.

## Pre-committed decision rule

- **B ≥ A + 2** (of 3) → commit-first earns its place. Keep D1.
- **B == A + 1** → weak, ambiguous at n=3. Keep D1, state the weakness plainly, do not claim
  the paper's effect reproduced here.
- **B ≤ A** → **the clause is ceremony. REVERT D1 in full**, including the tests, and record
  the reversal. A change that cannot change a verdict on the three artifacts that motivated
  it does not belong in twelve briefs.

## Stated limits, before seeing anything

n=3, one adversary, one model, no repetition — this cannot produce a rate and will not be
reported as one. It is a kill-test, not a measurement: it can refute D1, it cannot confirm it.
A `k`-heavy `Prior:` line in arm B is also not evidence of anything by itself; self-reported
counts are the weakest signal here and are recorded, not scored.
