# §0 plan — doctrine-claim pin + calibration-signal truth

- **Slug:** `2026-08-25-doctrine-claim-pin` (permanent; supersedes nothing)
- **Status:** DRAFT — awaiting David's review. Not approved, not started.
- **Origin:** review of `tjboudreaux/cc-thinking-skills` (2026-08-25), plus the verification
  that falsified most of that review's recommendations.
- **Landing path once approved:** `docs/plans/gated/2026-08-25-doctrine-claim-pin.md`
- **Repo conventions discovered and layered on the universal floor:** `CLAUDE.md` +
  `AGENTS.md` (generated) release-discipline section; blessed gate `sh scripts/civerd_gate.sh`
  as the ONLY suite entrypoint; every mechanical change ships a **planted-input test**;
  §13 guard calibration (replay against the motivating artifact, then freeze the shape);
  §12 a control carries its denominator; `capabilities.json` registry entry required for
  any new gate; rule (d) gate-surface journaling. No `docs/TESTING*` and no
  `.claude/skills` testing addendum exist — those two are "none found".

---

## Spec integrity

**The request as given was "plan the three adoptions." That framing is falsified, and the plan
does not follow it.** Verification against this repo — and then two adversaries against the
draft — found that **three of the four things proposed are already built here, most of them
more strongly than in the repo they were copied from.**

| Proposed adoption | Verified state in this repo |
|---|---|
| Hash-pin the generated reference doc | **BUILT, stronger.** `plugins/tdd-playbook/tests/test_reference_docs.py:36` byte-equality vs `render_reference.render()`; per-input provenance hashes; PLANTED authority drift and PLANTED manual edit both refused. Same for `AGENTS.md` via `render_agents.py`. The source repo has the hash pin and no planted test. |
| Negative-trigger / distractor cases | **BUILT, stronger.** Paired clean controls (`control_for`), FP rate over controls, `must_not_match` so a control *can* fail, unpaired-plant invariant, shrink-only `GRANDFATHERED_PLANT_IDS`. |
| Headroom / difficulty band | **BUILT.** `calibration/plant_vitality.py` (saturated / discriminating / failing / insufficient), capability `plant-vitality`, `test_harness.py::_vitality_tests`. Ran it: `VITALITY: 15 saturated / 10 discriminating / 12 failing / 13 insufficient (K=4)`. |
| *(draft D1)* pin CLAUDE.md's guard-roster enumeration | **BUILT.** `plugins/tdd-playbook/tests/test_hooks.py:1503` `test_guard_roster_derived_and_pinned` derives the roster from `hooks.json` × each script's `NAME` × `_common._DEFAULT_MODES` and pins the prose in **both** `CLAUDE.md` and `README.md`, with five planted fixtures and a vacuity refusal. |

**Assumptions, stated:**

1. The intent behind "adopt these three" is *close the gaps the review actually found*, not
   *ship code matching the review's wording*. The plan follows that reading. The literal
   reading — build all three as written — would produce a second owner for two mechanisms
   that already exist, which `calibration/ledger.py:60-64` names as the exact failure mode:
   *"No second list: a divergent copy is how one of them silently stops covering something."*
2. Today is 2026-08-25. All expiry dates below are relative to it.
3. The plan touches no shipped guard behaviour and no release path. It is doctrine-integrity
   and registry-truth work.

**A materially simpler approach exists and the plan takes it.** The draft proposed *parsing*
hand-written prose and comparing it to a roster. This repo already ruled between the two
available idioms and chose the other one: **generate the volatile passage between sentinels**
(`plugins/tdd-playbook/bin/render_agents.py:99-104` `_replace_block`;
`plugins/tdd-playbook/bin/review_ledger.py:728` `record_output_block()`). That docstring names
the recurrence keys `constant-second-home` and `unpinned-prose-constant` and says plainly:
*"a tidier copy-paste would not have fixed that."* D1 below therefore **generates**, and the
draft's second parser is dropped entirely.

**Open questions for review — not planned around:**

- **Q1 (blocks D4 only).** `check_staleness.py` is the mechanism that used to make a stale
  scoreboard loud, and `capabilities.json:311` records that it now *"gates nothing and nothing
  invokes it."* v1.32.0 retired its clock deliberately. D4 asks you to choose between
  re-activating it in a non-blocking form and recording that it stays dark. **This is your
  call, not the plan's** — it re-opens a doctrine decision, and picking silently would be
  the drift this plan exists to stop.
