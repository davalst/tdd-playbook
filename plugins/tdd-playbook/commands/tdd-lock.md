---
description: TEST-LOCK — commit the red tests, then make them mechanically read-only while implementing to green (the strongest validated anti-gaming defense).
argument-hint: <test file(s) to lock — or blank to lock the tests just written red>
---

Engage the **TEST-LOCK** (Playbook §1, HACK_CATALOG H2/H5) for: $ARGUMENTS

The documented top agent attack vector is editing/weakening the failing test instead of
fixing the code. The lock converts §1's iron rule from an honor system into a mechanism —
the same upgrade `/claims` got from `verify_citations`.

1. **Preconditions:** the tests exist, are RED for the right reason (a behavioral
   assertion — dispatch `red-first-verifier` if there's any doubt), and are COMMITTED.
   Never lock uncommitted tests — the commit is the tamper-evident baseline.
2. **Lock:** `python3 "${CLAUDE_PLUGIN_ROOT}/bin/tdd_lock.py" lock <test files...>`
   Include every test file authored from the current plan. The `test_lock_guard` hook now
   BLOCKS edits to those files AND to the verifier surface (conftest.py, pytest/jest/vitest
   configs) until unlock.
3. **Implement to green** — source edits only. If a locked test blocks you, that is the
   system working: the answer is almost always "fix the source."
4. **If the TEST itself is genuinely wrong** (wrong expected value, over-strict invariant):
   `/tdd-unlock` with a real reason — never work around the guard.
5. **On green:** run the suite, report Tripwire N/N as usual, then unlock with reason
   "green — implementation complete" (the journal entry closes the cycle for `/grade`).

Report: `Test-lock: N file(s) locked · <commit sha of the red tests>`.
