# Plan — Review as a judgment surface: closing the codification loop

**Date:** 2026-08-14 · **Revision:** v2, post-adversary
**Branch:** `claude/code-review-taste-judgment-2czk91`
**Provenance:** four recommendations derived from reading *"Code review is a taste problem"*
(Jain & Poll, TNS, 2026-08-13) against this repo's doctrine and artifacts.

---

## What happened to this plan

The v1 draft proposed five deliverables, ~335 lines. Three fresh-context adversaries were
dispatched against it per §0. All three returned negative verdicts:

| adversary | verdict | the finding that mattered |
|---|---|---|
| `architecture-adversary` | **BAND-AID (7)** — "net-negative as written, should be roughly 90% smaller" | four of five deliverables are refuted by code that already exists in this repo |
| `integration-adversary` | **ISLANDS (4)** | three human-only emitters with no scheduled reader; D2's required fields have no producing seam anywhere in the shipped surface |
| `adoption-adversary` | **STRANDED (4)** | the plan's own dark-feature mitigation does not measure usage; `capability_registry.py:187` computes darkness from *declared activation*, never observation |

**Every load-bearing claim in all three reports was independently verified against the tree
before acceptance** (§12: subagent reports are unverified claims). The verification is recorded
below, per finding. Nothing was accepted on the adversary's word.

**Outcome: ~335 lines → ~55 lines plus one re-scoped deliverable.** Three of five deliverables are
**deleted**, one is **replaced by a decision rather than code**, and the two survivors are
re-seamed onto machinery that already exists.

This is the plan working. A plan whose premise was "this repo's disease is accretion" proposed to
rebuild three things the repo already had — because it did not read the existing surface first.
`readable_surface.py:9-10` states the rule the draft needed: *"Not an extractor: any new derivation
belongs to the existing owner."*

---

## Correction record (§12) — five claims of mine, refuted and verified

The draft's executive summary carried a statistics table. Most of it was wrong. Each correction
below was verified by me directly, not taken from the adversary.

**C1 — "112 registered doctrine changes."** *Refuted.* Running this repo's own parser:
`parse_ledger` returns **58 registered + 54 scored = 112**. I read a union of two row types as one
count. The honest coverage figure is **54 of 58 registered entries priced = 93%**, which is the
near-opposite of the ~46% my table implied.

**C2 — "roughly a third of measurable doctrine changes measured as HIT."** *Refuted.* 16/51 put 20
`INCONCLUSIVE(no-baseline)` rows into the denominator — the exact coercion the draft's own D1
honesty rules ordered the tool to refuse. Measured-only: 16 HIT + 2 PARTIAL of 32 = **56%**. I also
dropped `REGRESSED 1` and `INCONCLUSIVE(below-noise-floor) 2` — and `REGRESSED` is the single most
decision-relevant class in the table.

**C3 — "nothing in the repo reads that column in aggregate."** *Refuted.* `calibration/ledger.py:720`
`cmd_report` counts every scored row by verdict, runs a one-sided sign test, and is registered as a
verb at `:803`. It prints `LEDGER SIGNAL: 18 of 19 moved entries moved as predicted — p=0.000`.

**C4 — "rule (d) makes doctrine additions free; nothing makes them accountable."** *Refuted.*
`calibration/ledger.py:758-782` `cmd_debts` requires every FLAT/REGRESSED/SURPRISE entry to carry a
dated follow-up, **exits 1** when one is missing, and `--emit` prints paste-ready registry debt JSON.

**C5 — "`CLAUDE.md` names v1.32.0 while the plugin is at 1.35.0" (carried from the conversation).**
*Refuted in v1 and still refuted:* all five occurrences are correctly-dated historical markers.

**What survived C1–C4:** the ledger has no *section* granularity, and doctrine is unmeasurable by
design. That is a real gap — but it is a decision at the registration seam, not a missing reader.
See "The one open decision" below.

---

## Deleted deliverables, with the evidence that killed them

### D0 (vendoring roster) — DELETED. The premise was false.

