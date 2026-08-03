# Review: the Cheliped "Dataflow Liveness" amendment proposal

**Date:** 2026-08-03 · **Prepared as:** CTO / senior-dev / QA-expert review, plain language
**Reviewed against:** SKILL.md as of v1.23.0 (HEAD of `main`), `capabilities.json`,
`/integration-audit`, the agent briefs, CLAUDE.md release discipline.
**Input:** `TDD_PLAYBOOK_AMENDMENT_DATAFLOW_LIVENESS.md`, submitted from the Cheliped repo's
2026-08-03 full-repo excavation (671 files / 184.5k LOC, 92 verified findings, 12
post-safeguard escapes, all twelve edge-class).

**Evidence caveat (§12):** the case study's numbers live in the Cheliped repo and are
SECONDHAND here — taken at face value as David-submitted; nothing in this repo verifies
them. The doctrinal assessment stands on the playbook's own text either way.

---

## 1. Executive verdict

**Adopt the doctrine now; stage the mechanisms by decidability.** The proposal's central
claim is correct, important, and — rarer — *earned the hard way*: the wiring net was run at
full depth on a real 184k-LOC codebase and went perfect on its home turf (nodes) while
every escape was an edge. That is not a criticism of the net; it is the net working well
enough to expose the next stratum. §13 calls this co-evolution; this proposal is the first
time a DOWNSTREAM repo has fed a validated gap back into the floor, which is exactly the
flywheel the playbook was designed to have.

But "adopt" splits three ways, and a flat merge would be a mistake:

| Decision | Items | Why |
|---|---|---|
| **Merge into doctrine now** | Migration consumer-parity DoD (6b.3) · output-end proof + evidence tiers (6b.4) · flow table in §0, scale-gated (6b.1) · escape-class tracking in §13 · the two *decidable* sweeps (render pairing, registry uniqueness) | Zero or near-zero false-positive cost; each closes a class nothing else touches; cheap forever |
| **Adopt as doctrine, pilot the mechanism in Cheliped for one calibration cycle before it joins the universal floor** | The heuristic sweeps: storage pairing, telemetry pairing, enum-value readers, ghost gates, exemption-prose, scheduled-vs-recorded | These are static-analysis heuristics maintained as tests; their false-positive economics are unproven, and a sweep that cries wolf grows an exemption list until it becomes the darkness hatch §6a warns about. Prove the FP rate where the flow kinds actually live, with yield instrumentation, then promote |
| **Correct before merging** | Section numbering (§6b is taken) · the "12/12" framing · the under-credit table in §2 below | Accuracy of the diff, honesty of the evidence |

One structural note up front: **the proposal was written against a stale copy of the
playbook.** §6b already exists (v1.2x, "Onboard, don't hide" — the default-OFF onboarding
contract), and several "why the current net missed it" cells describe doctrine that has
since landed. The new material lands as **§6c**. This is itself a finding with teeth:
Cheliped's vendored `.claude/` is behind — run the standing refresh prompt there, and note
that the very drift that produced this misdiagnosis is the class `install_into_repo.py
--doctor` exists to catch.

## 2. Placing the proposal in the discipline — what it actually is

A senior reviewer should name the thing: **the proposal is def-use / liveness analysis from
compiler theory, applied at system granularity and maintained as tests.** Every class maps
to a known static-analysis or contract-testing concept, which is *good news* — it means the
classes are principled, not artifacts of one codebase:

- **T2 (written, never read)** is *dead-store detection* lifted from registers to
  tables/events/fields. Industry has point tools for the code-level version (vulture,
  knip, ts-prune); nobody ships it at the data/telemetry level as a standing gate, which
  is precisely why the escapes lived there.
- **T4 (value accepted, no reader)** is *value-level* def-use — a lattice refinement of T2.
  It is the sharpest item in the proposal, and its severity call is exactly right: a
  risk-gated flip that no-ops is **worse than no switch**, because the ceremony
  manufactures confidence. The full risk apparatus fired, reported ON, and changed
  nothing. That is a false-green at the *governance* layer, the most expensive place to
  have one.
- **T5 (input-end verification)** is the *tracer-bullet / sentinel* pattern: the only proof
  of a pipe is a marked value observed at the far end. The `str.format` instance
  generalizes (see §5 below) — Python's `format` silently ignores surplus kwargs, so the
  supply side can be "fixed" forever without a reader ever existing.
- **T6 (registry collision)** is a missing *idempotence invariant* on registration.
  Last-write-wins registries are a known landmine in plugin systems; the fix (raise on
  duplicate) is a one-line invariant, not a test.
