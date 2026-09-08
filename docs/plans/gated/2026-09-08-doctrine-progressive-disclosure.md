# TDD plan — doctrine progressive disclosure

**Slug:** `2026-09-08-doctrine-progressive-disclosure` (permanent; no collision — the only other
2026-09 gated plan is `2026-09-06-tripwire-reminder-lock-aware.md`)
**Base sha:** `b32346413383f2fc02a82e91f51d45f5703d1014`
**Request:** split `SKILL.md` into a progressive-disclosure reference bundle without weakening the
gate-surface ratchet.

---

## Repo-local testing conventions layered on top of the universal floor

Discovered, not assumed:

- **`CLAUDE.md` — release discipline.** Every mechanical change ships with a planted-input test; a
  planted violation that slips past a check is a failure. Suites run ONLY via
  `sh scripts/civerd_gate.sh` (the one blessed entrypoint), never piped — a piped `$?` is `tail`'s.
- **`CLAUDE.md` — rule (d).** Removing a gate surface (a SKILL `##` heading, an agent brief, a
  command file) costs a journaled `calibration/gate-changes.md` entry; adding one is free.
- **`CLAUDE.md` — plans land in the repo** at `docs/plans/gated/YYYY-MM-DD-<workstream>.md`,
  committed with the work. This file is that.
- **`CLAUDE.md` — guard blocks are recorded** (`guard_note.py record`), because splitting a blocked
  command into pieces is indistinguishable from complying with it.
- **`AGENTS.md` — host neutrality.** Codex vendoring is adapter-owned; unavailable capabilities are
  reported as unavailable, never rounded up.
- **Test shape:** suites are plain `python3` scripts with a `check(name, condition, detail)` helper
  and pass/fail counters (`plugins/tdd-playbook/tests/test_*.py`), not pytest. New suites are
  auto-discovered by `gate-manifest.json`'s `suite_glob` and must be re-acknowledged
  (`acknowledged_roster_sha256`, enforced at `plugins/tdd-playbook/bin/gate_plan.py:98`).
- **Vacuity guards are mandatory** on any sweep that enumerates a roster — a check that scanned
  nothing passes everything (`calibration/plant_forms.py:274` states this in its own docstring).

---

## Spec integrity

**Assumptions, stated so they can be refused:**

1. The goal is fewer always-loaded doctrine tokens **at equal or better agent behavior**. Token
   reduction that degrades what agents catch is a failure, not a trade.
2. Anthropic's published 500-line bar is guidance for the format, not a repo requirement. This plan
   treats it as the target and reports honestly when a phase does not reach it.
3. "Without weakening the ratchet" is read STRICTLY: after this change, deleting a moved section
   must cost exactly what deleting it costs today. Equal protection, not "protection somewhere".

**Two readings of the request; this plan follows the second.**

- *Reading A — move the text, journal the removals.* Move sections into `reference/`, write a
  `gate-changes.md` entry per moved heading, done. Cheapest. **Rejected:** the journal entry exists
  to record a genuine gate removal. Using it to wave through a move teaches the ratchet nothing and
  leaves the destination unprotected, which is the precise thing the request forbids.
- *Reading B — extend the protection to the destination first, then move (this plan).* No text
  moves until the three rosters that currently cover `SKILL.md` cover the bundle, proven by planted
  deletion. Slower; it is the only reading under which the ratchet is not weakened even transiently.

**A materially simpler approach exists and is worth naming.** Doing nothing is defensible: the
skill works, the cost is diffuse, and this plan touches four assurance mechanisms to save context.
The reason to proceed anyway is that this repo can *measure* the outcome (`calibration/`), which is
the standing argument in `docs/recommendations/mantis-pattern-review-2026-09.md` §F1 addendum. If
the measurement in D8 comes back negative, the correct outcome is to revert and record the number.

**Open questions for review — planned around, not silently answered:**

- **Q1.** Phase 1 lands the spine at ~590 lines, still 18% above the published bar. Reaching it
  needs §0 (153 lines) or §1 (195) moved, both arguably every-turn content. This plan proposes
  moving §0's *detail* with a summary stub in the spine (→ ~450 lines) as **D5b, gated on your
  approval**. If you'd rather stop at 590, D5b drops and the plan still delivers 60%.
