---
description: Release the TEST-LOCK with a journaled reason (reviewed by /grade). The reason is the point — an unlock without one is refused.
argument-hint: <why the lock must lift — e.g. "test asserted the wrong rounding; corrected per plan review" (pick a --class: phase | feature-end | test-wrong | gate-wrong)>
---

Release the **TEST-LOCK** (Playbook §1) — reason: $ARGUMENTS

1. **Pick the CLASS**, then state the reason honestly and specifically. The class is the
   closed vocabulary the yield instrument measures — prose alone is not enough:

   | `--class` | when | counts as a false positive? |
   |---|---|---|
   | `phase` | phase boundary: green, opening up to add the next red batch, will re-lock | no |
   | `feature-end` | the cycle/feature/release is complete; the lock has no more work to guard | no |
   | `test-wrong` | the TEST was wrong — wrong expected value, over-strict property, tests a non-contract | no |
   | `gate-wrong` | the GATE was wrong — it blocked work it had no business blocking | **YES — the only one** |

   `test-wrong` is NOT a false positive: stopping, saying why the test was wrong, and
   re-verifying red is the lock *working*. Only `gate-wrong` says the friction bought
   nothing, and it is the one class that can drive a guard's retirement — so it demands ≥30
   characters naming WHICH block fired and why it was wrong, and is REFUSED below that bar.
   Do not reach for it because it sounds exculpatory; a phase-shaped reason claiming it is
   flagged for `/grade`. NOT legitimate under any class: "the test is inconvenient", "need to
   adjust assertions to match output" (that is H2 — the exact move the lock exists to stop).
2. Run: `python3 "${CLAUDE_PLUGIN_ROOT}/bin/tdd_lock.py" unlock --reason "$ARGUMENTS" --class <class>`
   (the reason is refused under 10 characters — a reason, not a mumble; omitting `--class`
   records UNCLASSIFIED, which measures nothing in either direction).
3. If the reason was "the test is wrong": fix the test, re-verify RED for the right reason
   (`red-first-verifier` on any doubt), re-lock, continue.

The journal (`.claude/tdd-lock-journal.jsonl`) is read by `/grade`: frequent unlocks, unlock
reasons that pattern-match "adjusted test to match output", and any entry carrying
`class_mismatch: true` (a phase-shaped reason claiming `gate-wrong`) are graded as
honor-system breaches (§13). The class also rides to the yield instrument, where only
`gate-wrong` counts a block as adjudicated — so mis-classing is how a guard gets retired on
a lie.
