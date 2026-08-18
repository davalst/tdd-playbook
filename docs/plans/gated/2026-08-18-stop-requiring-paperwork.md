# TDD Plan — stop requiring paperwork per commit

**Slug:** `2026-08-18-stop-requiring-paperwork`
**Status:** ready to implement. One coherent change. No follow-on queue.

---

## Context

Four agents and three documents have deliberated this. Everyone now agrees on the direction, and
the remaining disagreement was only about scope. This resolves it.

**The measurement that settles the scope question already existed and it was in the first
message of this thread:** cadence at a snail's pace, and considering stopping. Asking for "a few
more commits to see what the friction is" would treat that as unmeasured data — the exact move
an earlier draft of this plan indicted itself for.

**Why D1 alone is not enough.** Removing the review-record rule removes **one artifact of
twelve**. The next commit would still need: a plan with an integration surface, an adversary
dispatch, a lock/unlock with a journaled reason, a planted-input test, a `current-state.md`
regeneration, a `gate-changes.md` entry, a pre-registered ledger entry, a registry entry, a
four-file bump, a CHANGELOG entry, a CI wait, a tag handoff. You would correctly conclude the
overhaul did nothing.

**The rule this change is really adopting:**

> **The playbook is silent until it has something real to say.**

The hooks already have that posture — four block, five are off, and they speak only when
something is wrong. That is a partner. The doctrine has the opposite posture: produce artifacts
*before* you may proceed. That is a checkpoint. This change moves the doctrine to the hooks'
posture.

---

## The change

### 1. Delete the per-commit record rule *(code)*

| File | Change |
|---|---|
| `bin/review_ledger.py` | delete `coverage_problems` **and** its call in `validate_repository` |
| `tests/test_review_ledger.py` | delete the `validate_repository` coverage assertion **and** `test_preimplementation_review_cannot_cover_candidate` — it tests the removed policy |
| `CLAUDE.md` | delete the "every non-metadata commit must be covered by a closed review record" rule and the metadata-tail dance |
| `AGENTS.md` | **generated** — re-render, never hand-edit |

**Kept:** the record schema and `validate` for records that ARE written, and `recurrence`.

### 2. Make the remaining per-change obligations opt-in *(doctrine prose)*

In `SKILL.md` and `CLAUDE.md`, these stop being required per change and become things you reach
for when they have something to say:

- the full plan document — a one-liner is the default; the full §0 treatment is for genuinely
  multi-deliverable work
- adversary dispatch — on request, or before a release
- a review record — when a review actually finds something
- `index.json` / `current-state.md` bookkeeping — follows records being optional

### 3. Explicitly NOT touched

Everything that watches your back stays exactly as it is: **the four blocking hooks, TEST-LOCK,
planted-input tests, red-first, the gate, rule (d) gate-surface journaling** (that one is an
anti-gaming control, not bookkeeping), **the capability registry, and the version bump** (it is
the plugin-cache shipping channel).

---

## The honest cost

**Records become optional, so `recurrence` may become sporadic or purely historical.** There is
no replacement trigger, and I checked rather than assumed: the six authoring briefs say
*"Review record output (when these findings land in `docs/reviews/`)"* — they specify fields
**when** a record is written and never require one. An earlier draft of this plan claimed those
briefs constituted a live trigger. That was wrong, and expanding this change to edit six briefs
would be exactly the scope creep this is meant to end.

Accepted, with eyes open: 205 findings, 57% keyed, **12 UNBUILT-GUARD keys and zero guards built
from any of them.** The signal was already unconsumed.

---

## Red-first

1. An **invalid** opt-in record still fails `validate` — the schema keeps its teeth.
2. A HEAD with **no** covering record now **passes** — the old assertion would have failed it.
3. `recurrence` still runs and still produces keys.

## Verification

```sh
python3 plugins/tdd-playbook/bin/render_agents.py render
python3 plugins/tdd-playbook/tests/test_review_ledger.py
python3 plugins/tdd-playbook/bin/review_ledger.py validate
python3 plugins/tdd-playbook/bin/review_ledger.py recurrence
sh scripts/civerd_gate.sh > /tmp/gate.out 2>&1
rc=$?
```

## Landing it

- Commit, with the rationale in the commit message — **no review record for this change.**
  Writing one final required record for the rule that removes required records is a metadata
  cycle for nothing; the plan and the commit message carry the reasoning, and the modified gate
  validates the new policy directly.
- Push the green checkpoint.
- **Do not version, tag, or release now** — batch it into the next release.
- Then go work normally.

## Out of scope — and staying that way

`verify_verdict` archival access · the doctrine line-count cut · the vacuous
`dataflow-sweeps.json` · `capture.py`'s unread store · turning the four recurrence keys into
buildable checks (they are heterogeneous and not shovel-ready — `outermost-wire-untested` alone
spans a hook subprocess, installer verification, dangling doctrine references and absence
citations) · the citation-resolver and `parse_ledger` instrument bugs.

**No dates, no debt entries, no queue.** Seven dated obligations to escape a bureaucracy problem
would be the quicksand itself. Revisit one only when real friction points at it.
