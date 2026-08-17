# TDD Plan — adversary accountability (Phase 1)

**Slug:** `2026-08-17-adversary-accountability`
**Status:** revision 4 — two in-repo adversaries returned (`Loop closed: yes`); three rounds of
external review (Codex ×2, Cheli/GLM-5.2 ×2) folded in, every load-bearing claim independently
verified against the tree.
**Scope:** Phase 1, with D7 promoted in. Phase 2 (§5b doctrine) specified but NOT built.

---

## Context

Two questions started this: is Cheli's §5b agent-eval draft worth adopting, and do the
Playbook's own adversary agents produce output that anything actually reads?

The second turned up a measured shortfall. Across the 39 records in `docs/reviews/`, the
`reviewers` field names `integration-adversary` 17×, `architecture-adversary` 15×,
`tripwire-auditor` 11×, `self-review` 11×, `security-adversary` 5×, `test-quality` 2×, and
`script` / `claims-verifier` / `adoption` once each. `observability-adversary` and
`edge-case-adversary` appear **zero** times.

The field is free text bound to nothing — `review_ledger.py:89` checks only that it is a
non-empty string list, and `:158` checks `closure_review` against the record's **own** reviewer
list, which is self-referential. The counts above are only as good as the spelling; a renamed
or misspelled agent passes silently.

Separately, `test_agents.py:148` asserts the string `"Loop closed:"` appears in the command
**file** — an artifact this repo wrote. It proves the instruction exists; it cannot detect a
loop that stopped closing.

**Intended outcome:** make the ledger's reviewer field mean something mechanically, and make
roster participation visible in a surface that is always read — with **no new recurring process
obligation**. This repo retired its weekly calibration clock in v1.32.0 precisely because "the
schedule produced obligations faster than it produced findings."

### Corrections this revision makes to the previous one

- **The grandfather cutoff does not survive later renames — I overclaimed.** A post-cutoff
  record naming `architecture-adversary` breaks if that file is renamed in 2027. Fixed below
  with a stated ID contract, not an alias table.
- **The "dated debt" section had an owner and nothing else** — no ID, expiry, done condition, or
  `validate --as-of` proof. That is prose parking, and it violates this repo's own deferral rule.
  Now registered properly; one item promoted out of debt entirely.
- **Verification covered Claude only**, asserting Codex in a comment, on a plan whose blocking
  prerequisite is *cross-layout* behaviour. Now installer-driven for both hosts.
- **`render_reference.py` with no argument runs `check`, not `render`** (`:178`) — my verification
  command was wrong.
- **Wording:** "no new roster, list, or exemption set" was false (D3 adds a vocabulary constant);
  `calibration/` is an eval **harness/script**, not an agent.

### Verified corrections to the external reviews

- Cheli: *"0 of 39 records have a `recurrence_key`"* — **false; 24 of 39 do.** Cheli confirmed
  the correction in the following round.
- Cheli: *"all 39 records pass D3 is an assertion"* — **was fair, now verified twice.** The 16
  distinct reviewer values are exactly 8 agent names + 8 non-agent tokens.
- Cheli: registry entries "may trigger the doctor's warning" — **stronger than stated.**
  `wired_by` / `exercised_by` are in `REQUIRED_FIELDS` (`capability_registry.py:50`), so an
  incomplete entry fails `validate`, not merely `doctor`.

---

## Phase 1 deliverables

### D0 — portable agent roster (blocking prerequisite for D3)

**What:** a roster accessor resolving the agents family in all three real layouts, returning
`None` — never raising — when the family is genuinely absent.

| Layout | Agents path | Result |
|---|---|---|
| In-repo | `<root>/plugins/tdd-playbook/agents/` | roster |
| Claude vendored | `<root>/.claude/agents/` | roster |
| Codex vendored | *(none — `CODEX_COPY_TREES` copies only `adapters`, `bin`)* | `None` |

**Files:** `plugins/tdd-playbook/bin/host_parity.py` (owner — add `agents_roster(root)`).

