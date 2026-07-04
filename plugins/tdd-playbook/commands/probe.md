---
description: Run a Playbook §5a UX probe — an intent-only agent drives the real interface; deterministic oracles block, agent signals are trend lines.
argument-hint: <user intent, e.g. "sign up for the meeting"> [N runs, default 3]
---

Run a **UX probe** (Playbook §5a) for the intent: $ARGUMENTS

A probe answers what a §5 journey structurally can't: *can a fresh actor who does NOT know
where the button is accomplish this goal?* The agent is the probe; the verdict is NOT.

1. **Guardrails first (refuse, don't improvise):** staging/fixtures target only — never live
   user data (page/screen content is a prompt-injection surface). CRITICAL journey only —
   probes are slow and metered; don't probe every flow. LLM keys stay harness-side. Engine
   telemetry/cloud-sync/built-in judges OFF. Dangerous actions (raw JS eval, web search)
   excluded from the action space. Per-run step/token caps set.
2. **Pick the driver from the §5a table** by detecting this repo's outermost interface and
   stack (apply repo-local conventions per the Playbook's composition rules): web/TS →
   Stagehand · web/Python → browser-use via `cdp_url` · Telegram mini-app → browser engine +
   `Telegram.WebApp` shim (native chrome stubbed into the action space) · TUI → tmux/PTY loop
   (`capture-pane`/`send-keys`) · Telegram bot → dispatcher harness / test DC · MCP → agent-SDK
   client with only the tool list. The HARNESS owns the browser/PTY and its own evidence
   capture (network/HAR, console, per-step transcript + snapshots).
3. **Phrase the intent as a GOAL, never a UI hint.** Prefer the §0 plan's "UX tests" bullets
   as the source. "Sign up for the meeting" — NOT "click the blue Sign Up button"; hints
   defeat the probe's purpose. If the only phrasing you can write leaks UI structure, say so —
   that's a finding about the plan, not a reason to hint.
4. **Run N times (default 3; never trust a delta from 1).** Persist per-run artifacts:
   transcript, snapshots, evidence captures, cost.
5. **Apply the oracle split — the load-bearing rule:**
   - **BLOCKING (deterministic, harness-owned):** persisted effect (DB row / file / state),
     no-5xx from the harness's own network capture, console-error budget, no forbidden hosts.
   - **TREND (never a gate):** agent-reported success rate, steps-to-done vs baseline,
     tokens/cost, friction events. A run where the agent claims success but the persistence
     oracle is red is a LYING-UI finding — the highest-value probe outcome; flag it loudly.
6. **Report:** `Probe: "<intent>" · oracles PASS/FAIL (each named) · success k/N · median
   steps · cost` + friction list + trend vs prior runs if history exists. **A failed-goal
   transcript is a deliverable, not a flaky test** — file it as a UX bug quoting where the
   agent got lost ("couldn't find how to cancel").
7. **First probe in a repo:** register the `ux_probe` marker (non-blocking lane), record the
   artifacts location + driver choice in the repo's testing addendum so this composes
   automatically next time, and recommend `ux-probe-calibrator` be dispatched before the
   probe's verdicts are trusted (§5a: a probe that never fails a plant is theater).