- **Q2.** Three files hardcode the `SKILL.md` path (D1/D2/D3 targets). Should they be factored into
  one shared roster? This plan says **no** and explains why in D1's note — the boundary between
  `calibration/` and the vendored `plugins/` package is real. Flagging it because the
  architecture-adversary is expected to raise it, and a silent "no" would be indistinguishable
  from not having thought about it.

---

## The measured baseline (facts this plan is built on)

| Fact | Value | Citation |
|---|---|---|
| SKILL.md size | 1,459 lines / 131,277 chars | this tree |
| Published bar | "under 500 lines" | Anthropic skill-authoring best practices |
| Movable (command-routed / rarely needed) | 869 lines = 60% | per-section counts below |
| Residual spine, phase 1 | ~590 lines | 1,459 − 869 |
| Residual spine, phase 1 + D5b | ~450 lines | −153 (§0) + ~13 stub |
| Internal `§N` cross-references | 148 | `grep -oE '§[0-9]+[a-c]?'` |
| Duplicated SKILL.md read sites in `test_agents.py` | 17 | `grep -c` |
| Text-needle assertions against SKILL.md | 32 | `grep -c "in text"` |

**Move set (869 lines):** §4 mutation (128) · §4a gate integrity (103) · §5a UX probes (45) ·
§5b agent evals (64) · §6a wiring liveness (63) · §6b onboarding (25) · §6c dataflow (67) ·
§9 security (47) · §10 CI hygiene (54) · §11 checkpoints (27) · §12 claims (137) · §13 learning
loop (109).

**Spine (590 lines):** preamble + ceremony table (30) · repo-extensions (22) · §0 plan (153) ·
§1 TDD loop (195) · §2 edge (23) · §3 property (20) · §5 UX journeys (16) · §6 Tripwire (72) ·
§7 determinism (34) · §8 test shape (18) · markers (7).

---

## THE SEQUENCING — why this order and no other

The whole risk of this change is that **the protection and the thing protected move apart, even
for one commit.** Three orderings fail, and naming them is the point:

- **Move first, protect after** → between the two commits the bundle is unprotected, and the
  `gate-changes.md` entries written to get past rule (d) are lies (nothing was removed). Rejected.
- **Protect and move in one commit** → if the gate REDs you cannot tell a broken ratchet from a
  lost section, and the planted test proving the new ratchet works has no pre-state to be red
  against. Rejected (this is §13's guard-calibration rule: a new guard is replayed against the
  motivating artifact *before* it is trusted).
- **Fix the tests last** → 32 needles go red in the same commit as the move, and a genuinely lost
  section is indistinguishable from a needle that needs repointing. Rejected.

**The only safe order:**

```
A. PROTECT THE DESTINATION      (D1 D2 D3)  — tree otherwise unchanged; refs don't exist yet
B. TEACH THE TESTS WHERE TEXT LIVES (D4)    — attribution map, all entries still "SKILL.md"
C. RE-ACKNOWLEDGE THE GATE      (D7)        — new suite enters the roster
D. MOVE, ONE SECTION PER COMMIT (D5 D6)     — attribution map updated per move
E. MEASURE                      (D8)        — calibration decides whether it stays
F. PROPAGATE                    (D9 D10)    — downstream refresh + registry
```

A→B→C is strict. D5's per-section commits are individually revertible, which is what makes E's
verdict actionable rather than all-or-nothing.

---

## Deliverables

### D1 — Rule (d) covers the reference bundle

**What.** Deleting a `##` heading from any file in `skills/tdd-playbook/reference/` costs a
`gate-changes.md` entry, exactly as deleting one from `SKILL.md` does today.

Today `calibration/check_scoreboard_integrity.py:200` reads headings out of one blob at one path
(`:58`). A moved section lands outside that path and its later deletion is free.

**Edge cases**
- *Empty/absent directory* — the bundle doesn't exist at A-time. The check must be a no-op when
  absent and must NOT silently pass once present-but-empty (vacuity).
- *Boundary — heading moved between two reference files.* Union-of-headings across spine + bundle,
  not per-file sets, or every move REDs as a removal.
- *Malformed* — a reference file with no `##` at all contributes nothing; must not crash.
- *Second-order* — a file DELETED wholesale removes all its headings at once; the union handles it,
  but the message must name the file, not just the heading.