**Reuse:** `host_parity._markdown_names` already lists agent basenames.
`review_ledger.catalog_rows()` (`:342-350`) is the exact house precedent — returns `None` when
the artifact is not vendored, caller degrades, docstring says so out loud ("stated here rather
than silently"). `agents_roster` mirrors its shape and its docstring discipline.

**Leave `canonical_inventory` alone.** Its strict vacuity guard (`:68-69`) is correct for parity
duty. A sibling accessor is the earliest seam that does not weaken an existing invariant.

**Precedence, stated precisely:** in-repo before `.claude/`. The docstring must say this returns
**canonical reviewer IDs**, not a description of the running installed copy — a dev tree
carrying both resolves to source, and that is deliberate.

**Edge cases**
- *Empty dir vs missing dir* — a directory that exists but is empty returns `None`; never a
  vacuously-passing roster of zero names.
- *Import safety* — `host_parity`'s module-level `REPO`/`POLICY`/`OUTPUT` are path joins that do
  not touch disk; nonsense downstream but must not raise on import.

---

### D3 — bind `reviewers` to the roster

**What:** `validate_record` requires each `reviewers` entry to be a canonical agent ID or a
member of an explicit non-agent vocabulary. Correct records pass unchanged; typos, renames and
invented names RED with the accepted values named in the message.

**Files:** `plugins/tdd-playbook/bin/review_ledger.py`, `plugins/tdd-playbook/tests/test_review_ledger.py`.

**The non-agent vocabulary** (verified exhaustive against all 39 records — 8 tokens, zero
uncovered, zero unused):
`self-review` · `release-gate` · `operator-field-report` · `live-dogfooding` ·
`cheliped-field-report` · `calibration-live-replay` · `d2d-live-probe` · `codex-field-report`

Declared beside `FINDING_CLASSES` (`:30`) under the same stated rule that governs it: one owner,
imported by briefs and tests, never copied.

**Two-part compatibility contract** (the previous revision had only the first half, and claimed
it did the work of both):

1. **Cutoff — grandfathers the rollout.** `REVIEWER_VOCAB_SHIP_DATE = "2026-08-17"`, reusing the
   `TAXONOMY_SHIP_DATE` (`:31`) + `taxonomy_required` (`:79`) pattern already in this file.
   Records dated earlier are untouched. **Eight records carry today's date and all already
   comply** (verified), so binding them costs nothing.
2. **Agent filenames are canonical IDs and are not renamed.** This is not a new constraint —
   renaming an agent *already* REDs the suite in two places: `test_agents.py:111`
   (`set(AGENT_CONTRACTS) == set(found)`) and `:588` (the completeness guard). The plan's job is
   to **name** that existing contract, and to state the escape hatch: if a rename ever becomes
   necessary, the old ID joins the non-agent vocabulary constant as a historical alias. One
   line, in a constant this deliverable already introduces. No alias table, no versioned IDs.

**Downstream degradation is a declared branch with its own test** — not a `try/except` at the
call site, which would go green here and dark everywhere it ships. When `agents_roster()`
returns `None`, accept any non-empty string and say so in the docstring (`catalog_rows`'s
contract). See **Known gaps** — this is the weakest point in the design and belongs there, not
buried in an edge-case list.

**Edge cases**
- *All 39 records pass unchanged* — verified in advance; re-assert mechanically as a test, never
  as a claim.
- *Roster absent* → shape-only, tested.
- *Pre-cutoff record with an unknown reviewer* → passes, tested.
- *Post-cutoff record with an unknown reviewer* → REDs, message enumerates the vocabulary.
- *Idempotency* — `validate` already runs repeatedly in the gate; the accessor stays pure.

**Property test:** invariant — *a post-cutoff record whose reviewers ⊆ (roster ∪ vocabulary)
never yields a reviewer problem; any post-cutoff record with a reviewer outside always does.*

**Vendoring test:** `test_review_ledger.py:375-384` `_vendor_bin` copies exactly
`review_ledger.py`, `dataflow_sweeps.py`, `_debt.py`, docstringed *"a test tree with the script
alone would be a layout the installer cannot produce."* Add `host_parity.py`.

---

### D3b — the six authoring briefs carry the vocabulary

**What:** the six briefs that author review records state the accepted reviewer vocabulary, so
the gate's producers know its contract.

**Files:** `plugins/tdd-playbook/agents/{claims-verifier,architecture-adversary,adoption-adversary,integration-adversary,script-adversary,tripwire-auditor}.md`,
`plugins/tdd-playbook/tests/test_agents.py`.

**Reuse the existing sweep.** `test_agents.py:1022-1055` already imports
`review_ledger.FINDING_CLASSES` into a vacuity-guarded family sweep over exactly these six
briefs, expressly *"so a vocabulary rename REDs here instead of leaving six briefs silently
stale."* The new constant joins the same sweep — one needle per brief.

**Derivation, not a hand list:** membership is `grep -l recurrence_key agents/*.md` → exactly 6.

---

### D4 — recorded review participation (report-only)

**What:** `review_ledger.py recurrence` gains a block printing, for every agent in the roster,
how many indexed records name it — with the six record-authoring briefs marked, and one sentence
stating what the number does and does not mean.

**Files:** `plugins/tdd-playbook/bin/review_ledger.py`,
`plugins/tdd-playbook/bin/render_reference.py`, and their tests.

**No partition, no exemption list.** Earlier drafts split the roster into "judgment" vs
"mechanical." Three reviewers flagged that as an Nth-copy classification and an unpinned darkness
hatch — and `run_calibration.py:55-59` already states the governing rule: *"the roster stays
DERIVED, never a second hand-maintained list."* Printing the **whole roster** deletes the problem
rather than relocating it: nothing is flagged, so nothing can be false-flagged. A reader sees
`observability-adversary 0` and judges. Same category as `capability_registry doctor`'s
dark-feature inventory.

**Naming discipline:** the header reads *recorded review participation*. Zero reads *"not named
in any indexed review."* Never "usage," never "dispatch." `reviewers` is hand-typed — it can
prove a name was recorded, never that an agent ran.

**Two consumers, one always-on.** `run_calibration.py:1282` already shells `recurrence` and
prints stdout wholesale. **That is not sufficient** — it is opt-in, triggered by "a verifier
misbehaves," and an agent with zero participation cannot misbehave, so the report would be dark
exactly when it matters. Route the block into `render_reference.review_section()` (`:65-84`),
which loads every record and is regenerated at **every release**.

**Report-only is deliberate.** A participation *gate* would force adversary dispatch on changes
that do not warrant it, and would reward name-stuffing a hand-typed field.

**Edge cases:** zero records → "unmeasured", never a vacuous 100% · mandatory vacuity guard on
the enumerator (§6c) · roster `None` → block omitted **with a stated reason**, not silently empty.

**Property test:** invariant — *participation counts sum to the number of `(record, reviewer)`
pairs whose reviewer is in the roster.*

---

### D7 — cadence reconciliation *(promoted from Phase 2)*

**What:** the README and registry still describe the calibration cadence that v1.32.0 retired.

| Surface | Current text | Problem |
|---|---|---|
| `README.md:215` | "calibrated behaviorally on a schedule" | contradicts the reversal |
| `README.md:220` | "weekly live calibration" | contradicts the reversal |
| `README.md:230` | "the 14-day cadence mechanical … fails loudly" | describes a retired gate |
| `capabilities.json:282` | "(weekly, David-run or scheduled…)" | registry disagrees with doctrine |
| `capabilities.json:309` | 14-day liveness declaration | same |

The README contradicts itself within a few lines — one passage says weekly, another says
retired. This is wrong **today**, independently of §5b, and it is the file newcomers read.
Promoting it also makes Phase 2's opt-in claim honest before it is written.

**Not in scope:** the WS5 "built but NOT started" line in `CLAUDE.md` — that becomes false only
when D1 lands, so it belongs to Phase 2.

---

### D8 — `mutation-runner` classification docstring *(promoted out of debt)*

**What:** `test_agents.py:567-579` classifies `mutation-runner` among the pinned **judgment**
verifiers while the same function's docstring says *"Mechanical test-runners stay inherit — they
run suites, not judgment."* Two statements in one function disagreeing.

**The classification is right, the docstring is imprecise** — `mutation-runner` triages survivors
real-vs-equivalent, which is judgment, and its frontmatter pins `model: opus` accordingly. Correct
the docstring to name the criterion actually in use. One line; too cheap to defer.

---

## Known gaps (stated, not discovered later)

- **D3's binding is weakest in the layout most likely to drift.** Codex-vendored copies have no
  agents family, so the reviewer check degrades to shape-only there. That is the right trade —
  you cannot bind to a roster that does not exist — but the consequence is that a Codex-side
  repo gets no protection from this deliverable, and §6b's own rule says a feature that cannot
  be measured in a layout must say so.
- **EXERCISED means the test exists at this sha, unskipped, gate green.** It is not "the
  behaviour was observed running." Source edits do not update installed plugin caches or
  vendored copies; a RUNNING claim would need a post-install probe this plan does not build.
- **D0's three-layout behaviour is adversary-verified, not yet test-verified.** Both adversaries
  scratch-installed and reproduced the crash; the installer-driven tests below are what convert
  that into a repo fact before merge.

---

## Flow table (§6c)

| flow | producer | consumer | liveness test |
|---|---|---|---|
| agent roster (or `None`) | `host_parity.agents_roster` | `review_ledger.validate_record` | installer-driven, both hosts |
| reviewer verdict | `validate_record` | `main` exit → `gate_runner` → `civerd_gate.sh` | unknown-reviewer planted pair |
| reviewer vocabulary | `review_ledger` constant | six briefs + `test_agents.py:1022` sweep | needle per brief |
| participation block | `recurrence` | `render_reference.review_section` (always-on) **and** `run_calibration.py:1282` | vacuity + count tests |
| cadence text | D7 | README readers; registry `validate` | `capability_registry.py validate` |

No empty consumer cells.

## Tripwire

| # | BUILT | WIRED | ACTIVATED | EXERCISED |
|---|---|---|---|---|
| D0 | `agents_roster` | imported by `review_ledger` | on by default | installer-driven ×2 hosts + empty-dir |
| D3 | roster binding | inside `validate`, already in the gate | on by default | 39-record pass · planted typo · grandfather pair · rename-alias case |
| D3b | six briefs | existing family sweep | on by default | needle per brief |
| D4 | participation block | `render_reference` + `run_calibration` | on at every release | vacuity · count · `None` |
| D7 | corrected text | registry `validate` | always on | `capability_registry validate` |
| D8 | corrected docstring | — | always on | existing `test_verifier_model_pins` |

---

## Verification (end-to-end)

```sh
# 1. Blessed gate — never piped; a piped $? is tail's (§4a)
sh scripts/civerd_gate.sh > /tmp/gate.out 2>&1; echo "rc=$?"    # must be 0

# 2. D3 must not break history — the assertion this plan refuses to make on faith
python3 plugins/tdd-playbook/bin/review_ledger.py validate       # exit 0 on all 39

# 3. D4 reaches the always-on surface (bare invocation is `check`, not `render`)
python3 plugins/tdd-playbook/bin/review_ledger.py recurrence
python3 plugins/tdd-playbook/bin/render_reference.py render
python3 plugins/tdd-playbook/bin/render_reference.py check

# 4. Cross-layout — through the PRODUCTION installer, both hosts, fresh trees
CL=$(mktemp -d); CX=$(mktemp -d)
python3 scripts/install_into_repo.py "$CL"
python3 scripts/install_into_repo.py --host codex "$CX"
#   Claude  -> roster resolves from .claude/agents/
#   Codex   -> roster is None; validate degrades to shape-only; NO crash
#   plus: an installed tree with an EMPTY agents dir refuses a vacuous roster

# 5. Registry stays honest (§6a dogfood) + debt expiry proof
python3 plugins/tdd-playbook/bin/capability_registry.py validate
python3 plugins/tdd-playbook/bin/capability_registry.py doctor
python3 plugins/tdd-playbook/bin/capability_registry.py validate --as-of 2026-11-01   # debt 1 EXPIRED
python3 plugins/tdd-playbook/bin/capability_registry.py validate --as-of 2026-11-16   # debt 2 EXPIRED
```

The installer-driven cases in step 4 become real tests, not manual steps. Directory-shape unit
tests may remain, but they do **not** substitute for going through the production installer —
that is the seam this deliverable exists to protect.

**Registry note:** every `capabilities.json` entry must carry `id, summary, surfaces, activation,
wired_by, exercised_by` (`capability_registry.py:50`) or `validate` fails — schema, not paperwork.

**Release hygiene:** closing implementation review record in `docs/reviews/` with `class` +
`recurrence_key` per finding, `review_range.head` at the bump commit, plus `index.json` and
regenerated `current-state.md`. Proposed key: `ledger-field-unbound-to-its-roster`
(`class: deterministic`). **`AGENTS.md` is generated** — edit `CLAUDE.md`, then
`render_agents.py render`; a hand edit to `AGENTS.md` is a gate failure (`render_agents.py:19-20`).

---

## Registered debt (real entries, not prose)

Both land in `capabilities.json` as `integration_debt` with an expiry test proving they RED.

| ID | Owner | Expiry | Done condition |
|---|---|---|---|
| `loop-closed-contracts-unparsed` | David | 2026-10-31 | The five `Loop closed:` contracts (`commands/{probe,mutate,integration-audit,edge,tdd-plan}.md`) emit a forced closed-vocabulary line parsed by a test, on the model of `calibration/holdout.py:630-637`. §5b territory — expiry set after Phase 2's window. |
| `codex-skill-surface-absent` | David | 2026-11-15 | `skills/` is a host-parity family (`host_parity.py:20`) or the Codex host's skill unavailability is a recorded parity disposition rather than a silent omission. |

Proof obligation: `validate --as-of <expiry+1>` must report each as `EXPIRED`, demonstrated in
step 5 above. A deferral that cannot be shown to expire is prose parking.

---

## Deliberately not built

- ❌ No `/eval` command, no `eval-calibrator` agent — `calibration/` is already an eval
  **harness/script** covering this repo's own agents. (It is not an agent, and it is not
  vendored downstream; Phase 2's §5b must state that it is a reference implementation, not a
  shipped tool.)
