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

## Final scoresheet — all six

| plan | A (anchored) | B (commit-first) |
|---|---|---|
| drift-detector | **HIT** — "already shipped" ×2, ZERO `Consumes` matches | **HIT** — verified `_CITE` returns [], and `d102bd9`/`57d1ffa` unreachable |
| replay-calibration | **HIT** — "the number is already in a committed file", `gate_yield.md` suppressed column | **HIT** — same premise falsified, plus the debt names its own remedy |
| gate-provenance | **HIT** — one writer/one deleter/zero readers; window is 15.9h not a week; **12** phrasings | **HIT** — prose trigger; `gate_plan.affected_plan` as the reuse |

**A = 3/3. B = 3/3. B == A.**

## Verdict, per the rule committed before the results

`B <= A` → **the clause is ceremony. REVERT D1 in full.** Executed.

## Why the test could not have said otherwise — recorded, NOT used to avoid the revert

**Arm A scored 3 of 3. The experiment had no headroom.** A design that cannot show
improvement cannot supply evidence of improvement, and I did not notice that when I chose
the subjects — the three plans were killed by objections `architecture-adversary` finds
reliably from either direction, so the ceiling was there before the first dispatch.

That is a flaw in MY experiment, not a defence of the clause. The rule stands as written and
the revert is executed. What the flaw changes is only what the result licenses:

- It is **NOT** established that commit-first does nothing. The test could not have detected
  it if it did.
- It **IS** established that the clause did not change a single verdict on the three artifacts
  that motivated building it. That was the bar I set, and it was not met.

Compounding, and flagged before the results landed: the subjects are `-REJECTED` documents
that partly state their own kill reasons, which hands arm A a hint.

## What a clean re-run would need

Subjects where the anchored baseline actually FAILS — the arm-A misses are the only place a
difference can show. Candidates: plans that were APPROVED and later turned out wrong, where no
reviewer caught the problem at the time. Until such a set exists, this question stays open and
the clause stays out.

## Kept, because they are unrelated to D1 and independently earned

- The `gate_yield` rollup crash arm A found — REPRODUCED, red-first regression, fixed.
- The text-is-product/text-describes-product rule.
- The escape ledger.
