# v1.52.0 — §4b reference implementation: `mutation_run.py` narrows BOTH halves per run

**Status:** APPROVED by David 2026-09-09, with amendments (Q2 and Q5 changed from the drafted
defaults; Q3/Q4/Q6/Q7 and the doctrine amendment approved with precise constraints; no second
approval round before D0). Building.
**Date:** 2026-09-09
**Origin:** SKILL.md §4b (v1.51.0, "the run must be scoped to what it measures"); owner decision
recorded in CHANGELOG 1.51.2 (planned reference implementation under five constraints).
**Review record:** draft v1 → `architecture-adversary` (9 findings, 9 accepted, 1 lead) and
`integration-adversary` (6 islands + 3 unowned clauses, all accepted); v2 → `intent-adversary`
LAST against David's verbatim decision (DRIFT 3, all reverted: reap "may"→"must"; accounting
denominator; unfinished split). Every citation spot-checked against source before folding.
**Slug:** `2026-09-09-scoped-mutation-runner`.

## Repo conventions layered on the universal floor
- Self-contained `plugins/tdd-playbook/tests/test_*.py` (`check()` / `unmeasured()`), run ONLY via
  `sh scripts/civerd_gate.sh`; `mutation_run.py` is `force_full` in `gate-manifest.json`.
  `test_mutation_preflight.py` owns the runner; its REAL-mutmut seam test is UNMEASURED where
  mutmut is absent (CI). Weaker truth up front: REAL rows are EXERCISED locally only.
- Planted-input test per mechanical change; a refusal born from a defect replays the motivating
  artifact (§13). Doubles never supply a seam production lacks (H9): every mutmut fact below was
  read in the installed 3.6.0 (`configuration.py`, `__main__.py`) or probed live.
- `capabilities.json` only grows; `validate` (incl. `R-WRITE-ONLY`) is in the gate.
- `bin/` ships to Codex (`CODEX_COPY_TREES`); `commands/`+`agents/` are Claude-only by decision.
- Tracked `.tdd-playbook/` is RESERVED for policy/configuration; runtime state lives under
  `<git-common>/tdd-playbook` (`host_contract.py:9-13,25`).
- `agents/mutation-runner.md` is an EFFECTFUL gate surface: a brief edit gets a
  `docs/calibration/ledger.md` row with target scenario + predicted direction (precedent
  `L-20260819-02`); oracle regexes in `calibration/scenarios.json` are journaled if touched.
- **§4 per-phase mutation applies to this build.** This repo has no mutmut config (accepted
  non-dogfood boundary), so each phase's score is the TARGETED-MUTANT form (§4: hand-applied
  mutants on the phase's functions, killed by the owning suite, recorded per phase in the
  CHANGELOG), with the broad pass labelled UNMEASURED. "Later" is not a status.