- *Idempotency* — re-running against an unchanged tree stays green (no accumulating state).

**Property test.** For any partition of a fixed heading set across spine + N reference files, the
union is invariant. Moving headings between files never REDs; deleting one always does.

**Note on Q2 (why not one shared roster).** `calibration/` is repo-local and never vendored;
`plugins/tdd-playbook/` ships downstream. A shared constant would either drag calibration code into
the vendored package or make the vendored package import from a directory that does not exist in a
downstream repo. The three rosters stay separate; D1/D2/D3 each get their own planted test, and the
divergence risk is answered by tests rather than by a shared import. **This is a decision, not an
oversight** — `calibration/ledger.py:58` already carries a comment asserting "no second list" while
being one, which is the drift this note exists to stop repeating.

### D2 — Gate-surface ledger covers the bundle

**What.** A change to any reference file counts as a changed gate surface for
`calibration/ledger.py`, as a change to `SKILL.md` does today.

`SURFACE_PATTERNS` at `:61` names the file; `:507` matches with `f == s or f.startswith(s)`, so the
entry becomes the directory prefix `plugins/tdd-playbook/skills/tdd-playbook/`. One line — but it
is load-bearing and gets its own planted case.

**Edge cases**
- *Boundary* — the prefix must cover `SKILL.md` itself, not just the subdirectory (it does; same
  parent). Assert both.
- *Over-capture* — the prefix must not swallow a sibling directory added later under `skills/`.
  Assert a non-bundle path under `skills/` is NOT captured, or accept and document it.
- *EFFECTFUL classification* — `:74` deliberately keeps SKILL.md OUT of `EFFECTFUL` (doctrine yield
  is unmeasured by decision, dated 2026-08-14). Reference files inherit that; changing it is a
  separate decision and is **explicitly out of scope**.

### D3 — Holdout-leak scan covers the bundle · **highest-severity item in this plan**

**What.** A holdout scenario id appearing in any reference file is caught, as it is in `SKILL.md`
today (`calibration/plant_forms.py:54` `LEAK_SCAN`, consumed at `:274`).

**Why this is the sharpest risk here.** `leakage_problems` returns a `scanned` count so a caller can
refuse a vacuous run — but after the move the spine is *still scanned*, so `scanned` stays healthily
nonzero while coverage of doctrine prose silently drops by 60%. **The existing vacuity guard cannot
see this failure.** A burned holdout is unrecoverable: the reporting set becomes the tuning set.

`_iter_files` at `:263` already handles a directory entry by walking it, so the fix is again a
prefix — but the *test* is the deliverable, not the edit.

**Edge cases**
- *Planted leak, red-first* — a holdout id written into a reference file must be caught. This is
  the motivating-artifact replay (§13): plant it, prove RED, then freeze it as a fixture.
- *Coverage-count assertion* — assert `files_scanned` GROWS by the bundle's file count. A count that
  stays flat is the silent-shrink signature, and nothing else detects it.
- *Vendored trees* — `VENDOR_DIRS` includes `.claude/skills` (a directory), so vendored references
  are already covered. Assert it rather than assume it.
- *Failure/rollback* — if the bundle is reverted, the scan must not error on the missing directory.

### D4 — One doctrine reader, with file attribution

**What.** Tests read doctrine through a single helper that knows which file each rule should live
in, so a section that lands in the wrong file, or in no file, goes RED.

17 duplicated read sites and 32 needles in `test_agents.py` (plus `plugins/tdd-playbook/tests/test_readable_surface.py:132`,
`plugins/tdd-playbook/tests/test_review_ledger.py:620`, `plugins/tdd-playbook/tests/test_installer.py:181`). The naive fix — concatenate everything and
keep searching the pile — **is a weakening**: a section could drift into a file nothing ever reads
and every needle stays green.

**Edge cases**
- *Attribution map is exhaustive* — every needle names its expected file; an unmapped needle is a
  hard error, not a default-to-anywhere. Vacuity-guarded against the real file list.
- *Planted misplacement* — a needle whose text is present but in the WRONG file must RED. Without
  this case the map is decoration.
- *Boundary — A-time state* — at D4 every entry is `SKILL.md` and the suite must be fully green
  before any move. That green run is the baseline the moves are measured against.
