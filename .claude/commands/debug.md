---
description: Feedback-loop-first debugging — build a tight reproduction loop BEFORE theorizing, form falsifiable hypotheses, fix only at root cause, then pin a regression test.
argument-hint: <the bug / symptom to diagnose>
---

Diagnose this bug the Playbook way — loop first, theory second: $ARGUMENTS

**HARD GATE — no theorizing before a reproduction loop exists.** If you catch yourself reading
code to build a theory before you can RUN the bug, stop. First build the tightest feedback loop
you can, and paste its invocation + output before going further. Pick the tightest available:
failing unit test → curl/HTTP call → CLI one-liner → headless-browser script → replay a captured
trace → throwaway harness → property/fuzz loop → bisection → differential (good-vs-bad) → last
resort, a scripted manual checklist. **Tighter = faster, sharper, more deterministic** — a
2-second deterministic loop beats a 30-second flaky one. For a non-deterministic bug, first raise
the reproduction rate (a 50%-flake is debuggable; 1% is not).

Then:
1. **Reproduce** — run the loop once; paste the exact command + observed vs expected output.
2. **Hypotheses** — list 3–5 ranked, FALSIFIABLE hypotheses, each with a stated prediction ("if
   this is the cause, then X will be true"). If you can't state the prediction, it's a vibe, not
   a hypothesis. Use tagged debug logs (`[DEBUG-xyz]`) so cleanup is one grep.
3. **Test the top hypothesis against the loop** — confirm or kill it by its prediction, not by
   vibes. **3-strike rule:** after 3 failed hypotheses, STOP and escalate (ask the human / add
   instrumentation / consider it may be architectural) — don't thrash.
4. **Root cause only** — no fix until the root cause is identified and confirmed by the loop. If
   there's no correct seam to fix at, THAT is the finding (flag the architecture; don't force a
   false-confidence patch).
5. **Pin it** — write the failing regression test FIRST (Playbook §1 IRON RULE), confirm it goes
   red on the bug and green on the fix, then remove the debug logs.