## Spec integrity (§0)
**Problem, verified:** `mutation_run.py` checks `--scope` by SUBSTRING against the raw config text
(`:276`; `--scope b` passes against `source_paths=plugins/tdd-playbook/bin`) and runs mutmut over
everything configured; its own baseline and mutmut's stats pass run the whole test selection. §4b
defines a scoped run as narrowing both halves. Its reader (`:195`) consults `tox.ini`, which
mutmut never reads (zero hits package-wide), and lists `setup.cfg` before `pyproject.toml`, the
reverse of mutmut's precedence (`configuration.py:19-45`: `[tool.mutmut]` wins outright). Inert
while read-only; lethal once the reader becomes a writer (D3).
**Prior art:** Cheliped `2fb23811` (worktree config rewrite; the keys it rewrites are deprecated in
3.6.0). In-repo: `host_contract.resolve_repository/_exclusive_file/_atomic_json` (canonical
identity + lock + atomic write, host-neutral); `reset_plan.worktree_paths/is_protected_worktree`
(reusable as-is); `gate_runner._atomic_private` (reusable; module import has side effects);
`with_snapshot.cmd_preflight` (CWD-bound, branded — NOT reusable as-is); `gate_runner.RunStore`
(gate-runs-specific — NOT reusable as-is); `run_bounded` (no cwd, SIGKILL only; the injected `run`
hook bypasses the Popen path).
**mutmut 3.6.0 facts (verified):** `pyproject.toml [tool.mutmut]` wins outright, else `setup.cfg`
(`configuration.py:19-45`); `paths_to_mutate` deprecated → `source_paths` (`:99-103`); `tests_dir`
deprecated and APPENDED to `pytest_add_cli_args_test_selection` (`:105-110`) — leaving it present
silently widens the baseline; `only_mutate`/`do_not_mutate` are `.py`/`*` globs (`:112-118`);
`pytest_add_cli_args` is a SEPARATE channel added to every pytest invocation (`:137`,
`__main__.py:401,408`); `results --all` needs `--all=true` (click option without `is_flag`, probed);
`export-cicd-stats` writes `mutants/mutmut-cicd-stats.json` whose `total` counts every generated
mutant regardless of status and whose per-status fields omit `not_checked` and
`caught_by_type_check` (`__main__.py:812-830`); statuses come from `status_by_exit_code`
(`:77-96`, a defaultdict → "suspicious"); generation happens inside `run` (`:1017-1021`), so no
count exists before the expensive phase.
**Assumptions:** A1 pytest + mutmut ≥ 3.6 on POSIX, else refuse by name. A2 the mapping is
repo-owned and checked in; the playbook never infers reachability. A3 equivalence/informational
survivor policy stays downstream. A4 the mapping IS the machine-readable mutation roster (one
list, cost lines included) — never a second copy of one.
**Simpler alternative:** keep 1.51.2's "downstream gates own scoping". Rejected by the owner.

## Decisions (David, 2026-09-09) — binding
- **Q2 — `--suite-args` is DEPRECATED OUTRIGHT.** In v1.52.0 it exists only to emit a migration
  refusal (naming the mapping and `pytest_add_cli_args`); removed in the next release. Selectors
  live in the mapping; NON-selection pytest arguments come from mutmut's effective
  `pytest_add_cli_args`, which D3 READS and D4 REPLAYS — otherwise the wrapper and mutmut can run
  materially different pytest configurations.
- **Q3 — 30s graceful window INSIDE an absolute deadline.** SIGINT at `deadline − 30s`, SIGKILL
  at the deadline. Never budget + 30s.
- **Q4 — line-anchored rewrite, fail-closed, no general TOML writer.** Must INSERT absent keys;
  must NEUTRALISE legacy `tests_dir` on the copy (or refuse), because mutmut appends it to the
  selection; `paths_to_mutate` MAY remain as the deprecated source root (`only_mutate` does the
  narrowing). Unsupported shapes (inline tables, multi-line arrays with comments) get a concrete
  migration instruction — and it is acknowledged that Cheliped's cited legacy roster shape
  (`paths_to_mutate` + `tests_dir` lists) is among them.
- **Q5 — "clean" is LITERAL.** Refuse on ANY non-ignored untracked file, not only test files
  under selected directories (selective detection misses `conftest.py`, helpers, fixtures, new
  source). Mutation runs occur at committed phase boundaries; full cleanliness is the simpler
  honest invariant. Never copy dirty state. Doctrine gains "commit the kill test, then
  re-measure".
- **Q6 — list-only by default; `--reap-stale` deletes.** The repo-wide lock is acquired BEFORE
  listing or reaping so setup cannot race cleanup. Delete only marked, lock-free worktrees; never
  automatically delete a retained forensic path.
- **Q7 — disagreement is fail-closed.** A missing or malformed CI export COUNTS as
  disagreement. Duplicate per-mutant names are rejected BEFORE totals are compared (one duplicated
  row can conceal one missing row).
- **Doctrine amendment — approved.** With an explicit authoritative mapping, falling back to the
  whole suite contradicts §4b; refusing and naming the roster gap is correct.
- **Non-dogfood boundary and the two dated debts — accepted.** For the local real-mutmut proof:
  preserve the COMPLETE log in-repo (`docs/plans/gated/2026-09-09-scoped-mutation-runner.real-mutmut.log`)
  and cite its run ID, HEAD, command, and mutmut version in the CHANGELOG — not one quoted line.

## Deliverables

### D0 — Named extractions so reuse is real, not narrated
- `with_snapshot.dirty_tracked(root) -> list[str]` AND `with_snapshot.untracked(root) -> list[str]`
  (non-ignored, `git status --porcelain --untracked-files=all`); `cmd_preflight` calls the first
  (byte-identical output pinned).