- *Concurrency* — none; single-process suites.

**Property test.** For any needle set, `found_in(needle) == declared_home(needle)` for all needles,
and the check fails if any needle resolves in two files (ambiguous home).

### D5 — The bundle: spine + `reference/`

**What.** `SKILL.md` keeps the spine and a complete one-level index; the 12 move-set sections
become `reference/*.md`, loaded only when the turn needs them.

**D5a (approved scope):** move the 869-line set → spine ~590.
**D5b (gated on Q1):** move §0's detail behind a stub → spine ~450, inside the published bar.

Layout follows Anthropic's Pattern 2 (domain organization), mirroring the command surface:
`reference/mutation.md` (§4, §4a) · `probes-and-evals.md` (§5a, §5b) · `wiring.md` (§6a, §6b, §6c) ·
`security-and-ci.md` (§9, §10) · `checkpoints.md` (§11) · `claims.md` (§12) · `learning-loop.md`
(§13) — and `planning.md` (§0) under D5b.

**Edge cases**
- *One level deep* — every reference file linked directly from SKILL.md's index. Nested-only
  reachability causes partial reads (`head -100`), per Anthropic's guidance. Assert mechanically:
  every file in `reference/` appears in the spine's index; no file is reachable only via another.
- *TOC on files > 100 lines* — `wiring.md` (155) and `mutation.md` (231) qualify; assert it.
- *Section content is byte-preserved across the move* — assert moved text is identical modulo the
  heading level and the added TOC, so "moved" can never quietly mean "rewritten".
- *Empty/duplicate* — no reference file is empty; no heading appears in two files.
- *Second-order — frontmatter description* is near the 1,024-char limit and is loaded for ALL
  skills at all times. Out of scope here; recorded as debt (see below) rather than smuggled in.

### D6 — Cross-reference resolution (148 links)

**What.** Every `§N` reference resolves to a real, directly-indexed location, from the spine and
from inside any reference file.

The heavily-cited targets are mostly in the move set (§13 ×16, §1 ×16, §6a ×15, §4 ×14, §6c ×13,
§12 ×13), so reference→reference links are unavoidable. The mitigation is structural: the spine
indexes every file, so no file is only reachable through another.

**Edge cases**
- *Dangling* — a `§N` naming a section that no longer exists. Sweep must RED.
- *Malformed* — `§6a` vs `§6` vs `§6c` must not collide on a prefix match.
- *Planted* — a deliberately dangling `§99` must be caught, or the sweep asserts its own inventory.
- *Scale* — 148 links; the sweep runs on every gate, so it must be O(file) not O(link × file).

**Property test.** Every `§N` token in the bundle maps to exactly one heading in the union set;
the map is total and injective on section ids.

### D7 — Gate roster re-acknowledgement and selection policy

**What.** The new suite is in the gate roster and the affected-selector routes bundle paths to a
full plan.

`gate-manifest.json`'s `suite_glob` auto-discovers `test_*.py`, and
`plugins/tdd-playbook/bin/gate_plan.py:98` enforces `acknowledged_roster_sha256`. Adding a suite
without re-acknowledging REDs the gate — correctly, but it must be a planned step, not a surprise.

**Decision, stated rather than defaulted:** do **not** add a `safe_rules` entry for `skills/**`.
Bundle paths stay "unknown" and fall back to the complete plan. A narrow safe rule would be an
optimization that risks under-selecting on exactly the assurance-bearing surface this plan touches.

**Edge cases**
- *Boundary* — roster digest changes; assert the new suite is IN the executed roster, not merely
  present on disk (the H8 built-vs-running distinction).
- *Failure* — a stale digest must fail loudly with the expected-vs-actual pair, which `:94` does.

### D8 — The measurement that decides whether this stays

**What.** A calibration run on the split tree shows the verifier agents catch what they caught
before.

This is the deliverable that makes the change provable rather than aesthetic, and it is the one
thing most projects cannot do. Plants whose doctrine moved out of the spine (mutation-class,
claims-class, wiring-class) are the ones that matter.

**Edge cases**
- *3× per scenario* — one roll is a coin flip. PASS only at k/k; AMBER is nonzero.
- *Paired clean controls* — a verifier that got noisier is as much a regression as one that got
  quieter; recall and false-positive rate are reported separately.
