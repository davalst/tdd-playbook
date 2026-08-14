# Plan — Review as a judgment surface: closing the codification loop

**Date:** 2026-08-14
**Author:** engineering (CTO/senior-dev framing, per David's request)
**Branch:** `claude/code-review-taste-judgment-2czk91`
**Provenance:** four recommendations derived from reading *"Code review is a taste problem"*
(Jain & Poll, TNS, 2026-08-13) against this repo's actual doctrine and artifacts. The article's
authors sell a product in this space; the recommendations below survived only where this repo's
own evidence — not the article — supports them.

---

## Executive summary — what this is and why

This repo is unusually good at one of code review's three jobs (**verification**) and has already
built most of a second (**capturing intent before the code**, via §0 plans, `capture.py`,
`deliberation.py`, and the `docs/reviews/` ledger). What it has not built is the **feedback
loop that turns judgment into mechanism**, and — more seriously — it has no counter-pressure
against its own growth.

The numbers this repo already collects, read in aggregate for what appears to be the first time:

| measure | value | source |
|---|---|---|
| SKILL.md size | 1109 lines | `plugins/tdd-playbook/skills/tdd-playbook/SKILL.md` |
| registered doctrine changes | 112 rows | `docs/calibration/ledger.md` |
| …carrying an outcome verdict | 51 (16 HIT · 13 FLAT · 20 INCONCLUSIVE(no-baseline) · 2 PARTIAL) | ibid., column 7 |
| …carrying no scenario at all | 15 (`scenarios: —`, `expect: none`) | ibid. |
| review findings recorded | 88 (69 verified_closed · 16 incorporated · 3 open) | `docs/reviews/*.json` |
| review findings ever **rejected** | **0** — despite `rejected` being a valid status since the schema was written | `bin/review_ledger.py:VALID_STATUS` |
| registered capabilities | 29 | `capabilities.json` |

Two readings jump out and they are the spine of this plan:

1. **Roughly a third of the doctrine changes that were measurable measured as HIT.** Twenty were
   registered against no baseline and are permanently unmeasurable. That is not damning on its own —
   but nothing in the repo reads that column in aggregate, so the ratio has never informed a
   decision. `gate_yield.py` does exactly this job for *machine gates* and has no sibling for
   *doctrine*. §13's decay principle is instrumented in one direction (gates getting weaker) and,
   for hooks only, in the other (gates getting more expensive than the risk). Doctrine — the
   largest and fastest-growing surface in the repo, and the one with exactly one reader — is
   instrumented in neither.

2. **Eighty-eight findings, zero rejections.** Either the adversary fleet is perfectly calibrated,
   or the review surface is confirmation wearing review's clothes. §0 already names this failure
   in its own words — *"a confirming reviewer rubber-stamps islands"* — and the rejection path it
   would show up in has never once been exercised. An unexercised control is an unfalsified
   control, which is a class this repo is otherwise ruthless about (§4a vacuity, §13 liveness-vs-
   detection plants).

**Design constraint that governs the whole plan:** every deliverable here *adds* surface to a repo
whose diagnosed disease is accretion. Therefore the deliverable that can *remove* surface ships
first. Shipping the accretion instruments before the retirement instrument would be the plan
enacting the very failure it diagnoses — the same logic as §0's "the deploy path is deliverable #1"
and §1's red-first.

---

## Correction record (§12 — a claim I made, refuted before it propagated)

In the conversation preceding this plan I asserted that `CLAUDE.md` "names v1.32.0 four times in
load-bearing positions while `plugin.json` is at 1.35.0", and offered version-drift as
deliverable #4.

**REFUTED.** All five occurrences (`CLAUDE.md:3,76,190,193,236`) are correctly-dated *historical*
markers — "changed in v1.32.0", "since v1.32.0", "until v1.32.0", "v1.32.0 onward", "pre-v1.32".
None claims to be the current version. The claim was a grep count read as a staleness signal
without reading the surrounding clause: precisely §12's "cite-or-refuse" failure, and precisely the
"absence/presence claims about text must parse the context" rule.

**What survived the refutation** is a different and smaller finding, carried forward as D4: the
standing prompt at `CLAUDE.md:76` makes a **roster claim** — "the four BLOCKING guards:
test_weakening_guard, test_lock_guard, snapshot_guard, tag_guard; plus the opt-in
exitcode/overmock/exhaustive/flaky/red_lock" — that is asserted in prose, shipped to every
downstream repo as instructions, and pinned by nothing. `test_agents.py:893-897,962` checks
`CLAUDE.md` with **substring presence** assertions only. That roster can drift the moment a
guard is added or retired, and the drift would be invisible.

This correction is itself the argument for D2: the finding that a rule was walked past is worth
more than the rule.

---

## Spec integrity (once, before deliverables — §0)

### Assumptions, stated rather than picked silently

1. **The reader is one person and his attention is the scarce resource.** Every instrument below
   is designed to produce a *short read*, not a complete one. If a deliverable's output cannot be
   read in under a minute, it has failed regardless of correctness.
2. **Nothing here is allowed to block a release on judgment.** D3 makes taste *auditable*, never
   *blocking*. The architecture- and adoption-adversaries stay advisory (§0 says so explicitly);
   what changes is that their disposition becomes an artifact instead of a chat turn.
3. **`docs/calibration/ledger.md` column 7 is schema-mixed across eras** — early rows carry
   scenario names, later rows carry outcome verdicts (HIT/FLAT/INCONCLUSIVE/PARTIAL). D1 must
   read what is actually there and report the mixed-era rows as **UNMEASURED**, never coerce them
   into a verdict. Inferring a class into a durable record is the exact fabrication the v1.27
   dated correction in `gate_yield.md` exists to end; D1 inherits that prohibition verbatim.
4. **Recurrence keys are authored, not inferred.** D2 does not attempt semantic clustering of
   finding text. A human (or the authoring agent) supplies the key; the tool only counts. An
   inferred key would produce a confident wrong number, which is worse than no number.

### Materially simpler approaches — considered, and where they win

- **Instead of D1 (doctrine yield):** just delete SKILL sections by judgment, periodically.
  *Rejected* — that is the current state, and 112 registered rows with no aggregate read is the
  result. But note honestly: D1's value is entirely in whether David *acts* on the candidate list.
  If after two cycles no candidate has ever been retired, D1 has failed and should itself be
  retired under its own rule. That self-application is written into D1's DoD.
- **Instead of D2 (taxonomy + recurrence):** keep classifying findings in prose. *Rejected on this
  repo's own evidence* — §12's Cheliped entry records "three rules in context the whole time,
  three misses in one sprint", a recurrence event captured as prose and never counted.
- **Instead of D3 (judgment artifacts):** nothing. *This is the closest call in the plan.* D3's
  entire value is making a zero-rejection rate visible. That could be achieved with a five-line
  script over `docs/reviews/*.json` and no schema change at all. **D3 is therefore scoped down to
  exactly that** — see D3, which deliberately does *not* add a new record type.
- **Instead of D4 (roster pin):** accept the prose. *Rejected* — it is ~15 lines and it converts a
  downstream-shipped instruction from honor-system into mechanism, which is §12's "when a class is
  named, ship the mechanism".

### Deferrals — trigger, not roadmap (H7)

Two items are deferred, each as a **dated `integration_debt` entry registered in the same commit**,
with `validate --as-of <expiry+1>` proven to exit **1 (EXPIRED)** before the commit lands:

| deferred | why | owner | expiry | trigger |
|---|---|---|---|---|
| Retirement *execution* (actually deleting a SKILL section that D1 flags) | Retirement is a human decision with the R4.3 shape; `gate_yield` made the same split and it was right | david | 2026-11-15 | first D1 candidate surviving two cycles |
| Back-classifying the 88 historical findings with D2's taxonomy | Historical records are append-only; re-classifying them retroactively is the record-rewriting D1 assumption #3 forbids. New findings only. | david | 2026-12-31 | if recurrence detection produces no signal in 3 cycles, revisit whether a historical seed is needed |

### Questions for David (do not plan around — §0)

- **Q1 (blocking for D1's threshold):** what should the retirement-candidate rule be? Proposed:
  *a SKILL section with ≥3 registered changes across ≥2 cycles and zero HITs*. That is a guess. The
  `gate_yield` precedent uses `--min-cycles 2` plus adjudicated friction; I have mirrored the shape
  but the numerator is genuinely arbitrary here and a wrong threshold produces noise that trains
  you to ignore the instrument.
- **Q2 (shapes D3):** if the zero-rejection rate turns out to be real rubber-stamping rather than
  calibration, is the intended response to strengthen the adversaries, or to accept that this
  repo's adversaries are advisory-by-design and stop treating rejection as a health signal?

---

## Ceremony sizing (§0 preamble, in numbers)

Feature / multi-deliverable work touching `bin/` and the release gate → **full flow**. Every
deliverable gets: red-first tests, edge cases, integration surface, flow table, and the closing
adversary dispatch. D4 alone is sub-threshold by line count (~15 lines) but touches `CLAUDE.md`,
which `gate-manifest.json:force_full` lists — so it runs the full suite regardless, and the
ceremony is charged to the gate rather than to the diff.

---

## Deploy surface (§0 — required: this plugin RUNS where this session does not control it)

Every deliverable adds or changes files under `plugins/tdd-playbook/bin/`, which are **vendored
into downstream repos' `.claude/bin/`** by `scripts/install_into_repo.py`. This is a real deploy
surface and the reflex "commit-and-push IS the deploy" is false here.

- **Runs where:** downstream repos' vendored `.claude/` copies (memrebel, cheliped, and any repo
  refreshed via the standing prompt in `CLAUDE.md`), plus this repo's own gate.
- **Gets there how:** `scripts/install_into_repo.py` — the reconciling installer. New `bin/` files
  must be added to its vendoring roster or they simply do not ship. **This is the single most
  likely way this plan ships dark**, and it is D0 below.
- **Verified how:** the existing scratch-repo `install_into_repo.py` parity run in the release gate,
  extended to assert the new bins and verbs are present; `test_vendoring.py` is the mechanical seam.
- **Divergence:** a downstream repo on an older vendored copy silently lacks the new verbs. It
  notices at its next refresh via the standing prompt's step 2 checklist, which D0 updates.

**D0 is therefore deliverable #0 and is not optional:** before any instrument is built, extend the
vendoring roster and its test so a new `bin/` file *cannot* be added without shipping. Same logic
as §0's deploy-path-first rule.

---

## Deliverables

Order is load-bearing. D1 ships before D2/D3 because D1 is the only deliverable that can *remove*
surface, and this plan otherwise adds four instruments to a repo diagnosed with accretion.

---

### D0 — Vendoring roster becomes self-enforcing (enabling; ~30 lines)

**Plain English:** today, adding a new tool to `bin/` and forgetting to list it in the installer
means downstream repos never get it, and nothing complains. Make that impossible.

**Red-first:** a test that adds a synthetic `bin/_plant_unvendored.py` to a scratch tree and
asserts `install_into_repo.py`'s roster check REDs. Must fail before the fix and pass after.

**Behavior:** `test_vendoring.py` gains a roster-parity check — every `plugins/tdd-playbook/bin/*.py`
not explicitly exempted must appear in the installer's vendoring set. Exemptions are an explicit,
commented list (today: `verify_verdict.py` + `_ed25519_verify.py` are deliberately kept and
deliberately unwired, per `CLAUDE.md`; they still vendor, so likely no exemptions are needed at all
— **verify this rather than assume it**).

**Edge cases:**
- a new `_private.py` helper imported by a vendored tool but never invoked directly → must still
  vendor, or the vendored tool breaks on import downstream (this is the `_debt.py` / `dataflow_sweeps.py`
  sibling pattern already in the repo — the fixture must cover it);
- a file added under `bin/` that is a fixture or data file, not a tool → exemption list, with reason;
- the check must count from `git ls-files`, not `os.listdir`, so an untracked scratch file cannot
  RED the gate and an untracked-but-committed-later file cannot slip past (§12: the roster must be
  one the file cannot drift with).

**UX test:** a developer adds a tool and forgets the roster → the gate names the missing file and
the exact line to add. Not "roster mismatch".

**Integration surface:**
- *Consumes:* `scripts/install_into_repo.py` (vendoring roster), `git ls-files`.
- *Emits → named consumer:* a RED in `test_vendoring.py`, consumed by `gate_runner.py` via
  `gate-manifest.json:suite_glob` (`plugins/tdd-playbook/tests/test_*.py`) — field granularity: the
  suite's non-zero exit is read by `gate_runner.py`'s stage loop.
- *Surface parity:* n/a — this is a repo-internal gate, no user-facing surface.
- *Reverse sweep:* the same roster-drift class applies to `hooks/scripts/*.py`. **Check whether the
  installer's hook merge already covers this**; if it does not, that is a second finding and becomes
  either a deliverable or dated debt — not a silent pass.
- *Activation:* on by default, part of the standing suite. No flag.

**Flow table (§6c):**

| flow | producer | consumer | liveness test |
|---|---|---|---|
| bin roster | `git ls-files plugins/tdd-playbook/bin/*.py` | `install_into_repo.py` vendoring set | `test_vendoring.py::test_bin_roster_parity` (planted unvendored file REDs) |

**DoD:** planted unvendored file REDs; real tree passes; scratch-repo install parity run still green.

---

### D1 — Doctrine yield: `ledger.py candidates` (the retirement instrument)

**Plain English:** the repo already records, for every doctrine change, whether it moved a
calibration scenario. Nobody reads those 112 rows together. This adds one command that reads them
and says which parts of the playbook have grown without ever demonstrably helping — the same job
`gate_yield candidates` does for hooks, pointed at prose.

**Why first:** it is the only deliverable in this plan that can subtract. Rule (d) makes doctrine
*additions* free; nothing makes them accountable. Shipping D2/D3 before D1 would add three
instruments to the accretion problem while the counter-pressure stayed unbuilt.

**Red-first:** a fixture ledger with a section at 3 changes / 2 cycles / 0 HITs must appear as a
candidate; a section at 3 changes / 2 cycles / 1 HIT must not; a section whose rows are all
mixed-era must be reported **UNMEASURED**, never as a candidate. All three assertions written and
RED before implementation.

**Behavior:** `calibration/ledger.py candidates [--min-cycles 2] [--min-changes 3]`, mirroring
`gate_yield.py candidates` in shape, flags, and honesty rules. Output: one line per candidate
section, plus an explicit **coverage line** (§12: never a numerator without its denominator) —
`sections scanned N · measured M · unmeasured K`.

**Honesty rules inherited verbatim from `gate_yield.py` (these are not decoration — they are the
reason `gate_yield` is trustworthy):**
- a section absent from the record is **UNMEASURED, never zero**;
- `INCONCLUSIVE(no-baseline)` rows count toward *unmeasured*, never toward "no effect" — a change
  that could not be measured is not a change that did nothing;
- mixed-era rows (assumption #3) are excluded from the numerator and **named in the output**, so
  the exclusion is visible rather than silent;
- candidates require ≥`--min-cycles` **committed** cycles, so a fresh clone cannot manufacture them.

**Edge cases:**
- a section renamed between cycles (SKILL headings do change) → rows must key on something more
  stable than the heading text, or renames silently reset a section's history. **This is the hardest
  part of D1 and should be designed before coding**; proposed: key on section *number* (`§12`), with
  a renames map in the ledger when a number changes, and a RED if a registered row cites a section
  number that does not exist in current SKILL.md;
- a section with exactly one cycle of history → UNMEASURED, not a candidate;
- zero candidates → must print "no candidates" plus the coverage line, never empty output (an empty
  render reads as "not run");
- the whole ledger unreadable/malformed → exit non-zero with the parse error, never an empty pass.

**UX test:** David runs `ledger.py candidates` and in one screen learns which sections to consider
cutting and how much of the playbook the answer covers. If the output needs a follow-up question to
be actionable, it has failed the `/readable` "size every worry" rule (L-20260813-09) — which is
this repo's own most recent lesson and applies directly.

**Integration surface:**
- *Consumes:* `docs/calibration/ledger.md` (existing, append-only), `calibration/ledger.py`'s
  existing `parse_ledger`/`_cells` parsers — **reuse them, do not write a second parser** (the
  Nth-copy band-aid the architecture-adversary exists to catch).
- *Emits → named consumer:* stdout, read by David. **This is deliberately a human-only consumer and
  therefore write-only by the §0 field-granularity rule** — no code reads it. That is registered as
  the honest answer, not hidden: an advisory human-facing report is legitimate, but it must be
  *named* as such, and it means D1 gets **no gate stage** and cannot RED a release.
- *Surface parity:* CLI only. Not a hook, not a gate stage. Matches `gate_yield candidates`, which
  is also CLI-only — parity with the sibling instrument is the point.
- *Reverse sweep:* `/grade` (§13's process-grading command) should mention this instrument, since
  that is where a human already goes to read the learning loop. One line in `commands/grade.md`.
- *Activation:* opt-in CLI, run by a human. Per §6b (onboard, don't hide), it needs an onboarding
  contract: a line in `CLAUDE.md`'s calibration block and in `docs/calibration/README.md`.

**Flow table (§6c):**

| flow | producer | consumer | liveness test |
|---|---|---|---|
| doctrine change rows | `calibration/ledger.py score` (existing) | `ledger.py candidates` | `test_ledger_candidates::test_zero_hit_section_is_a_candidate` |
| candidate list | `ledger.py candidates` | **David (human)** — no code consumer, registered as advisory | reader-facing; no mechanical liveness (stated, not hidden) |
| coverage line | `ledger.py candidates` | `test_ledger_candidates::test_coverage_line_names_unmeasured` | planted mixed-era row must be named in output |

**DoD:** all three red-first assertions green; run against the real 112-row ledger and the output
reviewed by David for signal-vs-noise; **registered in `capabilities.json`** with the advisory
human-consumer honestly stated; ledger entry registered for any SKILL/CLAUDE.md text added.

**Self-application (the rule D1 must survive):** if after two cycles D1 has produced candidates and
none was ever acted on, D1 is itself a zero-yield instrument and gets retired under its own
criterion. Registered as dated debt, owner david, expiry 2026-11-15.

---

### D2 — Finding taxonomy + recurrence detection (the codification loop's missing input)

**Plain English:** when a review finds something, record what *kind* of thing it is — a rule a
machine could check, something a test could catch, or a genuine judgment call — and give it a short
key. When the same key shows up twice, that is a guard nobody built yet, and the tool says so.

**Red-first:** a fixture with two records sharing `recurrence_key: "grep-counts-docstrings"` and
`class: deterministic` must produce exactly one unbuilt-guard finding; the same key across two
records with `class: judgment` must produce none (judgment recurring is not a missing guard — it is
a genuinely recurring judgment); a single occurrence must produce none. RED before implementation.

**Behavior:**
1. `bin/review_ledger.py` finding schema gains two **optional-then-required** fields:
   `class: deterministic | execution-testable | judgment` and `recurrence_key: <short-slug>`.
   Optional for existing records (append-only; assumption #4 and the deferral above forbid
   retroactive classification), **required for records whose `id` date is ≥ the ship date** —
   enforced in `validate_record`, so the requirement arrives without rewriting history.
2. New verb `review_ledger.py recurrence`: prints keys appearing in ≥2 records, grouped by class,
   with the record ids. A `deterministic` key at ≥2 is labelled **UNBUILT GUARD** and cites §13's
   authoring ritual (replay against the motivating artifact, freeze as a planted fixture citing the
   pre-fix sha) as the next step.

**Why this is one schema change and not two:** D3 also wants to read `docs/reviews/`. Doing D2 and
D3 as separate migrations of the same record type would be the Nth-copy pattern. **One schema, two
readers** — stated here so the architecture-adversary has something to refute rather than discover.

**Edge cases:**
- an author picks a fresh key for a recurring problem (the obvious defeat) → the tool cannot detect
  this and **must say so in its own output**: "counts authored keys; a re-keyed recurrence is
  invisible to this instrument" (§12: a control carries its denominator, and this one's blind spot
  is the honest denominator);
- a key recurring across *the same* review record → counts once, not twice;
- `class` present but `recurrence_key` absent on a post-ship record → RED with the specific missing
  field, not a generic schema error;
- an existing pre-ship record touched for an unrelated reason → must not suddenly require the new
  fields, or every historical edit becomes a migration (this is the trap that makes "optional-then-
  required" schemas fail in practice, and it needs its own planted test);
- key collision between unrelated findings (`"parser"`) → no mechanical defense; mitigated by
  requiring keys to be ≥3 hyphenated words, checked in `validate_record`.

**UX test:** after a review, David runs `recurrence` and sees a short list of "this keeps happening
and no guard exists". Empty list prints "no recurring keys" plus the coverage line — never nothing.

**Integration surface:**
- *Consumes:* `docs/reviews/*.json` + `index.json`, `bin/review_ledger.py`'s existing
  `validate_record`.
- *Emits → named consumer:* (a) the RED path — `validate_record`'s problem strings are consumed by
  `validate_repository` → `main()` → **`gate-manifest.json`'s ledger-adjacent stage and
  `force_full` on `docs/reviews/**`**, so a malformed record already fails the gate at field
  granularity; (b) the `recurrence` verb's stdout → David (human, advisory, no code consumer —
  stated, not hidden, same as D1).
- *Surface parity:* CLI only; the schema half is enforced everywhere the gate runs (local + CI),
  which is the important parity.
- *Reverse sweep:* the adversary agent briefs (`agents/*.md`) should instruct agents to emit
  `class` and `recurrence_key` in their findings — otherwise the fields are populated by hand
  forever and will rot. **This is the deliverable's real integration risk** and gets its own
  sub-task: update `claims-verifier`, `integration-adversary`, `architecture-adversary`,
  `adoption-adversary` briefs. Note that `agents/*.md` is a **watched gate surface** under rule (d),
  so this needs a `calibration/gate-changes.md` entry.
- *Activation:* schema enforcement on by default (it is part of an existing blocking validator);
  `recurrence` verb is opt-in CLI with a §6b onboarding line.

**Flow table (§6c):**

| flow | producer | consumer | liveness test |
|---|---|---|---|
| `class` / `recurrence_key` fields | adversary agents + human authors | `validate_record` (RED on post-ship record missing them) | planted post-ship record without `class` must RED |
| recurrence counts | `review_ledger.py recurrence` | David (human, advisory) | planted 2× deterministic key → exactly one UNBUILT GUARD line |
| agent-emitted fields | `agents/*.md` briefs | the record files themselves | a brief that does not mention the fields is caught by `test_agents.py` roster check |

**DoD:** red-first assertions green; four agent briefs updated *and* `gate-changes.md` entry
written; run against the real 88 records with all pre-ship records still validating; registered in
`capabilities.json`.

---

### D3 — Make the zero-rejection rate visible (deliberately the smallest deliverable)

**Plain English:** in 88 findings, nothing has ever been rejected. Print that number so it stops
being invisible. Do not build a system around it.

**Scope discipline (why this is 20 lines, not 200):** the spec-integrity section asked whether a
materially simpler approach exists, and here it plainly does. My first instinct was a new record
type for advisory-adversary findings with required dispositions. That is speculative machinery
built on a number nobody has looked at yet. **Look at the number first.** If the rate stays zero
for two more cycles with a visible counter, *then* the machinery is justified by evidence rather
than by hunch — and by then D2's taxonomy makes it nearly free.

**Red-first:** a fixture with 3 incorporated / 1 rejected must report `rejected 1 of 4 (25%)`; a
fixture with 0 rejected must report `rejected 0 of N (0%) — no finding has ever been rejected`
as an explicit, unmissable line rather than a `0` in a table.

**Behavior:** `review_ledger.py stats` (or a `--stats` flag on the existing verb — decide at
implementation, one entry point either way) prints the status distribution across all records, with
the zero-rejection case called out in words. Advisory. **Never gates.**

**Edge cases:**
- a single record with one finding → percentages are meaningless at N=1; print counts and suppress
  the percentage below a stated N;
- `open` findings → excluded from the rejection denominator (an open finding has not been
  adjudicated yet), and the exclusion is **named in the output**, not silent;
- new statuses added later → unknown status must be counted and listed, never dropped into "other".

**UX test:** the line reads as plain English to a non-code reader — "no finding has ever been
rejected" — per the `/readable` business-owner test (L-20260813-08). It must not read
"rejection-class cardinality: 0".

**Integration surface:**
- *Consumes:* `docs/reviews/*.json` — same loader as D2, **shared, not duplicated**.
- *Emits → named consumer:* stdout → David (human, advisory, no code consumer — stated).
- *Surface parity:* CLI only.
- *Reverse sweep:* `/grade` should surface this alongside D1's candidates — both are learning-loop
  reads and should not be two separate rituals.
- *Activation:* opt-in CLI. Explicitly **not** a gate stage: gating on a rejection *rate* would
  create direct pressure to manufacture rejections, which is the metric-gaming failure §13 is built
  around. Stated here so the decision is on the record rather than assumed.

**Flow table (§6c):**

| flow | producer | consumer | liveness test |
|---|---|---|---|
| status distribution | `docs/reviews/*.json` | `review_ledger.py stats` → David | fixture with 1 rejected → `25%`; fixture with 0 → the words |

**DoD:** red-first assertions green; real-tree run prints `0 of 85 adjudicated`; **Q2 answered by
David** before any follow-on machinery is considered.

---

### D4 — Pin the standing prompt's guard roster (~15 lines, mechanism over prose)

**Plain English:** `CLAUDE.md` tells every downstream repo which guards exist. That list is prose.
Make a test compare it to the guards that actually exist.

**Red-first:** delete a guard name from `CLAUDE.md`'s roster line in a fixture → RED; add a
non-existent guard name → RED; add a real new guard to `hooks/scripts/` without updating
`CLAUDE.md` → RED. The third is the one that matters and is the one a substring check cannot do.

**Behavior:** `test_agents.py` (which already reads `CLAUDE.md`) gains a roster-parity check:
the guard names in the standing prompt's roster == the guard scripts in
`plugins/tdd-playbook/hooks/scripts/` that are registered as PreToolUse hooks in `hooks.json`,
partitioned into blocking vs opt-in, matching what the prose claims. Replaces presence-by-substring
with a set comparison.

**Edge cases:**
- a hook script that is a helper, not a guard (`_common.py`, `capture.py`, `intent_nudge.py`,
  `build_completion_reminder.py`) → must be excluded by *what `hooks.json` registers it as*, not by
  a hardcoded name list that drifts (§12's "a roster this file cannot drift with");
- a guard registered but demoted by default → belongs in the opt-in partition; the test must
  distinguish the two partitions, since conflating them is exactly the v1.32.0 fact the prose
  encodes;
- `AGENTS.md` is byte-equal to `CLAUDE.md` + HOST_NOTES (`test_reference_docs.py:168`) → the fix
  must not break that equality; the check reads `CLAUDE.md` only and the existing equality test
  covers propagation.

**UX test:** a developer adds a guard, forgets the prompt, and the failure message says which guard
is missing from which line — not "roster mismatch".

**Integration surface:**
- *Consumes:* `CLAUDE.md` roster line, `hooks/hooks.json` registrations, `hooks/scripts/*.py`.
- *Emits → named consumer:* RED in `test_agents.py` → `gate_runner.py` stage loop (same field-level
  path as D0).
- *Surface parity:* the pin protects the *downstream* surface — every vendored repo receives the
  roster as instructions, so this is the highest-leverage 15 lines in the plan.
- *Reverse sweep:* the same prose-roster class exists in the standing prompt's step-2 verification
  checklist (it names `tdd_lock.py`, `with_snapshot.py`, `grade_from_otel.py`,
  `capability_registry.py`, `dataflow_sweeps.py`). **That list is also unpinned and also ships
  downstream** — D0's vendoring roster and this check should share one source of truth rather than
  become a third list. Fold into D0's implementation or register as dated debt; do not leave as a
  silent third copy.
- *Activation:* on by default; part of the standing suite.

**Flow table (§6c):**

| flow | producer | consumer | liveness test |
|---|---|---|---|
| guard roster | `hooks.json` registrations | `CLAUDE.md:76` prose ← pinned by `test_agents.py` | planted new guard without prose update REDs |
| bin roster (D0) | `git ls-files bin/*.py` | `CLAUDE.md` step-2 checklist + installer | shared source of truth or dated debt |

**DoD:** all three red-first assertions green; `AGENTS.md` equality still holds; the reverse-sweep
third-list question answered (folded or dated), not left open.

---

## Sequencing and rationale

| # | deliverable | size | why here |
|---|---|---|---|
| D0 | vendoring roster self-enforcing | ~30 lines | nothing else ships correctly without it — deploy path first |
| D1 | doctrine yield candidates | ~120 lines | the only subtractive instrument; must precede the additive ones |
| D2 | taxonomy + recurrence | ~150 lines + 4 agent briefs | the codification loop's missing input side |
| D3 | zero-rejection visibility | ~20 lines | scoped down deliberately; evidence before machinery |
| D4 | roster pin | ~15 lines | highest leverage per line; protects the downstream surface |

Total ≈ 335 lines of implementation plus tests. **D2 is the only deliverable that touches watched
gate surfaces** (`agents/*.md`) and therefore the only one needing a `gate-changes.md` entry under
rule (d).

## Release-gate impact (checked against `gate-manifest.json`)

- New `bin/` verbs and new `tests/test_*.py` files are picked up automatically by `suite_glob`.
- `bin/review_ledger.py` is already in `force_full` — D2 and D3 will trigger full-suite runs. Expected, not a problem.
- `CLAUDE.md` and `capabilities.json` are in `force_full` — D1, D2 and D4 all trigger it.
- **New test files may need `safe_rules` entries** so unrelated future diffs do not run them
  needlessly. Add during implementation; verify with `gate_plan.py` rather than by inspection.
- `capability_registry.py validate` must pass with the new capability entries — this is enforced
  mechanically by `test_capability_registry.py::test_own_registry` on the real clock, so an
  expired debt entry REDs the suite, not just the checklist.

## Risks — what would make this plan wrong

1. **The plan is itself accretion.** Four new instruments in a repo whose disease is too much
   surface. Mitigated by D1-first and by D1's self-application clause, but the mitigation is a
   promise, not a mechanism. **This is the finding I most want the architecture-adversary to press
   on**, and if it says the plan is net-negative, that verdict should be taken seriously rather
   than folded in as a caveat.
2. **D1's threshold is a guess (Q1).** A wrong threshold produces noise, noise trains the reader to
   ignore the instrument, and an ignored instrument is worse than none because it looks like coverage.
3. **D2's keys are authored, so D2 is defeatable by anyone who re-keys.** Stated in its own output;
   no mechanical fix exists. Honest limit, not a bug.
4. **D3's number may mean the opposite of what it looks like.** Zero rejections could be genuine
   calibration. The deliverable is built to *show* the number, not to interpret it — Q2 must be
   answered by a human.
5. **Three of four instruments have a human as their only consumer.** By this repo's own §0
   field-granularity rule that is write-only, and write-only is not integrated. It is stated
   honestly in every integration surface above rather than dressed up — but if David does not
   actually run these, they are dark features, and §6a will correctly report them as such.

## Adversary dispatch (§0 — mandatory, this plan adds user-facing capabilities)

| agent | why | mandatory? |
|---|---|---|
| `integration-adversary` | every deliverable adds a config gate or user-facing capability — §0 makes this dispatch mandatory, and the risk-5 write-only concern is exactly its hunt | **yes** |
| `architecture-adversary` | four instruments sharing two loaders and one schema — the Nth-copy and knob-sprawl risk is concentrated here; also asked to rule on risk #1 | **yes** |
| `adoption-adversary` | three new CLI verbs whose only consumer is one human who must *find and choose* to run them — the S38/S41 hunt (can a user find this; does anything say whether it got used) is the plan's central weakness | **yes** |
| `script-adversary` | no operator-facing verify/deploy/health script in this plan — dispatch would be ceremony | no, and stated |

Findings are folded in below as deliverables or owned debt, or rejected with a reason —
and per D3's own subject matter, **a rejection here should actually be exercised if one is
warranted**, since this plan's premise is that the rejection path has never fired.

---

## Adversary findings and dispositions

*(populated after dispatch — see the closing section)*

## Loop closed

*(stated after dispatch: yes/no)*