The draft claimed *"new `bin/` files must be added to its vendoring roster or they simply do not
ship."* **There is no such roster.** `scripts/install_into_repo.py:43-50` `COPY_TREES` names
*directories* — `("bin", "bin")` — and `_copy_tree` at `:74-98` walks them with `os.walk`. Every
`bin/*.py` vendors by construction. `capabilities.json:573` already registers this by name:
*"COPY_TREES bin/ vendor rule — auto-vendors"*.

D0's red-first test could not have gone red for its stated reason: the planted file would vendor.
The draft would have *created* the per-file roster it proposed to guard.

Its own deferred question is also answered: `_merge_hooks:124-166` prunes and re-adds from
`hooks/hooks.json` wholesale — no roster, already covered.

**The one real hand-maintained roster in this family is `CODEX_COPY_FILES:58-61`** (two files, for
the Codex host). That is the only place the D0 *class* of drift can occur. Retained as D-D below,
optional, ~5 lines.

### D1 (doctrine-yield reader) — DELETED as a reader. Structurally vacuous.

Verified directly: **all 9 SKILL.md-surfaced ledger entries carry `expect: none`**, and
`calibration/ledger.py:67-70` explains why in a comment — `EFFECTFUL` covers
`scenarios.json`, `corpus/approved/` and `agents/` because *"Doctrine prose and command text can
legitimately be inert."*

Consequences, both fatal:
- Under D1's own inherited honesty rule (INCONCLUSIVE ⇒ unmeasured), **every** SKILL.md row is
  unmeasured ⇒ SKILL.md is UNMEASURED ⇒ **zero candidates, permanently**.
- The `surface` cell holds file paths (`ledger.py:161`), not section anchors. All 9 entries carry
  the identical cell. There is no section history to group by. Worse, 8 of the 9 are dated
  `2026-08-06` — one cycle — so nothing clears the ≥2-cycles leg either.

The draft called section-keying "the hardest part of D1"; it is not an edge case, it is the entire
feature, and it requires a **ledger schema change the draft never listed as a deliverable**.

**The plan's sole stated mitigation for its own accretion risk — "the deliverable that can remove
surface ships first" — was therefore not a promise. It was a promise that provably could not be
kept.** That is the honest verdict on the draft and it is recorded rather than softened.

### D3 (zero-rejection visibility) — DELETED. Already shipped and gate-enforced.

`docs/reference/current-state.md` already contains, under "Adversarial review records":

```
- Review records: 15. Findings: 88.
- `incorporated`: 16   · `open`: 3   · `rejected`: 0   · `verified_closed`: 69
```

Generated by `render_reference.py:130-140`, staleness-REDs at `:151`, wired into
`gate-manifest.json`, pinned by `test_reference_docs.py`. Those are the draft's own
executive-summary numbers — I took them from this artifact and then proposed building it.

If the *words* are the deliverable, that is D-C below: ~3 lines in the existing generator.

---

## What survives

### D-A — Finding taxonomy + recurrence detection (the only substantial survivor)

**Plain English:** when a review finds something, record what *kind* of thing it is and give it a
short key. When the same key appears twice, that is a guard nobody built, and the tool says so.

This survived all three adversaries as the one genuinely missing mechanism. It is also the one the
draft under-specified most, so the re-scope is substantial.

**Red-first:** two records sharing `recurrence_key: "grep-counts-docstrings"` at
`class: deterministic` → exactly one UNBUILT GUARD line; same key at `class: judgment` → none
(recurring judgment is not a missing guard); single occurrence → none. RED before implementation.

**Behavior:**
1. `bin/review_ledger.py` finding schema gains `class` + `recurrence_key`, **optional for existing
   records, required for records whose `id` date is ≥ ship date** — enforced in `validate_record`,
   so the requirement arrives without rewriting append-only history.
2. New verb `review_ledger.py recurrence`: keys appearing in ≥2 records, grouped by class. A
   `deterministic` key at ≥2 is labelled **UNBUILT GUARD**.

**Changes forced by the adversaries — each with its evidence:**

