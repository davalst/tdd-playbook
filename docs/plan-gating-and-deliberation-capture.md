# Plans-in-repo & deliberation capture — operating notes

## docs/plans/gated/ — the convention (rewritten 2026-08-09, v1.32.0)

Approved feature plans land IN the repo they govern, as `docs/plans/gated/<slug>.md`,
written as ordinary markdown. `/tdd-plan`'s closing section carries the rules that still
apply: dated permanent slugs, an explicit "Unenforceable deliverables (prose)" section, and
never gate small work.

**What changed, stated plainly because the previous version of this file was false in every
load-bearing sentence.** Until v1.32.0 these files were scaffolded by `bin/plan_block.py`
into a machine-readable `civerd-plan` block, and the only consumer of that block was the
CIVerd engine's plan-predicate evaluator. v1.32.0 retired the engine, so producer and
consumer were deleted together. Three claims went with them:

- *"authored by `plan_block.py scaffold`"* — the tool no longer exists.
- *"The no-README hazard (do not 'fix' this)"* — this forbade a README in the directory
  because the engine's `plan_globs` would parse a stray `.md` as a malformed plan and brick
  the release gate. There is no engine, no `plan_globs`, and no release gate to brick. The
  instruction outlived its reason and, being written as a warning against fixing it, was
  built to survive review. A README there is now merely unnecessary, not dangerous.
- *"a registered integration debt (`plan-authoring`, expires 2026-09-15) that REDs the suite
  at expiry"* — that capability was deleted in v1.32.0, so the RED it promised can never
  fire. A doc asserting a mechanical backstop that does not exist is the exact inversion of
  the deferrals-need-mechanical-triggers rule.

**Honest current state: nothing mechanically validates a gated plan file.** `plan_block.py
validate` was the only reader, and `docs/plans/gated/*.md` is now a write-only surface —
files a convention says to write and no code reads. That is a real §6c gap, recorded as
dated debt on `gate-surface-ledger` rather than left implied. Two things do still consume the
directory indirectly: `docs/reviews/*.json` records name a plan path in their `plan` field
(`review_ledger.validate_record` requires the string, and as of v1.32.0 resolves it on disk),
and `/tdd-plan` anchors the Tripwire to whatever the plan says.

## The deliberation store — posture, with honest labels

- **What it is:** append-only per-day JSONL of human turns + assistant finals
  (`~/.claude/deliberation/` or `TDD_PLAYBOOK_DELIBERATION_DIR`), captured by
  `hooks/scripts/capture.py`, fail-open, never stdout. Conveyed ≠ ratified; closure
  records are appended ONLY by `bin/deliberation.py close` — David's word.
- **Honest label — honour-system, not enforced:** dir 0700 / files 0600 is a courtesy
  lock against other local users, not a security boundary. The store sits INSIDE Claude
  Code's own trust domain (leak-#3 applies): any session on this machine can read it.
  "Open/closed" is a label derived from closure records, not an ACL.
- **Answer-key exclusion:** `calibration/child_env.py` pins `TDD_PLAYBOOK_HOOK_CAPTURE=off`
  for every nested claude the calibration pipeline spawns (both spawn sites, stub-proven),
  and env `off` beats the enrollment marker by a named test. The calibration answer key
  must never enter this store.
- **Enrollment:** the marker `<store>/ENABLED` is written by the BUILD on David's
  machines — his consent is the commission; a stranger's marketplace install ships OFF
  (a silent always-on prompt recorder is the finding our own /security-review would
  flag). Coverage is therefore PARTIAL by design: un-enrolled machines, cloud sandboxes,
  and non-Claude-Code surfaces (Cheli/GLM) are never captured. The doctor line
  (`capability_registry.py doctor` → `capture: ON/OFF`) makes "is it recording?" always
  answerable; the enrollment sweep is a dated debt (2026-08-31).

## v2 matcher — binding label constraint, written down NOW

When the v2 shingle matcher lands (the store's PRIMARY named consumer, debt 2026-10-31),
unmatched spans are labeled **"unattributed" — NEVER "David's own words."** Under partial
coverage, no-match does not imply human authorship, and that inference's failure
direction — assistant words attributed to the human — is exactly what the store exists
to prevent.

## guard_env hand-off (S1b)

When the engine's expected-wiring check lands on the box, `capture.py` (and its
`--event`-argument registrations) must be added to the root-owned expected-hooks list —
otherwise the first audit after arming reads capture as UNEXPECTED wiring in every
Playbook repo. This is an engine-side line item; it rides the same root-store channel as
`repos.yml` (David pastes, sessions never touch).
