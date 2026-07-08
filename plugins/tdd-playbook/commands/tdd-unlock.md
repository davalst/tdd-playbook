---
description: Release the TEST-LOCK with a journaled reason (reviewed by /grade). The reason is the point — an unlock without one is refused.
argument-hint: <why the lock must lift — e.g. "test asserted the wrong rounding; corrected per plan review">
---

Release the **TEST-LOCK** (Playbook §1) — reason: $ARGUMENTS

1. State the reason honestly and specifically. Legitimate: the test itself is wrong (wrong
   expected value, over-strict property, tests a non-contract); the plan changed at review;
   implementation is green and the cycle is complete. NOT legitimate: "the test is
   inconvenient", "need to adjust assertions to match output" (that is H2 — the exact move
   the lock exists to stop; if the output is right and the test is wrong, SAY WHY the test
   is wrong).
2. Run: `python3 "${CLAUDE_PLUGIN_ROOT}/bin/tdd_lock.py" unlock --reason "$ARGUMENTS"`
   (refused under 10 characters — a reason, not a mumble).
3. If the reason was "the test is wrong": fix the test, re-verify RED for the right reason
   (`red-first-verifier` on any doubt), re-lock, continue.

The journal (`.claude/tdd-lock-journal.jsonl`) is read by `/grade`: frequent unlocks, or
unlock reasons that pattern-match "adjusted test to match output", are graded as
honor-system breaches (§13).
