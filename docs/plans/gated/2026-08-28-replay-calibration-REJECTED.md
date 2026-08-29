# §0 TDD plan — commit the replay as a calibration instrument

**Repo:** `davalst/tdd-playbook` @ `01a6af0` (v1.46.0, tagged).
**Status:** PLAN FOR REVIEW. Nothing built.
**Scope:** the replay engine ONLY. `cite_guard` stays `off` and is not touched; the
provenance design is abandoned (three reviews + external research).

## Repo-local conventions found and applied
`sh scripts/civerd_gate.sh` is the one blessed entrypoint, unpiped with `rc` captured ·
hook tests are pytest-free, subprocess-driven, G5 temp-yield isolated · every mechanical
change ships a planted-input test · `capability_registry.py validate` gates the release ·
`calibration/` is NOT vendored by `install_into_repo.py`, so anything placed there stays in
this repo — which is load-bearing for D1's privacy argument, not a convenience.

---

## §0.0 Spec integrity

**The problem, stated as a fact rather than a hope.** Five guards ship `off`. Their own debt
entry (`capabilities.json::advisory-guards-optin`, **expires 2026-11-15**) says: *"RE-READ THE
YIELD BEFORE MAKING THIS PERMANENT… THE THRESHOLD'S UNIT IS BROKEN"* — because v1.32.0 retired
the calibration clock, so "cycles" stopped meaning weeks and the bar silently got ~20× cheaper.
The debt cannot be discharged, because an `off` guard emits no rows: `gate_yield.py:34` —
*"a gate absent from the record is UNMEASURED, never zero."* That is a closed loop. A replay
over historical tool events is the only thing that opens it, and it supplies the missing unit:
**fires per N frozen historical events**, which does not depend on what a "cycle" means.

**Assumption stated, not chosen silently.** This ships as a **calibration instrument**, never
as a finding-delivery channel. Google's FindBugs deployment failed because results went to a
dashboard nobody visited (*Lessons from Building Static Analysis Tools at Google*, CACM 2018),
and a replay report is dashboard-shaped. It informs mode decisions; it never tells anyone to go
fix something.

**The materially simpler alternative, named as the doctrine requires.** Do nothing; let the
debt expire on 2026-11-15 and delete the five guards unread. That is cheaper and legitimate.
It is rejected because deletion-without-measurement is the same unmeasured act as
retention-without-measurement, and the entry explicitly refuses that outcome. **If review
prefers it, say so — "delete the five, no instrument" is a good result, not a failure.**

**Open question for David (do not guess).** The frozen corpus is built from real transcripts
across repos. D1 defaults to THIS repo only. Should the corpus ever include cheliped/civerd
turns — richer data, but other projects' prose on your disk? My default is no; opt-in per repo.

---

## D1 — `calibration/replay_corpus.py`: freeze a corpus, and fix the decode

**What.** Build an immutable, hash-pinned corpus of historical tool events from live
transcripts, so every later number is reproducible against a fixed input.

**Happy path.** `replay_corpus.py build --projects tdd-playbook` → reads
`~/.claude/projects/*/*.jsonl`, resolves each session's project root **from the `cwd` field
inside the session records**, extracts tool events + turn boundaries, writes
`calibration/corpus/replay/<name>.jsonl` (**gitignored**) plus a **tracked**
`<name>.manifest.json` carrying `{sha256, n_sessions, n_turns, n_events, per_project_counts,
built_at, tool_version}` — counts and a hash, never prose.

**Why the decode must be fixed first.** The current script infers the root by inverting the
folder name (`"/" + basename.lstrip("-").replace("-","/")`). Measured: **1,008 of 1,017 dirs
fail to resolve**, and `tdd-playbook` decodes to `/…/GitHub/tdd/playbook`, which does not exist.
The skip is perfectly correlated with a dash in a path segment — i.e. with modern repo naming.
Consequence, measured: **86.6% of all `Loop closed` traffic sits in the excluded set.** A
committed tool carrying that bug would bake the exclusion into the repo permanently.

