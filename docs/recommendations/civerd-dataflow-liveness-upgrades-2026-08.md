# Proposal to CIVerd: dataflow-liveness upgrades — 2026-08

**From:** the tdd-playbook repo (the §6c Dataflow Liveness adoption,
`docs/recommendations/dataflow-liveness-amendment-review-2026-08.md` +
`docs/plans/dataflow-liveness-implementation-plan-2026-08.md`).
**To:** CIVerd engine backlog — for consideration, on CIVerd's own plan discipline.
**Status:** PROPOSAL. Nothing here is a commitment on the engine; adoption, sequencing,
and design are CIVerd's call. Items are ordered by value to the repos CIVerd protects.

**Context in one paragraph.** A downstream excavation (Cheliped, 2026-08-03) found the
node-level wiring net perfect on its home turf while all 12 post-safeguard escapes were
**edge** failures — flows produced with no live consumer, values accepted with no
reader, fixes verified at the supply end. The playbook is adopting an edge discipline
(§6c: every flow names a live consumer; migrations prove parity for the replaced seam;
"wired" claims are proven at the output end; health checks declare evidence tiers). The
same lens, pointed at the CIVerd machinery we lease trust from, surfaces the upgrades
below. Several are questions as much as proposals — repo-side we can only see our end of
the wire, and per §12 we flag what we could not verify rather than asserting it.

**Standing constraint honored throughout:** everything engine-side stays **root-owned
with no agent write path** (repos.yml, plant recipes, baselines, decomposition — trust-
floor contract). Every proposal below is read-only from the repo side: new *echoes* and
*fields*, never new agent-writable inputs.

**CORRECTIONS (2026-08-03, from the engine session's review — applied inline below):**
(a) the cross-validation corpus path is
`plugins/tdd-playbook/tests/fixtures/civerd_crossvalidation_corpus.json` (the original
cited a wrong relative path); (b) the sweep's real path in this repo is
`plugins/tdd-playbook/bin/dataflow_sweeps.py` (`.claude/bin/…` is only where downstream
repos receive the vendored copy); (c) the engine reads NOTHING from this repo as
configuration — root config only — so `civerd-integrity.yml` is this repo's DECLARATION
of its gate/targets, mirrored into root config by David, never a live config seam. Item
2's open question was answered engine-side with evidence (a dropped check yields a green,
accepted verdict), making the repo-side roster pin the primary deliverable — shipped in
this repo 2026-08-03 (`verify_verdict.py` EXPECTED_REQUIRED/EXPECTED_PRESENT). Item 5's
`dataflow` check went LIVE in root config the same day. Items 1/2's engine-side transport
(`snapshot.armed`, `checks_expected`) is explicitly NOT coming soon — the snapshot schema
is closed by design; nothing in this repo may wait on those fields.

---

## 1. Armed-surfaces echo — output-end proof for `repos.yml` arming ⭐ highest value

**The dangling edge, in our own registry today** (`capabilities.json`,
`plan-authoring.deploy_surface.divergence`): *"if repos.yml is never armed, plans land
INERT: release_verify keeps consuming verdicts with no plan predicate — the pipeline
reads as live while enforcing nothing."* That is a textbook supply-side-verified wire:
we can prove plans are authored, conformant, and pushed; we cannot prove the engine
*enforces* them. The current mitigation is a dated debt entry and David's memory.

**Proposal:** the engine exposes, per watched repo, an **armed-surfaces echo** — the
globs/checks it is actually enforcing for that repo (plan_globs, integrity_globs, check
roster). Preferred transport: a field inside the signed run verdict (`snapshot.armed`),
so it rides the existing ledger with the existing signature and freshness semantics —
no new endpoint, no new trust surface. Repo-side, `verify_verdict.py`/doctor compares
the echo against the repo's expectation and reports **ENFORCING / AUTHORED-BUT-INERT**
per surface. Dark arming becomes a red doctor line instead of a memory.

This is the engine-side twin of the version-echo rule the playbook already lives by
("running == intended", §6a): *enforcing == intended*.

## 2. Check-roster pinning — scheduled-vs-recorded for the engine's own checks

**The question first (we could not verify this from the repo side):** if a check is
silently dropped from the engine's configuration — or a config edit stops scheduling it
— does the next verdict go red, or does it arrive green with a shorter `checks[]` that
`may_release` still accepts? Repo-side we verified our verifier's ledger/signature/
freshness handling, but we found no repo-side pin of the *expected roster*.

**Proposal (if the answer is "shorter roster still passes"):** two small interlocking
pins. Engine-side: the signed verdict carries `checks_expected` from root-owned config,
and a run whose executed set ≠ expected set is RED with its own reason string (a check
that dies must fail loud, not vanish). Repo-side (our work, listed for symmetry): the
vendored verifier pins the roster it requires for a release and refuses a verdict
missing any of it. This is the excavation's absence-blind-monitor finding applied to
the monitor we trust most: *dead and quiet look identical from the run side* — a check
that stops being scheduled leaves no row.

## 3. Verdict-schema field liveness — T2 applied to the verdict itself

