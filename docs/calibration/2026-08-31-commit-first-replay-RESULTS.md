# D3 replay — RESULTS (scored against the rule in `2026-08-31-commit-first-replay.md`)

Kept separate from the pre-registered rule file so that file stays untouched and diffable.

## Running scoresheet

| # | plan | arm | named the killing objection? | what it named |
|---|---|---|---|---|
| 1 | drift-detector | A (anchored) | **YES** | F2 "already shipped" (capability_registry.py:262-293 already implements typed refs); F5 "D2 is already built" (f5318d3); F1 "the data is not there" — exhaustive grep, ZERO `Consumes` matches in the motivating plan |

## METHODOLOGICAL FLAW, found on the first result — recorded before the rest land

**The subject documents are contaminated, and the contamination favours arm A.**

The three subjects are named `-REJECTED`, and at least `drift-detector` **states inside the
document why its own predecessor was killed** — review #1 quotes "the three reasons given
(nominal reuse, dangling calibration refs, Codex non-shipping)" as already present in the plan.

So an ANCHORED reviewer, which reads the plan first, is handed part of the ground truth by the
artifact itself. A COMMIT-FIRST reviewer forms its prior before seeing that text.

This does not void the experiment, but it changes what a result can mean:

- **B > A is now a STRONGER result** than designed — arm B wins despite arm A getting a hint.
- **A >= B is WEAKER evidence than designed** and must NOT be read as "commit-first does
  nothing." It may only mean the hint was sufficient.

The pre-committed decision rule is UNCHANGED — moving it now is exactly the goalpost shift the
pre-registration exists to prevent. If the outcome is `B <= A`, D1 still gets reverted per the
rule, and this contamination is recorded as the reason the reversal is provisional rather than
conclusive, with a clean re-run (subjects stripped of their rejection prose) as the follow-up.