**Edge cases**
- a session whose records carry no `cwd` → excluded AND counted as `unresolved`, never silently dropped
- two folders decoding to the same root (worktrees) → distinct sessions, root recorded per session
- a project dir that no longer exists on disk → `unresolved`, counted
- a session file being appended while reading → read once, record byte length in the manifest
- an empty project (0 sessions) → present in the manifest with 0, so absence is visible
- corpus rebuilt with different inputs → **new file + new hash**; existing corpora are never
  edited (the corpus rule `check_scoreboard_integrity.py:50` already enforces: *"a form you can
  rewrite lets a holdout plant… be rewritten"*)

**Integration surface**
- *Consumes:* `hooks/scripts/transcript.py` (the one reader — parse, turn boundaries, vocabulary).
- *Emits → named consumer:* the frozen corpus → `calibration/gate_replay.py` (D2), at field
  granularity: D2 reads `events[]` and `turns[]`. The manifest hash → D2's output header and
  D3's identity assertion.
- *Surface parity:* CLI only. Not vendored (calibration/ is excluded from `install_into_repo.py`),
  so no downstream surface exists and none is claimed.
- *Reverse sweep:* `run_calibration.py` is the only other calibration entrypoint; it gains
  nothing here and is deliberately untouched. `author_plants.py`'s corpus rules are the model
  this corpus follows rather than a second uncalibrated library.
- *Activation:* on by default when invoked; there is no flag to turn the redaction off.

**PRIVACY IS A DELIVERABLE, NOT A CAVEAT.** This plugin is public. The current scratch artifact
holds **104 KB of verbatim claim sentences and absolute paths** from four private repos. Rules:
the corpus body is gitignored; only counts and hashes are tracked; a tracked file containing a
claim sentence is a **test failure**, not a review comment (D3).

---

## D2 — `calibration/gate_replay.py`: replay any guard, emit counts

**What.** Drive a registered guard over a frozen corpus and report a fire rate with its
denominator.

**Happy path.** `gate_replay.py --corpus <name> --gate exitcode` → feeds each historical event
to the guard as a subprocess with its opt-in env, counts exit codes, prints
`gate exitcode · corpus <sha[:12]> · events 300 · fires 12 · 4.0% · recall 5/5`.

**The anti-Goodhart control, and it is the point of the deliverable.** A replay is a
fire-rate MINIMISER, and this repo's own doctrine says a lower number must never be the metric.
So: **`gate_replay` REFUSES to print a rate unless the paired planted-recall run is green** for
that guard — the planted rows already in `test_hooks.py`, whose every silent case has a firing
twin. A rate with no recall beside it is not emitted at all.

**Edge cases**
- guard not in `_DEFAULT_MODES` → refuse, naming the roster (no silent skip)
- guard whose planted rows do not exist → refuse; an unmeasurable guard is not zero-yield
- a guard that hangs → per-event timeout under the hook's own 15 s; a timeout is `unmeasured`, counted
- an event shape the guard does not handle → `not-applicable`, counted separately from `clean`
- corpus hash mismatch vs manifest → refuse (the corpus moved under the measurement)
- zero events selected → **refuse a vacuous pass** (§4a), never print 0.0%

**Integration surface**
- *Consumes:* D1's corpus + manifest; `hooks/scripts/*.py` as subprocesses; `_common._DEFAULT_MODES` as the roster.
- *Emits → named consumer:* a counts row → `docs/calibration/replay.md` (tracked, append-only),
  read by the human answering the advisory-guards-optin debt. **Named at field granularity:**
  the `fires`/`events` columns are what the debt's "re-express the bar in a surviving unit" asks for.
- *Surface parity / Reverse sweep / Activation:* as D1.

---

## D3 — The accounting identity and the vacuity guard

**What.** Make a beautiful low number impossible to produce by measuring nothing.

**The assertion, in one line, and it REFUSES rather than warns:**
```
fired + clean + not_applicable + unmeasured == events_in_corpus     (per guard, per project)
and events_in_corpus == manifest.n_events                            (the corpus did not move)
and for a claims-shaped guard: claims_extracted > 0 and resolved_refs > 0
```
**The violating input, stated so the test can be written:** point a replay at a corpus whose
project roots do not exist → every reference resolves to nothing → **0.0% fires**, and today
nothing distinguishes that from a perfect guard. That is the planted case.

**Also enforced here:** no tracked file may contain a claim sentence. A grep-shaped test over
`docs/calibration/replay.md` and the manifests asserting counts-and-hashes only.

---

## D4 — Roster separation: a replayed counterfactual is not live exhaust

**What.** `REPLAY_EVENTS`, disjoint from `GATE_EVENTS` / `USAGE_EVENTS` / `COVERAGE_EVENTS`.

**Why.** `gate_yield.py:162-163, 345-347` already splits rosters *"because usage events NEVER
mint a gate row."* Same rule, fourth roster: a replayed fire is a counterfactual about the
past, and letting it mint a live gate row would corrupt the exact record the mode decision
reads. Pinned by a test asserting all four rosters are mutually disjoint.

---

## D5 — Registration, and discharge the debt with the new unit

`capabilities.json` entry (`replay-calibration`) · `docs/calibration/replay.md` (tracked,
append-only) · the `advisory-guards-optin` debt updated to state the measured unit and the
first readings · `CLAUDE.md` gains the invocation next to the other calibration commands.
**Expect the gate roster digest to RED** when a new `calibration/` suite appears — that is the
gate working; acknowledge it, do not loosen it.

---

## §0.3 Tests (red first)

Every fix here NARROWS or REFUSES, so each gets a **twin**: the refusal must fire, AND the
legitimate case must still pass.

| test | proves |
|---|---|
| decode: a dashed repo name resolves from `cwd` | the 1,008 come back — twin: a session with no `cwd` is `unresolved`, not silently dropped |
| corpus: manifest hash matches body; a mutated body REDs | the corpus cannot move under a measurement |
| **privacy: no tracked artifact contains a claim sentence** | planted: inject a sentence into a manifest → test REDs |
| vacuity: a corpus with non-existent roots REFUSES | planted: the 0.0%-for-the-wrong-reason case |
| identity: `fired+clean+n/a+unmeasured == n_events` | no silent denominator loss |
| recall pairing: a guard with red plants REFUSES to print a rate | the anti-Goodhart control |
| rosters: all four event vocabularies mutually disjoint | replay rows can never mint gate rows |
| determinism: two runs on one corpus are byte-identical | a calibration number that moves on its own is not a number |

---

## §0.4 Tripwire deliverables

| # | BUILT | WIRED | ACTIVATED | EXERCISED |
|---|---|---|---|---|
| D1 | `calibration/replay_corpus.py` | consumed by D2 | CLI, documented in CLAUDE.md | `calibration/test_replay.py` |
| D2 | `calibration/gate_replay.py` | reads D1 manifest | CLI | same |
| D3 | assertions inside D2 | refuses on violation | always on, no opt-out flag | planted vacuity case |
| D4 | `REPLAY_EVENTS` in `gate_yield.py` | rollup routes them | always on | disjointness test |
| D5 | registry + docs | `capability_registry validate` | n/a | `test_capability_registry::test_own_registry` |

**Not remote.** Everything runs locally in this repo; no RUNNING leg applies.

## §0.5 Decay contract
Named metric: whether a replay reading ever changes a guard's mode. Review: at the
advisory-guards-optin expiry (2026-11-15). **Kill condition: if by that date no replay reading
has changed a single mode decision, delete the tool** — an instrument that informs nothing is
the ceremony this repo retired the calibration clock to avoid.

## Close the loop
`integration-adversary` and `architecture-adversary` on this plan before code; Codex panel in
parallel. Loop closed: pending.
