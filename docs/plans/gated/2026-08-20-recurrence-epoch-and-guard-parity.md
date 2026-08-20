# TDD Plan — reset the recurrence tracker, and make it self-resolving from here forward

**Slug:** `2026-08-20-recurrence-epoch-and-guard-parity`
**Status:** plan, revised after three review rounds (integration-adversary, architecture-adversary,
Codex ×2) and David's scope decision. Supersedes `2026-08-19-mutation-run-wrapper` (shipped).

---

## Context

The Playbook records every review finding. When the same *kind* of defect appears twice or more, it
prints **"UNBUILT GUARD — go build a check for this."** That list is meant to be the to-do list for
what to automate.

**The list is unreliable, and I proved it by measuring rather than reading it:**

- **It cannot see a guard that was built.** Four of its items are guards misfiring; `tag_guard` was
  fixed in v1.42.0 by this repo. It will nag forever.
- **One item is a junk drawer.** `outermost-wire-untested` holds five unrelated findings; two are
  already fixed, one cannot be caught by a machine.
- **The field that links a defect to its check is barely populated and partly wrong.** 6 of 205
  findings carry it; of the 3 recurring keys that have one, 2 point at the wrong category.

So the earlier claim — mine, and the overhaul doc's — that *"four checks your records have been
asking for"* are overdue was a reading of a broken gauge.

**The scope decision that shapes this plan.** My previous draft asked David to retroactively
classify 9 unlabelled keys. He is non-technical and cannot do that curation, and neither can I do it
for him honestly — it is judgment about what each old defect meant. **So the historical list is
retired wholesale and the tracker restarts today**, with the labelling moved to *record-authoring
time*, where the person who found the defect answers it while they still know the answer.

**What that costs, plainly:** the tracker goes quiet until two post-epoch findings share a key —
realistically weeks. **What it does not cost:** anything actionable. Of the 12 items, exactly one is
clearly real and already-unbuilt — guards firing outside their jurisdiction — and **D2 builds it in
this span.** The rest are fixed, already guarded, unverifiable, or not one defect.

---

## Spec integrity

- **Records are NOT deleted.** "Wipe the list" = reset the counter. `docs/reviews/` is append-only
  evidence and stays readable; it simply stops driving the verdict. Deleting it would destroy the
  data that produced this diagnosis.