- `gate_runner.RunStore(common, run_id, keep, subdir="gate-runs")` + `prune_dir(root, keep,
  lock_name)` lifted so D6 shares the CODE with its own lock file.
- `run_bounded(argv, deadline_s, cwd=None, grace_s=30)`: `cwd` (mutmut config discovery is
  CWD-relative); SIGINT to the group at `deadline − grace`, SIGKILL at `deadline` (Q3); the
  injected `run` hook stays for argv-shape tests, and every lifecycle test drives a REAL child
  (the hook bypasses Popen).
- Identity/common-dir from `host_contract.resolve_repository(root)` — never `gate_runner.REPO`.
**Tests:** existing suites green; preflight output byte-identical; retention tests pass with the
default subdir; real-child SIGINT-then-SIGKILL timing test (a child that ignores SIGINT is killed
at the deadline, one that honours it exits in the grace window).

### D1 — Scope contract: `.tdd-playbook/mutation-scopes.json` IS the roster
**What:** `--scope <name>` selects `{ "sources": ["pkg/mod.py", "pkg/sub/*"], "tests":
["tests/test_mod.py", "tests/test_x.py::TestY"], "cost": "a survivor here costs …" }`. The file is
the repo's machine-readable mutation roster; §4a's "roster entry with no gate invocation is a
comment" parity test reads THIS file (the playbook ships the validator via `--dry-run`; the repo
wires it). A roster elsewhere → reconciliation assertion, never a second list.
**Validation (fact, not proxy):** sources resolve by REALPATH CONTAINMENT against mutmut's PARSED
`source_paths` (replaces the `:276` substring check; planted `--scope b` replay); each glob
matches ≥1 tracked file; each selector collects ≥1 test (`--collect-only -q` in the worktree,
with `pytest_add_cli_args` replayed); `cost` present; duplicate names rejected
(`object_pairs_hook`); no `..`/absolute paths; a source hit by `do_not_mutate` → refuse.
**Roster gap (§4b, amended doctrine):** a selector collecting zero → refuse: `could not narrow:
no test reaches <sources> — a ROSTER gap, not a gate defect`.
**Edge cases:** missing mapping → refuse + print a scaffold (never write it); unknown name →
refuse listing names; mapping untracked/dirty → refused by D2's literal-clean rule; size cap
256 KiB; mutmut unconfigured → existing refusal with the exact fix.
**UX:** `scope billing: 3 source(s) → 41 tests collected · cost: "…"` before anything runs.
**Anti-narrowing (cheap form):** per-scope counts + mapping sha256 in the D6 record. The
acknowledged-sha shape (`gate_plan.py:43`) → dated debt `mutation-scopes-acknowledged-sha`
(david, 2026-11-15).
**Integration:** *Consumes:* D3's mutmut-sourced reader (`mutmut_config_scope` deleted).
*Emits→consumer:* resolved scope → D3, D4; counts+sha → D6 → D8 doctor. *Parity:* both hosts,
path from `resolve_repository(root).root`. *Activation:* on; no mapping → refuse.

