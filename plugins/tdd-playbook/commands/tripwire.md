---
description: Run the Playbook §6 Tripwire — verify every plan deliverable is BUILT + WIRED-IN + EXERCISED, report N/N.
argument-hint: [deliverable list or plan reference]
---

Run the **Tripwire** wiring check against the current plan's deliverables: $ARGUMENTS

For EACH deliverable, verify and report three things separately (don't round up):
- **BUILT** — its route/entry/tool/command is actually registered (cite file:line).
- **WIRED-IN** — a real user entry point references it (UI button / CLI command / MCP
  tool / nav). A registration or export is NOT a wire — trace who reaches it.
- **EXERCISED** — point at a specific `file::test_name` (or this repo's equivalent) and
  confirm it is DEFINED and NOT skip-marked. A grep proving a *reference* is not enough;
  a hollow button or a skipped test must TRIP the Tripwire.

Use the repo's own test runner/markers. Where a deliverable fails any of the three, mark
it RED with the exact gap. Report `Tripwire: N/N` (green/total). It is a FLOOR — never add
a hollow stub to go green. If a behavioral test is missing, write it (red-first) rather
than reporting the deliverable green.