- **Q2 (scope).** D2 extends the roster pin to three prose claims. Should `docs/HACK_CATALOG.md`
  and the vendored `SKILL.md` sections also come under a doctrine pin, or is that a later
  workstream? The plan assumes later.

---

## D1 — the release-identity roster gets one owner, and CLAUDE.md's sentence is generated from it

**What.** The four release-identity file paths live in exactly one importable place; the
sentence in `CLAUDE.md` that enumerates them is rendered from that place between sentinels, so
the prose can never again name a different set than the mechanism checks.

**Why this one is real.** `CLAUDE.md:213-219` records its own failure: the line said
*"BOTH … and …"*, naming two of the four, and stayed wrong until v1.32.0. The roster today is a
dict literal inside a test function (`plugins/tdd-playbook/tests/test_installer.py:215-223`);
an exhaustive sweep of `plugins/`, `scripts/`, `calibration/` for
`adapter.json|marketplace.json|plugin.json` and `adapter_version|identity_files|VERSION_FILES`
found no other copy of that set — only single-file readers for unrelated purposes
(`run_calibration.py:539-547`, `install_into_repo.py:211-213`, `reset_plan.py:88`). So there is
one literal and one prose copy, and nothing joins them.

**Edge cases** (§2 — only the ones that genuinely apply):

- **Boundary — a fifth identity file is added.** The generated sentence must change without a
  human editing prose; the count word must follow. This is the failure the existing roster pin
  hits from the other side (`test_hooks.py:1449` `_NUMBER_WORDS` is a hardcoded 2..7 table an
  eighth guard breaks) — generation avoids needing the table at all.
- **Malformed — sentinel markers absent or duplicated in `CLAUDE.md`.** Must raise, never
  silently no-op and leave stale prose. This is the vacuous-pass shape §4a bars.
- **Idempotency — render twice, same bytes.** Required, because `AGENTS.md` is a byte-exact
  concatenation of `CLAUDE.md` (`render_agents.py:32-33`) and `test_reference_docs.py:211`
  pins that equality; a non-deterministic render would red the gate on an unrelated commit.
- **Second-order — `AGENTS.md` inherits automatically.** Verified clean by the integration
  adversary; no `AGENTS.md` deliverable is owed. Stated so it is not re-derived later.
- **Failure/rollback — the owner module must not ship downstream.** `install_into_repo.py:43-50`
  vendors `bin/`; a module whose only content is *this* repo's release paths would be copied
  into every consumer repo. The owner therefore lands in `plugins/tdd-playbook/tests/` or
  `scripts/` (never vendored — `vendoring.py:4-7`), **not** `bin/`.

**UX tests** (real interface = the blessed gate and the CLI a maintainer types):

- Maintainer edits the generated block in `CLAUDE.md` by hand → runs `sh scripts/civerd_gate.sh`
  → gate goes **RED** naming the hand edit, exactly as an `AGENTS.md` hand edit does today.
- Maintainer adds a fifth identity file to the owner → runs the renderer → `CLAUDE.md`'s
  sentence and count update with no prose editing → gate green.
- Maintainer runs the renderer twice → second run writes identical bytes → gate green.

**Integration surface:**

- *Consumes:* `plugins/tdd-playbook/tests/test_installer.py` (`test_release_version_identity`,
  which becomes a reader of the owner instead of holding the literal); the sentinel-render
  idiom in `render_agents.py` / `review_ledger.record_output_block`.
- *Emits → named consumer, field granularity:* the rendered sentence in `CLAUDE.md` is read by
  (a) `render_agents.py:32-33`, which concatenates `CLAUDE.md` verbatim into `AGENTS.md`, pinned
  byte-exact at `test_reference_docs.py:211`; (b) the new equality check (`committed == render()`)
  whose consumer is the **gate exit code** via `gate_plan._suite_stages` glob discovery — with
  **no rollup**, unlike `gate_yield.py`'s hook-block rollup. That is acceptable and is stated
  rather than left blank. The roster **value** is read by `test_installer.py`'s version
  comparison at field granularity (`marketplace.plugins[0].version`, `plugin.version`,
  `claude-adapter.adapter_version`, `codex-adapter.adapter_version`).
- *Surface parity:* `CLAUDE.md` (source) and `AGENTS.md` (generated, inherits). `README.md` does
  not carry this claim — verified, no divergence to state.