- *Non-root* — the headless doer cannot run as root (`run_calibration.py` header); an INVALID run
  is not a passing run.
- *Baseline* — the pre-split run is the comparison. **If no recent baseline exists, the baseline
  run happens BEFORE phase D**, or D8 has nothing to compare against. This is a sequencing
  constraint, not a nice-to-have.

**Honest scoping.** This is agent-behavioral evidence, not proof. A stable calibration result does
not prove the split helped; it proves it did not visibly hurt. The token reduction is the claimed
benefit; behavioral neutrality is the bar it must clear.

### D9 — Downstream and vendored parity

**What.** A repo that re-vendors gets the whole bundle, and the vendored copy is verified per-file.

`scripts/install_into_repo.py:76` walks `COPY_TREES` and `plugins/tdd-playbook/bin/vendoring.py:90`
derives the manifest from the same walk, so **no installer change is needed** — verified, not
assumed. But `plugins/tdd-playbook/tests/test_installer.py:194` asserts "vendored SKILL present" and `:198` compares one file;
that must become per-file across the bundle or the references ship unverified.

**Edge cases**
- *Manifest round-trip* — install → uninstall → install stays byte-identical (the manifest carries
  no timestamp by design); assert with the bundle present.
- *Uninstall by name* — `plugins/tdd-playbook/bin/vendoring.py:12` removes the `.claude/skills/tdd-playbook/` subtree, so
  the bundle is covered. Assert, don't assume.
- *Codex parity* — `CODEX_COPY_TREES` (`:57`) ships `adapters` and `bin` only; skills are already
  unavailable on Codex. **No new divergence** — but `docs/architecture/host-parity-policy.json`
  should say so explicitly rather than leaving it inferred.
- *Stale downstream* — a repo vendored pre-split has a monolithic SKILL.md and no bundle. The
  reconciling installer prunes by previous manifest (`scripts/install_into_repo.py:410`), so the stale file
  is replaced. Assert against a scratch repo seeded with the OLD layout.

### D10 — Registry and doctrine bookkeeping

**What.** The bundle is a registered capability with a named consumer, and the standing refresh
prompt tells downstream repos what changed.

**Edge cases**
- *`validate` passes* on this repo's own `capabilities.json` (the §6a dogfood, enforced with the
  real clock by `test_capability_registry.py::test_own_registry`).
- *No expired debt introduced* — any debt entry gets an owner and a date that is a real trigger.
- *`AGENTS.md` is generated* — hand edits fail `test_reference_docs`; CLAUDE.md changes must be
  re-rendered via `render_agents.py`.

---

## Integration surface

**Consumes.** `calibration/check_scoreboard_integrity.py` (rule d) · `calibration/ledger.py`
(gate-surface ledger) · `calibration/plant_forms.py` (holdout leak scan) ·
`plugins/tdd-playbook/bin/gate_plan.py` (roster acknowledgement) ·
`scripts/install_into_repo.py` + `bin/vendoring.py` (vendoring) · the Claude Code skill loader
(runtime, out of repo). **Not "none" — this plan is almost entirely integration.**

**Surface parity.** Claude: full. Codex: skills are already `unavailable`
(`docs/architecture/host-parity-policy.json`); this plan adds no new divergence and D9 makes the
existing one explicit. Cloud/vendored: identical to local via the walk-derived manifest.

**Activation.** ON by default the moment the bundle exists — a skill's file layout is not
switchable. **This is a plan that ships a change with no user-facing switch**, which §6b normally
treats as an audit finding waiting to happen. The mitigating control is that D5's per-section
commits are individually revertible and D8's calibration run is the go/no-go. Named rollback:
`git revert` of the D5 range restores the monolith; D1–D4 are additive and stay.

**Reverse sweep.** Which existing features should adopt this once it exists?
- `plugins/tdd-playbook/commands/*.md` (12 files, 49,671 bytes) carry doctrine restatements that
  could point at reference files instead of repeating them. **Not a deliverable here** — dated debt
  `commands-restate-doctrine`, owner David, so this plan does not grow a second workstream.
- `docs/adversary-scenario-inventory.md` and the 16 agent briefs are the other large always-loaded
  prose surfaces. Same shape, out of scope, same debt entry.

