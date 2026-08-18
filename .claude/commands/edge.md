---
description: Walk a deliverable through the Playbook §2 edge-case checklist and scaffold the tests that genuinely apply.
argument-hint: <function / endpoint / deliverable to harden>
---

Run the **edge-case pass** (Playbook §2) on: $ARGUMENTS

Methodically walk this checklist; for EACH category, decide if it genuinely applies and
why (one line) — the count is derived from real failure modes, never padded to hit a quota:
- boundaries / limits (off-by-one, min/max, empty vs one vs many)
- empty / null / missing input
- malformed / invalid / wrong-type input
- permission & auth NEGATIVE cases (denied → refused, not silently allowed)
- state/lifecycle transitions + idempotency / double-submit / re-entry
- concurrency / ordering / retries / duplicates
- failure & error paths + rollback / cleanup
- scale / large input
- second-order / cross-surface effects

For the categories that apply, write behavioral tests (this repo's runner + its `edge`
marker or equivalent), red-first. Assert OUTCOMES, not "the route fired". For any pure
logic, propose a property-based invariant (§3) instead of enumerating cases by hand.
Report which categories applied vs were N/A and why.

**Close the loop (not optional):** after writing the tests, DISPATCH the
`edge-case-adversary` agent on the same deliverable — an independent, fresh-context pass
that hunts the gaps your enumeration missed (the "bounded by my own imagination" weakness
is exactly why the author's own list can't be the last word). Address or explicitly defer
each gap it names.

End the report with: `Loop closed: yes (edge-case-adversary dispatched — <its top finding>)`
or `Loop closed: NO — <why>` (a skipped adversary pass is a visible decision, never a default).