- **6b.3 (consumer parity)** is *consumer-driven contract testing* (the Pact discipline)
  turned inward, applied at the strangler seam. The strangler-fig literature has always
  said the migration ends when the old path's obligations are discharged; what practice
  ships is "new path green." The proposal's DoD — enumerate everything the old seam FED;
  each consumer fed, retired-with-deletion, or dated debt, pinned by a parity test —
  is the missing enforcement, and one refactor producing 5 of the 12 escapes is exactly
  the incidence rate that pattern predicts.
- **T7 (event never fired on a surface)** and the absence-blind-monitor discovery are both
  instances of the audit's founding observation — *dead and quiet look identical from the
  run side* — which §6a already enshrines. These are extensions of an existing principle
  to two new places (per-surface event matrices; the monitors themselves), not new
  principles.

The proposal's cost claim also survives scrutiny: every mechanism is a static sweep or a
one-time test. No runtime infra, no model calls, no new registries. The expensive part is
not CPU — it is **false-positive triage and exemption-list governance**, which is where
the staging decision in §1 comes from.

## 3. Where the proposal overstates, and where the current playbook already stands

**3a. "Would have caught 12 of 12" is retrodiction, not evidence.** The taxonomy was
derived from those twelve escapes; a taxonomy that failed to cover its own deriving corpus
would be malpractice. Worse for inference: 5 of the 12 came from one refactor event, so
the effective independent sample is ~8. The classes are still credible — because they map
to known analysis classes (§2), not because of the count. Forward evidence is defined the
way this playbook always defines it: the 6b.5 plants catch at adoption, and the next
excavation cycle's escape count *by class* trends to zero. Quote that, never 12/12.

**3b. The under-credit table.** Corrections so the amendment diffs against reality:

| Proposal's "why the net missed it" | What v1.23.0 actually says | Residual gap (the real one) |
|---|---|---|
| T2: "R-WRITE-ONLY exists at capability granularity" | Correct — `emits[].consumers` + doctor's write-only-emitter inventory are topic-level | Field/table/event-type granularity: **real, adopt** |
| T5: "wired was proven by the supply side" | §1 "assert the outcome, not the proxy" and §12 "trace the wire end-to-end" already state the doctrine in prose | No *mechanical bar* for "wired" claims — the sentinel rule is the missing teeth: **adopt into §12** |
| T6: "registration tests check presence" | §6/§6a's symmetric reachability *through the production composition root* would catch a shadowed handler if "reachable" were proven through real dispatch | In practice membership tests pass; **adopt raise-on-duplicate as invariant + amend §6a: reachable means through the real dispatch order** |
| T7: "per-surface event-parity was untested" | §0 surface parity + §6a assembly suite "per platform" already demand it — Cheliped's assembly suite never built two of its platforms | Downstream implementation shortfall, not a doctrine hole. The flow-row makes it *checkable instead of rememberable*: **adopt the row; fix the suite in Cheliped** |
| Absence-blind monitors | §6a passive liveness ("registered but zero runs in N days") is the same observation | The new content is **monitors record SUCCESS; scheduled-set vs observed-rows; silence goes red** — merge into §6a's existing bullet, don't duplicate |
| T3: eviction/maintenance callers | §4's survivor-reading has caught write-only emitters incidentally; nothing systematic | **Real, adopt** — it is the flow table's "who prunes" column |
| T4: accepted-value readers | Nothing. §6 ACTIVATED validates the *switch*, not each accepted value | **Real, adopt — highest severity of the eight** |
| Ghost gates | §6a's exemption-hatch companion test walks *declared* fields | **Real blind spot, adopt** — undeclared `getattr(config, "x_enabled", True)` is invisible to every declared-field walker |

The pattern in this table matters for how the amendment is written: in five of eight rows
the *principle* already exists and the proposal supplies the *mechanism or granularity*.
Write §6c as sharpening — "the edge-granularity enforcement of §6/§6a" — not as a parallel
discipline. Smaller diff, no ceremony duplication, and the doctrine reads as one system.

## 4. The expert cut the proposal doesn't make: decidability tiers

The eight sweeps are presented as peers. They are not. They split cleanly by whether the
check is *exact* (decidable from the artifact, near-zero false positives) or *heuristic*
(static approximation of a dynamic property, FP rate unknown until measured). This
distinction should be **in the doctrine**, because it dictates governance:

**Tier 1 — exact; mandatory wherever the flow kind exists; failures BLOCK:**
- **Render pairing** (sweep 4): `string.Formatter().parse` enumerates placeholders;
  supplied-keys ⊇/⊆ checks are decidable. FP only on genuinely dynamic templates — rare,
  and a named exemption is honest there.
- **Registry uniqueness** (sweep 5, first half): duplicate registration raises. An
  invariant in the registry itself, not even a test. The reachability half (dispatch
  through real order) is Tier 1 where the dispatch table is data, Tier 2 where it's code.