- *Reverse sweep:* `test_installer.py:215-223` must stop holding the literal and import the
  owner — that is inside this deliverable, not a follow-on. `docs/HACK_CATALOG.md` and vendored
  `SKILL.md` sections are **Q2**, deferred by decision, not by omission.
- *Activation:* **on by default** — it is a gate suite, and `CLAUDE.md` is in `force_full`
  (`gate-manifest.json:45-46`), which `gate_plan.affected_plan` evaluates *before* `safe_rules`
  (`gate_plan.py:178-183`), so a `CLAUDE.md` edit always falls back to the full gate. There is no
  path on which this ships dark.

**Property tests.** `render()` is a pure text transform over (roster, template): idempotence
(`render(render(x)) == render(x)`), and totality — for any roster of size *n* ≥ 1 the rendered
sentence names exactly *n* paths and the count word agrees, with no hardcoded number table.

**Repo-local extras.** Planted-input test is **mandatory** (release discipline): plant a
CLAUDE.md whose sentence names three of four paths and assert the check REDs; plant a missing
sentinel and assert it raises rather than passing vacuously.

**§13 guard calibration — stated weaker, honestly.** The doctrine requires replaying a new guard
against its motivating artifact via `git show <pre-fix-rev>:<file>`. **That is not available
here.** This working tree is a shallow clone (50 commits) with 6 revisions of `CLAUDE.md`, and
an exhaustive scan of all of them found no revision carrying the `"BOTH … and …"` phrasing. The
plant must therefore be a **synthesised** pre-fix fixture whose docstring says so and cites
`CLAUDE.md:216-219` as the recorded description of the defect, **not** a replayed sha. This is a
weaker proof than §13 asks for and the plan states it rather than rounding up.

---

## D2 — extend the existing roster pin to the three claims that escape its window

**What.** The guard-roster pin that already exists reaches one prose location per file; three
further count claims sit outside its reach and are unpinned. Widen the existing owner — do not
add a second one.

**Verified, by measurement, not by reading:**

| Claim | Position | Inside the pin's window? |
|---|---|---|
| `CLAUDE.md:74` "the four BLOCKING guards: …" | char 4522 (the anchor itself) | **yes — covered today** |
| `CLAUDE.md:169` "four block, five are off" | char 11401 | **no** (~6.9k chars past a 500-char window) |
| `CLAUDE.md:184` "the four blocking hooks" | char 12394 | **no** |
| `README.md:17-19` "four block by default … five more are opt-in" | char 1220 | **no — it precedes README's anchor at char 5225** |

Note the correction to the adversary's stated reason: `README.md` *does* contain the literal
`blocking guards` (line 74), so its anchor is found and that location **is** pinned. The
uncovered claim at line 17 fails because `_roster_chunk` uses `re.search` — first match only —
and line 17 sits *before* it.

**Edge cases:**

- **Boundary — `search` → `finditer`.** Every occurrence must be pinned, not the first. This is
  the whole defect.
- **Empty/vacuous — zero anchors found.** The existing vacuity refusal
  (`test_hooks.py:1471-1472`) must survive the change and still refuse a pass; widening a gate
  is the classic moment a vacuity guard gets dropped.
