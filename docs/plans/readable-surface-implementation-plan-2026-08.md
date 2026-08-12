# Implementation plan: The Readable Surface — 2026-08

**Status:** DRAFT v2 — for David's review. Nothing built. Target version: **v1.33.0**.
**Upstream spec:** the "when code no longer matters" thread, 2026-08-12.
**Companion:** `docs/reference/adversary-scenario-inventory.md` (S01–S42, manual checklist).
**Loop closure:** `integration-adversary` → **ISLAND** (16 findings);
`architecture-adversary` → **BAND-AID** (11 findings). Dispositions in §F.

> **v2 is a scope collapse, not a patch.** v1 proposed eight deliverables including a
> routing table, an exposure ledger and a demotion journal. The adversaries proved the
> routing half is undeliverable as specified — its adversary targets do not exist, its
> flagship fact has no extractor, its adjudication field has no producer, and its only
> switch turns it off. v2 builds **three** things and explicitly declines to build the rest
> (§E). The scenario inventory survives as a manual checklist, not a mechanism.

---

## A. The finding that reordered everything

v1 derived its "facts" from `capabilities.json`. That file is **hand-authored self-report**:
`capability_registry.py:96-160` checks presence and type only — R-WRITE-ONLY accepts any
non-empty string as a consumer, which is why the live registry carries consumers like
`"learning-loop (unlock journal via /grade)"`, and nothing anywhere resolves `wired_by` or
`exercised_by` to a file (sole exception: one hand-pinned instance,
`test_capability_registry.py:259-263`).

So a readable surface built on it would faithfully re-render whatever an agent typed — and
be **precisely wrong in the case David cannot detect**, which is this plan's own
load-bearing assumption. v1 also quoted `gate_yield.py:30-31` — *"derived from EXHAUST,
never self-report"* — and then built the comprehension instrument on the repo's one
self-report artifact.

**Consequence: registry resolution teeth are D1, and nothing renders before they land.**

---

## B. Repo-local conventions discovered and applied

- **One blessed gate entrypoint:** `sh scripts/civerd_gate.sh`, never piped (§4a).
- **Gate admission is `gate-manifest.json`**, not "a `gate_runner` stage" (v1 said the
  latter; wrong). `gate_plan.py:89-102` refuses the plan unless `acknowledged_plan_sha256`
  and `acknowledged_roster_sha256` are re-acknowledged; every peer bin
  (`dataflow_sweeps.py`, `render_reference.py`, `review_ledger.py`, `host_parity.py`) has a
  `force_full`/`safe_rules` entry. Each deliverable below carries its manifest line.
- **Generated-and-checked wiring is a suite test:** `test_reference_docs.py:35-77`, with a
  planted staleness pair at `:56-74`. That is the pattern D2 follows.
- **Planted-input rule** with a **paired clean control** (v1.17 pair quota).
- **Stdlib-only** under `plugins/tdd-playbook/bin/`.
- **One debt shape** `{what, target, owner, expires}` via `_debt.py`.
- **Registry dogfood:** `test_capability_registry.py::test_own_registry` runs with the real
  date; an expired debt REDs the suite.
- **Gate surfaces** (SKILL `##`, `agents/*.md`, `commands/*.md`): additions free, removals
  need `calibration/gate-changes.md` (v1.22 rule d). This plan is additions-only.
- **`CLAUDE.md` is the source of `AGENTS.md`** (`render_agents.py:26-27` — verbatim plus
  curated host notes). Codex learns nothing unless CLAUDE.md is edited. v1 asserted the
  opposite.
- **Codex parity is `unavailable` by policy**, not by oversight:
  `host-parity-policy.json:31-41` marks codex `commands`/`agents` unavailable, and
  `install_into_repo.py:51-57` deliberately excludes them from `CODEX_COPY_TREES`. Any new
  command ships claude-only with dated debt.
- **`docs/` is not vendored.** `install_into_repo.py:43-50` `COPY_TREES` has no `docs`.
- **Release authority:** David tags. Nothing here changes that.

**Conflict with new work: none.** One tension stated: CLAUDE.md's v1.32.0 reversal retired
schedule-driven obligations. This plan introduces no schedule.

