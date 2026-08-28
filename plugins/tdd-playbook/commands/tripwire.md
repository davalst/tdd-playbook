---
description: Run the Playbook §6 Tripwire — verify every plan deliverable is BUILT + WIRED-IN + ACTIVATED + EXERCISED, proven through the production composition root, report N/N.
argument-hint: [deliverable list or plan reference]
---

Run the **Tripwire** wiring check against the current plan's deliverables: $ARGUMENTS

For EACH deliverable, verify and report four things separately (don't round up):
- **BUILT** — its route/entry/tool/command is actually registered (cite file:line).
- **WIRED-IN** — a real user entry point references it (UI button / CLI command / MCP
  tool / nav). A registration or export is NOT a wire — trace who reaches it. And prove it
  through the PRODUCTION composition root: the real daemon/app factory, the real per-platform
  agent build — NOT a test fixture that wires the component up itself (the documented root
  cause of whole-subsystem darkness: components that work in a fixture that never exists in
  production). Reachability checks must be SYMMETRIC — everything registered is reachable in
  the real build AND everything reachable is registered.
- **ACTIVATED** — its state in the SHIPPED default config: on, or off behind a NAMED,
  user-reachable switch (UI toggle / wizard step / documented command). Off with no on-switch
  is RED. A gate that depends on another DISABLED gate must report itself dark, never
  silently no-op. For a USER-CONTROLLABLE (toggle-gated) deliverable this is a TWO-surface
  test: code that merely reads the flag is the route-exists trap — the switch must be reachable
  through the project's canonical feature-control surface (the `/features`/settings equivalent)
  AND visible in its health/status surface (the doctor/dark-inventory equivalent). Dark in
  either surface is RED. If the repo carries a capability registry, the deliverable's entry is
  part of this proof — run:

      python3 "${CLAUDE_PLUGIN_ROOT}/bin/capability_registry.py" validate

  and paste the summary line (a FAIL here is a RED deliverable).
- **MEANS** — did the implementation use what the plan SAID it would use? The four legs above
  ask whether each DELIVERABLE exists and is wired; this asks whether the plan's stated
  *means* were the ones actually used. They are different questions, and only the first was
  ever checked: on 2026-08-28 an auditor returned a clean-looking `3/5` on work whose approved
  plan said "refounded on `bin/verify_citations.py`" while the shipped code referenced it zero
  times. Nothing owned that gap, because a means is not a deliverable.
  Enumerate the plan's NORMATIVE means — the files, functions and mechanisms it committed to
  building on. For each, report `honoured`, `acknowledged` (deliberately not used, with the
  reason), or `drift` (silently not used). A file the plan merely MENTIONS is not a means;
  current-state descriptions, examples and rejected alternatives are not commitments.
  Report the forced line:

      Means: <H> honoured · <A> acknowledged · <D> drift

  A nonzero `drift` is not automatically RED — a deviation can be right — but it must be
  named, because the failure this catches is the silent kind: the plan said X, the code did
  Y, and no one noticed the difference existed.

- **EXERCISED** — point at a specific `file::test_name` (or this repo's equivalent) and
  confirm it is DEFINED and NOT skip-marked. A grep proving a *reference* is not enough;
  a hollow button or a skipped test must TRIP the Tripwire.

Use the repo's own test runner/markers. Where a deliverable fails any of the four, mark
it RED with the exact gap. Report `Tripwire: N/N` (green/total). If the plan carries a §0
flow table (§6c), also verify each flow row's liveness test is named and GREEN and report
`Tripwire: N/N (+ FLOWS M/M)` — a deliverable can be four-leg green while its flow
dead-ends. It is a FLOOR — never add a hollow stub or a fake on-switch to go green. If a
behavioral test is missing, write it (red-first) rather than reporting the deliverable
green.
