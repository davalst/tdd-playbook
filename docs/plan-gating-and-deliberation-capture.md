# Plans-in-repo & deliberation capture — operating notes (v1.23.0, CIVerd briefs)

## docs/plans/gated/ — the convention

Approved feature plans land IN the repo they govern, as `docs/plans/gated/<slug>.md`,
authored by `plan_block.py scaffold` (see `/tdd-plan`'s closing section for the full
rules: permanent slugs, weaker-truth predicate semantics, prose section for unenforceable
deliverables, `active` always, never gate small work).

**The no-README hazard (do not "fix" this):** `docs/plans/gated/` must contain ONLY plan
files. Once the engine's `plan_globs` is armed for `docs/plans/gated/*.md`, ANY stray
`.md` there — a README, a notes file — is parsed as a plan and, having no `civerd-plan`
block, produces a MALFORMED verdict that bricks the release gate. The convention lives
here, outside the directory, precisely for that reason. The directory itself is
materialized by the first plan (`makedirs`), never committed empty.

**Enforcement is currently DARK — deliberately visible.** Predicates are evaluated only
after David pastes the two root-owned `repos.yml` lines on srv1621832 (the playbook
session hands him the exact lines; cross-repo authorship rule). Until then plans are
authored but inert. This is a registered integration debt (`plan-authoring`, expires
2026-09-15) that REDs the suite at expiry — armed or consciously re-dated, never silently
dark.

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
