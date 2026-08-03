# Implementation plan: Dataflow Liveness (§6c) — 2026-08

**Status:** EXECUTING (approved 2026-08-03; David chose the stated defaults on all three
open questions). Target version: **v1.24.0**.
**Upstream spec:** `docs/recommendations/dataflow-liveness-amendment-review-2026-08.md`
(the CTO/QA review of the Cheliped amendment proposal) — this plan implements that
review's dispositions, not the raw proposal. **NOTE (2026-08-03):** the review doc was
never committed to this repo (it lived in the authoring session); execution proceeds on
this plan's own dispositions, per David. The escape-class taxonomy it defined is
grounded here directly from the Cheliped excavation's escape table
(`EXCAVATION_AUDIT.md`, 2026-08-03): **T1** refactor-orphaned-consumer · **T2**
written-never-read · **T3** built-never-called · **T4** accepted-value-no-reader ·
**T5** render-seam gap (key supplied, no placeholder) · **T6** registry
collision/interception · **T7** event-never-fired-per-surface.
**Discipline:** this plan is written in the Playbook's own §0 shape and dogfoods the
flow table it introduces (§D below).

---

## A. Repo-local conventions discovered and applied

- **One blessed gate entrypoint:** all suites run ONLY via `sh scripts/civerd_gate.sh`
  (CLAUDE.md; the 2026-07-28 prose-loop divergence). Every deliverable's tests join that
  gate, never a side loop.
- **Planted-input rule:** every mechanical change ships a planted violation that must go
  RED, with a **paired clean control** (v1.17 pair quota) — unpaired plants are rejected.
- **Gate surfaces** (SKILL `##` sections, `agents/*.md`, `commands/*.md`): additions are
  free; removals/renames need `calibration/gate-changes.md` entries (v1.22 rule d). This
  plan is additions-only. Gate-surface text changes are **live-calibrated before being
  trusted** (§13; capabilities.json debt precedent).
- **Registry dogfood:** `capability_registry.py validate` runs mechanically on every suite
  run with the real date (`test_own_registry`); new capabilities register in the same
  commit that builds them. The registry only grows.
- **Release**: both manifests + CHANGELOG bump; scoreboard-integrity vs last tag; scratch-
  repo installer parity; `install_into_repo.py --doctor .`; tag ONLY via
  `scripts/release_verify.py` on a green signed CIVerd verdict (F4 — no bypass).
- **Stdlib-only invariant** for everything under `plugins/tdd-playbook/bin/`.
- **§4a house invariants apply to any new checker:** vacuity guards on scope AND
  execution; exit codes captured; "0 violations" must never be reachable by scanning
  nothing.

## B. Spec integrity (once, before the deliverables)

**Assumptions (stated, not silent):**
1. The Cheliped case-study numbers are secondhand (§12 caveat in the review); this plan
   depends only on the *classes*, which map to known static-analysis/contract-testing
   theory, not on the counts.