| # | change | why (verified) |
|---|---|---|
| A1 | **Six agent briefs, not four** — add `tripwire-auditor` and `script-adversary` | real records name six reviewers: `integration-adversary` 13, `architecture-adversary` 8, **`tripwire-auditor` 4**, `script-adversary` 1, `claims-verifier` 1, `adoption-adversary` 1. The draft's list missed the third most frequent author. |
| A2 | **Ship the producing seam, or a dated debt saying records stay hand-authored** | exhaustive sweep (`grep -rn "docs/reviews"` across `commands/`, `agents/`, `skills/`, `CLAUDE.md`) returns **zero** authoring instructions. Every hit is a reader. The record type has no producer in the shipped surface. |
| A3 | **Replace the liveness test** — assert on a *record*, not on brief text | the draft's test ("a brief that does not mention the fields is caught by `test_agents.py`") is a §1 self-consistency test: it reads a file this repo authors, with no representation of the consumer. It would still pass with `validate_record` deleted. |
| A4 | **Name the vocabulary's owner** — one tuple in `review_ledger.py`, imported by the briefs' roster test and the verb | `readable_surface.py:44-49` establishes the rule by citation: a class vocabulary needs ONE machine owner, *"a rename would leave every copy silently wrong."* |
| A5 | **Feed `docs/HACK_CATALOG.md:294`, don't parallel it** | that table is headed *"Guard ↔ entry map (kept current; a row with '—' is a known open gap)"* — a curated unbuilt-guard list with a quarterly ritual and a DECAY WARNING. `recurrence` output names the H-row it maps to, or proposes a new one. One place a reader learns "this class has no guard." |
| A6 | **Budget the ledger cost** | `agents/` is in `EFFECTFUL` (`ledger.py:69-70`), so `no_effect_problems:356-365` REDs any covering entry using `expect: none`. Six brief edits must pre-register named scenarios and a `claimed` movement at plan time, and `unscored_problems:430-435` makes scoring mandatory once a run binds. Plus a `calibration/gate-changes.md` entry (rule d). |
| A7 | **Ship a coverage ratio instead of declaring the blind spot unfixable** | the draft said re-keying defeats it and *"no mechanical fix exists."* `guard_note.py:24-29` documents the house answer: *"Self-report can move the numerator; it cannot touch the denominator."* Keyed-vs-total findings is a denominator that moves against re-keying with no semantic clustering. |
| A8 | **Route into the cycle block** — `calibration/run_calibration.py:750-811` | that block already carries `gate_yield` rollup/candidates, the dataflow trend, `ledger.py report` and plant vitality. A verb with no scheduled reader is §6b dark waste. ~4 lines, wrapped like its neighbours so it never fails the run. |
| A9 | **Log a machine usage event** — copy `readable_surface.py:285-294` (6 lines) | `capability_registry.py:187` computes the dark inventory as `activation.default == "off"` — declared, never observed. The draft's risk-5 mitigation ("§6a will report them as dark") measures nothing either way. `docs/calibration/usage.md` is the real denominator. |
| A10 | **Register the consumer as typed `kind: "human"`** | `capability_registry.py:61` `CONSUMER_KINDS = ("capability","file","human","external")`, and `doctor:236-259` buckets human/external as *legitimate, NOT a finding*. So a human consumer **is** legal — but only in typed form; untyped prose lands in the `unset` bucket and grows the registry's own open migration debt (57 untyped today). |
| A11 | **Correct the emits citation** | the draft cited *"`gate-manifest.json`'s ledger-adjacent stage"*. That stage is `calibration/ledger.py check` — a different tool. `review_ledger.py` reaches the gate via `test_review_ledger.py:181`, which calls `validate_repository(REPO)` on the real tree. |
| A12 | **First-run contract** | `review_ledger.py:328` resolves the repo root with four `dirname` hops — correct at `plugins/tdd-playbook/bin/`, **off by one** at a vendored `.claude/bin/`, where it names the repo's *parent*. Inherit `readable_surface.py:141-142`'s exit-3 vacuous refusal with a relay instruction, and prove root resolution from a vendored layout in the same test. |