### D2 — One disposable worktree per invocation; both halves run inside it
**What:** require Git; refuse if `dirty_tracked(root)` OR `untracked(root)` is non-empty (Q5,
literal), naming the files and the rule ("commit the kill test, then re-measure"). Acquire the
repo-wide advisory lock (`_exclusive_file` on `<common>/tdd-playbook/mutation.lock`) FIRST
(Q6), then list stale worktrees, then `git worktree add --detach
<common>/tdd-playbook/mutation-worktrees/<run_id> HEAD`; write
`.tdd-playbook-mutation-run.json` (run_id, scope, HEAD, started — PROVENANCE) and hold a
per-run `flock` on `<worktree>/.tdd-playbook-mutation-run.lock` for the run's life (LIVENESS =
lock held, never a pid). Run D4 then D5 inside with `sys.executable`. Write D6 BEFORE cleanup;
`git worktree remove --force <that path>` only; failure → nonzero + `RETAINED: <path> — remove
with: git worktree remove --force <path>` as the LAST line.
**Stale worktrees (Q6):** under the repo lock, enumerate `mutation-worktrees/*` with our marker
whose per-run lock is free → LIST with the removal command. `--reap-stale` removes exactly those;
unmarked or locked dirs are named and left. A `RETAINED:` path is never auto-deleted. Never
`git worktree prune`; `is_protected_worktree` reused for anything registered elsewhere.
**D2b:** a second invocation refuses immediately naming the holder from D6's in-progress stub.
**Edge cases:** not git → refuse; add fails (leftover path) → refuse naming it; symlinked roots
(realpath both sides); disk full → refuse; SIGINT to the runner → cleanup still runs
(try/finally), record says `interrupted`. Second-order: no `mutants/` cache across runs — each
run pays generation for the NARROWED set; stated, accepted.
**Integration:** *Consumes:* D0, `host_contract._exclusive_file`, `reset_plan.*`. *Emits→
consumer:* marker → stale list/reap; lock → second invocation; retained line → operator. *Reverse
sweep:* `reset_plan`'s `shared` allowlist (`reset_plan.py:163`) gains `mutation-worktrees/`,
`mutation.lock`, `mutation-runs/` (this plan). *Activation:* on; no in-place switch (decision).

### D3 — Config adapter: ask mutmut, rewrite a COPY, read back
**What:** in the worktree, learn the EFFECTIVE config from mutmut (`sys.executable -c "from
mutmut.configuration import Config; …"`, `cwd=<worktree>`): parsed `source_paths`, `only_mutate`,
`do_not_mutate`, `pytest_add_cli_args`, `pytest_add_cli_args_test_selection`, and WHICH file
supplied them (pyproject `[tool.mutmut]` wins; else `setup.cfg`; `tox.ini`-only → refuse by
name). Rewrite THAT file in the worktree only, line-anchored (Q4): SET `only_mutate` = D1
sources, SET `pytest_add_cli_args_test_selection` = D1 tests (inserting either key if absent),
NEUTRALISE `tests_dir` on the copy (or refuse), preserve `do_not_mutate` and
`pytest_add_cli_args`, leave `paths_to_mutate` as the deprecated root with a printed note.
Unsupported shapes → refuse with a concrete migration instruction (name the key, the expected
one-key-per-line form, and that the legacy `paths_to_mutate` + `tests_dir` list shape is one
of them). Then READ BACK through mutmut and assert both keys took effect and `tests_dir` no
longer widens the selection. Real file: sha256 before/after in the main tree asserted equal.
**Edge cases:** unconfigured → existing refusal; mutmut import fails in the worktree
interpreter → refuse naming it; existing `only_mutate` → replaced, noted.
**UX:** `worktree config (pyproject.toml [tool.mutmut]): only_mutate=[…] selection=[…]
pytest_add_cli_args=[…] · read back OK · real config untouched (sha256 …)`.
**Integration:** *Emits→consumer:* worktree config → mutmut (D5); effective `pytest_add_cli_args`
→ D4; read-back → D6. *Reverse sweep:* `mutmut_config_scope` + tox.ini branch DELETED.

### D4 — Baseline narrowed identically, non-selection args replayed
**What:** baseline = `python -m pytest <D1 tests> <effective pytest_add_cli_args>` in the
worktree — the same selection AND the same non-selection arguments mutmut will use.
`--suite-args` → migration refusal (Q2). `baseline_share = baseline_s / (max_minutes*60)`; if
the baseline alone exceeds a fifth of the budget, print `BASELINE DOMINATES: <s>s of <budget> —
the GATE is misconfigured (scope's selection too wide), not the module` and continue (a
diagnosis; the projection decides affordability).
**Edge cases:** red in worktree but green at HEAD → refuse naming the test; all-skipped →
UNMEASURED refuse; `--collect-only` inside `pytest_add_cli_args` → refuse (it would collapse the
baseline); existing refusals kept.
**Knobs:** `--expected-mutants`/`--factor` stay this release (generation is inside `run`); dated
debt `projection-from-observed-count` (david, 2026-11-15). `--dry-run` = validate everything and
stop.