2. "Adopt as doctrine, pilot Tier-2 in Cheliped" (the review's staging decision) is the
   accepted frame. This plan ships doctrine + Tier-1 mechanism from this repo; Tier-2
   mechanisms are Cheliped-side pilot work, tracked here as dated debt.
3. §6b keeps its name (onboarding contract); new doctrine lands as **§6c**.

**Materially simpler alternative (say so, let review choose):** doctrine-only — amend
SKILL.md/commands and ship NO new bin tool. Cheaper, zero maintenance surface.
**Default: rejected**, because the escapes happened in a repo that already had the
*doctrine* of consumer-naming; the proposal's own evidence is that prose without a
mechanical sweep does not hold. But the choice is David's at plan review.

**Open questions for David (plan proceeds on the defaults if unanswered):**
1. Ship the Tier-1 reference tool (`dataflow_sweeps.py`, D10)? **Default: yes.**
2. Land this plan as a *gated* plan (`bin/plan_block.py scaffold` →
   `docs/plans/gated/`) so CIVerd can hold the release to its predicates once
   `repos.yml` is armed? **Default: yes** (dogfoods D1 plan-authoring; stays inert until
   the existing arming debt is paid — that debt is already owned and dated, expiry
   2026-09-15).
3. Version 1.24.0? **Default: yes.**

**Deferral rule (H7):** every "later" in this plan is a dated `integration_debt` entry
with an owner, and the expiry trigger is PROVEN in the landing commit via
`validate --as-of <expiry+1>` exiting 1. No prose deferrals.

---

## C. Deliverables, by phase

Ceremony scale: this is a multi-deliverable feature on gate surfaces → full flow
(plan → red tests → implement → Tripwire → adversaries → release gate).

### Phase 1 — Doctrine (SKILL.md; all additions)

**D1 — New §6c "Dataflow Liveness".**
One-line: nodes are necessary; edges are the truth — every flow names a live consumer,
every migration proves parity for the seam it replaces, every "wired" claim is proven at
the output end. Contents:
- the doctrine line + the flow-kinds checklist (persisted rows/fields incl. who prunes ·
  queryable telemetry · config fields AND each accepted enum value · template/prompt keys
  · registry/dispatch names + order · lifecycle events per surface · queues/dirs/caches
  incl. eviction · **silent-default boundaries** (`dict.get`/`getattr`/`**kwargs` sinks —
  the general class behind the template escape) · **schedule overlap** for time-windowed
  flows);
- the standing sweeps in **two decidability tiers**: Tier 1 exact (render pairing ·
  registration uniqueness+dispatch-order reachability · exemption-prose consistency) —
  mandatory where the flow kind exists, blocking; Tier 2 heuristic (storage pairing ·
  telemetry pairing · enum-value readers · ghost gates) — adopted with an FP budget,
  yield-instrumented, promoted from pilot data;
- **sweep governance:** sweep exemptions REUSE the house debt-entry shape
  (`{what/target, owner, expires}` — the registry's R-DEBT contract; an EXPIRED
  exemption REDs the sweep, provable via `--as-of`), never a new sibling format; an
  exemption naming a user-facing flow FAILS the suite — by CROSS-REFERENCE to §6a's
  companion rule (one canonical statement, no drift-prone verbatim copy), keyed on the
  registry's new audience attribute (D12), not a proxy; the excluded share is audited
  MECHANICALLY via committed per-cycle rows + a trend check (D13) — §4's
  equivalent-mutant filter-audit rule, with the same teeth: a growing exemption list
  under a green sweep means the list is doing the tests' work;
- **migration consumer-parity DoD:** a strangler/migration is done when every consumer
  the OLD seam fed is enumerated in the diff and each is fed / retired-with-deletion /
  dated debt; a seam-parity test pins the enumeration; leftover references to the deleted
  mechanism are defects (they encode a false model), swept in §12's exhaustive-negatives
  pass.
- Happy path: an agent planning a migration reads §6c and produces the old-seam output
  enumeration unprompted. Edge cases covered by the text: external/cross-repo consumers
  (named + probed, version-echo shape); dynamic templates (named exemption); values
  consumed outside the repo (dated exemption naming the external reader).

**D2 — §0: the flow table, scale-gated.** "Emits → named consumer" becomes a table
(`flow · producer · consumer · liveness test`) for feature/multi-deliverable/migration
work only (ceremony preamble governs; small diffs keep the prose answer). Empty consumer
cell = dated debt or the flow doesn't ship (existing §0 rule, now impossible to skip
silently). Migration deliverables MUST enumerate the replaced seam's outputs here.

**D3 — §6: FLOWS in the Tripwire accounting.** Multi-deliverable plans report
`Tripwire: N/N (+ FLOWS M/M)` — each plan flow row's liveness test named and green.
`commands/tripwire.md` gets the matching one-line instruction.

**D4 — §6a: three merges (no new bullets, sharpen existing ones).**
(a) evidence tiers for health surfaces: `config-read < import < runtime-probe <
composition-root`; import-existence alone can never render OK; (b) the canary/staleness
bullet gains "monitors record SUCCESS as well as failure; a standing check compares the
scheduled set against observed rows — silence goes red"; (c) symmetric reachability is
proven **through the real dispatch order** (a membership list passes a shadowed handler;
duplicate registration raises — last-write-wins is banned).