---

## C. Spec integrity

**Assumptions**

1. **The reader cannot fall back to source.** The surface must be *pointable*, not
   *complete*. An omission is recoverable (dispatch an agent at the coordinates); a **wrong**
   row is not. This is why D1 precedes D2 and why D3 gates prose.
2. **Facts and prose must not be mixed.** Derived facts are deterministic and diffable; LLM
   prose is neither — regenerating a description of unchanged code yields a large
   meaningless diff that trains the reader to stop looking.
3. **Cheliped is the intended pilot reader — and cannot receive `docs/`.** Stated as debt,
   not assumed away.

**Readings**

- **Followed:** a *comprehension* instrument. Every existing Playbook output is a verdict
  (pass/fail, N/N, green/red). This adds the first artifact whose output is *description*.
- **Rejected — a new gate.** Prose never gates. Two mechanical things gate: registry
  resolution failures (D1) and a stale snapshot (D2).
- **Rejected — 63 subsystem pages.** Organised the way the code is organised, which is the
  organisation David cannot navigate. One page, organised by worry.

**Materially simpler approach, and why it is now rejected.** v1 proposed shipping the
inventory plus a derive-on-demand `/readable` that commits nothing. The architecture
adversary showed this is LLM description with no derived facts, no idempotency, no staleness
gate and no plants — the version an agent can already produce with zero new mechanism, and
the one *most* exposed to the fluent-but-wrong risk. Worse, its stage gate ("did David open
it twice") could pass merely because prose is pleasant to read. That is comfort mistaken for
coverage — the exact failure this whole thread began by naming. **Rejected.**

**Open questions for review — plan proceeds on the stated defaults**

1. **D1 will RED this repo's own registry on day one.** 26 entries carry free-text
   consumers. **Default: yes, that is the point** — it is a planted-error result arriving
   for free — with a one-cycle grace window: existing entries get a dated
   `resolution_exempt` debt (expires 2026-10-31), new/edited entries must resolve
   immediately. Alternative: fix all 26 first, which blocks D2 for a cycle.
2. **Which single page does D2 build?** **Default: "what nothing checks"** — effects and
   capabilities with no test behind them. Shortest, most damning, purest product judgment
   once you have it.
3. **`/readable` ships claude-only.** **Default: yes**, with dated codex debt under the
   existing `test-lock/codex-command-agent-discovery` ref.

---

## D. Deliverables

### D1 — Registry resolution teeth (`capability_registry.py`)

**What.** `validate()` stops accepting free text where it means a reference. Two new rules:
**R-WIRED** — every `wired_by` / `exercised_by` entry resolves to an existing path (with
`::test_name` suffix tolerated); **R-CONSUMER** — every `emits[].consumers` entry resolves
to a registered capability id, an existing path, or a `resolution_exempt` debt. Existing
R-WRITE-ONLY keeps its shape; it gains teeth.

**Edge cases**
- *Boundaries:* `path::test_name` and `path::Class::test` forms both resolve to the file.
- *Empty/null:* a capability with no `emits` — untouched, not an error.
- *Malformed:* a consumer string with prose around a real path (`"gate_yield.py (per-cycle
  rollups…)"`) — extract-and-resolve, and **say so in the message** when the match came from
  a substring, so the tolerance is visible rather than silent.
- *Auth-negative:* a `resolution_exempt` debt past its expiry REDs, via `_debt.py`.
- *Idempotency:* validate is pure; two runs identical.
- *Scale:* Cheliped's 63 entries — resolution is file-stat, not parse; must stay fast enough
  for every suite run.
- *Second-order — the migration hazard:* 26 live entries will fail at once. The grace debt
  is what keeps this from being a flag day; its expiry is what keeps the grace from becoming
  permanent.

**UX tests.** A capability naming a consumer that does not exist → `R-CONSUMER <id>: …` with
the unresolvable string quoted. Real interface: `python3 …/bin/capability_registry.py
validate` and the suite (`test_own_registry`).

**Integration surface**
- *Consumes:* `capability_registry.py`, `_debt.py`.
- *Emits → named consumer:* validation failures → `gate_runner` (already wired) and
  `capability_registry.py doctor`. No new flow.
- *Surface parity:* the bin ships to claude **and** codex (`CODEX_COPY_TREES` includes
  `bin`) — the one deliverable with genuine parity. Stated because the other two do not.
- *Reverse sweep:* **Cheliped's 63-entry registry gets the same teeth on its next refresh.**
  That is the highest-value consequence of this deliverable and is a Cheliped-side task, not
  one this repo can perform — dated debt on `capability-registry`.
- *Activation:* ON. It is a gate rule, not a feature.

**Property tests.** Resolution is order-independent; a resolvable set stays resolvable under
list reordering; exempted entries never mask a *different* rule's violation.

**Repo-local extras.** Planted pair: a registry fixture with an unresolvable `wired_by` must
RED; the paired clean control must pass. `gate-manifest.json` — `capability_registry.py` is
already in `force_full`; the new `tests/` additions change `acknowledged_roster_sha256`,
which must be re-acknowledged in the same commit.

---

### D2 — `readable_surface.py` — one page, checked facts only

**What.** A stdlib-only bin tool that renders **one** worry page — *what nothing checks* —
from facts that D1 has made resolvable, plus the test roster. Writes
`docs/reference/readable-surface.md` and `readable-surface.json`. Regenerating in the suite
must produce **no diff**.

**Explicitly not a general extractor.** It reads the registry and the test roster. It does
**not** classify effects, scan for egress, or invent a taxonomy — v1's "outbound effect"
fact had no producer anywhere in the repo, and inventing one is not in this plan.

**Edge cases**
- *Empty/null:* no `capabilities.json` → fail loudly telling the user to run `init`; never
  render an empty page that reads as "nothing here."
- *Vacuity:* zero capabilities scanned → exit 3, matching `dataflow_sweeps.py`'s contract.
  "0 unchecked" must be unreachable by scanning nothing (§4a).
- *Malformed:* an entry missing a field → rendered **"not stated"**, never omitted. An
  absent fact and a false fact must look different.
- *Scale:* 63 entries must render to something a human finishes.
- *Idempotency:* byte-identical output on an unchanged tree — stable ordering, no timestamps
  inside the artifact.
- *Failure/rollback:* a stale committed page REDs the suite (the `test_reference_docs.py`
  planted-staleness pattern), so the artifact cannot silently drift.
- *Second-order:* the page becoming authoritative. Every row cites `file:line` so an agent
  can be dispatched at it; the page is an index, not a claim.

**UX tests.** David runs the renderer → sees a list of capabilities with no `exercised_by`
that resolves, each citing its registry line → picks one → "explain this one" is a
well-scoped dispatch. Real interfaces: CLI, and the suite's staleness check.

**Integration surface**
- *Consumes:* D1's resolved registry, the test roster, `_debt.py`, `render_reference.py`'s
  generated-and-checked pattern (pattern reuse, not code duplication — different content,
  different audience, same mechanism).
- *Emits → named consumer:* `readable-surface.md` → David. `readable-surface.json` →
  **nobody yet** (v1's routing consumer is not being built). Registered as dated integration
  debt on `readable-surface`, owner David, expires **2026-11-30**. Alternative accepted at
  review: drop the `.json` until something reads it — **recommended**, and the default if
  question 2 is answered without comment.
- *Surface parity:* CLI only in this deliverable; the command is D3. Stated divergence.
- *Reverse sweep:* `commands/integration-audit.md:20-56` step 1 currently re-enumerates
  subsystems from entry points on every run; it should consume this page instead. Dated debt
  on `readable-surface` (expires 2027-01-31), not a silent deferral.
- *Activation:* ON. The staleness check is the part with teeth and ships ON.

**Property tests.** `render(render(x)) == render(x)`; every rendered row's citation
resolves; summary counts equal row counts (no silent truncation).

**Repo-local extras.** Pinned summary line: `readable_surface render: capabilities N ·
unchecked N · not-stated N`. `gate-manifest.json`: new `force_full` entry for the bin, and
`safe_rules` already routes `docs/reference/**` to `test_reference_docs`. **`review_ledger.py:20`
hardcodes `ALLOWED_REVIEW_TAIL` to `docs/reviews/` + exactly `docs/reference/current-state.md`** —
a release commit regenerating the readable surface would trip `:142-143`; extend it, with a
planted test.

---

### D3 — Narration honesty (`verify_citations.py` + `/readable`)

**What.** (a) A `--require-citation-per-claim` mode in `verify_citations.py` under which
zero citations is a **refusal**, not a clean exit. (b) A planted narration scenario in
`calibration/scenarios.json` whose oracle `must_not_match` a known-false claim. (c) A
`/readable` command that renders the page and, on request, narrates it in plain language —
gated by (a).

**Why this is a deliverable and not a note.** v1 mitigated its self-declared worst risk
(fluent, confident, wrong narration that David cannot check) by pointing at
`verify_citations.py`. That tool **returns 0 when it finds no citations at all**
(`:108-110`), and that behaviour is *pinned* by `test_verify_citations.py:76`. The
mitigation did not exist. A plan that mitigates its worst risk with a check of a different
property has no mitigation.

**Edge cases**
- *Empty:* nothing unchecked → "nothing unchecked" as explicit output, not silence.
- *Auth-negative:* narration with zero citations → refused under the new mode; the existing
  default mode keeps its current exit-0 behaviour so no existing caller changes.
- *Malformed:* a citation that resolves but whose quote does not match → already handled by
  the optional quote check; **made mandatory** for this consumer.
- *Second-order — the residue, stated:* a citation that resolves *and* whose quote matches,
  attached to a false conclusion, still passes. The plant in (b) is the only control on
  that, and it is a sample, not a proof. This is the honest limit of the whole approach and
  belongs in the review conversation, not in a footnote.

**UX tests.** `/readable` with nothing unchecked → one line. With findings → plain sentences,
each citing a resolvable line. Narration with a fabricated claim → refused, and the plant
proves the refusal fires.

**Integration surface**
- *Consumes:* `verify_citations.py`, `calibration/scenarios.json` (the existing 26-row
  plant→agent→oracle corpus), D2's page.
- *Emits → named consumer:* refusals → the caller. Narration → David. **`/grade` is not a
  consumer** — v1 claimed it was; `commands/grade.md` reads `grade_from_otel.py`, the
  TEST-LOCK journal and git history, and has no narration input. Corrected, not deferred.
- *Surface parity:* **claude only.** `host-parity-policy.json:31-41` marks codex commands
  unavailable and `install_into_repo.py:51-57` excludes them by design. `/readable` ships as
  another unavailable row under the existing `test-lock/codex-command-agent-discovery` debt.
  Adding `commands/readable.md` changes `host_parity.canonical_inventory`
  (`host_parity.py:51-58`), so `acknowledged_inventory_sha256` must be re-acknowledged in
  the same commit or `materialize` raises (`:93-97`).
- *Reverse sweep:* `README.md:19,31-39,228` lists the command set three times; `/readable`
  joins all three. (This is **S38** on our own inventory — "can a user find this without
  being told it exists" — and v1 mentioned README zero times.)
- *Activation:* ON. Prose never gates.

**Property tests.** The new mode is strictly stricter — anything it accepts, the default
accepts. Refusal is deterministic given the same input.

**Repo-local extras.** Plants live in `plugins/tdd-playbook/tests/fixtures/` (the
`test_dataflow_sweeps` shape) for the deterministic checks, and in `calibration/scenarios.json`
for the agent-graded narration oracle. **Not** in `calibration/corpus/approved/`, which is
pinned byte-identical forever (`plant-forms.md:11-13`, scoreboard-integrity rule (b)) and
would collide with §13 replay-and-adjust. `plant_vitality.py` derives staleness from the
calibration scoreboard, which deterministic fixtures never populate — **no vitality claim is
made** for the fixture plants. (v1 claimed inheritance; wrong.)

---

## E. What this plan explicitly does NOT build, and why

Stated so the absences are decisions rather than oversights.

| Not built | Why |
|---|---|
| **Routing table** (`adversary-routes.json`, `route_adversaries.py`) | `gate_plan.py:163-220` + `gate-manifest.json` is already a config-driven change→action router with fail-closed handling, escalation and digest acknowledgement; SKILL §9 (`SKILL.md:744-750`) already states route R01 semantically in prose. A third router needs a reason neither adversary could find. If routing is built later, it extends `safe_rules` with an `adversaries:` field. |
| **Effect / egress extraction** | No such fact exists anywhere in the repo; the registry has no effect field and `ghost_gates` is unarmed. v1's flagship route keyed on `requests.post` — a source-pattern proxy of exactly the kind `dataflow_sweeps.py:19-22` warns against. Real work, its own plan. |
| **Exposure ledger** | Its load-bearing field ("was the finding acted on") has no producer, and `gate_yield.candidates()` keys on adjudicated overrides that routes would not have. `capabilities.json` → `gate-yield` already carries dated debt (expires **2026-11-15**) recording that five of six existing gates "can NEVER become retirement candidates" for this reason. Fix that debt first; it is a prerequisite, not a parallel task. |
| **Demotion journal** | `gate_yield.py:40-42` says build it "when the first candidate actually appears." No candidate can appear until the debt above is paid. Building it now is **S16** on our own inventory. |
| **Six new adversaries** (`reach`, `consent`, `unchecked`, `silence`, `waste`, `adoption`) | They do not exist; `agents/*.md` is a protected gate surface and a host-parity asset. The inventory's Route column has been re-mapped onto the ten real agents, with 20 rows honestly marked manual-only. |
| **Vendoring the inventory** | `COPY_TREES` has no `docs`. Registered as dated debt rather than solved by moving the file somewhere it does not belong. |
| **SKILL §6d doctrine** | A vendored gate surface describing a mechanism this plan mostly declines to build. Doctrine follows a mechanism, never precedes it (§6c's founding lesson). |

---

## F. Adversary findings — dispositions (27 total)

**Accepted and folded in as deliverables or corrections (19).**
Registry self-report → **D1** (arch F1). `verify_citations` cannot refuse → **D3** (arch F2,
integ #9). Six nonexistent adversaries → **inventory Route column re-mapped** (arch F4,
integ #1). HACK_CATALOG duplication → **S25=H11, S26=H4 stated + dated debt** (arch F5).
"Acted on" has no producer → **exposure ledger not built** (arch F7, integ #3).
`armed` boolean + env knob → **not built** (arch F8). Taxonomy in three places → **one page,
no taxonomy** (arch F9). Wrong wiring seam → **`gate-manifest.json` lines in D1/D2/D3**
(arch F10, integ #7). Codex parity false → **corrected in B and D3** (arch F11, integ #6).
`docs` not vendored → **stated + dated debt** (integ #2). No ON-switch / invalid activation
values → **all three deliverables are `on`; nothing dark** (integ #5). Downstream write-only
`gate_yield` → **not extended** (integ #8). `/grade` not a narration consumer → **corrected**
(integ #10). Plants in the wrong corpus + unsupported vitality claim → **fixtures +
scenarios.json, no vitality claim** (integ #11). Four silent "D8 or debt" deferrals →
**registered in §G** (integ #12). CLAUDE.md is AGENTS.md's source → **stated in B; CLAUDE.md
edit is a release-time task** (integ #13). `review_ledger` ALLOWED_REVIEW_TAIL →
**D2 extras** (integ #14). Stage-1 cancellation landmine → **no staging; nothing registered
that cancellation would strand** (integ #15). `/readable` absent from README → **D3 reverse
sweep** (integ #16).

**Accepted as prerequisites, deliberately blocking (3).** Routing (arch F3, integ #4) and
retirement (integ #3) are gated on the `gate-yield` per-gate adjudication debt (2026-11-15)
and on an effect extractor that does not exist. Both are named in §E rather than staged,
because staging implies a commitment this plan cannot honour.

**Accepted as a method correction (1).** The stage-1 pilot tested the wrong artifact (arch
§G). v1's gate — "did David open the surface twice" — could pass because prose is pleasant.
**Staging removed entirely**; the plan is now small enough to build and judge on the result.

**Rejected with reasons (4).**
- *arch F5's stronger form* — "let rows with an armed mechanism inherit it rather than await
  a route." No routes are being built, so there is nothing to inherit into; the S↔H mapping
  is registered as debt instead.
- *arch F6* — protecting `adversary-routes.json` in `check_scoreboard_integrity.py`. The
  file is not being created.
- *integ #1's alternative* — authoring six new agent briefs as deliverable D0. Six untested
  adversaries is exactly the fleet-dilution failure identified in the source thread; agents
  should be born from escapes, not from an org chart.
- *integ #15's second half* — naming a producer for the "did David open it" counter. The
  metric is gone with the staging.

**Unverified claims carried forward, not treated as facts** (integ, own statement): whether
`test_reference_docs.py` accepts a new file under `docs/reference/`, and whether
`review_ledger.validate_record` rejects unknown finding keys. Both are D2/D3 build-time
checks, listed here so they are not silently assumed.

---

## G. Flow table (§6c)

| Flow | Producer | Consumer | Liveness test |
|---|---|---|---|
| resolution failures | `capability_registry.py validate` | `gate_runner`, `doctor` | planted unresolvable `wired_by` REDs; clean control passes |
| `readable-surface.md` | `readable_surface.py render` | David | stale page REDs (planted staleness pair) |
| `readable-surface.json` | `readable_surface.py render` | **nobody** — dated debt, or dropped per open question 2 | n/a until a consumer exists |
| citation refusals | `verify_citations.py --require-citation-per-claim` | `/readable` | planted zero-citation narration is refused |
| narration | `/readable` | David | planted false claim caught by the `scenarios.json` oracle |

**Consumer parity:** this plan replaces no seam, so no old-seam enumeration is owed. Stated
so the absence is a fact rather than an omission.

---

## H. Tripwire deliverable list

| # | Deliverable | BUILT | WIRED (production composition root) | ACTIVATED | EXERCISED |
|---|---|---|---|---|---|
| D1 | Registry teeth | R-WIRED + R-CONSUMER in `capability_registry.py` | `gate-manifest.json` force_full (already present) + roster re-ack | ON | planted unresolvable + clean control; `test_own_registry` with real date |
| D2 | One derived page | `readable_surface.py` + committed artifact | `gate-manifest.json` force_full entry; `safe_rules` docs/reference → `test_reference_docs` | ON; staleness gate ON | planted staleness pair; vacuity exit 3 |
| D3 | Narration honesty | `--require-citation-per-claim`; `commands/readable.md`; narration plant | README ×3; `host_parity` inventory re-ack; claude-only + codex debt | ON; prose never gates | zero-citation refusal; false-claim oracle |

---

## I. Capabilities and dated debts

| id | activation | debt (owner: David) |
|---|---|---|
| `capability-registry` (existing) | on | one-cycle `resolution_exempt` grace for the 26 live entries — expires **2026-10-31**; Cheliped-side adoption of the same teeth — expires **2027-01-31** |
| `readable-surface` (new) | on | `.json` has no consumer (or is dropped) — expires **2026-11-30**; `/integration-audit` should consume the page — expires **2027-01-31** |
| `scenario-inventory` (new) | on | not vendored (`COPY_TREES` has no `docs`) — expires **2026-11-30**; S↔H mapping incomplete — expires **2026-11-30**; no security adversary for S17–S24 — expires **2027-01-31** |
| `citation-gate` (existing) | on | the residue: a resolvable, quote-matching citation attached to a false conclusion still passes — expires **2027-01-31** |
| `gate-yield` (existing) | on | **unchanged and load-bearing** — the per-gate adjudication debt (2026-11-15) is the prerequisite for any future routing or retirement work |

---

## J. Loop closure

`Loop closed: yes (integration-adversary — ISLAND: the routing half's adversary targets,
flagship fact, adjudication producer and on-switch are all absent, and the readable half
reaches no host but this repo's Claude surface; architecture-adversary — BAND-AID: the
surface derives its facts from a hand-typed self-report that nothing resolves, which is the
one artifact the intended reader cannot check.)`

19 findings folded in as deliverables or corrections, 3 accepted as blocking prerequisites,
1 accepted as a method correction that removed the staging, 4 rejected with reasons, 2
unverified claims carried forward as build-time checks. Scope reduced from 8 deliverables to
3.
