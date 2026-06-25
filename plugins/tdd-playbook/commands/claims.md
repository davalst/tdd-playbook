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

MECHANICAL GATE (don't just self-report — run the check): write your draft findings, each
with its `file:line` citation and — where you quote the source — the quote right after it in
backticks, e.g. ``finding … `src/auth.py:42`: "return False"``. Then run the verifier:

    python3 "${CLAUDE_PLUGIN_ROOT}/bin/verify_citations.py" <your-findings-file> --base <repo-root>

Every citation it reports UNRESOLVED (file/line missing) or MISMATCH (quote not on the line)
is fabricated or wrong evidence — DEMOTE that finding to a lead; it cannot carry a severity.
Only publish findings whose citations the tool marks VERIFIED.

Report `Claims: N load-bearing · N verified (verify_citations) · N demoted to leads`, and
PASTE the tool's summary line so the count is auditable, not asserted — a self-reported "N/N"
is narration with a colon in it.
