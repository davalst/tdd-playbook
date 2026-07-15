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
- **EXERCISED** — point at a specific `file::test_name` (or this repo's equivalent) and
  confirm it is DEFINED and NOT skip-marked. A grep proving a *reference* is not enough;
  a hollow button or a skipped test must TRIP the Tripwire.

Use the repo's own test runner/markers. Where a deliverable fails any of the four, mark
it RED with the exact gap. Report `Tripwire: N/N` (green/total). It is a FLOOR — never add
a hollow stub or a fake on-switch to go green. If a behavioral test is missing, write it
(red-first) rather than reporting the deliverable green.