**A12 is a pre-existing defect in shipped code, not a plan gap** — it affects `review_ledger.py`
today in every downstream vendored copy. It is folded here because D-A is the diff that touches
that file; if D-A is dropped, A12 should be filed separately rather than lost.

**DoD:** red-first assertions green · six briefs updated · `gate-changes.md` entry · ledger
pre-registration with named scenarios · real-tree run with all 88 pre-ship records still validating
· typed `kind:"human"` registry entry with a `liveness.probe` on `usage.md` rows · usage row proven
to appear after one invocation · cycle-block line landed.

### D-B — Guard roster pin, re-seamed (~15 lines, strictly better coverage than the draft's)

**Plain English:** `CLAUDE.md` and `README.md` each tell readers which guards exist. Both are prose.
Derive the answer from the machinery instead of pinning one copy.

**The draft's spec was wrong in a way that would have shipped broken.** It said the check reads
guards *"registered as PreToolUse hooks in `hooks.json`, partitioned into blocking vs opt-in."*
Verified by parsing `hooks/hooks.json`:

```
PreToolUse  -> exitcode_guard, snapshot_guard, tag_guard, test_lock_guard
PostToolUse -> exhaustive_claim_guard, flaky_guard, overmock_guard, red_lock, test_weakening_guard
```

`test_weakening_guard` — the guard the roster **leads with**, one of the four BLOCKING — is
PostToolUse. A PreToolUse-restricted check would have excluded 5 of 9. And the blocking/opt-in
partition does not come from the event type at all: it lives in `hooks/scripts/_common.py:26-53`
`_DEFAULT_MODES`, which is **three**-valued (`off`/`warn`/`block`), not two.

**Re-specified behavior:** derive from `host_parity.canonical_inventory()["guards"]`
(`bin/host_parity.py:38-48` already parses the roster out of `hooks.json` — do not write a second
parser) × `_common._DEFAULT_MODES` for the partition. Assert set-equality against **both**
`CLAUDE.md:76` and `README.md:72-74`, and **replace `test_hooks.py:478-483`'s hardcoded name lists
in the same diff** so the fix does not become a sixth roster.

**There are five prose rosters, not the three the draft counted:** `CLAUDE.md:76` (guards),
`CLAUDE.md` step-2 (bins), `README.md:72-74` (guards), `README.md:69-70` (bins), and
`test_hooks.py:478,481` (hardcoded partition). **The two bin lists already disagree today** —
README says `verify_citations`, CLAUDE.md says `dataflow_sweeps.py`. D-B fixes the guard rosters and
**names the bin-roster divergence as dated debt** rather than silently leaving it.

