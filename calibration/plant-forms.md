# Plant form register — APPEND-ONLY

Which calibration plants are **dev** (the tuning set, run every cycle) and which are
**holdout** (the reporting set, read quarterly and never tuned against). Design:
`docs/plans/calibration-lift-and-deletion-ratchet-2026-07.md` item 3 (RATIFIED), built
2026-08-06. Read by `calibration/plant_forms.py`; enforced append-only by
`check_scoreboard_integrity.py` rule (a) alongside `history.md`, `oracle-changes.md`,
`gate-changes.md` and `ledger.md`.

## Why the form lives HERE and not in the plant file

The obvious design — a `form` key in each plant's `_meta` — is unbuildable. Rule (b) pins
every file under `calibration/corpus/approved/` byte-identical forever, and the suite checks
it against the latest tag on every run. That blocks back-filling the legacy plants, which was
foreseen; it also blocks **burn-on-failure**, which was not. A holdout plant that fails must
still drive an agent fix, and the moment it does it is contaminated and has to rotate into
dev — a change of form on a file that can never change. So the form is recorded beside the
corpus instead of inside it, and a burn is an APPEND. The corpus only grows; so does its form
record.

## Rules of the register

- **The latest entry for a `plant_id` wins.** Earlier entries stay as the audit trail — a
  burn is visible as a `holdout → dev` transition, never as a rewritten line.
- **An id with NO entry is `dev`.** The 14 plants that predate this register need no entry and
  no byte changes. Absence is a decision, and it is the safe one: an unassigned plant is
  tuned against, never quietly reported as a clean measurement.
- **`content_sha256` pins what the name resolves to.** Form assignment is name-keyed, and
  name-keyed authorization is only sound when something pins the CONTENT behind the name —
  the lesson from `d5dec34` (CIVerd's engine sweep), where a quarantine granted for an old
  defect would have carried over to whatever later took the same name. For an id present in
  `corpus/approved/`, `plant_forms.py` RECOMPUTES the sha256 and REFUSES a mismatch. For an
  id held privately (see below), the hash is recorded but cannot be verified here, and the
  tool says exactly that rather than implying it checked.
- **Holdout material never appears in anything published** (Decision 1, ratified 2026-08-05).
  The future public scoreboard ships results and signed verdicts, never plants. Holdout plant
  BODIES live in a private sibling repo; only their **ids and hashes** are public here,
  because ids leak nothing and are exactly what the leakage tripwire must scan for.
- **Never edit a row to reclassify.** Append the new state with a reason.

## Legal values

| column | values |
|---|---|
| `date` | ISO date of the assignment |
| `plant_id` | a scenario id — in `corpus/approved/` (verifiable here) or held privately |
| `form` | `dev` \| `holdout` |
| `content_sha256` | sha256 of the plant JSON, or `private` when the body is not in this repo |
| `reason` | `initial` \| `burn-on-failure` \| `rotation` \| free text naming why |

## Entries

| date | plant_id | form | content_sha256 | reason |
|---|---|---|---|---|

*(No holdout classes assigned yet. The mechanism ships armed and empty on purpose: the first
holdout assignment happens at the next authoring cycle, once the private sibling repo exists.
That is not a silent OFF — it is a dated `integration_debt` on the `plant-forms` capability
that REDs the suite at expiry, per the standing ships-on-or-triggered rule.)*
