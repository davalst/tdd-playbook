# Implementation plan: The Readable Surface + adversary routing (§6d) — 2026-08

**Status:** DRAFT — for David's review. Nothing built. Target version: **v1.33.0** (stage 1
only; see §G staging).
**Upstream spec:** the "when code no longer matters" thread, 2026-08-12 — the working
session that established the problem, the design corrections, and the 42-row inventory.
**Companion artifact:** `docs/reference/adversary-scenario-inventory.md` (S01–S42 +
governance G1–G5), written alongside this plan and referenced throughout.
**Discipline:** written in the Playbook's own §0 shape, and dogfoods §6a (registry), §6b
(onboarding contract), §6c (flow table), §12 (denominators), §13 (plant-before-trust).

---

## A. Repo-local conventions discovered and applied

Discovered from `CLAUDE.md`, `SKILL.md` (§§0, 4a, 6a–6c, 12, 13), `capabilities.json`
(26 entries), and the existing bin/hook/test layout. Layered on top of the universal floor:

- **One blessed gate entrypoint.** All suites run only via `sh scripts/civerd_gate.sh`
  (never piped — §4a, a discarded exit code is a discarded truth). Every test below joins
  that gate; no side loop.
- **Planted-input rule.** Every mechanical change ships a planted violation that must go
  RED, with a **paired clean control** (v1.17 pair quota). Unpaired plants are rejected.
- **Stdlib-only** for everything under `plugins/tdd-playbook/bin/`. No new dependency.
- **Gate surfaces** (SKILL `##` sections, `agents/*.md`, `commands/*.md`): additions free;
  removals/renames require a `calibration/gate-changes.md` entry (v1.22 rule d). This plan
  is additions-only.
- **Registry dogfood.** New capabilities register in the same commit that builds them;
  `capability_registry.py validate` runs with the real date on every suite run
  (`test_capability_registry.py::test_own_registry`), so an expired debt REDs the tests.
- **One debt shape.** `{what, target, owner, expires}` via the shared `_debt` module — the
  registry's R-DEBT contract. No fifth debt shape.
- **Four identity files + CHANGELOG** on any version bump; `test_installer.py::test_release_version_identity` pins all four equal.
- **§4a house invariants for any new checker:** vacuity guards on scope *and* execution;
  exit codes captured; "0 violations" must never be reachable by scanning nothing; pinned
  machine-readable summary line.
- **Release authority:** David tags. No script creates a tag
  (`test_no_script_creates_a_release_tag` + `tag_guard.py`). Nothing here changes that.
- **Vendoring:** anything downstream repos need ships via `scripts/install_into_repo.py`
  and must appear in both `adapters/claude/adapter.json` and `adapters/codex/adapter.json`.

**Conflicts with the new work: none found.** One tension, stated rather than resolved
silently: CLAUDE.md's v1.32.0 reversal retired schedule-driven obligations because "the
schedule produced obligations faster than it produced findings." The routing table is
change-driven, not schedule-driven, which is on the right side of that reversal — but §D6
below introduces one time-based element (the demotion timer), and it is deliberately shaped
to produce a **question**, never a run. See B/reading-2.

---

## B. Spec integrity

### Assumptions (stated, not silent)

1. **The reader cannot fall back to source.** This is the load-bearing assumption and it
   inverts the normal requirement: the surface must be *pointable*, not *complete*. A
   generated view that omits something is recoverable (David dispatches an agent at the
   coordinates); a generated view that is *wrong* is not, because he cannot check it. This
   is why D7 (plants) is a gate on arming, not a nice-to-have.
2. **Facts are cheap, prose is expensive, and they must not be mixed.** Derived facts are
   deterministic and diffable. LLM prose is neither — regenerating a description of
   unchanged code yields a large meaningless diff. The split in D2/D6 follows from this.
3. **The 42 inventory rows are a starting catalogue, not validated controls.** Each is held
   to G1 (no plant, no arming). They exist so coverage does not start at zero; they are not
   claimed to be the right 42.
