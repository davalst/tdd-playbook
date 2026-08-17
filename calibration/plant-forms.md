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

## Fixture design notes (moved here from the fixture, U3a 2026-08-15)

The fixture must not explain its own plants (a docstring naming the harness hands the checker
the answer — `fixture_legibility_problems` now REDs the gate on such prose). The design notes
that used to live in the fixture files belong here instead, where the doer never looks:

- `fixture/tools.py` + `fixture/audit.py` each keep their OWN copy of the read-only tool-name
  list. They agree today; nothing enforces it. This is the seam the `band-aid-parallel-list`
  plant exploits (add a name to one copy only) and the `good-fix-single-source` plant repairs
  (a single per-tool attribute both call sites read). The architecture-adversary must tell the
  band-aid apart from the good fix.
- `fixture/calc.py` is the known-good module the plants subtract from; `fixture/tests/` is
  complete-by-design so a plant's weakening shows as a coverage or vacuity change.

## Entries — first holdout assignment (2026-08-17)

APPENDED, not edited in place: this file is append-only under
`check_scoreboard_integrity.py` rule (a), and the first draft of this assignment rewrote the
table above and was REDded by the gate for it. The empty legacy table stays exactly as it was;
`parse_register` re-arms on any heading beginning "Entries" and accepts 5-cell (legacy) and
7-cell rows alike, so these rows are read together with anything already there.

This pays the FIRST HOLDOUT ASSIGNMENT debt on the `plant-forms` capability. 20 bodies live in
the private sibling repo, so every row records `private`: a sha256 recorded here for a body
this repo cannot see would imply a check nothing performed, and `form_problems` refuses it in
exactly those words. Header and rows are written by `plant_forms.ENTRIES_TABLE` and
`format_register_row` — the same functions `parse_register` reads, so writer and parser cannot
drift apart.

**Two extra columns beyond the "Legal values" table above** (the 2026-08-16 D0 migration):
`status` is `current` | `legacy-invalid` | `asymmetric`, and `supersedes` names the `plant_id` a
row replaces. Four of these twenty are `legacy-invalid` — superseded at remediation after the
control-quality judge returned REJECT or FIX-ORACLE. They are still registered, because a
retired holdout id must still never leak.

**The `reason` cell is PUBLIC — keep it categorical.** The private vault's own register carries
verbose reasons that describe each defect in plain English ("greps for its own expected string,
so it passes without exercising the target"). Copying those here would publish the answer key in
prose while the bodies stayed private, defeating the split for anything that reads this file.
These rows therefore record `initial`. Ids are public by design (`plant_forms.py`'s LEAK_SCAN
note: "what must stay private is the BODY"); DESCRIPTIONS are not, and the schema's `free text
naming why` is a licence the holdout form should decline.

Before these ids were published the leakage tripwire was run against them across all four live
scan roots: 0 leaks. It is now ARMED — `plant_forms.py check` reports `20 holdout / 0 dev` and
can fail, where it previously reported itself unarmed and could not.

| date | plant_id | form | content_sha256 | reason | status | supersedes |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-08-15 | control-probe-canary-selftest | holdout | private | initial | current |  |
| 2026-08-15 | control-twin-export-shares-authz-helper | holdout | private | initial | current |  |
| 2026-08-15 | probe-passes-on-any-nonzero-exit | holdout | private | initial | current |  |
| 2026-08-15 | twin-export-command-skips-authz | holdout | private | initial | current |  |
| 2026-08-16 | alias-branch-reimplements-authz | holdout | private | initial | current |  |
| 2026-08-16 | control-csv-escape-rfc4180-complete | holdout | private | initial | legacy-invalid |  |
| 2026-08-16 | control-describe-added-to-single-source | holdout | private | initial | legacy-invalid |  |
| 2026-08-16 | control-dump-alias-shares-authorize | holdout | private | initial | current |  |
| 2026-08-16 | control-nonfinite-pct-rejected | holdout | private | initial | current |  |
| 2026-08-16 | control-plan-flag-is-optout | holdout | private | initial | current |  |
| 2026-08-16 | control-plan-parity-both-surfaces | holdout | private | initial | current |  |
| 2026-08-16 | control-probe-greps-only-attempt-output | holdout | private | initial | current |  |
| 2026-08-16 | control-probe-reads-deployed-key-in-place | holdout | private | initial | current |  |
| 2026-08-16 | csv-quote-escape-untested | holdout | private | initial | legacy-invalid |  |
| 2026-08-16 | nan-pct-slips-range-guard | holdout | private | initial | current |  |
| 2026-08-16 | plan-parity-blind-second-surface | holdout | private | initial | current |  |
| 2026-08-16 | plan-ships-behind-opt-in-flag | holdout | private | initial | current |  |
| 2026-08-16 | probe-certifies-a-copy-not-the-key | holdout | private | initial | current |  |
| 2026-08-16 | probe-greps-its-own-expectation | holdout | private | initial | current |  |
| 2026-08-16 | write-lock-exemption-third-list | holdout | private | initial | legacy-invalid |  |