- **No SKILL.md doctrine line is added.** The originating question (Cheli's *"building seam is not
  the running seam"*) is already §1; it stays in Claude Code memory.
- **Simpler approach, named:** D1+D2 alone are shippable. D3–D6 are what stop them shipping dark.
- **Retracted from my own earlier drafts, all four verified wrong:** that a machine could sort the
  unlabelled keys; that `test_review_ledger.py:558-573` exercises downstream output (it asserts a
  refusal); that `resolve_mode` is the right liveness authority (it is environment-dependent); and a
  calibration budget figure wrong by 12×.

---

## D1 — an epoch line, and a forward rule that resolves itself

**What:** findings before today stop being counted; findings from today forward must say what would
have caught them, so the verdict is always computable and never needs curation.

### (a) The line

`RECURRENCE_EPOCH = "2026-08-20"` in `review_ledger.py`, beside `TAXONOMY_SHIP_DATE` (`:33`) and
`REVIEWER_VOCAB_SHIP_DATE` (`:54`) — the repo's established idiom for a rule that binds only
records dated on or after it.

Pre-epoch findings are **historical**: never counted, never classified, and reported as **one
honest summary line** naming the count and pointing at `docs/reviews/`. Not silence — silence would
look like "no history exists," which is the H15 shape. `outermost-wire-untested` needs no split, no
overlay, no per-finding curation: it is pre-epoch, and the whole junk-drawer problem retires with it.

### (b) The forward rule — the part that makes it self-resolving

From the epoch, `validate` REFUSES a finding that does not answer **"what would have caught this?"**

```
"guard": {"kind": "hook" | "test" | "none",
          "ref":  "<hook NAME>" | "<file>::<symbol>" | null,
          "why":  "<one line — required when kind is none>"}
```

This is the actual fix. The old design asked a *reader* to infer, months later, whether a defect was
guarded. The new one asks the *author*, at the moment of writing, while they still know — and
`"none"` is a first-class, honest answer, not a gap. **Nothing accumulates that a human must later
sort.**

`validate` checks the answer resolves: a `hook` names a real registered hook; a `test` names a
symbol that exists **and is invoked from its module's `main()`**. Reuse `closure_evidence_exists`
(`:297-315`) — this module's existing `file::symbol` resolver — rather than adding a second.

### (c) The verdict, computed not curated

| state | decided by |
|---|---|
| `UNBUILT` | ≥2 post-epoch findings share a key and every one answered `kind: none` |
| `GUARDED` | the named mechanism resolves and ships live |
| `GUARD DARK` | the named hook's **shipped default** is `off` (`_common.py:50-54`) |

**Shipped default, not `resolve_mode()`.** `resolve_mode` reads per-hook env vars, the global env
var, and break-glass state (`:202-229`). D3 commits this inventory to a generated file whose test
asserts committed == rendered — so the same tree would render differently on two machines and fail
the gate for whoever had an override set. **A generated artifact must be a pure function of the
tree.** Session-effective state may be printed by the CLI as a separate, explicitly labelled line;
it is never committed.

`catalog_row` stays **human context only** — it never decides state. H13's cell names both a live
mechanism *and* the default-off `exitcode_guard`, so no row-level rule can classify it.

**Edge cases:** a `ref` that does not resolve → loud refusal, never a silent `GUARDED` · exactly 2
post-epoch findings (the threshold, `:620-627`) · downstream, where `docs/` ships to **neither**
host (`install_into_repo.py:43-57`, verified), states print without row titles and say so ·
`_log_usage` fires **per invocation** by declared contract (`capabilities.json:934`).

## D2 — the one real check on the old list *(and the reason it stops nagging you)*

**What:** every guard that blocks by default must prove both that it blocks the bad thing **and**
that it stays quiet on ordinary work.

Four recorded findings are guards firing outside their jurisdiction — including the one that reached
you as *"why am I seeing all these hook errors."* All four blocking guards happen to pass both
directions today (`test_hooks.py:110-116`, `:622-636`, `:381-402`, `:1191-1204`). **Nothing requires
it of the next one.** The `"CALIBRATED IN BOTH DIRECTIONS"` marker on 4 of ~13 hooks is a docstring
self-claim — §13's *"the one nobody re-checks."*

**Reuse the enumerator; do not build a second.** `test_hooks.py:1503` already derives the family
from the REAL registry (`host_parity.canonical_inventory`), maps short→file (`:1430-1442`), computes
the blocking set (`:1528`), and carries the vacuity assertion (`:1538`). `_DEFAULT_MODES` alone is
the weaker registry — a mode key not registered in `hooks.json` never runs. Factor `:1519-1528` into
a helper both tests call.

**The corpora already exist** — `tag_guard` at `:381-402`, `lock_guard` FP1–FP4 at `:1191-1204`
*with* negative controls at `:1213-1218`, `exitcode_guard` at `:233-246`. A second corpus that can
drift from the first, in the repo that ships `fixture_guard` because corpora drift, is the defect
this plan exists to fix.

**No module-global tally.** A tally accumulated as earlier tests run is order-dependent —
`main()`'s dispatch tuple (`:1593`) puts the parity test last, so calling it alone would pass
vacuously. Instead: calibration rows are **declarative at module load**, and the parity calculation
is a **pure function** `parity_problems(blocking_roster, case_table)`. The family test calls it with
the derived roster; the planted test calls it with a fabricated blocking member and asserts it REDs.
The plant is trivial only because the function is pure.

**Scope is "blocking BY DEFAULT", stated precisely** — `_common.py:363-365` advertises
`TDD_PLAYBOOK_HOOK_<NAME>=block`, so an opt-in hook can be escalated on a documented switch. Those
get a dated debt entry, not silent exclusion. Denominator printed (H15).

**One genuinely new thing:** a short SHARED out-of-jurisdiction corpus — reading a file, running a
test, writing to `~/.claude` memory/plan-mode/scratchpad, recording a `guard_note` — run against
**every** blocking guard. Today each guard has its own allow rows and no row runs against all of
them, so cross-guard overreach has no test. `lock_guard:338-343` already implements this rule for
itself; the corpus generalizes it to the family.

## D3 — put the report where it is actually read

`recurrence`'s only code consumer is `run_calibration.py:1279-1291`, and `CLAUDE.md:5-7` says
*"There is no weekly clock any more."* Fix the gauge and it stays invisible.
`render_reference.py:86-90` already recorded this verdict about this exact verb:

> *"That verb's reader is run_calibration, which is opt-in… so the report would have been dark in
> exactly the case it exists to show. This file is regenerated at every release, so the inventory is
> READ."*

D3 renders the inventory beside `participation_report` (`:92-95`) into
`docs/reference/current-state.md`, and extends `PROVENANCE_INPUTS` (`:21-28`) — which today lists
neither `docs/HACK_CATALOG.md` nor the guard-mode authority (`hooks/scripts/_common.py`).

## D4 — re-point the consumers of the old two-state vocabulary

| consumer | site | why |
|---|---|---|
| H10 map-row pin **and its planted control** | `test_agents.py:928`, `:934` | pins `"\| H10 \| —"` literally; D5's row edit **REDs the gate** without re-authoring both |
| self-parsed telemetry | `review_ledger.py:708` | counts `startswith("UNBUILT GUARD")`; add `guarded`/`dark`/`historical` counters rather than silently redefining it |
| three format assertions | `test_review_ledger.py:272-275`, `:305-307`, `:348-349` | all go RED. Re-baselining assertions is the shape `weakening_guard` fires on — deliberate, one commit, reasons stated |
| registry emit contract | `capabilities.json:919`, `:922` | both name "UNBUILT GUARD lines" and a human workflow that no longer exists |
| doctrine prose | `CLAUDE.md:278` | states the retired equivalence |
| `AGENTS.md:309` | generated | **re-render via `render_agents.py`; a hand edit is a gate failure** |

## D5 — tests, and the catalog row D2 closes

`docs/HACK_CATALOG.md` H13 gains D2 as its mechanical guard; the `test_agents.py` needles above are
re-authored in the same commit.

**`test_review_ledger.py`** — planted, red-first:
- a post-epoch finding with no `guard` answer → REFUSED; a pre-epoch one → untouched (the epoch is
  the difference, and both directions are pinned);
- an unresolvable `ref` → loud refusal, never `GUARDED`;
- a hook whose shipped default is `off` → `GUARD DARK`, never `GUARDED`;
- **negative control:** two post-epoch findings both answering `kind: none` must **still** print
  `UNBUILT` — a reset that merely silenced the report is the same defect with the sign flipped;
- the historical summary line is present and names a non-zero count (silence ≠ "no history");
- **purity:** rendering with `TDD_PLAYBOOK_HOOK_OVERMOCK=block` set, and with break-glass active,
  produces byte-identical output;
- a new downstream fixture — `docs/reviews` present, `HACK_CATALOG.md` absent — prints states
  without row titles. The existing stranded-install test (`:558-573`) asserts a *refusal* and stays
  a separate contract; my earlier draft mis-cited it as covering this.

**`test_hooks.py`** — the family test plus the fabricated-member plant against pure
`parity_problems`.

House idiom: hand-rolled `check()` + `_results` + `main()` + `sys.exit(1 if fail)`. **No pytest.**
D2's new function must be referenced from `test_hooks.main()` —
`test_aaa_suites_via_main.py:102-116` REDs on any `def test_*` its module never invokes.

## D6 — the six agent briefs: generate them, then verify once

The record-authoring rule lives in **six** canonical briefs (`adoption-adversary.md:82`,
`architecture-adversary.md:100`, `claims-verifier.md:45`, `integration-adversary.md:102`,
`script-adversary.md:99`, `tripwire-auditor.md:90`) — and D1(b) changes what a record must contain,
so all six are now wrong. My "every consumer" sweep had named only one, which is exactly the §12
failure this plan is about.

**(a) One source, six generated — no spend.** Six hand-maintained copies of one sentence is
`constant-second-home` / `unpinned-prose-constant` (2 records each).
- Source of truth in `review_ledger.py`, beside `FINDING_CLASSES` (`:30`) — the prose is derived
  from the constants that define the vocabulary, so a brief can never describe a state that no
  longer exists.
- Rendered between sentinel markers; the rest of each brief stays hand-written.
- **A §6c family parity sweep pins it** — roster enumerated from the real directory, vacuity-guarded,
  each brief asserted to carry the current block. A seventh brief is covered the day it lands.
- **Placement caution:** every `*.md` in `agents/` is a discoverable agent id, so the shared source
  must not live there.

**(b) Verify it behaviorally, once — ~12 headless runs.** `agents/` is a ledger SURFACE and
**EFFECTFUL**, so:
1. Ledger entry appended **before** the edits, `baseline_sha` = pre-change HEAD. `expect: none` is
   unavailable by construction.
2. Author one plant + control → `corpus/proposed/`.
3. **David reviews and approves** (`--approve`) — proposed plants are human-reviewed, never
   self-approved.
4. **Pre-edit RED baseline** — the plant must bite on the current block. Without this leg a
   post-edit green proves nothing. *(My previous draft ran calibration before the edit and never
   re-ran it — it verified nothing.)*
5. Render the block (D6a).
6. **Post-edit GREEN run.**
7. `python3 calibration/ledger.py score`, then append its emitted block. `run_calibration.py`
   invokes `report`, **not** `score` (`ledger.py:817`); scoring APPENDS, never edits a prediction.

**A plant surviving to a clean verdict is a BLOCKING failure — fix the agent, never the plant.**

**Stated honestly:** this buys one behavioral proof, not six. The claim is *"the shared block is
correct and cannot drift"* — the other five are covered deterministically by (a). Six independent
proofs would cost ~72 runs; that was priced and declined.

---

## Integration surface

- **Consumes:** `_common._DEFAULT_MODES`; `host_parity.canonical_inventory` / `agents_roster`;
  `closure_evidence_exists`; `author_plants.py` + `calibration/ledger.py` (D6b).
- **Emits → named consumer:** the six rows in D4, plus D3's render into `current-state.md`.
- **Surface parity:** code travels to both hosts; `docs/` travels to neither, so row titles are
  source-repo-only. Divergence stated, downstream contract specified in D1's edge cases.
- **Reverse sweep:** `capability_registry.validate` never resolves `wired_by`/`exercised_by`
  (`:114-116`) — the same unresolved-string weakness D1(b) fixes for findings. Dated
  `integration_debt`, not a silent deferral.
- **Activation:** all ON by default; nothing behind a switch.

## Unenforceable deliverables (prose)

None.

---

## Tripwire deliverable list

| # | deliverable | BUILT | WIRED | ACTIVATED | EXERCISED |
|---|---|---|---|---|---|
| D1a | epoch line + historical summary | `review_ledger.py` | `recurrence` | default | epoch-boundary pair + non-zero-count line |
| D1b | `guard` answer required post-epoch | `review_ledger.py` | `validate` | default | refusal + unresolvable-ref + dark-hook tests |
| D2 | pure `parity_problems` over derived roster | `test_hooks.py` | `test_hooks.main()` | every gate run | fabricated-member plant |
| D3 | inventory rendered where it is read | `render_reference.py:92-95` + `PROVENANCE_INPUTS` | release step 2 | every release | `test_reference_docs.py` + purity test |
| D4 | six consumers re-pointed | see table | — | default | format assertions + `test_own_registry` |
| D5 | H13 row + `test_agents.py` pins | `HACK_CATALOG.md`, `:928`, `:934` | `catalog_rows` | — | needle + planted-stripped pair |
| D6a | shared block generated from constants | `review_ledger.py` + renderer | sentinels in six briefs | on dispatch | §6c parity sweep, vacuity-guarded |
| D6b | one behavioral pair, pre-RED / post-GREEN | `corpus/approved/`, `ledger.md` | ledger entry | the run | the block appended by `ledger.py score` |

## Verification

```sh
python3 plugins/tdd-playbook/tests/test_review_ledger.py
python3 plugins/tdd-playbook/tests/test_hooks.py
python3 plugins/tdd-playbook/tests/test_agents.py
python3 plugins/tdd-playbook/bin/review_ledger.py recurrence     # expect: historical summary only
python3 plugins/tdd-playbook/bin/review_ledger.py validate
python3 plugins/tdd-playbook/bin/render_agents.py                # AGENTS.md re-rendered
python3 plugins/tdd-playbook/bin/render_reference.py render
python3 plugins/tdd-playbook/bin/capability_registry.py validate
python3 calibration/ledger.py check                              # DEFAULT scope — epoch-first
sh scripts/civerd_gate.sh > /tmp/gate.out 2>&1; rc=$?            # never piped (§4a)
```

**Ledger entry:** required, because D6 touches `agents/`. Appended **before** the edits;
`baseline_sha` = pre-change HEAD; real prediction against the new plant.

**Release:** four identity files + CHANGELOG + `current-state.md`; push; CI green on the exact sha;
then the tag command handed to David — and that message ends the span.

## Out of scope, named not queued

Retroactively classifying the pre-epoch keys (**the decision this plan is built on** — it needs
judgment neither of us can supply honestly) · resolving `wired_by`/`exercised_by` in the registry ·
a general "outermost caller never exercised" checker · the verb-less invocation sweep · any
SKILL.md doctrine line.

---

## Loop closed: yes — three review rounds, every load-bearing claim measured before acceptance

- **integration-adversary — ISLANDS (6).** Top island: the report ships dark; the repo had already
  recorded that verdict about this verb. → **D3.** Also folded: the `test_agents.py:928` pin,
  `docs/` in neither COPY_TREES, format consumers, registry emit fields, blocking-by-default.
- **architecture-adversary — BAND-AID (2).** Top band-aid: path-existence was gate-by-proxy — 14 of
  15 catalog cells hold no path, and `isfile` would report dark guards as BUILT. → mechanism
  answers, keyed on shipped defaults. Also: D2 collapsed to an assertion reusing the existing
  enumerator and corpora.
- **Codex ×2 — 9 findings, all verified, all folded.** Per-finding classification was impossible
  from a key→key map; row-level state cannot classify H13's mixed cell; `resolve_mode` makes
  generated output environment-dependent; a dict literal swallows the duplicate its own test should
  catch; `registry_rule` named an "active set" that **does not exist**; D6 never verified its own
  edits; one plant targets one agent.
- **Rejected: none.** Five claims were confirmed by direct measurement rather than taken on report.
  **Four of my own statements were retracted**, and the epoch reset — David's call — removed the
  curation burden that three of the surviving designs had quietly assumed.