4. **Cheliped is the pilot consumer.** The Playbook ships the mechanism; Cheliped (63
   registered capabilities) is where the surface is first read in anger. Nothing here
   depends on Cheliped-side work landing.

### Readings — the request supports more than one; this plan follows reading 1

- **Reading 1 (followed): a comprehension instrument that feeds a routing decision.** The
  Playbook's outputs today are all *verdicts* — pass/fail, N/N, green/red. This adds the
  first artifact whose output is *description*, plus a deterministic table that decides when
  description is worth escalating to a paid adversary. It answers "what is it?", which
  nothing in the Playbook currently answers.
- **Reading 2 (rejected): a new gate.** Making the readable surface block merges on prose
  quality would convert it into something to satisfy rather than something to read, and the
  Playbook's own history says that is how instruments die. **The prose never gates.** Only
  two mechanical things gate: the snapshot being stale (D2), and an expired demotion (D6).
- **Reading 3 (rejected): 63 subsystem pages.** A page per registered capability is
  organised the way the *code* is organised, which is precisely the organisation David
  cannot navigate. The pages are organised by *worry*, cutting across subsystems.

### A materially simpler approach — and the recommendation

**Simpler alternative:** ship D1 (the inventory) and a derive-on-demand `/readable` command
that commits nothing. No snapshot, no diff, no routing table, no yield instrument. Perhaps
a fifth of the work.

**This plan's recommendation as CTO: take the simpler alternative first, deliberately, as
stage 1.** The entire value of the snapshot/diff/routing machinery is conditional on David
reading the surface repeatedly. That is an untested behavioural assumption about a single
user, and it is cheap to test and expensive to assume. Stage 1 is therefore a **decision
gate, not a partial build** — if the surface goes unread for three weeks, stages 2–3 are
cancelled and the money is unspent. See §G.

This is also the honest reading of David's own constraint in the source thread ("I don't
mean take a massive leap that all of a sudden makes it harder").

### Open questions for review — plan proceeds on the stated defaults if unanswered

1. **Does the routing table ever auto-dispatch paid adversaries?**
   **Default: NO in v1.** It prints a recommendation with reasons; a human or the
   orchestrator dispatches. Auto-dispatching paid agents from a hook is an unbounded spend
   path with no cap — which is row **S23** on our own inventory. Dogfooding beats
   convenience here.
2. **Where does the readable surface live for a downstream repo?**
   **Default:** `docs/reference/readable-surface.md` + `.json`, same pair as
   `docs/reference/current-state.md`. Installer-created, gitignored never.
3. **Demotion timer default.** **Default: 120 days**, surfacing as a question. (G3.)
4. **Does stage 1 ship the SKILL §6d doctrine, or does doctrine wait for stage 2?**
   **Default: doctrine ships with stage 2**, because a `##` section is a gate surface that
   downstream repos vendor, and doctrine describing a mechanism that may be cancelled at
   the stage-1 decision gate is exactly the "prose without a mechanism" failure §6c was
   created to stop.

---

## C. Deliverables

### D1 — The scenario inventory (`docs/reference/adversary-scenario-inventory.md`)

**What.** A standing, hand-maintained catalogue of 42 things that go wrong, each phrased as
a plain-language question, with a stable ID that the routing table, review-ledger records
and plant docstrings all cite. Includes governance G1–G5 (plant-before-arm, exposure
recording, demote-never-delete, conspicuous loosening, growth-from-escapes).

