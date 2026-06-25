---
description: Apply the Playbook §12 claims discipline to an audit/review/diagnosis — cite-or-refuse, exhaustive negatives, Claims N/N.
argument-hint: [audit scope or findings to harden]
---

Apply the **claims discipline** (Playbook §12) to: $ARGUMENTS

For analysis/audit/review/diagnosis work, claims are the deliverable and the same
anti-performative rules as TDD apply — no claim before resolving evidence. For every
load-bearing claim:
- **Cite-or-refuse:** each claim points at a specific file:line / grep / runtime probe.
- **Negatives need an EXHAUSTIVE sweep:** "X is never called / unreachable / dead / not
  wired" requires grepping ALL reference & assignment sites and citing the sweep — the
  refutation usually lives in a file you didn't open. One file where X "should" appear
  proves nothing.
- **Built ≠ wired ≠ usable for claims too:** trace who SETS the value, who CONSUMES it,
  which config gates it, before asserting wired/unwired.
- **Secondhand/subagent reports are UNVERIFIED** until spot-checked; prefer a cheap runtime
  probe (import/registration check, hit the route) over static inference.
- **No severity without verification:** a hedged claim cannot carry a severity. Demote it to
  an explicit "Unverified leads" section WITH its falsification path. Leads are first-class;
  the sin is uncertainty wearing a severity badge.

Report `Claims: N load-bearing · N verified (grep/runtime/cited) · N demoted to leads`,
each "verified" pointing at the actual evidence so the line is auditable.