- **Malformed — a claim phrased by function, not by script name** (`README.md:17`: "test
  weakening, the TEST-LOCK, snapshot re-approval, release tags"). The pin must key on the
  **fact** (the count, and the mode partition derived from `_DEFAULT_MODES`), not on script-name
  substrings, or it will false-RED on the friendly phrasing that is already shipped.
- **Second-order — rewording false-REDs.** Acknowledged limitation of the parse idiom the repo
  already owns here. This deliverable does **not** convert `test_hooks.py` to generation; it
  widens reach within the existing design. Converting the guard roster to generation is
  explicitly **out of scope** and left as a note, because that mechanism is working and has
  five planted fixtures.

**UX tests:**

- Maintainer changes "four block" to "five block" at `CLAUDE.md:169` without touching
  `hooks.json` → gate **RED** naming the line. (Today: green.)
- Maintainer registers a genuinely new blocking guard in `hooks.json` → gate **RED** at all
  four prose sites until each is updated → after updating, green.
- Maintainer rewords `README.md:17` while keeping the counts true → gate stays **green**
  (the anti-brittleness check).

**Integration surface:**

- *Consumes:* `plugins/tdd-playbook/tests/test_hooks.py` (`_roster_chunk`, `_roster_problems`,
  `_ROSTER_ANCHOR`), `host_parity.canonical_inventory`, `hooks/scripts/_common._DEFAULT_MODES`.
- *Emits → named consumer:* gate exit code, no rollup (same as D1; stated, not blank).
- *Surface parity:* `CLAUDE.md` and `README.md` both gain the extra covered sites.
  `AGENTS.md` inherits `CLAUDE.md` byte-exactly. No divergence.
- *Reverse sweep:* none — this widens an existing pin and creates no new capability.
- *Activation:* on by default; already inside a gate suite that runs today.

**Property tests.** `_roster_problems` is pure: for a synthesised text containing *k* roster
claims of which *j* are wrong, it returns exactly *j* problems — for all *k* ≥ 1, *j* ≤ *k*.

**Repo-local extras.** Planted-input test per new site (three plants), following the five that
already exist at `test_hooks.py:1556-1577`.

---

## D3 — `plant-vitality`'s registry entry stops lying about how it is reached

**What.** `capabilities.json`'s `plant-vitality` entry describes an activation path and a
consumer that are both false; correct them so the darkness inventory reports the real state.

**Verified defects:**

- `activation.switch` reads *"VITALITY tail line printed by every `run_calibration` run"* — a
  switch that lives inside `calibration-loop`, whose own `activation.default` is **`off`**
  (opt-in since v1.32.0). As written, an on-by-default capability is reached only through an
  off-by-default one.
- `wired_by` names `run_calibration.py` and `author_plants.py` and **omits** both real paths:
  the standalone CLI (`plant_vitality.py:107-143`, which I ran — free, zero model calls, reads
  only `docs/calibration/history.md`) and the gate exercise
  (`calibration/test_harness.py:1794`, which subprocess-runs it against the **real** scoreboard).
- `emits[0].consumers` names `docs/calibration/quarterly.md (the escalation-ceiling watch)`,
  whose mechanism the registry **itself** records as retired: `capabilities.json:320`,
  *"RETIRED OBSOLETE 2026-08-09 (v1.32.0): the MECHANISM this debt names no longer exists."*
  So the capability names two consumers, one behind an off switch and one deleted.

**Why this is the honest heir to "add a headroom band."** The band exists. What is wrong is that
the registry — the thing `doctor` and `/readable` read to answer *"what is built that nothing
reaches?"* — describes it inaccurately, which is precisely why my review misdiagnosed it as
missing. A registry that misreports wiring manufactures exactly this class of wasted work.

**Edge cases:**

- **Auth-negative equivalent / gate refusal:** `capability_registry.py validate` must still pass,
  and `test_capability_registry.py::test_own_registry` runs it with the **real date** on every
  suite run — so a corrected entry that introduces an expired debt REDs the gate immediately.
- **Empty — a consumer with no replacement.** If the retired `quarterly.md` consumer has no
  successor, the honest output is a dated `integration_debt` entry (owner: david;
  expiry: 2026-11-25), never a blank cell and never a silently deleted `emits` row.
- **Idempotency:** re-running `validate` after the edit is a no-op.

**UX tests:**

- Maintainer runs `python3 plugins/tdd-playbook/bin/capability_registry.py doctor` → the
  dark-feature inventory reports `plant-vitality` against its **real** reach (standalone CLI +
  gate exercise), not "reachable only via an off-by-default parent".
- Maintainer runs `sh scripts/civerd_gate.sh` → green, with `test_own_registry` passing on the
  corrected entry.

**Integration surface:**

- *Consumes:* `capabilities.json`; `capability_registry.py validate|doctor`.
- *Emits → named consumer, field granularity:* the corrected `activation` and `wired_by` fields
  are read by `capability_registry.py`'s doctor inventory and by
  `readable_surface.derive()` (`readable_surface.py:128-142`), which derives its pages **only**
  from `capabilities.json` — so this edit is the single change that makes the corrected state
  visible on the `/readable` `dark-inventory` page (`readable_surface.py:54-70`).
- *Surface parity:* `doctor` and `/readable` both; no divergence.
- *Reverse sweep:* worth one sweep pass for other entries whose `switch` names a parent that is
  off — findings become rows here or dated debt, not a silent TODO.
- *Activation:* on by default; both readers already run.

**Property tests.** None — this is a data correction, not new logic.

**Repo-local extras.** `capability_registry.py validate` must pass before commit (release-gate
requirement, enforced mechanically by `test_own_registry`).

---

## D4 — decide, out loud, what happens to `check_staleness.py`

**What.** `check_staleness.py` is the mechanism that used to make a stale scoreboard loud. It is
BUILT and EXERCISED (planted-input calibrated at `calibration/test_harness.py:1123`) and
**never ACTIVATED**: `capabilities.json:311` records *"It gates nothing and nothing invokes it:
absent from `gate-manifest.json`, `gate_runner.py` and `.github/workflows/gate.yml`."*

This is the real form of the gap my review was gesturing at. `CLAUDE.md:39-41` already states
the cost with eyes open — *"nothing now notices if the verifiers decay quietly … the trigger is
a human noticing a verifier behaved badly."* v1.32.0 removed the clock **deliberately**.

**This deliverable does not pick.** It puts two options to you, and whichever you choose becomes
a mechanical row:

- **(a) Re-activate non-blockingly** — `check_staleness --warn-only` emits an advisory line in
  the gate's output. It cannot RED the gate (that would restore the cadence you removed) but the
  fact stops being invisible. Requires a `gate-manifest.json` entry and re-acknowledgement.
- **(b) Record that it stays dark** — a dated decision entry so the next reviewer (or the next
  me) does not re-propose it a third time. Costs nothing and closes the loop honestly.

**Why it is a deliverable and not a question buried in prose:** the §0 discipline says an
unclear item becomes a question for review. This is that question, and it is the *only* one in
this plan that blocks its own deliverable. Everything else proceeds regardless of the answer.

**Integration surface** (option (a) only): *consumes* `gate-manifest.json`, `gate_runner.py`;
*emits → consumer* an advisory line whose consumer is **a human reading gate output** — stated
in those words, following the precedent `render_reference.py:96-105` sets for
`participation_report`; *surface parity* local gate and `.github/workflows/gate.yml`;
*reverse sweep* none; *activation* explicitly **warn-only, on**, never blocking.

---

## Cross-cutting activation steps (fail-closed — these will stop the build if skipped)

1. **`gate-manifest.json` roster re-acknowledgement.** A new `plugins/tdd-playbook/tests/test_*.py`
   file **is** discovered by the glob (`gate_plan.py:66-75`), but `full_plan` then raises
   `PlanError("gate roster digest mismatch…")` (`gate_plan.py:96-101`) until
   `acknowledged_roster_sha256` is updated; editing the manifest at all also requires
   re-acknowledging `acknowledged_plan_sha256` (`gate_plan.py:87-91`). The gate refuses to run
   until both are done — loud, not silent, but it must be in the plan.
2. **Regenerate `docs/reference/current-state.md`.** `gate-manifest.json` is a provenance input
   (`render_reference.py:23`) and the rendered `Discovered suites` / `Suite IDs` lines change
   with any new suite file.
3. **Register the D1/D2 pin in `capabilities.json`** as `doctrine-claim-pin`
   (`activation.default: on`; `wired_by` naming the suite; `exercised_by` naming the planted
   test). Without this it is invisible to `doctor` **and** to `/readable`, because
   `capability_registry.py validate` cannot detect an *absent* capability by construction.
4. **Rule (d) / `gate-changes.md`: nothing owed.** `check_scoreboard_integrity.py:191-224`
   protects SKILL `##` headings, `agents/*.md`, `commands/*.md`; `ledger.py` `SURFACE_PATTERNS`
   the same set plus `scenarios.json` and `corpus/approved/`. `CLAUDE.md` is in **neither** — and
   that absence is the single strongest argument *for* D1 and D2: a whole doctrine section can be
   deleted from `CLAUDE.md` today with no journal entry and no RED.

---

## Rejected, with reasons (so they are not re-proposed a third time)

| Rejected | Reason |
|---|---|
| A second CLAUDE.md guard-roster parser | Already owned by `test_hooks.py:1503` with five planted fixtures. `ledger.py:60-64`: *"No second list: a divergent copy is how one of them silently stops covering something."* |
| "Make the vitality reading free" | Already free. `plant_vitality.py` reads only `history.md`, has a standalone CLI, costs zero model calls, and runs in the blessed gate. Premise was false. |
| Render vitality into `docs/reference/current-state.md` | Three independent objections: **layering** — `bin/` is vendored (`install_into_repo.py:43-50`), `calibration/` is not, so the import direction breaks the vendored copy; **staleness** — `summary_line()` carries no as-of date, so a year-old reading renders as a current fact in a doc that says "machine-owned facts"; **duplication** — it would be a fifth place the same reading appears, risking the `write-only-audit-artifact` shape the ledger already records twice. If a rendered line is ever wanted, it must import `plant_vitality.summary_line`, add `history.md` to `PROVENANCE_INPUTS`, name a producer-side re-render trigger, and stamp `history_format.latest_run_date`. |
| Converting the guard roster from parse to generation | Out of scope. The existing mechanism works and is planted-tested; churn without a defect. Noted for a future workstream. |
| Extending the doctrine pin to `HACK_CATALOG.md` / vendored `SKILL.md` | Deferred by decision (**Q2**), not omission. |

---

## Unenforceable deliverables (prose)

**D5 — a `docs/reviews/` record of this episode.** Not a mechanical deliverable and not disguised
as one. It captures that four proposed adoptions were checked and three were already built, so
the next reviewer does not spend the cycle again. Written as a real record against
`review_ledger.py validate` (findings dated on/after the epoch require
`class: deterministic|judgment`, a `recurrence_key`, and `guard: {kind, ref, why}`).

Proposed keys: `already-built-adoption-proposed` (judgment; `guard: {kind: none, …}` — no machine
could have caught a reviewer's unverified negative) and `registry-understates-wiring`
(deterministic; guard ref = the D3 correction). Both are honest `none`/`test` answers rather than
blanks — the blank was the problem the epoch fixed.

*(D5 has a named file and a named reader — `review_ledger validate` and the `recurrence`
inventory rendered into `current-state.md`. An unnamed prose file would have been decoration.)*

---

## Tripwire deliverable list

| # | Deliverable | BUILT | WIRED (production composition root) | ACTIVATED | EXERCISED |
|---|---|---|---|---|---|
| D1 | Identity roster owner + generated CLAUDE.md sentence | owner module + renderer | `test_installer.py` imports the owner; `render_agents.py` concatenates into `AGENTS.md` | on; `CLAUDE.md` in `force_full` so no affected-mode skip | planted 3-of-4 roster + missing-sentinel plant |
| D2 | Roster pin widened to the 3 escaped claims | `finditer` + fact-keyed checks in `test_hooks.py` | existing suite, already in the gate roster | on | 3 new plants beside the existing 5 |
| D3 | `plant-vitality` registry truth | `capabilities.json` edit | `capability_registry validate`; `readable_surface.derive()` | on; both readers already run | `test_own_registry` with the real date |
| D4 | `check_staleness` decision | option (a) manifest entry, or (b) dated decision record | (a) `gate_runner`; (b) the registry | (a) warn-only on; (b) explicitly none | (a) planted stale scoreboard (exists: `test_harness.py:1123`); (b) n/a |
| D5 | Review record (prose) | `docs/reviews/*.json` | `review_ledger validate` | n/a | schema validation only — **not** a behavioural test |

**Stated weaker, per the rule:** every EXERCISED cell above means *the test exists at this sha,
unskipped, gate green*. None of them means *the behaviour was observed running* — that is the
RUNNING leg, and no row here claims it.

---

## Loop closed

**yes** — `integration-adversary`: top island *"D1's guard-roster half is already built at
`test_hooks.py:1503`; re-proposing it creates the divergent second owner `ledger.py:60-64`
forbids"* (8 islands; islands 1, 2, 3, 5, 6 folded in as D2/D3/D4 and the activation steps;
island 4 folded into Spec integrity; island 7 folded into the rejection table; island 8
addressed by D3, which is the single edit that reaches `/readable`).
`architecture-adversary`: top band-aid *"D1 picks the parse idiom this repo already abandoned
for exactly this defect shape — generate the passage instead"* (5 findings; findings 1, 2, 3, 4,
5 folded in as the D1 redesign, the D3 rewrite, and three rows of the rejection table).

Two adversary claims were independently re-verified and **one was corrected**: the
`README.md:17` gap is real, but not for the stated reason — `README.md` *does* contain the
literal `blocking guards` at line 74, so its anchor is found; line 17 escapes because
`_roster_chunk` uses first-match `re.search` and line 17 precedes the anchor.

**Claims: 21/21** — every file:line in this plan was read or executed in this working tree on
2026-08-25. The one negative I could not establish exhaustively is stated as such: the §13
motivating-artifact replay for D1 is **unavailable** in this shallow 50-commit clone, and the
plan requires a synthesised fixture that says so rather than a replayed sha.