**Edge cases**
- *Malformed / drift:* an ID referenced by `adversary-routes.json` that does not exist in
  the file — dangling reference, must RED. (This is the file's only mechanical contract.)
- *Boundaries:* ID renumbering or reuse. Forbidden; a test pins that IDs are unique and
  never decrease in count.
- *Second-order:* the inventory silently implying complete coverage. Mitigated by the
  stated distribution (26 facts / 16 agent) and G1 — membership ≠ control.

**UX tests.** David opens the file and can answer "what would a CISO ask about this
change?" without reading code. Driven through the real interface: the file itself, and
`/readable` (D6) citing IDs in its output.

**Integration surface**
- *Consumes:* nothing at rest. It is data.
- *Emits → named consumer:* `adversary-routes.json` (D3) reads the IDs;
  `review_ledger.py` records cite them; plant docstrings (D7) cite them. **Until D3 exists
  the file has no mechanical consumer** — that is stage-1 reality and is registered as
  dated integration debt on capability `scenario-inventory` (owner: David, expires
  2026-11-30), not a silent write-only loop.
- *Surface parity:* not surface-bound; ships to both adapters via the installer as a doc.
- *Reverse sweep:* `/tdd-plan`, `/edge` and `/integration-audit` should cite scenario IDs
  in their output once armed — deliverable D8, or dated debt if D8 is cut.
- *Activation:* ON. It is a document; there is nothing to switch.

**Property tests.** IDs unique; every `Route` value is either `—` or a name present in
`agents/` or in `adversary-routes.json`; role values from a closed set.

**Repo-local extras.** Gate-surface rule: this is `docs/`, not a `##` SKILL section, so it
is not under the v1.22 removal ledger. Stated so the exemption is a decision, not an
oversight.

---

### D2 — `readable_surface.py` — derive the facts, render two artifacts

**What.** A stdlib-only bin tool that derives per-worry facts from sources that **already
exist** — `capabilities.json` (nodes), `dataflow-sweeps.json` + `dataflow_sweeps.py`
(edges), the test roster, `git ls-files`, hook config — and writes a machine snapshot
(`readable-surface.json`) plus a human page (`readable-surface.md`). Regenerating in the
gate must produce **no diff**; a stale snapshot REDs.

**Explicitly NOT a new extractor.** It composes existing producers. Any new extraction it
needs (e.g. effect classification) is added to the *existing* owner, not re-implemented.

**Edge cases**
- *Empty/null:* a repo with no `capabilities.json` — must fail loudly with "run
  `capability_registry.py init` first", never render an empty page that reads as "nothing
  here." (§4a: 0 violations must not be reachable by scanning nothing.)
- *Vacuity:* zero subsystems scanned → exit 3 (vacuous refusal), matching
  `dataflow_sweeps.py`'s existing contract.
- *Malformed:* a registry entry missing `activation` or `emits` — rendered as **"not
  stated"**, never omitted. An absent fact and a false fact must look different.
- *Scale:* 63 capabilities (Cheliped) must render to something a human finishes. Page is
  worry-organised, not subsystem-organised, precisely for this.
- *Idempotency:* two runs on an unchanged tree produce byte-identical output — ordering
  stable, no timestamps inside the artifact.
- *Second-order:* the page becoming authoritative in its own right. Every row cites its
  source `file:line` so an agent can be pointed at it; the page is an index, not a claim.

**UX tests.** David runs `/readable` → sees the worry pages; picks a row → the citation is
precise enough that "explain this one" is a well-scoped agent dispatch. Real interfaces:
CLI (`python3 …/bin/readable_surface.py render`) and the `/readable` command on both
adapters.

**Integration surface**
- *Consumes:* `capability_registry.py`, `dataflow_sweeps.py` + `dataflow-sweeps.json`,
  `_debt.py` (debt shape), `gate_runner.py` (joins the blessed gate),
  `render_reference.py`'s generated-and-checked pattern.
- *Emits → named consumer:* `readable-surface.json` → `route_adversaries.py` (D3) and
  `/readable` (D6). In stage 1 the JSON's only consumer is `/readable`; the routing consumer
  arrives in stage 2 — dated debt on capability `readable-surface`, owner David, expires
  2026-11-30.
- *Surface parity:* CLI + both adapters. `AGENTS.md` is generated
  (`render_agents.py`, capability `generated-agents-md`), so Codex inherits it — verified,
  not assumed.
- *Reverse sweep:* `/integration-audit` currently re-enumerates subsystems from entry
  points every run; once the snapshot exists it should consume it instead. **Deliverable
  D8**, or dated debt.
- *Activation:* ON by default (a read-only renderer). The *staleness gate* is the part with
  teeth and it ships ON, matching `render_reference.py`.

**Property tests.** Render is idempotent (`render(render(x)) == render(x)` on the
snapshot); every rendered row carries a resolvable citation; the summary counts equal the
row counts (no silent truncation).

**Repo-local extras.** Pinned summary line for `gate_yield` parsing:
`readable_surface render: subsystems N · effects N · unproven N · not-stated N`.
Planted-input test: a registry entry with a fabricated `emits` consumer must show up in the
"nothing reads this" section; paired clean control alongside.

---

### D3 — `adversary-routes.json` + `route_adversaries.py` — the deterministic table

**What.** Given two snapshots (previous committed, current), compute the fact delta, map it
through the routing table to scenario IDs and adversary names, and **print a recommendation
with reasons**. Never dispatches.

Row shape (mirrors `dataflow-sweeps.json`'s config-driven, `unarmed`-declaring pattern):

```json
{ "id": "R01", "when": "capability gained an outbound effect",
  "scenarios": ["S17","S19","S23"], "run": ["reach","consent"],
  "because": "new external contact is the fastest route to a surprise",
  "unless": "target listed in known_egress", "armed": false, "plant": "P-R01" }
```

**Edge cases**
- *Empty:* no previous snapshot (first run) — must refuse with a stated reason, never treat
  "everything is new" as 400 findings.
- *Boundaries:* a delta touching 40 rows at once (a big refactor) — cap the recommendation
  and **say what was capped**; a silent top-N is a lie by omission (§12).
- *Auth-negative:* a route referencing an agent name that does not exist → RED.
- *Idempotency:* running twice on the same delta yields identical recommendations.
- *Concurrency:* two gate runs on the same commit must not double-append the exposure row.
- *Failure/rollback:* a malformed routes file fails closed — no recommendation is not the
  same as no risk.
- *Second-order:* trigger inflation. Every row must state its `because` and be reviewable
  on yield (D5).
- *The denominator:* the config declares what fires **nothing** (docs-only change,
  prompt-text change, new test, dependency bump) so the shape of the blind spot is
  approved, not implied.

**UX tests.** A commit adds a `requests.post` to a module with no prior egress → the gate
prints `R01 → reach, consent (because: …)` with the citation. A docs-only commit prints
`no routes fired (docs-only; see declared no-fire classes)` — the quiet case must be
*visibly* quiet, not absent.

**Integration surface**
- *Consumes:* D1 (scenario IDs), D2 (snapshots), `agents/*.md` roster, `_debt.py`.
- *Emits → named consumer:* recommendations → David + the orchestrator (human-in-loop);
  exposure rows → `gate_yield.py route-rollup` (D5). Both named, no write-only loop.
- *Surface parity:* CLI + gate output; both adapters via `/readable --routes`.
- *Reverse sweep:* the existing `/edge`, `/mutate`, `/probe`, `/tdd-plan`,
  `/integration-audit` commands already end by dispatching adversaries on a **prose** rule.
  Those dispatch points should cite route IDs so their dispatches are recorded on the same
  ledger — **D8**, or dated debt.
- *Activation:* ships **ARMED-BUT-ADVISORY with zero rows armed**, using the exact
  `unarmed` declaration block `dataflow-sweeps.json` already uses. Named switch:
  `TDD_PLAYBOOK_ROUTES=off`. Per §6b, arming a row requires its plant (G1), and the
  onboarding contract is: metric = routes fired vs. findings acted on (D5); review = each
  calibration cycle; kill = a row with real exposure and zero acted-on findings is demoted.

**Property tests.** Delta computation is order-independent; recommendation set is a pure
function of (delta, table); `armed=false` rows never appear in recommendations.

**Repo-local extras.** Planted route: a fixture snapshot pair with a known new effect must
produce exactly the expected route set; paired clean control (a docs-only delta) must
produce none. Vacuity guard: refusing to report "0 routes" when the delta itself was empty
vs. when it was non-empty is a distinguishable exit.

---

### D4 — Exposure recording (extends `gate_yield.py`, does not replace it)

**What.** Every route evaluation records **exposure**, not just outcome: change class, area
touched, delta size, risk tier, armed/unarmed, and whether a resulting finding was acted
on. One committed row per route per cycle, in `gate_yield.py`'s existing rollup shape.

**This is the brakes rule made mechanical**, and it is an extension because `gate_yield.py`
already carries the exact doctrine: *"a gate absent from the record is UNMEASURED, never
zero"* and *"unadjudicated friction is not evidence of zero yield."* Building a second
ledger would duplicate the honesty rules and let them drift apart.

**Edge cases**
- *Empty:* a fresh clone with an ephemeral raw log must not make a healthy route look like
  a zero-yield candidate — `gate_yield`'s existing committed-rollup rule covers this and is
  inherited, not re-derived.
- *Boundaries:* the first cycle — candidates need ≥2 committed cycles.
- *Malformed:* an exposure row missing `change_class` is UNMEASURED, never defaulted.
- *Second-order:* exposure attributes chosen so that they can be gamed into always looking
  high-exposure. Mitigated: attributes derive from the fact delta (D2), not from self-report.

**UX tests.** `gate_yield.py route-candidates` after two cycles prints candidates with
their exposure profile — David can see "ran 20 times, 18 were docs-only" at a glance.

**Integration surface**
- *Consumes:* `gate_yield.py`, D3 output, `_common.emit()`'s existing event log.
- *Emits → named consumer:* `docs/calibration/route_yield.md` → `route-candidates` → D5 →
  David. Named end-to-end.
- *Surface parity:* CLI only (it is an instrument, not a user surface). Stated divergence.
- *Reverse sweep:* none — this *is* the existing instrument, extended.
- *Activation:* ON with D3. Recording must start at run #1; exposure cannot be computed
  retroactively. **This is why D4 is stage 2 with D3, and not deferred with D5.**

**Property tests.** Rollup is associative over cycles; draining the raw log is idempotent;
counts never decrease.

---

### D5 — The demotion journal (R4.3 shape, built for routes)

**What.** `docs/calibration/demotions.md` — a demoted route carries `{what, target, owner,
expires}`; an expired demotion REDs the gate. Demotion moves a route to the manual
inventory with a 120-day timer that surfaces **as a question**, never as a run.

`gate_yield.py`'s header states this instrument is to be "built when the first candidate
actually appears." Routes provide that occasion — but only after D4 has produced ≥2
committed cycles, so **D5 is stage 3 and deliberately not built earlier**. Building a
retirement mechanism before anything is retirable is the speculative-generality failure
(**S16** on our own inventory).

**Edge cases**
- *Auth-negative:* deletion attempted on fire-count alone → refused with the structural-vs-
  statistical distinction printed (G3).
- *Boundaries:* expiry exactly today.
- *Failure:* a demotion whose target route no longer exists → dangling, RED.
- *Second-order:* demotion used as a quiet disarm. Mitigated by G4 — loosening is journaled
  with who/when/why (`guard_note.py` pattern).

**Integration surface.** *Consumes:* `_debt.py`, `gate_yield route-candidates`, D1.
*Emits → named consumer:* the release gate (expired demotion fails it) and `/grade`.
*Activation:* ON when built. *Reverse sweep:* guards themselves become demotable on the
same journal once it exists — dated debt on `advisory-guards-optin`, not a silent gap.

---

### D6 — `/readable` — the narration contract

**What.** A command that (a) renders the current worry pages on demand, and (b) when the
fact snapshot changed, narrates **the change** in plain language and appends it to an
append-only log. Standing descriptions are regenerated fresh and never stored.

**The rule that makes this work:** *facts are diffed; prose is written about the diff and
kept; descriptions are on demand and discarded.* Diffing regenerated prose produces large
meaningless diffs and trains the reader to stop looking.

**Edge cases**
- *Empty:* no change since last snapshot → "nothing changed" as an explicit output, not
  silence.
- *Malformed:* narration that cites a fact absent from the snapshot → must fail the
  citation gate (`verify_citations.py`, already built and consumed by `/claims`).
- *Second-order — the load-bearing risk:* a fluent, confident, **wrong** narration. David
  cannot check it; that is the one way this makes him *less* accountable. Mitigated by D7,
  which is a hard precondition on arming, not a follow-up.

**UX tests.** `/readable` with no change → one line. `/readable` after a change → plain
sentences with citations. `/readable S17` → the CISO question answered for the current tree.

**Integration surface**
- *Consumes:* D2 snapshot, `verify_citations.py`, D1 IDs.
- *Emits → named consumer:* narration log → `/grade` (§13 cycle grading) and David.
- *Surface parity:* both adapters (`commands/readable.md` ships to claude + codex).
- *Reverse sweep:* `/integration-audit`'s report shape should cite the same worry pages —
  D8 or dated debt.
- *Activation:* ON. Prose **never gates** (reading 2, rejected).

**Repo-local extras.** Narration output goes through `verify_citations.py` — an
uncitable sentence is refused, reusing the existing gate rather than inventing a check.

---

### D7 — Plants for every armed route (§13, v1.25 shape)

**What.** Each armed route ships a planted fact-change it must fire on, frozen in
`calibration/corpus/`, with a docstring citing the motivating scenario ID and — where the
route was born from a real defect — the pre-fix sha. **No plant, no arming (G1).**

Starter plants, matching the six routes in the inventory: add a network call (R01/reach);
defang a test (unchecked); remove an approval gate (consent); ship a feature default-off
with no metric (waste); orphan a consumer (silence); mislabel a control (adoption — reuses
`ux-probe-calibrator`, not a new mechanism).

**Edge cases.** *Second-order:* a plant that a route fires on for the *wrong reason*
(keyed on a proxy name rather than the fact). Mitigated by the v1.25 replay rule — the
route is replayed against the motivating artifact before it is trusted, and the paired
clean control must NOT fire.

**Integration surface.** *Consumes:* `calibration/`, `plant_forms.py`, `plant_vitality.py`
(does the plant still discriminate). *Emits → named consumer:* calibration history + the
arming decision. *Activation:* plants are the arming gate; nothing ships armed without one.

**Repo-local extras.** `plant_vitality.py` already answers "has this plant gone stale" —
routes inherit it rather than growing a parallel staleness notion.

---

### D8 — Doctrine + adoption (SKILL §6d, command citations, vendoring)

**What.** A new `## 6d` SKILL section — *the readable surface: description is not a
verdict* — plus scenario-ID citations wired into `/tdd-plan`, `/edge`,
`/integration-audit`, and installer/adapter updates so downstream repos receive the
command, the bins, and the config.

**Stage 2, not stage 1** (open question 4): a `##` section is a vendored gate surface, and
doctrine describing a mechanism that may be cancelled at the stage-1 decision gate is the
prose-without-mechanism failure §6c exists to prevent.

**Integration surface.** *Consumes:* `install_into_repo.py`, both `adapter.json` files,
`render_agents.py`. *Emits → named consumer:* downstream repos (Cheliped first).
*Surface parity:* claude + codex, verified by `test_host_parity.py`.
*Reverse sweep:* this **is** the reverse sweep for D1–D7. *Activation:* ON.

---

## D. Flow table (§6c dataflow liveness)

| Flow | Producer | Consumer | Liveness test |
|---|---|---|---|
| scenario IDs | `adversary-scenario-inventory.md` | `adversary-routes.json`, plant docstrings, review-ledger records | dangling-ID test REDs on an unknown ID (both directions) |
| `readable-surface.json` | `readable_surface.py render` | `/readable`, `route_adversaries.py` | gate REDs if regeneration diffs (stale snapshot) |
| worry pages (`.md`) | `readable_surface.py render` | David (human) | citation resolves via `verify_citations.py` |
| route recommendations | `route_adversaries.py` | David + orchestrator | fixture delta produces exactly the expected set |
| exposure rows | `route_adversaries.py` | `gate_yield route-rollup` | rollup row count equals evaluation count per cycle |
| retirement candidates | `gate_yield route-candidates` | D5 demotion journal → David | candidate requires ≥2 committed cycles (inherited rule) |
| demotion entries | `demotions.md` | release gate | expired demotion REDs the gate |
| narration | `/readable` | `/grade`, David | every sentence citation-checked |

**Consumer parity (migration rule).** This plan replaces no seam, so no old-seam consumer
enumeration is owed. Stated explicitly so its absence is a fact, not an omission.

---

## E. Tripwire deliverable list

| # | Deliverable | BUILT | WIRED (production composition root) | ACTIVATED | EXERCISED |
|---|---|---|---|---|---|
| D1 | Scenario inventory | file exists, 42 rows, IDs unique | cited by D3 config + plants | n/a (document) | dangling-ID test |
| D2 | `readable_surface.py` | bin tool, stdlib-only | `gate_runner.py` stage | ON; staleness gate ON | planted fabricated-consumer + clean control |
| D3 | Routing table | `route_adversaries.py` + config | gate output + `/readable --routes` | advisory, 0 rows armed, `TDD_PLAYBOOK_ROUTES` switch | fixture delta → expected route set; docs-only → none |
| D4 | Exposure recording | `gate_yield route-rollup` | same gate stage as D3 | ON with D3 | rollup/candidate tests over ≥2 synthetic cycles |
| D5 | Demotion journal | `demotions.md` + validator | release gate | ON when built (stage 3) | expired-demotion REDs; dangling-target REDs |
| D6 | `/readable` | `commands/readable.md` + renderer | both adapters, `test_host_parity.py` | ON | citation gate on narration; no-change path |
| D7 | Plants | `calibration/corpus/` entries | arming precondition in D3 validator | n/a | each plant fires its route; clean control does not |
| D8 | Doctrine + vendoring | SKILL §6d, command edits, installer | `install_into_repo.py`, both adapters | ON | scratch-repo install parity; `test_reference_docs.py` |

---

## F. Registered capabilities and dated debts

New `capabilities.json` entries, registered in the commit that builds each:

| id | activation | debt (owner: David) |
|---|---|---|
| `scenario-inventory` | on | no mechanical consumer until D3 — expires **2026-11-30** |
| `readable-surface` | on | routing consumer arrives stage 2 — expires **2026-11-30** |
| `adversary-routing` | advisory, 0 armed | every row unarmed pending its plant (G1) — expires **2027-01-31** |
| `route-exposure` | on with D3 | demotion consumer (D5) is stage 3 — expires **2027-01-31** |

Existing capability touched: `advisory-guards-optin` gains dated debt — guards become
demotable on D5's journal once it exists (expires **2027-01-31**).

---

## G. Staging — stage 1 is a decision gate, not a partial build

**Stage 1 (v1.33.0):** D1 + a derive-on-demand `/readable` (D6 without the snapshot). No
commit-time artifact, no routing, no doctrine. **Then stop.**

**The gate:** three weeks of ordinary work. Did David open the surface unprompted more than
twice, and did it change a decision at least once? If no → stages 2–3 are **cancelled**,
D1 remains as a manual checklist, and the money is unspent. Recorded either way in
`docs/calibration/`.

**Stage 2 (v1.34.0):** D2 (committed snapshot + staleness gate), D3 (advisory, 0 armed),
D4 (exposure from run #1), D7 (plants for the first two routes only), D8 (doctrine).

**Stage 3 (when `route-candidates` returns its first candidate):** D5. Not before — the
repo's own rule.

---

## H. Loop closure

Adversaries dispatched on this draft per §0. Findings folded in below.

<!-- LOOP-CLOSURE-PENDING: replaced after dispatch -->
