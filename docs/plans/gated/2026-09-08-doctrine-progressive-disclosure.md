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
- **Q2 — REVERSED BY REVIEW.** The draft said the rosters should stay separate. The
  architecture-adversary refuted both halves of that reasoning and it is withdrawn. See
  **D-1** below: the rosters are unified, and the prior art the draft failed to sweep for is
  cited there. The draft's error is kept visible rather than edited away, because "we thought
  about it and said no" and "nobody looked" are indistinguishable from the outside.
- **Q3 — NEW, needs your call.** `.agents/skills/tdd-playbook/SKILL.md` is a tracked,
  byte-identical third copy of the doctrine that no mechanism protects (D0). Delete it, or
  protect it? The plan cannot proceed past D0 without an answer.

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

**The only safe order (revised — the draft's phase C was invalid):**

```
0. ENUMERATE + DECIDE THE COPIES  (D0)      — three tracked doctrine copies, not one
A. UNIFY THEN EXTEND PROTECTION   (D-1 D1 D2 D3)  — one roster owner, then coverage
B. TEACH THE TESTS + ACKNOWLEDGE  (D4 + D7 SAME COMMIT) — see F5 below
D. MOVE, ONE SECTION PER COMMIT   (D5 D6 D6b) — attribution + citations updated per move
E. MEASURE                        (D8)      — calibration decides whether it stays
F. PROPAGATE                      (D9 D9b D10) — vendored self-parity, downstream, registry
```

**Phase C was deleted, and why matters.** The draft sequenced "re-acknowledge the gate roster"
as a separate phase AFTER adding the new suite. `plugins/tdd-playbook/bin/gate_plan.py:99`
**raises** `PlanError` on a digest mismatch — it does not warn. A commit that adds a suite
without re-acknowledging in the same commit has no runnable gate at all: not a red suite, a
refused plan. Acknowledgement is a line in the commit that adds the suite, never a phase.
The draft sequenced against a rule it had already written down in its own conventions section,
which is the failure this note exists to make un-repeatable.

0→A→B is strict. D5's per-section commits are individually revertible, which is what makes E's
verdict actionable rather than all-or-nothing.

---

## Deliverables

### D0 — Enumerate the doctrine copies and decide `.agents/` · **blocks everything**

**What.** Every tracked copy of the doctrine is named, and each is either protected or deleted,
before one line of text moves.

The draft assumed one canonical file plus vendored copies. There are **three tracked copies**:

| Copy | State | Protected by |
|---|---|---|
| `plugins/tdd-playbook/skills/tdd-playbook/SKILL.md` | canonical | rule (d), ledger, leak scan, full-lane |
| `.claude/skills/tdd-playbook/SKILL.md` | this repo's own vendored copy, in sync | leak scan via `VENDOR_DIRS` |
| `.agents/skills/tdd-playbook/SKILL.md` | **byte-identical, tracked, written by nothing** | **nothing** |

Verified: `git ls-files .agents` returns exactly that one file; `diff` against canonical is
empty; `calibration/plant_forms.py:68` `VENDOR_DIRS` covers `.claude/*` only; rule (d) reads one
path (`calibration/check_scoreboard_integrity.py:58`); `plugins/tdd-playbook/bin/review_ledger.py:626`
`_FULL_LANE_PREFIXES` covers `plugins/…/skills/` only. No tool writes `.agents/` —
`scripts/install_into_repo.py:44` targets `.claude`/`.codex`.

**Why this blocks the plan.** The moment D5 lands, `.agents/…/SKILL.md` becomes the tree's *last
remaining monolith* — an unscanned, unratcheted, full copy of the doctrine that a leak scan never
reads and a deletion ratchet never guards. Splitting the protected copy while an unprotected copy
survives is a weakening of exactly the kind the request forbids, arrived at by accident.

**Edge cases**
- *Auth-negative analogue* — a holdout id in `.agents/` today is already unscanned. This is a
  **pre-existing hole**, not one this plan creates; it is D0's job to say so out loud rather than
  inherit it silently.
- *Deletion is not obviously right* — the directory may serve a host discovery surface nobody
  documented. D0's first step is `git log --diff-filter=A` on the path, not `rm`.
- *Idempotency* — if kept, adding `.agents/skills` to `VENDOR_DIRS` must not double-count files in
  the leak scan's `files_scanned` total (which D3 asserts grows).

**This is Q3 and it needs your decision.** The plan does not choose for you.

### D-1 — One roster owner · **supersedes the draft's Q2**

**What.** The set of paths meaning "this is doctrine / a gate surface" is defined once and imported,
not restated in four places.

**The draft was wrong and the review proved it.** Q2 argued a shared constant would cross the
`calibration/` ↔ vendored `plugins/` boundary. It would not: **all three targets are in
`calibration/`** — `calibration/check_scoreboard_integrity.py:58`, `calibration/ledger.py:61`,
`calibration/plant_forms.py:55`. No boundary is crossed. Both halves of the reasoning are refuted
by prior art the draft never swept for:

- `calibration/history_format.py:2` — *"the ONE owner of the calibration scoreboard's on-disk
  format… Format knowledge lives here and nowhere else — the previous arrangement (a writer, a
  date regex, and column-string asserts in three files) **was the parallel-list bug one level
  up**."* The pattern is installed, named, and defended in the very directory Q2 declined to use it in.
- `calibration/history_format.py:18` — `import plant_forms  # the ONE status-vocabulary owner
  (arch-F3) — no second literal here`. A prior architecture adversary already won this argument.
- `plugins/tdd-playbook/bin/review_ledger.py:626` — `_FULL_LANE_PREFIXES` is a **fourth** roster of
  the same concept, already a directory prefix (`"plugins/tdd-playbook/skills/"`), already covering
  `reference/` with zero edits, and living in the vendored package — which refutes Q2's second horn
  directly.
- Cross-boundary imports already happen in the direction Q2 called impossible:
  `calibration/run_calibration.py:967` inserts `plugins/tdd-playbook/hooks/scripts` on the path;
  `calibration/test_harness.py:1418` imports `dataflow_sweeps` from `plugins/tdd-playbook/bin`.

Without D-1 this plan ends with **five** definitions of the same membership question in **three
incompatible shapes** — exact-file, directory-prefix, heading-union — under a comment at
`calibration/ledger.py:58` that still reads *"No second list: a divergent copy is how one of them
silently stops covering something."*

**Edge cases**
- *Policy stays local* — each consumer keeps its own subsetting (`EFFECTFUL` at
  `calibration/ledger.py:74` is a decision dated 2026-08-14 and must not be swept into the shared
  owner). The owner exports membership; it does not export policy.
- *Vacuity* — the shared roster must be non-empty and enumerated from something real; an empty
  tuple would make all three consumers pass by checking nothing.
- *Planted divergence* — a consumer that stops importing the owner and re-inlines a literal must
  RED. Without this case the unification is a convention, not a mechanism.
- *`review_ledger.py` is the fourth* — it ships downstream and cannot import `calibration/`.
  Decide explicitly: normalise it to the same prefix form and pin the two against each other with a
  test, or record why it stays independent. **Do not leave it unmentioned, which is what the draft did.**

### D1 — Rule (d) covers the reference bundle

**What.** Deleting a `##` heading from any file in `skills/tdd-playbook/reference/` costs a
`gate-changes.md` entry, exactly as deleting one from `SKILL.md` does today.

Today `calibration/check_scoreboard_integrity.py:200` reads headings out of one blob at one path
(`:58`). A moved section lands outside that path and its later deletion is free.

**The proxy problem the draft missed (architecture F3).**
`calibration/check_scoreboard_integrity.py:204` defines a section as *"a line starting with
`## `"* and compares the rendered heading **strings** as a set. The draft's D5 then permitted
moved text to change "modulo the heading level" — so `## 4. Mutation testing` becoming
`# Mutation testing` in its own file **vanishes from the set and is reported as an unjournaled
removal**, for all 12 sections. Journalling those to get green is precisely Reading A, which this
plan rejects. The gate keys on a proxy for the fact it cares about.

**Resolution:** D1 keys on a stable section **id** (an explicit `<!-- gate-surface: 4a -->`
anchor, or the `§N` token), not the rendered heading. D5 then either byte-preserves heading text
or carries the anchor through. Assumption 3 is not satisfiable without this.

**Edge cases**
- *Baseline-absent vs candidate-absent are NOT symmetric* (integration F9). Baseline-absent →
  legitimate no-op (the bundle didn't exist yet). Candidate-absent with baseline-present → **every
  heading in it counts as removed**. The draft said only "no-op when absent", which if keyed on the
  candidate side makes `rm -rf reference/` free — the exact protection this plan exists to keep.
  Planted case: delete the whole directory, expect RED.
- *Boundary — heading moved between two reference files.* Union across spine + bundle, computed at
  BOTH revisions (`git ls-tree <rev>`), not per-file sets.
- *Malformed* — a reference file with no headings contributes nothing; must not crash.
- *Wholesale file deletion* — message must name the file, not just the orphaned heading.
- *Idempotency* — re-running on an unchanged tree stays green; no accumulating state.

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

**Do not hand-write the map (architecture F4).** 149 of 173 needle labels in
`plugins/tdd-playbook/tests/test_agents.py` already begin `"SKILL §N: …"`, and D6 is already
building a total `§N → file` map. Derive `declared_home` from the label through D6's map; keep a
vacuity-guarded exception list for the ~24 unsectioned needles (`SKILL description…`,
`SKILL markers:…`). A hand-maintained 173-entry map would be a **fifth** roster that must be
edited on every future move — growing the drift surface this plan exists to shrink.

**Sites the draft's enumeration missed:**
- `calibration/test_harness.py` — the rule-(d) planted fixtures build a fake tree containing only
  the canonical SKILL path, and `:2112` is the ledger CONTROL case. It is in `gate-manifest.json`
  `force_full`, i.e. itself a gate surface. **D1/D2's planted tests land here**, and the draft's
  Tripwire EXERCISED cells never named the suite.
- `plugins/tdd-playbook/tests/test_agents.py:1342` — `"SKILL: still 22 top-level sections"`, a
  **count** assertion over the `## ` prefix. The spine becomes ~10. D4's `found_in == declared_home`
  property cannot see a count assertion; it needs the union set (which D1's F3 fix supplies).
- `README.md:253` — the layout block names `SKILL.md  # the doctrine (auto-fires)`, and it is
  pinned by a README needle in `test_agents.py`.
- `CLAUDE.md` standing refresh prompt — instructs downstream repos to *"confirm the vendored
  SKILL.md mentions … §6a wiring liveness, §6c Dataflow Liveness"*. Both are in the move set, so
  after D5 that instruction sends every downstream repo looking in the wrong file. U2 promised
  CLAUDE.md "gains a line"; it must also **repoint the existing verification list**.

**Edge cases**
- *Exception list is exhaustive* — an unparseable-and-unlisted label is a hard error, never a
  default-to-anywhere. Vacuity-guarded against the real file list.
- *Planted misplacement* — a needle whose text is present but in the WRONG file must RED. Without
  this case the map is decoration.
- *Ambiguity* — a needle resolving in two files fails; homes are unique.
- *Boundary — B-time state* — every entry resolves to `SKILL.md` and the suite is fully green
  before any move. That green run is the baseline the moves are measured against.

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

### D6b — Line-anchored citations INTO SKILL.md, repo-wide · **new, from integration F5/F6**

**What.** Every `SKILL.md:<line>` citation and every `§N` pointer written OUTSIDE the bundle still
resolves after the split.

The draft's D6 covered `§N` tokens *inside* the bundle. Two larger populations sit outside it:

- **13 line-anchored citations** (`git grep -nE "SKILL\.md:[0-9]+"`): `capabilities.json:42`,
  `docs/reviews/2026-08-16-v1.37.0-release.json:50`,
  `docs/reviews/2026-08-17-mutation-attribution-doctrine.json:20,21,34,35,47,48,60,61`, and — with
  some irony — `docs/recommendations/mantis-pattern-review-2026-09.md:74,75,208,264,271`. The spine
  drops to ~590 lines, so anchors at `:768/:940/:945/:1344` become UNRESOLVED and the rest silently
  point at different text. **The consumer is real and named:**
  `plugins/tdd-playbook/bin/verify_citations.py`, dispatched by `agents/claims-verifier.md`,
  `commands/claims.md`, `commands/integration-audit.md` and `commands/readable.md`. A committed
  review record whose evidence no longer resolves is exactly what the citation gate exists to catch.
- **622 `§N` pointers in the named directories** — agents 45 · commands 45 · hooks 27 · bin 66 ·
  tests 328 · calibration 71 · CLAUDE.md 20 · AGENTS.md 20 (930 across the wider tree). These are
  file-less: `commands/claims.md` says "Playbook §12", `agents/mutation-runner.md` says "the
  Playbook §4 mutation pass". §12 and §4 are both in the move set.

**Edge cases**
- *Historical records are append-only.* A committed review record must NOT be rewritten to chase a
  moved line. The fix is de-anchoring (cite the section id, not the line) going forward, plus a
  recorded decision that pre-split anchors are historical. **Rewriting them would be the
  scoreboard-integrity violation this repo blocks.**
- *Prefix collision* — `§6` vs `§6a` vs `§6c` must not match on prefix.
- *Planted dangling* — a deliberate `§99` must RED, or the sweep asserts its own inventory.
- *Totality* — the property covers `agents/**`, `commands/**`, `hooks/**`, `bin/**`, `tests/**`,
  `calibration/**`, `CLAUDE.md`, `AGENTS.md` — not just the bundle.

### D9b — This repo's own vendored copy · **new, from integration F2**

**What.** `<repo>/.claude/skills/` is re-vendored and committed in the same change, and a gate check
pins it to canonical.

The draft scoped D9 to "a repo that re-vendors" and a scratch install. **This repo is itself a
vendored repo with committed artifacts** — `.claude/skills/tdd-playbook/SKILL.md` is tracked and in
sync (differing from canonical only at the two `${CLAUDE_PLUGIN_ROOT}` rewrite lines), and
`.claude/.tdd-playbook-manifest.json` carries 74 entries with exactly one skills entry. That is the
tree this repo's own sessions load.

Consequences if unaddressed: the plan's headline benefit **does not land in this repo**; the
committed manifest goes stale; and `_prune_upstream_removals` (`scripts/install_into_repo.py:410`),
which prunes from the *previous* manifest, never runs to remove the stale monolith.

**Edge cases**
- *No self-parity pin exists today* — `plugins/tdd-playbook/tests/test_installer.py:193` compares
  only a `tempfile` install; nothing compares `<repo>/.claude/skills` to canonical. The pin is the
  deliverable.
- *Rewrite lines* — the comparison is modulo the plugin-root rewrite, per-file across the bundle.
- *Double registration* — this repo carrying both the plugin and a vendored copy is known, dated
  debt (`double-registration-risk-doctor`); the split changes file count, not that posture. Named so
  it is not rediscovered as new.

### D7 — Gate roster re-acknowledgement · **folded into D4's commit, not a phase**

**What.** The new suite is in the gate roster and the affected-selector routes bundle paths to a
full plan.

`gate-manifest.json`'s `suite_glob` auto-discovers `test_*.py`, and
`plugins/tdd-playbook/bin/gate_plan.py:98` enforces `acknowledged_roster_sha256`. `:99` **raises** `PlanError` — it does not warn. A commit that adds a suite without
re-acknowledging in the same commit has NO RUNNABLE GATE: not a red suite, a refused plan. This is
why the draft's phase C was deleted rather than reordered.

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

**Surface parity.** Claude: full. Codex: **the draft's citation here was wrong and is corrected.**
It claimed skills are "already `unavailable` per `docs/architecture/host-parity-policy.json`" —
that file records nothing about skills for either host (`grep -ci skill` = 0 on both parity JSONs),
and `plugins/tdd-playbook/bin/host_parity.py:20` reads `FAMILIES = ("commands", "agents",
"guards")`. Skills are not a parity family at all. The real record is dated debt
`codex-skill-surface-absent` at `capabilities.json:1384` (owner david, **expires 2026-11-15**),
whose DONE condition is verbatim what D9's draft edge case proposed. **D9 cites that debt and does
not open a parallel obligation.** Cloud/vendored: identical to local via the walk-derived manifest.

**Activation.** ON by default the moment the bundle exists — a skill's file layout is not
switchable. **This is a plan that ships a change with no user-facing switch**, which §6b normally
treats as an audit finding waiting to happen. The mitigating control is that D5's per-section
commits are individually revertible and D8's calibration run is the go/no-go. Named rollback:
`git revert` of the D5 range restores the monolith; D1–D4 are additive and stay.

**Reverse sweep.** Which existing features should adopt this once it exists? The draft deferred
two items with no expiry and one by forward-reference to an entry that did not exist —
`capability_registry.py validate` refuses debt without owner AND date, so as drafted neither could
be created. Both are now concrete, to be written into `capabilities.json` in D10's commit or
dropped from the plan:

| Debt id | What | Owner | Expires |
|---|---|---|---|
| `commands-restate-doctrine` | 12 command files (49,671 bytes) and 16 agent briefs restate doctrine that could point at reference files | David | 2026-12-15 |
| `skill-description-budget` | the frontmatter `description` is near the 1,024-char limit and is loaded for ALL skills at all times; out of scope here | David | 2026-12-15 |

Neither becomes a deliverable in this plan — that is a deliberate scope hold, not a silent one.

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

| line-anchored citations | `SKILL.md:<line>` in 13 places | `plugins/tdd-playbook/bin/verify_citations.py` resolves each anchor | D6b: a stale anchor REDs the citation gate |
| `§N` pointers outside the bundle | 622 in agents/commands/hooks/bin/tests/calibration/CLAUDE/AGENTS | each doc's reader; totality asserted | D6b planted dangling `§99` |
| registry wiring claims | `capabilities.json` `wired_by` strings carrying `§N` anchors | `capability_registry.py` resolves by FILE existence only — never reads the anchor | D10 sweep: an anchor whose home moved |
| this repo's vendored tree | `COPY_TREES` walk | `<repo>/.claude/skills/**` + committed manifest (74 entries) | D9b self-parity pin (none exists today) |
| third doctrine copy | `.agents/skills/tdd-playbook/SKILL.md` | **NOBODY — written by nothing, scanned by nothing** | D0: deleted, or added to `VENDOR_DIRS` + the union |

**One empty consumer cell, and it is the point.** `.agents/skills/tdd-playbook/SKILL.md` has no
producer and no consumer — a tracked, byte-identical copy of the doctrine that no mechanism reads
or guards. The draft's flow table did not contain this row because the draft did not know the file
existed. It is now D0, and it blocks the plan.

**The `capabilities.json` row is the H11 tell in its textbook form:** the registry receives the
path, `capability_registry.py` resolves it by file existence, and the `§6c` anchor inside the
string is never read. `capabilities.json:659` claims SKILL.md `§6c names it the Tier-1 reference
tool`; after D5 that is false and `validate` stays green, because SKILL.md still exists. A consumer
that ignores the field is no consumer.

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
| D0 | doctrine copies enumerated | decision recorded | `.agents/` deleted or in `VENDOR_DIRS` | on | planted holdout id in the third copy is caught (or the copy is gone) |
| D-1 | one roster owner | shared module | imported by all consumers | on | planted re-inlined literal REDs |
| D6b | citations resolve repo-wide | sweep | gate suite | on | planted dangling `§99` + a stale line anchor REDs |
| D9b | this repo's vendored tree | re-vendored + committed | self-parity pin | on | `<repo>/.claude/skills` == canonical modulo rewrite |
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
