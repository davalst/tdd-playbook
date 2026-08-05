# Proposal to CIVerd: seam-contract (self-consistency test) support — 2026-08

**From:** the tdd-playbook repo (the v1.26 seam-contract adoption — SKILL §1 "Test at the
seam you don't own", §4 mutation-score limitation, §6c family parity sweep;
origin proposal: Cheliped, `PLAYBOOK_PROPOSAL_seam_contract.md`, 2026-08-04).
**To:** CIVerd engine backlog — for consideration, on CIVerd's own plan discipline.
**Status:** PROPOSAL. Nothing here is a commitment on the engine; adoption, sequencing,
and design are CIVerd's call. Scoped deliberately small: ONE engine ask (item 2), one
root-config action that needs no engine work (item 1), and the repo-side precondition we
owe first (item 0).

**Context in one paragraph.** Cheliped shipped two commands (`/runmode`, `/apps`,
2026-08-04) that passed every gate and did nothing visible: handlers *returned*
`CommandResult(message=...)` while the adapter contract was `ctx.post_message(...)`, and
the tests asserted on the *returned* value. Implementation and tests shared the same
wrong belief about the seam — a test cannot catch a mistake it also makes. Red-first was
honestly red; mutation score would be 100% (mutant and assertion sit on the same side of
the misunderstood seam); registration-level wiring evidence was real. The playbook's
v1.26 answer is doctrinal (a §1 test-shape rule reviewable by eye) and mechanical (the
§6c **family parity sweep**: one repo-local test per pluggable family — command handlers,
hooks, adapters, middleware — that enumerates the family from the REAL registry and
asserts the host's contract for every member, with a MANDATORY vacuity guard on the
enumerator count). What makes this class CIVerd-relevant: **every repo-local guard for it
is written by the same mind that holds the wrong belief, and lives in the doer's write
zone.** The parity sweep is precisely the test a doer most plausibly weakens *honestly* —
or writes vacuously (the origin author's first parity sweep imported a registry accessor
that did not exist; only the count assertion surfaced it). Third-party integrity is the
one property the local suite cannot supply.

**Standing constraint honored:** everything engine-side stays **root-owned with no agent
write path**. Both items below are read-only from the repo side. Reconciled against the
2026-08-03 corrections in `civerd-dataflow-liveness-upgrades-2026-08.md`: the engine
reads NOTHING from this repo as configuration — repo files are DECLARATIONS David mirrors
into root config; non-Python surfaces are armed via the integrity FLOOR, not globs.

---

## 0. Repo-side precondition (our work, listed for symmetry — not an engine ask)

A **parity-sweep registration surface**: a config key (planned home:
`dataflow-sweeps.json`, a `family_parity` section listing each family-parity test file
and the registry it enumerates). Today no artifact says "these files ARE the parity
sweeps," so neither the integrity FLOOR nor any future check can distinguish them from
ordinary tests. This key is the earliest seam for both items below and is repo-side by
construction. Ships as v1.26 follow-on work (dated debt in `capabilities.json`,
`TIER-2 FIELD-PAIRING SWEEP` entry carries the sibling machinery decision).

## 1. Root-config action, David — no engine feature needed

**Arm the family-parity test files as protected surfaces.** The mechanism already
exists and is already exercised for this repo's release-trust surface (armed 2026-08-03:
Python surfaces per-file, non-Python via the integrity FLOOR — *not* globs; that
correction is on record). The deliverable is a roster line in root config on srv1621832
adding the registered family-parity test files (from item 0's key, once it exists;
`plugins/tdd-playbook/tests/test_agents.py` — this repo's own family sweep over
agents/commands — qualifies today). Weakening, emptying, or deletion of an armed parity
sweep then flags engine-side in the signed verdict, outside the doer's write zone.
**Owner: david · tracked as the `SEAM-CONTRACT RECOMMENDATION FORWARDED` debt entry on
`civerd-release-gate` (expires 2026-09-15).**