### D5 — Bounded run, graceful interrupt, FULL accounting from ONE per-mutant source
**What:** `mutmut run` via `run_bounded(cwd=worktree, deadline, grace=30)`. Afterwards (complete
OR cut off) read `mutmut results --all=true` as the ONE per-mutant status source; REJECT
duplicate mutant names first (Q7); classify each into exactly one bucket: **decided** (killed,
survived) · **terminal-unscored** (no tests, skipped, suspicious, timeout, segfault, caught by
type check) · **unfinished** (check was interrupted by user, not checked). Unknown status →
refuse. Denominator: `mutmut export-cicd-stats` → `total`; assert `len(rows) == Σ(buckets) ==
total`; per-status fields compared on the fields it emits. Missing or malformed export, or ANY
disagreement → REFUSE with both numbers (Q7). Complete run: unscored > 0 → refuse to certify.
Timeout: `PARTIAL — kill rate <k>/<k+s> = <pct>% over <decided> decided, <u> unscored, <n>
unfinished at cutoff (<i> interrupted mid-check, <q> not yet checked) — NON-AUTHORIZING`,
survivor list, exit 1. Joint reporting only if a future mutmut stops distinguishing the two.
**Property test:** buckets partition any multiset over mutmut's vocabulary; unknown raises;
duplicates raise.
**Calibration seam:** the brief KEEPS `killed + survived < generated` (oracle anchor for
`unmeasured-not-certified`) and ADDS the three-bucket restatement; `scenarios.json` untouched;
ledger row with predicted direction "no change on the 8 mutation-runner scenarios".

### D6 — Run record under the common dir, with a CODE consumer
`<common>/tdd-playbook/mutation-runs/<run_id>.json`: `in-progress` stub at start (read by D2b's
refusal), full record BEFORE cleanup: scope, sources, tests, counts, mapping sha, HEAD, worktree,
baseline_s/share, `pytest_add_cli_args` replayed, budget, buckets, config file + read-back, exit
reason, timestamps. 0600, atomic, keep 20 via D0 `prune_dir`. Consumer: D8 doctor line.
Registered as `emits` with consumers `[install_into_repo.py --doctor, "David, reading the doctor
line"]`. Unwritable dir → still report, exit nonzero naming the record failure.

### D7 — Doctrine + consumers (prose; pinned by needles + ledger + validate)
`/mutate` step 2 (mapping; `pytest_add_cli_args`; baseline share; buckets; commit-then-re-measure;
`--suite-args` gone), `mutation-runner` brief (same; keep `killed + survived < generated`;
`with_snapshot begin/verify` rescoped to non-runner passes), SKILL §4b worked example (this
runner first, Cheliped second; the "does not yet narrow" sentence dies), §4b + brief + command
"keeps the whole folder" → "…or, with an explicit mapping, refuses and names the roster gap",
SKILL `:1282` isolated-worktree advice cites the runner, `capabilities.json` `mutation-preflight`
(summary, `activation.switch`, `surfaces`, `exercised_by`, `emits`; close
`scoped-baseline-and-partial-measurement`; re-scope the Codex-parity debt), `CLAUDE.md` standing
prompt step 3b (seed the mapping from the existing roster), `docs/calibration/ledger.md` row,
CHANGELOG 1.52.0 with the Cheliped comparison, per-phase targeted-mutant scores, and the
real-mutmut proof citation (run ID, HEAD, command, mutmut version, log path).

### D8 — Doctor + refresh surface (adoption)
`install_into_repo.py --doctor`: `mutation scopes: N entries (validated) | MISSING — run
mutation_run.py --dry-run --scope <name>` and `last mutation run: <scope> <when> <result>` from
D6. Standing prompt step 3b.

### Unenforceable deliverables (prose)
- Dogfood limit: no in-repo mutmut config; fixture repos + one LOCAL real-mutmut run with the
  complete log preserved in-repo. RUNNING downstream is NOT claimed.
- Cheliped comparison (generalised vs left downstream) in the CHANGELOG.

## Phases (each: red tests committed → implement → suite green → targeted mutants recorded → commit)
1. D0 (extractions, `run_bounded` deadline semantics) — pure refactor + real-child timing test.
2. D1 + D3 reader (mapping, containment, mutmut-sourced effective config, `tox.ini` refusal).
3. D3 writer + read-back (Q4 rules) + D4 (replayed args, `--suite-args` migration refusal).
4. D2 + D2b + stale list/`--reap-stale` + `reset_plan` allowlist.
5. D5 accounting + D6 record.
6. D7 + D8; local real-mutmut proof; CHANGELOG; version bump; release gate.