- **Exemption-prose consistency** (sweep 7): the exemption entry claims "default-on"; the
  default is in the artifact; compare them. Decidable.

**Tier 2 — heuristic; adopt with an explicit FP budget and yield instrumentation; pilot
before joining the universal floor:**
- **Storage pairing** (1) and **telemetry pairing** (2): readers hide behind ORMs, raw SQL
  strings, reflection, BI dashboards, and humans running queries — i.e., *legitimate
  consumers outside the repo's AST*. These sweeps will accrete an exemption list; §6a's
  own doctrine says the exemption list is the single most efficient darkness vector.
  Non-negotiable governance if these ship: the companion-test rule carries over verbatim
  (an exemption naming a user-facing flow FAILS), every exemption names its external
  consumer and how to probe it, and the excluded share is audited over time exactly like
  §4's equivalent-mutant filter — **if the exemption list grows while the sweep stays
  green, the list is doing the work the sweep should.**
- **Enum-value readers** (3): values are compared via variables, tables, and serialized
  boundaries; a naive sweep either misses (FN) or floods (FP). Scope it to *risk-gated*
  enums first — where the T4 incident actually lived and where severity is highest — and
  widen only with yield data.
- **Ghost gates** (6): near-Tier-1 in grep terms, but the `getattr` idiom has legitimate
  uses; expect a short exemption list. Cheap enough to pilot immediately.
- **Scheduled-vs-recorded** (8): needs runtime rows, so it is a *liveness canary*, not a
  static sweep — it belongs inside §6a's existing canary/staleness machinery ("record
  success, not only failure; compare scheduled set vs observed rows; silence goes red"),
  not as a standalone item.

This tiering is also the answer to the maintenance-tax question a CTO must ask: Tier 1 is
write-once, near-zero forever. Tier 2 is a standing analysis product whose upkeep scales
with the codebase's idioms — which is exactly the kind of gate §13's *second decay
direction* (more expensive than the risk it retires) exists to watch. **Wire the Tier-2
sweeps into `gate_yield` from day one** so retirement/promotion decisions are made from
telemetry, not vibes. The proposal calibrates its sweeps for recall (6b.5, credit where
due — it applied the planted-error rule to itself unprompted) but never instruments them
for precision; that is its one real governance omission.

## 5. What the proposal misses — additions a world-class net should carry

Four gaps in the proposal itself, in descending order of importance:

1. **The general class behind T5 is *silent-default reads*, not just templates.**
   `str.format` dropping a surplus key is one member of a family: `dict.get(k, default)`,
   `getattr(obj, name, default)`, `.get()` chains over parsed JSON, protobuf/dataclass
   fields with defaults, `**kwargs` sinks. Every one lets a producer "supply" a value the
   consumer never sees, silently, forever — the edge-level twin of the ghost gate (which
   is the same idiom on the *read* side). The flow-kinds checklist should name
   *silent-default boundaries* explicitly, and the sentinel rule (6b.4) is the universal
   antidote: a marker value observed at the far end pierces every default in the chain.
2. **Cross-repo/external edges.** All eight sweeps are intra-repo. The playbook already
   knows edges leave the repo (`deploy_surface`, version-echo); telemetry consumed by an
   external dashboard or a peer service is a *named external consumer*, and the honest
   mechanism is the same shape as §6a's version-echo: an exemption that names the external
   consumer AND a probe that can confirm it still exists. An unprobed "the dashboard reads
   this" ages into fiction.
3. **Temporal edges.** A producer and consumer can both be live and still never meet:
   retention windows shorter than read cadence, queues whose consumer is dead-lettering
   everything, TTLs that expire before the weekly reader runs. Low incidence, but the flow
   table already has the right slot — the liveness-test column should ask "and do their
   schedules overlap?" for any time-windowed flow. One sentence of doctrine, no mechanism.
4. **Precision instrumentation** — covered in §4 above: the sweeps measure recall via
   plants but nothing measures their FP economics. `gate_yield` wiring closes it.

## 6. Item-by-item disposition (delta from §1's decision table)

- **6b.3 consumer-parity DoD — adopt unchanged; the single highest-value item.** Home:
  §6c, plus one line in §0 making old-seam output enumeration a mandatory plan answer for
  any migration/strangler deliverable. The "leftover references to the deleted mechanism
  are defects, not cruft — they encode a false model for the next reader" rule is
  first-rate and slots into §12's exhaustive-negatives pass.