**D5 — §12: output-end proof.** A "now wired" claim is proven at the OUTPUT end or it is
not proven: supply-side evidence (key added, handler registered, config set) is
necessary-not-sufficient; the probe is one sentinel observed in the rendered/delivered/
persisted artifact. Lands beside the remote-runtime claims rule (same move: a pushed
commit is not a running process; a supplied key is not a rendered value).

**D6 — §13: escape-class tracking.** Audits/excavations report escapes BY CLASS (node
classes + T1–T7); a class that repeats across cycles means its mechanism isn't real yet.

*Tests for Phase 1:* doctrine is text, so the mechanical pin is D11's content-marker test
(canonical AND vendored SKILL must contain the §6c heading + doctrine line) — planted by
deleting the marker in a fixture copy → RED.

*Integration surface (Phase 1):* Consumes: SKILL.md structure, §0/§6/§6a/§12/§13 anchor
text. Emits → consumers: doctrine text → every Playbook session (via plugin load), →
vendored repos (via installer + refresh prompt), → calibration scenarios (oracle
anchors). Surface parity: local plugin + cloud/vendored — identical by construction
(one canonical SKILL). Reverse sweep: `/integration-audit`, `/tdd-plan`,
`integration-adversary` must ADOPT the new doctrine — that is exactly Phase 2; no silent
deferral.

### Phase 2 — Gate surfaces (commands + agent briefs; additions only)

**D7 — `/integration-audit`: fifth darkness class.** "**Dangling dataflow**" joins the
four classes — hunt list = T1–T7 (+ ghost gates, absence-blind monitors, exemption
prose), each with its one-line signature. **With an explicit partition boundary**, so
the class taxonomy stays disjoint and D6's repeat-class metric isn't corrupted by
double-homing: capability/topic-level write-only stays class 4 (R-WRITE-ONLY's
granularity); field/value/event-instance-level goes to class 5; exemption-PROSE
inconsistency is class 5, exemption-AS-HATCH stays class 2. §12 rules already in the
command govern the findings (every one is a negative). Happy path: an audit on a repo
with a written-never-read table files it under the fifth class with the storage-pairing
sweep named as the standing mechanism (step 5 of the command already demands this
closure).

**D8 — `integration-adversary`: flow-granularity refute prompts.** The five island
patterns gain a sixth: **dangling flows** — "name a flow this plan writes that nothing
reads; a value it accepts that nothing compares; a template key with no placeholder; a
surface whose lifecycle events the plan never fires; the migration whose old seam's
outputs are not enumerated." **The forced verdict lines are NOT touched** — calibration
oracles anchor on them (v1.22 house contract); this is an addition inside the hunt list
only.

**D9 — `/tdd-plan`: flow-table authoring.** The §0 rendering instructions gain the
scale-gated flow table (and the migration old-seam enumeration requirement), so plans
authored via the command carry it without the author re-reading SKILL.

*Tests for Phase 2:* command/agent files are gate surfaces — the mechanical pin is the
live calibration run (Phase 4, D16); the deterministic pin is the existing
`check_scoreboard_integrity` rule-(d) watch (these files are in the watched set) plus
content-marker assertions in the suite for the new class/prompt strings (planted-marker-
deleted fixture → RED, paired clean control).