**Open sub-decision (advisory finding, worth a minute of David's time):** generation may beat
pinning. `render_agents.py:31-36` already generates `AGENTS.md` from `CLAUDE.md` with a byte-equality
gate and the banner *"GENERATED FILE — do not edit by hand"* — and its docstring describes exactly
this failure: *"hand-maintained as a mirror and it rotted exactly as hand-maintained mirrors do."*
A pin makes drift loud; generation makes it impossible and deletes the maintenance. Counterweight:
the roster sits inside hand-authored editorial prose, so generating all of `CLAUDE.md` is not on the
table — a marked generated *block* would be. **Pin first, note the option.**

**DoD:** three red-first assertions green (missing name / phantom name / new guard added without
prose update) · both files asserted · `test_hooks.py` hardcoded lists removed in the same diff ·
`AGENTS.md` byte-equality still holds · bin-roster divergence filed as dated debt.

### D-C — The rejection sentence, in the artifact that already exists (~3 lines)

`current-state.md` prints `rejected: 0` as a table row. The one thing worth adding is the *words*,
per the `/readable` business-owner test: **"no finding has ever been rejected"** rather than a `0` a
reader's eye slides past. Land it in `render_reference.py`'s existing review section, and unify the
two duplicate status enums (`review_ledger.VALID_STATUS:15` and
`render_reference.VALID_REVIEW_STATUS:26`) in the same diff.

### D-D — Codex roster check (~5 lines, optional)

`CODEX_COPY_FILES:58-61` is a genuine hand-maintained two-file roster and the only real drift
surface D0 was reaching for. Assert it covers every script the Codex adapter's `hooks.json`
registers, reusing `host_parity._guard_names`. Take it or leave it; it is not load-bearing.

---

## The one open decision (replaces D1 — a decision, not code)

Doctrine yield is unmeasurable **by design**, at one line: `calibration/ledger.py:69-70`.

**Q1 — should `plugins/tdd-playbook/skills/tdd-playbook/SKILL.md` join `EFFECTFUL`?**

- **Yes** → doctrine changes must pre-register scenarios and a predicted effect, exactly as agent
  briefs do. Doctrine stops being free. Costs real work per doctrine edit. In two cycles the ledger
  would hold data a reader could group, and D1 could be re-opened **non-vacuously**.
- **No** → the current comment stands (*"Doctrine prose can legitimately be inert"*), and the honest
  position is that this repo does not measure doctrine yield and does not intend to. That is
  defensible — but it should be a **recorded decision**, not a default nobody revisited.

Either answer is ~1–5 lines. Both are better than the draft's ~120-line reader. **The second half
of the decision, if "yes":** the `surface` cell needs section-anchor granularity (`SKILL.md#§12`),
which is a ledger schema change and its own deliverable.

**Q2 (unchanged from the draft, still unanswered):** the integration adversary demoted to a lead a
point worth taking seriously — `docs/reviews/*.json` records *plan and implementation* reviews whose
blockers must be closed to pass the gate (`review_ledger.py:91-99`), not the advisory adversary
dispositions where a rejection would naturally live. **The zero may be a schema fact rather than a
rubber-stamp signal.** That materially weakens the draft's framing of it, and D-C prints the number
without interpreting it — which is now the right scope.

---

## Sequencing

| # | deliverable | size | note |
|---|---|---|---|
| 1 | **Q1 decision** | 1–5 lines or a recorded "no" | unblocks whether doctrine yield is ever measurable |
| 2 | D-B roster pin | ~15 lines | highest leverage per line; removes a live inconsistency |
| 3 | D-C rejection sentence | ~3 lines | lands in a generated, gate-checked artifact |
| 4 | D-A taxonomy + recurrence | ~150 lines + 6 briefs | the only substantial build; carries A1–A12 |
| 5 | D-D codex roster | ~5 lines | optional |

**D-A ships last, not first.** The draft ordered D1 first on the theory that the subtractive
instrument must precede the additive ones. That theory was sound and its instance was vacuous. The
replacement ordering is: **make the cheap corrections that remove existing inconsistency first, then
build the one new thing** — and D-A now carries A8/A9 (a scheduled reader and a usage denominator),
so it cannot become the sixth human-only instrument sitting unread beside the five that exist
(`readable_surface facts`, `gate_yield candidates`, `ledger report`, `capability_registry doctor`,
`current-state.md`).

Evidence that this matters: `docs/calibration/usage.md` contains its header and **no rows**, while
`gate_yield.md` carries rollups dated 2026-08-12 and 2026-08-13 from the same drain pass. Two cycles
recorded zero machine usage events for the most recent human-facing instrument this repo shipped.

## Gate impact

`bin/review_ledger.py`, `CLAUDE.md`, `capabilities.json` are all in `gate-manifest.json:force_full`
— D-A and D-B trigger full-suite runs. Expected. New tests under
`plugins/tdd-playbook/tests/test_*.py` are picked up by `suite_glob`; anything under `calibration/`
is **not** and reaches the gate only via the `calibration/test_harness.py` fixed stage — the draft
got this wrong and it is corrected here. `capability_registry.py validate` must pass with the new
typed entries, enforced by `test_capability_registry.py::test_own_registry` on the real clock.

---

## Adversary findings — dispositions

Every finding, with its outcome. **Two are rejected with reasons** — the draft's own subject matter
made it worth checking whether the rejection path can actually be exercised, and it can.

| finding | disposition |
|---|---|
| arch F1 / integ P1-1 / adopt note — D0 premise false | **ACCEPTED** — D0 deleted; retargeted at `CODEX_COPY_FILES` as optional D-D |
| arch F2 — statistics are a denominator error | **ACCEPTED** — C1/C2 in the correction record; verified independently |
| arch F3 / integ P1-2 — D1 structurally vacuous | **ACCEPTED** — D1 deleted as a reader; became the Q1 registration-seam decision |
| integ P0-1 — `ledger.py report` already aggregates; `cmd_debts` already holds FLAT accountable | **ACCEPTED** — C3/C4; the draft's spine claim was false |
| arch F4 — D3 already shipped and gate-enforced | **ACCEPTED** — D3 deleted; reduced to D-C |
| arch F5 / F6 — D4 pins one of ≥2 disagreeing rosters; generation is the established seam | **ACCEPTED** — D-B asserts both files, replaces the hardcoded list, names all five rosters; generation noted as an open sub-decision |
| integ P1-4 — D4's PreToolUse spec excludes 5 of 9 guards; `host_parity._guard_names` already exists | **ACCEPTED** — verified by parsing `hooks.json`; D-B re-specified |
| integ P0-3 — D2's fields have no producing seam; 6 reviewers not 4 | **ACCEPTED** — A1, A2, A3 |
| arch F7 / F8 — vocabulary needs an owner; HACK_CATALOG H-map already exists | **ACCEPTED** — A4, A5 |
| arch F10 — `agents/` is EFFECTFUL, brief edits carry unbudgeted ledger cost | **ACCEPTED** — A6 |
| arch F9 / integ P0-2 / P1-5 / adopt F1, F2 — human-only instruments, no scheduled reader, no usage signal | **ACCEPTED** — A8, A9, A10 |
| adopt F3 — cold/vendored first run resolves above the repo | **ACCEPTED** — A12, and flagged as a pre-existing shipped defect |
| integ P2-3 — emits citation names a stage that does not exist | **ACCEPTED** — A11 |
| arch/integ — D2's re-keying blind spot has a house answer | **ACCEPTED** — A7 |
| integ P1-3 — deploy surface is per-deliverable, not uniform | **ACCEPTED** — corrected in Gate impact; `calibration/` is deliberately never vendored |
| adopt F5/F6, integ P2-2 — `/grade` and README routing unowned | **ACCEPTED for D-A** (DoD), **REJECTED for D-B/D-C** — those land in generated artifacts already routed from `README.md:19`; adding routing lines for a 3-line generator edit is the ceremony §0's preamble warns against |
| integ P2-6 — verbs not reachable through `tdd.py`, the portable front door | **REJECTED, with reason** — `tdd.py:373-394` hosts health and state-changing verbs (`doctor`, `reset`, `uninstall`), not reporting. The adversary demoted this to lead L1 itself ("cannot prove the convention excludes reporting"). Adding a reporting verb there would set a convention on one data point. Revisit if a second reporting verb ever wants a home. |
| integ P2-1 — human consumers must be typed | **ACCEPTED** — A10; and it partly *rescues* the draft's honesty claim: `kind:"human"` is explicitly legitimate |
| integ P2-4 — five prose rosters, not three | **ACCEPTED** — D-B names all five; bin divergence filed as dated debt |
| adopt F4 — D2 onboarding line names no file | **ACCEPTED** — folded into A8/A9 (shipping ON with a metric is the cheapest satisfying move) |
| adopt S40 — error messages clean | **noted, no action** |

**Claims: 22 load-bearing · 22 verified (parser runs, `hooks.json` parse, greps, file reads cited
inline) · 0 demoted to leads.** Every adversary claim I acted on was re-derived from the tree.

## Loop closed

**Yes.** Three adversaries dispatched (`integration`, `architecture`, `adoption`);
`script-adversary` correctly not dispatched — no operator-facing verify/deploy/health script in
this plan. All findings dispositioned above: 20 accepted, 2 rejected with stated reasons. The plan
shrank ~85% and two of its five deliverables were deleted as already-existing.