- ❌ No scheduled cadence of any kind.
- ❌ No change-type → required-adversary mapping.
- ❌ No new required review-record field.
- ❌ **No duplicate agent roster and no exemption set.** (D3 *does* add one new constant — the
  non-agent reviewer vocabulary. Naming it here because the previous revision claimed "no new
  list," which was false.)
- ❌ No participation gate.

## Phase 2 — specified, NOT built (separate approval)

- **D1** §5b agent-eval doctrine, generalised from `calibration/`: corrected oracle split
  (blocking = agent-path-**independent** invariants; path-dependent outcomes reuse
  `run_calibration`'s k/k + AMBER + BLOCKING-on-repeat); forced closed-vocabulary output as the
  precondition for parsing (`calibration/oracle-changes.md:35`); replay-not-live for any
  per-commit lane; R11 refinements (`world-class-recommendation-analysis-2026-07.md:233`);
  opt-in cadence; the §1 seam rule applied to agents; §5b stated as BYO-harness downstream.
  Deletes `## Open upgrade` → requires a `calibration/gate-changes.md` entry (rule (d)).
  Also retires the WS5 "built but NOT started" line in `CLAUDE.md`.
- **D2** `[→EVAL]` resolves; `eval` + `eval_judge` markers; description trimmed by dedupe
  (currently 1018/1024, six characters spare).

## Gated — D5 (subagent count)

**Blocked on evidence, by design.** `grade_from_otel.main` reports telemetry-unavailable only
when total records are zero (`:153`), so an export containing ordinary tool events but no
dispatch events prints a confident `subagents: 0`. Required before any code: one real export
with a known dispatch **and** a paired no-dispatch control, proving the event and attribute
names. Then distinguish `0 observed` from `schema incapable`, define nested-dispatch semantics,
and add a planted export where tools exist but dispatch observability does not — which must
return `unmeasured`. If the schema cannot carry it, D5 is dropped and registered as debt. A
fixture invented around `tool_name="Task"` proves only that a fixture can be invented.