## §6c flow table
| flow | producer | consumer | liveness test |
|---|---|---|---|
| resolved scope (+counts, sha) | D1 | D3, D4, D6 | planted bad entries; `--scope b` replay |
| effective config + file + `pytest_add_cli_args` | D3 reader (mutmut) | D3 writer, D4 | tox.ini-only refuses; pyproject-over-setup.cfg; args replayed |
| worktree config | D3 writer | mutmut (D5) — read back via mutmut | REAL: read-back keys; `tests_dir` neutralised; generated count == narrowed |
| real-config hash | D3 | planted test + operator | hash unchanged; planted expectation flip |
| baseline_s / share | D4 | projection, D6, `/mutate`, brief | dominates-named |
| buckets + denominator | D5 | D6, `/mutate`, brief | property; dup names; missing export refuses; REAL PARTIAL |
| marker + per-run lock | D2 | stale LIST; `--reap-stale` | list names lock-free dirs; reap spares a live child |
| repo lock | D2b | second invocation; stale list | refuses naming holder; list under lock |
| run record | D6 | D8 doctor, human | record-before-cleanup; unwritable → nonzero; doctor reads |
| shared artifacts | D2/D2b/D6 | `reset_plan --shared` | rows appear |
| brief vocabulary | D7 | calibration oracle (unchanged) | ledger row; regex untouched |

## Tripwire deliverable list — FILLED AT COMPLETION (2026-09-09)
Tripwire: 10/10 BUILT + WIRED + ACTIVATED + EXERCISED. Weaker truth: the REAL-mutmut rows are
EXERCISED locally (mutmut 3.6.0 present) and reported UNMEASURED in CI by design; RUNNING in a
downstream repo is NOT claimed. Per-phase targeted-mutant scores: D0 7/7 · D1+D3-reader 7/7 ·
D3-writer+D4 7/7 · D2 6/7 (+1 equivalent, recorded) · D5+D6 7/7 (plus the two Phase 4 re-measures, 9/9 in the same run) · D8 4/4.
| deliverable | BUILT | WIRED | ACTIVATED | EXERCISED |
|---|---|---|---|---|
| D0 extractions | with_snapshot/gate_runner/run_bounded/host_contract | callers switched | — | suites green; byte-identical preflight; real-child timing |
| D1 mapping = roster | `load_scopes`, containment | `--scope` | on (missing → refuse) | planted entries; `--scope b`; roster-gap wording |
| D2 worktree + stale list/reap | `Worktree` ctx mgr, marker, per-run flock | main() | on; reap opt-in | leftover/protected/retained; literal-clean refusal; list-only; reap spares live child |
| D2b repo lock | `_exclusive_file` | main() (before list) | on | second invocation refuses |
| D3 adapter | mutmut-sourced reader, anchored writer, read-back | worktree path | on | REAL read-back; tox.ini; precedence; `tests_dir`; hash; migration text |
| D4 baseline parity | `baseline(selection, add_args)` | main() | on | `--suite-args` migration refusal; dominates line; args replayed |
| D5 accounting | `classify`, deadline bound | `run_bounded` | on | property; dup names; missing export; REAL PARTIAL |
| D6 record | `write_record` + stub | before cleanup | on | ordering; unwritable; doctor reads |
| D7 doctrine | SKILL/commands/agents/registry/CLAUDE.md/ledger | needles + validate + scoreboard | — | test_agents; registry; scoreboard integrity |
| D8 doctor | `--doctor` lines | installer | on | planted missing mapping → line present |

## Rejected / re-scoped review items
- Copy the working tree instead of HEAD: reintroduces dirty-tree replication (constraint 3).
- Automatic startup reap (v2): "may" is not "must"; restored as `--reap-stale` (Q6).
- Read `mutants/*.meta` directly: private file (constraint 4); `results --all=true` is public.
- Delete `--expected-mutants`/`--factor` now: generation is inside `run`; dated debt.
- Selective untracked-test detection (v2/v3 default): replaced by literal clean (Q5).
- Print-and-continue on view disagreement (v2): replaced by refuse (Q7).