## 2. The one engine ask — a parity-sweep VACUITY check class

**The gap, precisely:** the integrity FLOOR protects a parity sweep's *existence and
text*. It cannot see the failure mode the origin incident documents: a sweep whose
**enumerator silently returns empty** (renamed registry accessor, mis-globbed listing,
dropped import) passes green having tested nothing — the file is intact, the suite is
green, and the family is unguarded. Repo-side vacuity guards (count assertions) close
this — but they are themselves repo-side text the doer can weaken to `>= 0`, and the
playbook's own dogfood audit (v1.26, finding G5) found its own family sweep shipped
without one.

**Proposal:** a `seam_parity` (name yours) check class on the engine timer, per watched
repo with a registered parity roster (root-owned, mirrored from item 0's declaration):
for each registered parity sweep, the check asserts **(a)** the file exists and collects
at least one test (existing floor semantics), and **(b)** a **non-vacuous enumeration**:
the sweep's count assertion exists and is not trivially satisfiable (`>= 0`, `> -1`,
comparison against a literal the same file defines). Result rides the existing signed
`checks[]` with its own reason strings — a vacuous parity sweep is RED with a named
reason, never a shorter green roster. Design of (b) is the engine's call: static
detection of a degenerate lower bound is Tier `import`-grade and already valuable;
a runtime probe (run the sweep against an emptied registry double and require RED) is
composition-root-grade and matches the evidence-tier ladder proposal already in the
2026-08 dataflow recommendation (item 4 there).

**Calibration requirement (trust-direction rule, standing):** the check is unproven
until a `must_fail` probe is green on the real host — extend the root-owned
`planted_probe` recipes with a seam-contract plant: a return-only handler + a
return-asserting test + a parity sweep whose enumerator returns `[]` with a `>= 0`
guard; the check must go RED on the plant. A net nobody has watched catch a plant is
theater. And the standing trust question applies before design: **can the untrusted zone
write the trusted output?** — the parity roster must be root-owned (mirrored by David),
never read live from the repo.

## Non-goals (explicit)

- CIVerd does **not** implement the parity sweeps — they are repo-local by construction
  (a generic scanner cannot enumerate arbitrary registries; only the repo's own test can
  import the real one).
- No LLM-judged gating anywhere in this proposal.
- No new bypass or predicate on the release-verdict path; `may_release` semantics are
  untouched. This adds a check class, not a release gate change.
- No new agent-writable engine input (the roster is root-owned, like plant recipes).

## Report-back contract

What this repo will record on receipt (the `SEAM-CONTRACT REPORT-BACK` debt entry on
`civerd-release-gate`, expires 2026-09-15, replaced by the answers): **(a)** adopted
y/n/deferred per item, **(b)** the check-class name as it appears in signed `checks[]`,
**(c)** the root-config surface the roster lives in (so this repo's docs can tell
downstream repos what to declare), **(d)** any correction to this proposal's model of
the engine — inline, the way the 2026-08-03 corrections were recorded. Claims made from
the repo side of the wire after adoption cite the signed `checks[]` rows, never engine
status prose.

---

**Claims: 5 load-bearing repo-side claims · 5 verified (the Cheliped incident narrative
against the origin proposal doc; the 2026-08-03 armed-surface record + "not globs"
correction in `civerd-dataflow-liveness-upgrades-2026-08.md:38-45` and
`capabilities.json` civerd-release-gate notes; the G5 dogfood finding — this repo's
`test_agents.py::test_commands` family sweep lacked a count assertion until v1.26; the
absence of any parity-sweep registration surface — swept `dataflow-sweeps.json` +
`capabilities.json` + `civerd-integrity.yml`, no key names parity-test files; the origin
sweep's vacuous-enumerator anecdote is quoted from the proposal doc §4c) · engine-side
internals (check-class plumbing, `planted_probe` recipe format, floor semantics beyond
the recorded contract) explicitly NOT verified from this repo — framed as proposals and
questions, not findings.**