*Integration surface (Phase 2):* Consumes: the agent dispatch seams (`/edge`-style "Loop
closed" convention), calibration oracle contracts. Emits → consumers: fifth-class
findings → owners + expiries via §12/registry debt (named consumer, existing); refute
prompts → plan authors (via adversary dispatch at §0 close). Surface parity: identical
across local/cloud (same files). Reverse sweep: `tripwire-auditor` — REVIEWED, no change
needed: parking/disposal audit already covers flow-row debt entries because they are
ordinary dated debt (decision recorded here rather than deferred silently).

### Phase 3 — Mechanism (Tier-1 reference tool + installer + registry)

**D10 — `plugins/tdd-playbook/bin/dataflow_sweeps.py`** (stdlib-only; the Tier-1
reference implementations, config-driven so repos tailor rather than fork). Subcommands:

- **`render-pairing`** — decidable template/supplier pairing.
  Happy path: AST-scan literal `str.format(...)`/`format_map` call sites (same-file
  decidable) + config-mapped template-file↔supplier-module pairs; assert BOTH directions
  (supplied ⊆ placeholders would over-fire — the check is: every placeholder has a
  supplier [missing = broken render], every supplied key has a placeholder [surplus =
  silently dropped value, the T5 escape]; the two directions report distinctly).
  Edge cases (each a test): positional `{}`/`{0}` · escaped `{{}}` · attribute/index
  fields `{a.b}` `{a[0]}` (pair on the root name) · f-strings SKIPPED (compiler-checked,
  stated) · `%`-style OUT of v1 (stated in `--help`, not silently unhandled) · dynamic
  templates → named dated exemption, never a silent skip · **vacuity: zero call sites /
  zero templates scanned → REFUSE ("refusing a vacuous pass"), exit 2**.
- **`ghost-gates`** — near-decidable undeclared-gate detection. **TIER 2 — ships in
  the tool but ADVISORY by default** (reports findings, exits 0; `--strict` flips it
  blocking), promoted to blocking only when the D19 pilot's promote verdict lands —
  the subcommand set must match the tier table it ships under (D1 classifies ghost
  gates Tier 2: its `*_enabled`/`*_mode` name-globs are a scoping proxy — an undeclared
  `use_cache` gate escapes them — tolerable only under FP/FN-budget governance).
  `--help` and D12's registry entry both state the tier.
  Happy path: AST-scan `getattr(obj, "NAME", default)` / `.get("NAME", default)` where
  NAME matches configured gate patterns (default `*_enabled`, `*_mode`); resolve NAME
  against the declared-fields source (config: a module/class path, or capabilities.json
  activation entries). Undeclared → finding. Edge cases: dynamic attr names → reported
  UNRESOLVABLE (a count in the summary, never a silent pass) · default-`True` ghosts
  flagged at higher severity (an undeclared always-on gate is invisible AND live) ·
  zero-sites vacuity refusal.
- **`exemption-prose`** — decidable prose-vs-default consistency.
  Happy path: config maps exemption entries carrying default-claims ("always-on",
  "on-by-default") to the artifact holding the real default (capabilities.json
  `activation.default`, or a named config file); mismatch → RED. Edge: referenced
  artifact missing → RED (fail closed), never skip.
- **Common contract (all subcommands):** machine-readable summary
  (`checked N · violations N · exempted N · unresolvable N` — house `·`-separated
  style) so the excluded share is auditable per cycle; exemptions use the house
  debt-entry schema `{what/target, owner, expires}` — an EXPIRED exemption REDs the
  sweep, `--as-of` makes the trigger provable (reusing/extracting the registry's
  R-DEBT date logic into a small shared helper — one debt shape, not a fourth);
  **the companion rule is mechanical** — an exemption whose target is a capability
  marked `user_facing` in the registry (the new D12 attribute — `surfaces` is
  deployment hosts, NOT an audience fact; keying on it would fire on everything or
  nothing) FAILS; **exit codes: 0 clean / 1 violation / 2 usage ONLY / 3
  vacuous-refusal** (the scoreboard-integrity multi-code precedent; "exit 2 is usage,
  never proof" is standing doctrine, and a vacuous scan is a REAL blocking verdict a
  mechanical consumer must be able to distinguish from a fat-fingered flag); exit codes
  and output are asserted by the tests, never discarded (§4a).

Red-first tests (`plugins/tdd-playbook/tests/test_dataflow_sweeps.py`), all planted with
paired clean controls: template-key-no-placeholder → RED / paired pass → GREEN ·
placeholder-no-supplier → RED · ghost `getattr(cfg, "x_enabled", True)` → reported
(advisory default) and RED under `--strict` / declared twin → clean in both modes ·
exemption claiming always-on over a default-off artifact → RED · EXPIRED exemption →
RED via `--as-of expiry+1` · user-facing exemption → suite FAILS · zero-scope → exit 3
with the refusal string, distinct from exit 2 usage · summary-line format pinned (a
consumer parses it — see flow table).

**D11 — Installer + content markers.** `install_into_repo.py` vendors
`dataflow_sweeps.py` (by the existing COPY_TREES `bin/` rule — construction, verified);
the scratch-repo parity check (release gate) asserts its presence. Content pins land at
the HOUSE seams, not a second home: the canonical "Dataflow Liveness" heading +
doctrine-line needle goes in `test_agents.py` (the established doctrine-pin suite, with
its paired planted-stripped fixture); `test_installer` gains ONE rewrite-aware equality
assertion — vendored SKILL == canonical modulo the `${CLAUDE_PLUGIN_ROOT}` rewrite —
which subsumes this marker and every future one (no per-marker treadmill). CLAUDE.md
refresh prompt: the VERIFY step adds `dataflow_sweeps.py` + the §6c mention, AND the
ADOPT block gains one §6c bullet ("plans carry a flow table for feature/migration work;
wire Tier-1 sweeps where the flow kind exists; migrations prove consumer parity") — the
ADOPT block is the canonical downstream mechanism-adoption surface, and without this
line every non-Cheliped vendored repo receives a runnable bin with no operational
instruction to use it (ACTIVATED-unstated, the exact §6 trap).

**D12 — Registry entry + schema attribute + engine handoff.** Three parts, one seam
each:
(a) `capabilities.json` += `dataflow-sweeps`: activation default ON (the bin ships and
runs anywhere; per-repo sweep CONFIG is the tailoring, not a dark switch; ghost-gates'
Tier-2/advisory status stated in the summary); `wired_by`: installer vendor rule +
`commands/integration-audit.md` (step-5 standing-mechanism closure names it) + SKILL
§6c + `scripts/civerd_gate.sh` (the D13 self-sweep invocation); `exercised_by`:
`tests/test_dataflow_sweeps.py`; `emits`: sweep summary lines → consumers: suite
assertions + the D13 committed rollup + trend check.
(b) **`capability_registry.py` schema gains an optional capability-level `user_facing`
(audience) attribute** — the ground truth the companion rule keys on (`surfaces` is
deployment hosts; grep confirms no audience fact exists anywhere in the schema today).
Capability-granular, so the "no per-field flows in the registry" rule holds. This also
gives §6a's existing companion-test doctrine its first machine-readable fact.
Mechanical change → planted tests: entry marked `user_facing` + exempted → RED;
internal entry exempted → GREEN. Existing entries annotated in the same commit.
(c) **`civerd-integrity.yml` `plant_targets` += `dataflow_sweeps.py`** — owned HERE so
it carries a Tripwire row (previously an unowned "Phase 5 mention"): the new checker
joins the engine-side plant coverage every other shipped checker in that file carries.
`validate` green in the same commit.

**D13 — Self-sweep + mechanical excluded-share audit.** Two halves, both mechanical
(the first draft had this as a CLAUDE.md prose line — that failed BOTH adversaries at
once: a consumer reading summaries nothing produced, at an evidence tier below the
plan's own ladder, re-creating the pre-F5 "David remembers" class the repo already
mechanized once):
(a) **The repo sweeps ITSELF.** A repo-local sweep config + a Tier-1 invocation added
to `scripts/civerd_gate.sh` (the ONE blessed entrypoint), blocking — this repo's own
shipped bins carry literal `.format(` render sites (`verify_citations.py`,
`plan_block.py`, …), so under D1's "mandatory where the flow kind exists" the flow kind
exists HERE and the doctrine would be violated on day one without this. Dogfood is the
deliverable, not a hope.
(b) **Committed rollup + trend check.** Each calibration cycle appends one committed
row per sweep (`date | sweep | checked | violations | exempted | unresolvable`) to the
gate-yield record (reusing `gate_yield.py`'s parse/rollup machinery — same instrument,
not a sibling), and a mechanical trend check flags an excluded share that grows N
consecutive cycles. The CLAUDE.md cycle-checklist line becomes a POINTER to that check
("read the trend check's output"), not the check itself. "A growing excluded share" is
a trend claim — undetectable from one run's summary line; it needs committed rows and a
comparator, exactly like F5 needed `check_staleness.py`, not a reminder.

*Integration surface (Phase 3):* Consumes: installer vendor list, capabilities.json,
test suite via `civerd_gate.sh` (the ONLY entrypoint — the tests are ordinary
`plugins/tdd-playbook/tests/test_*.py`, auto-collected by the existing loop; VERIFY at
build time that the gate's collection actually picks the new file up — §4a
collection-check, planted by temporarily breaking the filename in a fixture run).
Emits → named consumers: per the flow table (§D). Surface parity: local + cloud
(vendored) — parity proven by the scratch-repo release-gate check. Reverse sweep:
`civerd-integrity.yml` `plant_targets` — owned by D12(c), Tripwire row included; this
repo's OWN bins — owned by D13(a), the self-sweep; the engine-side `dataflow`
check-class proposal goes to CIVerd (separate doc,
`docs/recommendations/civerd-dataflow-liveness-upgrades-2026-08.md`) — cross-repo, its
forwarding tracked by the D19 dated line.

### Phase 4 — Calibration (§13 — the plan is not done when the code lands)

**D14 — In-suite deterministic plants** ship in the SAME commits as D10/D11 (listed
above; the pair quota holds).

**D15 — Corpus co-evolution (next authoring batch).** Author edge-class plants via
`author_plants.py` (adversary ≥ doer tier, human-approved): plan-omits-consumer (the
integration-adversary must flag a flow-table row with an empty consumer) ·
migration-without-parity (a plan replacing a seam with no old-output enumeration) ·
ghost-gate fixture. **Known limitation, now load-bearing:** `apply_edits` cannot CREATE
files, and writer-with-no-reader plants naturally want new fixture files → the `create`
capability is promoted from "possible future enhancement" (corpus README) to an owned
deliverable-or-debt: registered as `integration_debt` on the `calibration-loop`
capability (owner: david, expiry 2026-09-15, trigger proven via `validate --as-of`).

**D16 — Live calibration of the changed gate surfaces** (D7–D9 text) in the ~2026-08-10
run, sequenced AFTER the already-owed 3-agent re-run (existing debt, expires
2026-08-17). The changed surfaces are not TRUSTED until their rows land in
`docs/calibration/history.md`. The forced-line contracts were deliberately left
untouched (D8) so existing oracles keep anchoring.

### Phase 5 — Release + downstream

**D17 — Version 1.24.0**: both manifests + CHANGELOG (checkpoint commits at each phase
boundary per §11, pushed green).

**D18 — Release gate, in order (per CLAUDE.md — the checklist is the existing one; no
new steps invented here):** `sh scripts/civerd_gate.sh` green · `check_staleness.py
--warn-only` · manifests parse · `capability_registry.py validate` ·
`check_scoreboard_integrity.py --baseline-rev v1.23.0` exit 0 · quarterly clock
`--warn-only` · scratch-repo installer parity (now incl. `dataflow_sweeps.py`) ·
`install_into_repo.py --doctor .` · push → CIVerd signs → `release_verify.py --wait-s`
→ tag only on exit 0.

**D19 — Cheliped pilot dispatch (CROSS-REPO).** Send the standing refresh prompt (the
stale vendored copy is itself a finding) PLUS the pilot addendum: Tier-1 sweeps blocking
immediately; Tier-2 (storage/telemetry/enum/ghost in their stack) with an explicit FP
budget, per-sweep summary counts, **and the summaries wired into that repo's gate-yield
record from day one** (the review's §4/§8 clause, restored: promote/retire decisions
come from committed telemetry, not vibes); run the 6b.5 plants at adoption; build the
two missing platforms into the assembly suite (T7 stays open until the real build
includes every platform); report yield at the next calibration cycle. **The
promote/tune/retire decision for each Tier-2 sweep is a dated debt entry** on
`dataflow-sweeps` (owner: david, expiry 2026-09-15) so the pilot cannot silently become
the permanent state — the verdict lands in a successor doc to the review. The same debt
entry carries one more dated line: **"CIVerd upgrade proposal forwarded: y/n"** — the
proposal doc's handoff is a human step, and the documented rot case is a review doc
that flagged a dead subsystem months before the audit re-found it; the line makes the
handoff expire loudly instead of silently.

---

## D. Flow table for THIS plan (dogfooding D2)

| flow (what moves) | producer | consumer (named) | liveness test |
|---|---|---|---|
| §6c doctrine text | SKILL.md | every session (plugin load); vendored repos (installer + refresh prompt VERIFY step) | D11 content-marker test (canonical + vendored) |
| sweep summary lines (`checked/violations/exempted/unresolvable`) | `dataflow_sweeps.py` — run BLOCKING on this repo's own bins via `civerd_gate.sh` (D13a) | suite assertions (test_dataflow_sweeps) + committed per-cycle gate-yield rows + mechanical trend check (D13b) | summary-format pin test; planted grown-share fixture → trend check flags |
| sweep exemption files | repo maintainers | companion check (user-facing → FAIL) + excluded-share audit | planted user-facing exemption → suite RED |
| fifth-class audit findings | `/integration-audit` runs | owners + expiries (registry debt / plan deliverables — existing §12 machinery) | D15 calibration scenario (plan-omits-consumer plant) |
| escape-class rows | audits/excavations (§13 line) | next-cycle grade + mechanism decisions (quarterly bundle reads them) | quarterly.md clock already enforced (`check_staleness --max-age-days 100`) |
| flow-granularity refute prompts | `integration-adversary` brief | plan authors at §0 close (mandatory dispatch, existing rule) | D16 live-calibration rows in history.md |
| Cheliped pilot yield data | Cheliped Tier-2 sweeps | promote/tune/retire verdict (successor doc) | dated debt on `dataflow-sweeps`, expiry 2026-09-15, `--as-of` proven |
| CIVerd upgrade proposals | `docs/recommendations/civerd-dataflow-liveness-upgrades-2026-08.md` | David → CIVerd engine backlog (cross-repo) | forwarding tracked by the D19 dated debt line ("forwarded: y/n", expiry 2026-09-15); ADOPTION stays CIVerd's call — not this repo's debt (stated, not implied) |

No row ships with an empty consumer cell.

## E. Deploy surface (the vendored copies run where this session doesn't)

- *Runs where:* every repo carrying vendored `.claude/bin` + local marketplace plugin
  installs.
- *Gets there how:* `scripts/install_into_repo.py` (reconciling) / `claude plugin update
  tdd-playbook@david-tools`. No hand-pasting.
- *Verified how:* `install_into_repo.py --doctor` version stamps (existing mechanism —
  the H8 guards-liveness check); scratch-repo parity in the release gate proves the new
  bin + markers vendor correctly BEFORE the tag exists.
- *Divergence:* doctor flags skew loudly; the stale-Cheliped-copy incident that produced
  this proposal's §6b collision is the documented failure mode — D19's refresh closes it.

## F. Tripwire plan

Full Tripwire (multi-deliverable): each of D1–D13 gets BUILT + WIRED + ACTIVATED +
EXERCISED rows anchored to this plan; report `Tripwire: N/N (+ FLOWS 8/8)` using §D.
Classification: **D1–D13, D17–D18 DIFF-VERIFIABLE** (paths/tests runnable here) ·
**D14 DIFF-VERIFIABLE** (plants in-suite) · **D15–D16 EXTERNAL-STATE** (probe:
`history.md` rows + corpus `approved/` entries — named, dated) · **D19 CROSS-REPO**
(cite: Cheliped refresh commit + pilot report; how checked: the successor-doc verdict).
RUNNING leg: not applicable to this release beyond the standing CIVerd verdict (the
engine echoes the release SHA — existing `R-DEPLOY` machinery covers it).

## G. Adversary loop closure (§0 mandatory — this plan adds gate surfaces)

Both adversaries dispatched fresh-context, refute-framed, plan-review mode, at the
doer's model tier (§13 verifier-strength: pins raised to match the doer). Verdicts on
the FIRST draft; every finding below is folded into the deliverables above (none
rejected):

**integration-adversary — `Verdict: ISLANDS (3)`** (first draft):
1. *Self-sweep island (worst):* Tier-1 declared "mandatory where the flow kind exists"
   while no deliverable ran the sweeps on THIS repo — whose own bins carry literal
   `.format(` render sites — so the D13 checklist consumer read summaries nothing
   produced. **Folded → D13(a):** blocking self-sweep invocation in `civerd_gate.sh`.
2. *Unowned engine-handoff edit:* the `civerd-integrity.yml` plant_targets line had no
   owning deliverable and no Tripwire row. **Folded → D12(c).**
3. *Vendored adoption gap:* the CLAUDE.md refresh prompt's ADOPT block (the canonical
   downstream adoption surface) gained no §6c instruction — non-Cheliped repos would
   receive the bin with ACTIVATED unstated. **Folded → D11.**
   Minor: the CIVerd-proposal human handoff got a dated "forwarded y/n" line (→ D19).

**architecture-adversary — `Verdict: MIXED (7)`** (first draft):
1. *Wrong seam / reuse miss:* excluded-share audit as a CLAUDE.md prose line — the
   pre-F5 "remembers" class, and the review's own gate_yield clause dropped. **Folded →
   D13(b)** (committed rows via gate_yield machinery + mechanical trend check) and
   **D19** (clause restored for the pilot).
2. *Duplication:* a fourth dated-exemption shape with no expiry teeth. **Folded → D10**
   (house `{what/target, owner, expires}` schema; expired → RED; `--as-of` provable).
3. *Gate-by-proxy (their top recommendation):* companion rule keyed on
   `capabilities.json` surfaces — which are deployment hosts, so the check fires on
   everything or nothing. **Folded → D12(b):** new capability-level `user_facing`
   attribute; the companion rule keys on the fact, not a proxy.
4. *Tier mislabel:* ghost-gates shipped in the Tier-1 floor while classified Tier 2.
   **Folded → D10:** advisory by default, `--strict` opt-in, promoted only on the D19
   pilot verdict.
5. *Overlapping taxonomy:* class 5 double-homed findings with classes 2 and 4,
   corrupting D6's repeat-class metric. **Folded → D7:** explicit partition boundary.
6. *Conflated exit code:* vacuous-refusal sharing exit 2 with usage errors, against
   "exit 2 is usage, never proof". **Folded → D10:** 0/1/2/3, vacuous = 3, pinned in
   D14 tests.
7. *Marker home:* SKILL needles split into `test_installer` instead of the house
   doctrine-pin suite. **Folded → D11:** needle in `test_agents.py`; ONE rewrite-aware
   vendored-equality assertion in `test_installer`.
   Lead folded: §6a companion rule cross-referenced, not restated verbatim (→ D1).

`Loop closed: yes` — both adversaries dispatched; 10 findings + 2 minors, all folded
above, none rejected. (Adversary-verified-clean, for the record: `dataflow_sweeps.py`
has no prior art in the tree; §6c-as-new-section vs sharpening-§6a is correctly
seamed; registry granularity holds; forced-line contracts untouched; the summary-line
format matches house style.)

## H. What this plan explicitly does NOT do

- No per-field/per-value flows in `capabilities.json` (the registry stays small;
  R-DUP/R-WRITE-ONLY already cover capability granularity — verified against
  `capability_registry.py`).
- No renumbering of existing SKILL sections (rule d).
- No Tier-2 sweep implementations in the universal floor this release (pilot first —
  the promote decision is dated debt, not a hope).
- No changes to adversary forced-line contracts (calibration oracles anchor on them).
