# 2026-08-17 — the holdout sha chain, and mutation's attribution blind spot

Two unrelated spans, planned together because one was discovered while gating the other.

D1 is a **blocking production fix**: the holdout approve path wrote a validation manifest whose
candidate sha could never match the body it authorized, and `holdout run` aborts on that. It
surfaced today because `MANIFEST_REQUIRED_SINCE = "2026-08-17"` is today's date — the reader that
exposes the defect activated this morning, on a repo whose gate was green yesterday.

D2 folds in a field report from a Codex build (`codex/gate-honesty-p1`, 2026-08-17) about mutation
gates, sandboxed runs, and long-run evidence.

## D0 — how the defect was found (worth recording; it is the argument for both deliverables)

The blessed gate went RED on a clean tree. The failure was *proven* pre-existing rather than
assumed: a detached worktree at HEAD, caches cleared, on Python 3.11 and 3.14, failed identically
(`571 passed, 1 failed`). CI was **green on the same sha** (run 31969034651). Both were telling the
truth — the date gate had not yet activated when CI ran.

That divergence is the finding underneath D1. A check whose activation is a hardcoded future date
is green on the day it ships and cannot be observed failing until the date arrives, so the defect
it guards against ships with it. §13 already says a guard is unverified until replayed against its
motivating artifact; a date-gated guard cannot be replayed at authoring time at all unless the
clock is injected.

## D1 — the manifest ↔ body sha chain (BLOCKING)

**Defect.** `cmd_approve_holdout` computed the manifest's `candidate_content_sha256` from the
**proposed/** file (`holdout.py:770`, `body_path=src`), TOCTOU-checked *that* file, persisted the
manifest, and then re-dumped the body into `bodies/` with `json.dump(sc, indent=2)` — different
bytes. The register recorded the *new* sha (which is why the register round-trip test passed and
only the manifest check failed). `vault_integrity_problems` then compared manifest sha against body
sha and reported the vault stale; `run_holdout` ABORTS on a stale vault.

**Why it stayed invisible.** `cmd_author_holdout` already wrote proposed bodies in exactly the
canonical form (`indent=2` + trailing newline) — the same literal, duplicated. So machine-authored
bodies matched *by luck of the duplication agreeing*, and only a hand-authored or reformatted
proposed body diverged. The flow invites exactly that: `holdout author` prints "review the file,
then: holdout approve".

**Fix.** One owner for the byte-form: `holdout.write_body(path, sc)`. `approve` canonicalizes the
proposed file *through it, before validating*, and lands the body through it too, so the bytes the
verifier measured are byte-identical to the bytes that land. `cmd_author_holdout` uses it as well,
retiring the third copy. This closes the identity chain rather than restamping the manifest with
the destination sha — restamping would make the check green while asserting the manifest covers
bytes the verifier never saw.

**Deliverable → test.** `test_harness.py` D1.c gains a named invariant: the manifest's candidate sha
IS the landed body's sha, exercised through a deliberately NON-canonical proposed file. Red-first
verified against `656eff5` (two differing shas printed), green after. The defect shape is frozen in
the test's comment citing the pre-fix sha (§13).

**Integration surface.** consumes: `proposed/<id>.json` bytes · emits: `bodies/<id>.json` +
`manifests/<id>.json` → consumer `vault_integrity_problems` (`holdout.py:175` reads
`candidate_content_sha256`) → consumer `run_holdout` (aborts on a non-empty problem list) ·
surface parity: all three write sites of the body byte-form now route through one owner ·
activation: live on the next `holdout approve`; no migration needed for bodies approved before
2026-08-17, which the date gate grandfathers.

**Not done here, stated rather than assumed.** Bodies already approved on/after 2026-08-17 from a
non-canonical proposed file carry a stale manifest that this fix does not retroactively repair —
`holdout validate` re-runs the gate and rewrites it. No such body exists in this repo (there is no
vault here); a private vault is David's to check.

## D2 — the Codex field report (doctrine)

The report's "preserve" list was already doctrine: §4a carries green baseline, positive executed
count, mechanical kill-test collection, `0 survivors ≠ pass`, and `killed + survived < generated →
UNMEASURED`. Its two prevented false greens are the first EXTERNAL evidence those rules work, on a
host they were not written for — recorded as an origin citation, because that is how a §-section
defends itself against a later prune.

What was genuinely missing:

1. **§4 — the attribution blind spot.** A behavior exercised only by spawning a fresh process is
   unmeasurable by mutation on any tool: no coverage tracer attributes child-process work to the
   parent test (889 generated / 0 executed, Codex `7e1f4539`/`fad338eb`). §4a's accounting rule
   CATCHES it; the fix is test shape, not tooling.
2. **§8 — the in-process twin.** Keep the fresh-process test (the real seam, and the only proof the
   executable runs) and ADD a twin driving the same public function. Latent here: every guard
   behavior in `test_hooks.py:52` shells out, so any guard placed on a mutation roster would
   reproduce 889/0 exactly. Not fixed in this span — no mutation tool is configured in this repo, so
   twins would be ceremony for a gate that does not exist.
3. **§4a — "baseline green" means green in the tool's REWRITTEN tree**, which is a different fact
   from green at HEAD; plus a preflight ordering (the same assertions, run first, cost seconds
   instead of a discarded 40-minute pass) and the duplicate-`paths_to_mutate` trap.
4. **§4a/§12 — a doctrine collision, named.** §12 tells you to assert on AST nodes for absence
   claims; those exact tests are structurally unsatisfiable against a mutation tool's rewritten
   modules. Two correct rules colliding — resolved per-test, never per-module.
5. **§7 — an environment restriction is never a reason to weaken a test**; offline enforced before
   collection; a hang must yield a stack.
6. **§12 — evidence you cannot re-read is not evidence.** Promotes what the release gate already
   does (`> /tmp/gate.out 2>&1`) into doctrine, after a Codex full-suite run was lost to a context
   compaction boundary.

**Host disposition — the report's own suggestion, declined.** Codex proposed a Codex-specific
addendum. Almost none of its runtime content is host-specific: sandboxes, libraries that phone home,
and lost long-run buffers apply to every host. Written host-neutrally into §7/§12, it reaches Codex
through the vendored SKILL (`install_into_repo.py:44` copies `skills/tdd-playbook` for both hosts).
A Codex-branded addendum would have gone in `commands/` or `agents/`, which are `unavailable` on
Codex under the standing `test-lock/codex-command-agent-discovery` debt — dark on the exact host it
was written for. No new surface, and no new debt on top of dated debt.

**Deferred, deliberately.** The `mutation-runner` brief edit is dropped from this span. `agents/` is
EFFECTFUL in the calibration ledger, so `expect: none` is unavailable there, and the one scenario
covering that agent (`shadowed-import-vacuous-suite`) measures shadowed imports — my preflight
additions would not plausibly move it. Registering `expect: up` against it would be satisfying the
instrument rather than using it. The brief change belongs with a plant+control pair authored for the
child-process attribution shape.

## Verification

- `sh scripts/civerd_gate.sh` green (unpiped, exit code captured).
- D1 red-first proven against `656eff5` in an isolated worktree before the fix.
- `calibration/ledger.py check` clean: SKILL.md and `commands/` are in SURFACE_PATTERNS but out of
  EFFECTFUL, so the doctrine change registers as an INERT coverage entry (`expect=none`), per the
  2026-08-14 decision and the L-20260816-02 precedent.