### §6c flow table

| Flow | Producer | Consumer (field-granular) | Liveness test |
|---|---|---|---|
| doctrine headings | spine + `reference/*.md` | `calibration/check_scoreboard_integrity.py:206` reads `## ` lines | D1 planted deletion in a reference file |
| changed gate surfaces | bundle file paths | `calibration/ledger.py:507` `f.startswith(s)` over `SURFACE_PATTERNS` | D2 planted reference-file edit counted as a surface change |
| doctrine prose (leak scan) | bundle file bodies | `calibration/plant_forms.py:274` `leakage_problems` per file body | D3 planted holdout id in a reference file + `files_scanned` growth |
| doctrine rules (assertions) | bundle text | `test_agents.py` 32 needles via D4 helper | D4 planted misplacement REDs |
| vendored roster | `COPY_TREES` walk `scripts/install_into_repo.py:76` | `plugins/tdd-playbook/bin/vendoring.py:90` `_paths_from_source` → manifest `files[]` | D9 per-file vendored comparison |
| suite roster | `test_*.py` glob | `plugins/tdd-playbook/bin/gate_plan.py:98` `acknowledged_roster_sha256` | D7 new suite present in the EXECUTED roster |
| T-vocabulary pin | §6c text (moving) | `plugins/tdd-playbook/tests/test_readable_surface.py:132` reads SKILL for §6c terms | D4 attribution follows §6c to `reference/wiring.md` |
| doctrine path class | file path | `plugins/tdd-playbook/tests/test_review_ledger.py:620` maps path → `"doctrine"` | D4 reference paths classify as doctrine |

**Empty consumer cells: none.** Every flow this plan produces has a named reader with a citation.

---

## Unenforceable deliverables (prose) — not disguised as mechanical

- **U1.** The decision record for Q1 (does §0 move) and Q2 (three rosters vs one). Prose, in this
  file, reviewed by David.
- **U2.** The `CLAUDE.md` standing refresh prompt gains a line about the bundle. Prose; its only
  mechanical half is `render_agents.py` re-rendering `AGENTS.md`.
- **U3.** The judgement of which sections belong in the spine. No test can express "an ordinary
  turn needs this"; D8 measures the consequence, not the judgement.

---

## Tripwire deliverable list

| # | Deliverable | BUILT | WIRED | ACTIVATED | EXERCISED |
|---|---|---|---|---|---|
| D1 | rule (d) covers bundle | heading union in `check_scoreboard_integrity` | called by the ledger stage in `gate-manifest.json` | on by default | planted reference-heading deletion REDs |
| D2 | ledger surface prefix | `SURFACE_PATTERNS` prefix | `ledger.py check` fixed stage | on | planted reference edit counted |
| D3 | leak scan covers bundle | `LEAK_SCAN` prefix | `plant-forms check` fixed stage | on | planted holdout id caught + `files_scanned` grows |
| D4 | doctrine reader + attribution | helper module | imported by all 17 sites | on | planted misplaced needle REDs |
| D5 | spine + `reference/` | files exist | indexed one level deep | loaded by the skill runtime | index-completeness + byte-preservation checks |
| D6 | cross-reference resolution | sweep | gate suite | on | planted dangling `§99` REDs |
| D7 | roster re-acknowledged | digest updated | `plugins/tdd-playbook/bin/gate_plan.py:98` | on | new suite in the EXECUTED roster, not just on disk |
| D8 | calibration measurement | run recorded in `docs/calibration/history.md` | — | — | **RUNNING leg, not EXERCISED** — a live agent run, 3×, paired controls |
| D9 | vendored parity | per-file comparison | `test_installer` | on | scratch-repo install from the OLD layout |
| D10 | registry entry | `capabilities.json` | `validate` in the release gate | on | `test_own_registry` with the real clock |

**Weaker truth, stated per §0:** D1–D7, D9, D10 reach EXERCISED — the test exists at a sha,
unskipped, gate green. Only D8 reaches RUNNING (behavior observed live). This plan does **not**
claim the split improves agent behavior; it claims the split is provably non-destructive to the
four assurance mechanisms, and that D8 measures whether behavior held.

---

## Adversary findings folded in

*(populated after dispatch — see the review record below)*