Every field the engine signs into a verdict should have a **named consumer** in the
reference verifier or the cross-validation corpus
(`plugins/tdd-playbook/tests/fixtures/civerd_crossvalidation_corpus.json` / memrebel's
golden bundle). A
signed field nobody reads is a write-only flow with signature costs; worse, it *looks*
load-bearing to the next maintainer. One-time sweep + a corpus rule ("new verdict field
⇒ new consumer case in the corpus, or a dated exemption naming the future consumer").
Cheap, and it keeps the verdict schema honest as it grows.

## 4. Evidence tiers declared per check

§6c introduces a tier vocabulary for health/verification surfaces:
`config-read < import < runtime-probe < composition-root`, with the rule that
**import-existence alone can never render OK** (the excavation found three health checks
green-lighting ~1k LOC of provably unreachable code on import-success). Proposal: each
check in a signed verdict declares its tier, so consumers can weight trust and the
scoreboard can show at a glance which greens are composition-root-grade and which are
config-reads. Also a useful forcing function internally: a check that can only claim
`import` tier is a check with a known upgrade path.

## 5. A `dataflow` check class on the engine timer

The repo-side declaration already has the right shape: `civerd-integrity.yml` states the
repo's gate + plant targets (a DECLARATION David mirrors into root config — the engine
reads nothing from the repo as configuration; see CORRECTIONS above). Proposal: repos
declare Tier-1 dataflow sweep commands the same way (in this repo:
`python3 plugins/tdd-playbook/bin/dataflow_sweeps.py all --config dataflow-sweeps.json`;
downstream repos run their vendored `.claude/bin/` copy), mirrored into root config as a
named `dataflow` check on the engine's timer —
so edge liveness is attested by the independent engine, not only by the working agent's
own suite run. Cost: one config key + a runner slot; the sweeps themselves are repo-side
and already exiting 0/1/2. (If folding into `suite_cmd` is judged sufficient, the named
check is still worth it for scoreboard legibility — a `dataflow: RED` row says what a
generic suite failure cannot.)

## 6. Planted-edge probes in the `planted_probe` rotation

The engine's `planted_probe` already proved its worth (its first firing caught a real
`capability_registry` gap). Proposal: extend the root-owned plant recipes with edge-class
plants against the new sweeps — a template key with no placeholder, a ghost
`getattr(cfg, "x_enabled", True)`, an exemption whose prose contradicts the artifact —
asserting the repo's dataflow gate goes RED. This gives the new gates the same
engine-side calibration the integrity floor has: a net nobody has watched catch a plant
is theater, and repo-side plants alone are visible to the agent being checked.
`dataflow_sweeps.py` joins our `plant_targets` list in the same release (repo-side diff,
already in the implementation plan).

## 7. Seam-parity DoD for engine migrations

The strongest single lesson from the excavation: one *successful* migration produced 5
of the 12 escapes, because "new path works" was the whole DoD and nothing enumerated
what the old path FED. CIVerd already practices the strong form in one place — the
memrebel golden corpus pins canonicalization + reason-string parity against the
reference implementation. Proposal: generalize that practice into the engine's own
migration DoD — any component replacement ships an enumeration of the old seam's
outputs (hooks fired, fields populated, rows written, cleanups performed) with each one
fed / retired-with-deletion / dated debt, pinned by a parity fixture. For an engine
whose product is *trust*, an orphaned consumer (say, a ledger field the old writer
populated and the new one silently doesn't) is a defect class worth pre-empting at DoD
level, not discovering at excavation level.

## 8. Registration uniqueness — ban last-write-wins in engine registries

Small and cheap: wherever the engine keeps name→handler registries (checks, repos,
verdict reason codes), duplicate registration RAISES at load. The excavation's `/plan`
registered-twice escape shipped behind a membership test; uniqueness-at-registration is
a one-line invariant that closes the class permanently. (Repo-side, our
`capability_registry.py` already enforces this as `R-DUP` — parity, not novelty.)

---

## Cost honesty & sequencing suggestion

Items 3, 4, 8 are one-time sweeps or one-line invariants. Item 1 rides the existing
verdict/signature path (a field, a comparison, two doctor strings). Item 2 is a small
schema + reason-string addition, but touches release semantics — it deserves CIVerd's
own red-first pass and a cross-validation corpus update. Items 5–6 are config-key +
runner-slot work on machinery that already exists (`suite_cmd`, `planted_probe`).
Item 7 is a discipline, not code — adopted at the next engine migration, when the seam
knowledge is freshest.

If only one item is taken: **item 1**. It converts the one place where our shared
pipeline currently *reads as live while enforcing nothing* into a mechanical red line —
which is the entire thesis of the dataflow-liveness amendment, applied to the trust
machinery itself.

**Claims: 6 load-bearing repo-side claims · 6 verified (capabilities.json divergence
note; civerd-integrity.yml suite_cmd seam; R-DUP in capability_registry.py; plant_targets
list; verify_verdict.py ledger/freshness handling; the planted_probe first-firing record
in capabilities.json) · engine-side behavior (items 1, 2, 5, 6 internals) explicitly
NOT verified from this repo — framed as questions/proposals, not findings.**