- **6b.4 output-end proof — adopt into §12** beside the remote-runtime rule (same move: a
  pushed commit is not a running process; a supplied key is not a rendered value).
  **Evidence tiers** (`config-read < import < runtime-probe < composition-root`;
  import-existence can never render OK) — adopt into §6a; it gives §1's
  "outcome-not-proxy" doctrine a rankable vocabulary for health surfaces, and the
  `RuntimeMaxSec` origin story is the same lesson already in the house.
- **6b.1 flow table — adopt, scale-gated** (feature/multi-deliverable/migration work
  only; the ceremony-scaling preamble governs). The flow-kinds list — extended with
  silent-default boundaries and schedule overlap per §5 — is the real asset: a checklist
  of edge types bounded imagination misses. "Empty consumer cell = dated debt or don't
  ship" is already §0 doctrine; the table makes the cell impossible to leave silently
  blank.
- **6b.2 sweeps — per the tiering in §4.** Ship as doctrine (the standing-suite shape each
  repo implements in its own stack, like §6a describes the assembly suite) + a **fifth
  darkness class in `/integration-audit`** ("dangling dataflow", T1–T7 as the hunt list)
  + one flow-granularity refute prompt in the `integration-adversary` brief ("name a flow
  this plan writes that nothing reads; a value it accepts that nothing compares").
- **6b.5 plants — adopt; required anyway** by this repo's release discipline and §13.
  Note the recorded pipeline limitation: corpus plants can only MODIFY existing fixtures;
  the writer-with-no-reader plant may need the `create` capability already flagged as a
  future enhancement.
- **§13 escape-class tracking — adopt.** One line: audits report escapes by class; a
  repeat class across cycles means the mechanism for it isn't real yet.

## 7. What NOT to do

- **Do not extend `capabilities.json` to per-field/per-value flows.** The registry's value
  is that it is small and machine-checkable. Flows live in the plan table (point-in-time)
  and the repo's sweeps (standing); the registry stays capability-level. The proposal
  doesn't ask for this; keep it that way.
- **Do not renumber existing sections.** §6b keeps its name (v1.22 rule (d) treats
  gate-surface renames as journaled events; don't spend that). New section is §6c.
- **Do not merge the Tier-2 sweeps into the universal floor untested.** The playbook's
  credibility rests on gates that earn their keep; enshrining unproven heuristics as
  universal floor is how ceremony-tax accusations become true. One pilot cycle in
  Cheliped, with yield data, then promote.
- **Do not let sweep exemption lists ship without the companion test.** This is the §6a
  lesson applied forward: the sweep's escape hatch must be incapable of hiding a
  user-facing flow.

## 8. Rollout (pending David's go-ahead — this document is review only)

1. **SKILL.md:** §0 (flow table, scale-gated; migration old-seam enumeration), §6 (FLOWS
   rows in the N/N accounting for multi-deliverable plans), §6a (evidence tiers;
   success-recording monitors + scheduled-vs-observed; dispatch-order reachability),
   **new §6c** (doctrine line; sweeps with decidability tiers and FP governance;
   consumer-parity DoD; silent-default boundaries), §12 (output-end proof), §13
   (escape-class tracking). All additions — no `gate-changes.md` entries owed under rule (d).
2. **`/integration-audit`:** fifth darkness class. **`integration-adversary`:**
   flow-granularity refute prompt. Both are gate surfaces → live-calibrate before trusting
   (§13 standing rule; the ~2026-08-10 run is the natural slot).
3. **Mechanical anything** ships with planted tests per release discipline; version bump
   both manifests + CHANGELOG.
4. **Cheliped (the pilot):** implement Tier 1 immediately (blocking), Tier 2 with FP
   budget + `gate_yield` wiring; run the 6b.5 plants at adoption; build the two missing
   platforms into its assembly suite (T7 stays open until every platform is in the real
   build); refresh the stale vendored playbook. One calibration cycle later: promote,
   tune, or retire each Tier-2 sweep from yield data, and land the verdict in this file's
   successor.

## 9. Bottom line

This is the strongest downstream contribution the playbook has received: a real
excavation, honestly birth-dated, that found the net perfect on nodes and blind on edges
— and proposed the edge discipline in the playbook's own idiom (named consumers, dated
debt, planted calibration, output-end proof). Its flaws are the flaws of a good first
draft: written against a stale copy, calibrated for recall but not precision, and
presenting decidable invariants and fragile heuristics as peers. Fix those three things
and §6c makes the wiring discipline whole: **nodes are necessary; edges are the truth —
and now both are enumerable, both are planted, and both decay under instruments instead
of in silence.**

**Claims: 11 load-bearing · 11 verified (all against SKILL.md / capabilities.json /
command + agent text / CLAUDE.md read in this session; the Cheliped case-study numbers
are explicitly secondhand — §12 caveat at top) · 0 demoted.**
