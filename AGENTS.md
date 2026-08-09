# AGENTS.md — standing memory for the TDD Playbook repo

## STANDING REQUIREMENT — calibration is not optional (§13 decay principle)

Every gate in this plugin is a decaying asset; the calibration schedule IS the product.
The scoreboard (`docs/calibration/history.md`) must show a live cadence before v2.0 ships.

**Staleness is now MECHANICAL, not a memory (audit finding F5).** The 14-day cadence is enforced by
`calibration/check_staleness.py` — it reads `history.md`, finds the most recent dated run, and exits
nonzero when it is missing or older than the threshold (`--as-of` injects the date for tests). The
release gate runs it `--warn-only` (loud, doesn't wedge a code release on a calibration chore), and
It also runs inside the blessed gate, so the CI job in `.github/workflows/gate.yml` re-runs it
off-box on every push (the CIVerd engine that used to do this was retired in v1.32.0).
Pinned by planted-date tests in `calibration/test_harness.py`. This replaces "David remembers"; the
run itself still needs a real `Codex` binary (below).

**Weekly (needs a real `Codex` binary — David runs or schedules this):**
```bash
python3 calibration/check_staleness.py            # deterministic: is the scoreboard stale? (F5)
python3 calibration/run_calibration.py            # cheap model, hard caps; appends history
                                                  # (3 reps/scenario by default since v1.17 —
                                                  # PASS only at k/k; AMBER is nonzero and
                                                  # promotes to BLOCKING on a repeat)
python3 plugins/tdd-playbook/bin/capability_registry.py doctor   # bundle check (v1.23, David's
                                                  # ships-on-or-triggered rule): capture must
                                                  # read ON on this machine, and the dark
                                                  # inventory is the list to act on (the old
                                                  # plan-authoring/repos.yml line went with the
                                                  # CIVerd retirement in v1.32.0)
                                                  # (v1.24) run_calibration's tail now prints the
                                                  # §6c dataflow rollup + DATAFLOW TREND line —
                                                  # READ IT: a flagged excluded-share trend means
                                                  # the exemption list is doing the tests' work
                                                  # (the check is gate_yield.py dataflow-trend;
                                                  # this line is a pointer, not the check)
```
- A plant surviving to a clean verdict is a **BLOCKING failure** — fix the agent, never the
  plant. File it, fix it, re-run before anything else ships.
- `--dry-run` is the free CI-safe validation; it does NOT count as calibration.
- Run as a NON-root user — the very first attempt logged INVALID because it ran under root, where
  the headless doer couldn't run (see `TDD_PLAYBOOK_CALIBRATION_ARGS` in `run_calibration.py`'s
  header for the sandbox-args env knob).
- Status as of 2026-07-28: last live run 2026-07-27 on haiku — 9/9 on the shipped suite after ONE
  agent fix (a `vacuous-mutation-scope` BLOCKING FAIL; the `mutation-runner` vacuity guard now
  resolves-the-scope-first), and — stated because the old summary rounded toward green (§13:
  that pattern is the loudest signal there is) — the same-day CORPUS rows show
  `csv-escape-fixed-at-call-site` failing twice and `shadowed-import-vacuous-suite` three times
  before their terminal passes. Under N=1 nothing distinguished "fixed" from "lucky roll"; v1.17's
  repeat sampling + AMBER verdict exists precisely because of those rows, and the NEXT run
  (~2026-08-10) is the first under the new instrument — it must land recall AND FP numbers.
  If `docs/calibration/history.md` is missing or its last entry is stale >14 days, raise it with
  David proactively — but READ `history.md` first; do not repeat the stale-status error of
  claiming it was never seeded.
- **Corpus: seeded 2026-07-27** — first co-evolution cycle complete: 4 adversary-authored plants
  (by `Codex-fable-5`, David-approved) in `calibration/corpus/approved/`, so live runs now cover
  the shipped + corpus suite. (Never write the scenario COUNT down here — hand-maintained
  counts drift silently; the harness derives the composition into every history.md run header,
  and `run_calibration.py` prints `selected N of M` live. That is the source of truth.)
  Since v1.17 every plant class carries a PAIRED CLEAN CONTROL (`control_for`) so false
  positives are measured, not just recall; the pair quota is mechanical — unpaired proposals
  are rejected at authoring, at `--approve`, and by the dry-run pairing invariant. Keep the
  cycle going each calibration period
  (`author_plants.py` below); the corpus only grows. Known pipeline limitation: plants can only
  MODIFY existing fixture files (`apply_edits` cannot create files — 4 of 6 first-batch candidates
  were mechanically rejected for that; the `create` capability is now OWNED DATED DEBT on
  `calibration-loop` (expires 2026-09-15, trigger string-pinned in test_capability_registry) —
  v1.24 promoted it from "possible future enhancement" because §6c's writer-with-no-reader
  plants need new fixture files, making the gap load-bearing).

**Each cycle, grow the corpus (co-evolution — a frozen plant library is a static gate):**
```bash
python3 calibration/author_plants.py --model <adversary >= doer tier>   # -> corpus/proposed/
python3 calibration/author_plants.py --list                             # review queue
python3 calibration/author_plants.py --approve <id>                     # human-reviewed only
```
The corpus only GROWS; plants record their authoring model.

**Quarterly:** the HACK_CATALOG refresh ritual (`docs/HACK_CATALOG.md`, bottom section) —
new system cards / METR / literature → new entries → new guard patterns WITH planted tests.
`run_calibration` prints a DECAY WARNING when the catalog is >100 days stale; treat it as a
due task, not noise.

**On any doer-model upgrade:** run calibration BEFORE trusting the new model's work in
Playbook repos (verifier-strength policy, SKILL.md §13).

## STANDING PROMPT — refreshing downstream repos (vendored `.Codex/` copies)

When David asks to update a repo that carries the vendored Playbook (or after any release
here), use/give this prompt in THAT repo's session:

```
Refresh the vendored TDD Playbook in this repo to the latest version and adopt its new
mechanisms.

1. REFRESH: Clone https://github.com/davalst/tdd-playbook (shallow is fine) to a temp
   directory and run: python3 <clone>/scripts/install_into_repo.py <this repo's root>
   The installer is reconciling: it prunes stale playbook hooks from .Codex/settings.json
   and adds current ones (the four BLOCKING guards: test_weakening_guard, test_lock_guard,
   snapshot_guard, tag_guard; plus the opt-in exitcode/overmock/exhaustive/flaky/red_lock,
   which ship OFF since v1.32.0 on 31 warns / 0 blocks). My own
   non-playbook hooks must survive — verify that before committing.

2. VERIFY: Confirm .Codex/bin/ contains tdd_lock.py, with_snapshot.py, grade_from_otel.py,
   capability_registry.py, and dataflow_sweeps.py (with its _debt.py sibling); confirm
   .Codex/settings.json has the PreToolUse guards; confirm the vendored SKILL.md mentions
   TEST-LOCK, the decay principle, the ACTIVATED Tripwire leg (§6a wiring liveness),
   §6c Dataflow Liveness, and the §1 seam rule + §6c family parity sweep (v1.26).

3. SEED THE REGISTRY (if this repo has no capabilities.json yet — don't wait for the next
   feature; the existing features are the ones already dark): run
   `python3 .Codex/bin/capability_registry.py init`, then replace the example entry with
   real entries enumerated from this repo's entry points — the daemon/app factory,
   schedulers/cron registrations, tool registrations, event topics, config gates,
   per-surface adapters. Cover the MAJOR subsystems honestly rather than everything
   perfectly; register what you couldn't map as an integration_debt entry (owner: me, dated
   expiry) so completeness is a loan, not a hope. `validate` must pass before you commit.
   If the registry already exists: run `validate` (fix violations) and `doctor`, and put the
   dark-feature inventory in your report.

4. CALIBRATION STALENESS CHECK (before deleting the temp clone): read
   <clone>/docs/calibration/history.md. If it is missing or its last entry is >14 days old,
   FLAG IT PROMINENTLY in your report: "the verification gates just vendored here have
   never been / not recently been live-calibrated" — cite the playbook AGENTS.md standing
   requirement. This is David's action in the tdd-playbook repo (needs a real `Codex`
   binary and budget), NOT something to run in this repo — your job is to make the
   staleness impossible to miss, not to run it.

   Then delete the temp clone, commit .Codex/ (+ capabilities.json) as
   "chore: refresh vendored TDD Playbook to v<version>", and push.

5. ADOPT — these change how you work in this repo from now on:
   - Integrity guards BLOCK by default (test weakening, snapshot auto-updates, exit calls
     in tests). If one blocks you, that's the system working — fix the source, don't look
     for a way around it. Demotion is TDD_PLAYBOOK_HOOK_<NAME>=warn, but ask me first.
     And RECORD the block (§12, v1.28): `python3 .Codex/bin/guard_note.py record --gate
     <name> --objected "..." --performed-elsewhere yes|no --dropped "..."`. Splitting a
     blocked command into pieces looks identical to complying with it; the record is what
     tells the two apart, and unaccounted blocks are reported every calibration cycle.
   - Use /tdd-lock after committing red tests for feature work; unlock only via /tdd-unlock
     with a real journaled reason.
   - /edge, /mutate, /probe — and now /tdd-plan and /integration-audit — end by dispatching
     their adversary agents and must report "Loop closed: yes/no".
   - Plans carry an INTEGRATION SURFACE per deliverable (consumes / emits→named consumer /
     surface parity / reverse sweep / activation) so features never ship as islands; a
     write-only loop becomes owned, dated integration debt, never a silent deferral.
   - §6c Dataflow Liveness: plans carry a flow table (`flow · producer · consumer ·
     liveness test`) for feature/migration work; wire the Tier-1 sweeps
     (`.Codex/bin/dataflow_sweeps.py` — render-pairing/exemption-prose blocking,
     ghost-gates advisory) where the flow kind exists in this repo, with a repo-local
     sweep config; migrations prove CONSUMER PARITY for the seam they replace (enumerate
     what the old seam fed; each consumer fed / retired-with-deletion / dated debt).
   - §13 guard calibration (v1.25): a NEW guard/sweep/tripwire born from a specific defect
     is replayed against the motivating artifact (`git show <pre-fix-rev>:<file>`) before
     it is trusted, then the defect shape is FROZEN as a planted fixture citing the
     pre-fix sha in its docstring — red-first alone proves a guard can fail, not that it
     fails for the reason it was built. And a test double may fake behavior but never
     supply an attribute/method/seam production lacks (build doubles with
     create_autospec/equivalent so a missing seam raises).
   - §1 seam rule + §6c family parity sweep (v1.26): test at the seam you don't own — a
     test whose every assertion reads an object your own code constructed, with no
     representation of the consumer, is a SELF-consistency test (it would still pass with
     the other side of the seam deleted); and where N pluggable members share a host
     (handlers, hooks, adapters, middleware), ONE vacuity-guarded repo-local test
     enumerates the family from the REAL registry and asserts the host's contract per
     member. Plan-time, emits→consumer is answered at FIELD granularity (cite the line
     that reads the field). A 100% mutation score does not cover any of this — the score
     is blind across a misunderstood seam (§4).
   - The Tripwire has FOUR legs now: BUILT + WIRED + ACTIVATED + EXERCISED, with wiring
     proven through the PRODUCTION composition root (self-assembling fixtures don't count).
   - The registry only GROWS as features land; `validate` joins the release gate and
     `doctor` prints the dark-feature inventory. When "I built X but never see it running"
     strikes, run /integration-audit instead of an ad-hoc dig.
   - Every new mock in a test needs a one-line justification.
   - Flaky quarantines need an owner and an expiry date.

6. REPORT: Tripwire-style summary — what was refreshed, what was verified (file paths),
   the registry state (seeded/validated + the doctor's dark-feature inventory), the
   calibration-staleness flag if it fired, the commit sha, and anything from my repo-local
   testing conventions that conflicts with the new defaults (stricter rule wins; flag
   conflicts, don't resolve silently).
```

Local-machine plugin installs update separately (no prompt needed):
`Codex plugin marketplace update david-tools && Codex plugin update tdd-playbook@david-tools`

## Release discipline for THIS repo

- Every mechanical change ships with a planted-input test (a planted violation that slips
  past a check is a failure). Suites: `plugins/tdd-playbook/tests/test_*.py` +
  `calibration/test_harness.py` — run them ONLY via `sh scripts/civerd_gate.sh`, the ONE
  blessed gate entrypoint (probe run 2, 2026-07-28: the prose loop and the engine's gate
  command silently diverged and calibration/'s 110 checks never ran in the gate; a script
  can be probed and planted-tested, a prose command cannot). Scenario sanity:
  `calibration/run_calibration.py --dry-run`.
- Release gate before any version bump: all suites green, `calibration/check_staleness.py
  --warn-only` run (F5 — surfaces a stale scoreboard loudly), `hooks.json`/`plugin.json`/
  `marketplace.json` parse, `capability_registry.py validate` passes on this repo's own
  `capabilities.json` (we eat the §6a dogfood — enforced MECHANICALLY by
  `test_capability_registry.py::test_own_registry` on every suite run with the real date,
  so expired integration debt fails the tests, not just the checklist),
  `calibration/check_scoreboard_integrity.py --baseline-rev <previous release tag>` exits 0
  (history append-only, corpus immutable, oracles never weakened unjournaled, and — v1.22
  rule (d) — gate surfaces [SKILL `##` sections, agents/*.md, commands/*.md] never removed
  without a `calibration/gate-changes.md` entry; ALSO enforced mechanically:
  `test_harness.py` runs it against the latest tag on every suite run),
  `python3 calibration/check_staleness.py --history docs/calibration/quarterly.md
  --max-age-days 100 --warn-only` (the quarterly-bundle clock: catalog refresh · lift read ·
  cross-tier — lapsed quarters are loud on every release),
  and a scratch-repo `install_into_repo.py` run proving cloud parity (new bins + hooks
  present, `${CLAUDE_PLUGIN_ROOT}` rewritten, `.Codex/.gitignore` written), plus
  `python3 scripts/install_into_repo.py --doctor .` on THIS repo (H8 guards-liveness:
  a commit postdating the last guard heartbeat means the release was built guard-dark —
  the 2026-07-28 incident; also catches standing demotions and version skew).
- Version bumps update ALL FOUR identity files —
  `plugins/tdd-playbook/.Codex-plugin/plugin.json`, `.Codex-plugin/marketplace.json`,
  `plugins/tdd-playbook/adapters/Codex/adapter.json` and `…/adapters/codex/adapter.json` —
  plus CHANGELOG.md. (`test_installer.py::test_release_version_identity` pins all four EQUAL;
  this line said "BOTH … and …" until v1.32.0, naming two of the four. The mechanism was
  right and the doctrine was stale — which is the direction to expect, and why the pin, not
  this sentence, is the control.)
- **Releasing (v1.32.0 onward — the CIVerd wall is retired).** A release is: the blessed gate
  green on the commit you are shipping → version bumped in all four identity files → **David**
  creates the tag → push. There is no verdict, no engine, no polling, and no script that
  creates a tag.
  1. `sh scripts/civerd_gate.sh > /tmp/gate.out 2>&1; rc=$?` — **never pipe it**; a piped `$?`
     is `tail`'s, and `exitcode_guard` will say so (§4a: a discarded exit code is a discarded
     truth). `rc` must be `0`.
  2. Bump the four identity files + `CHANGELOG.md`; regenerate
     `docs/reference/current-state.md`; commit.
  3. **`git push origin main` FIRST — before any tag.** The order is the point, not a
     formality: `.github/workflows/gate.yml` triggers on push, so it can only re-run the gate
     on a commit that has been pushed. Tagging first would mean the check David is told to
     read has never run on the commit he is tagging, and the independent re-execution that
     justifies keeping any CI at all would be delivered into a moment nobody can stand in.
  4. **Wait for the `gate` check to go green on that exact sha** (`gh run list --branch main
     --limit 1`, or the commit's check mark on GitHub). This is the ONLY independent evidence
     that the gate passed somewhere the agent cannot reach; step 1 is the agent's own machine
     reporting on itself. A red or missing check stops the release — a missing check is not a
     pass, it usually means the workflow failed to parse.
  5. **David** runs `git tag -a vX.Y.Z -m "…"` (use `-s` once a signing key is configured —
     `git config user.signingkey` is currently unset, so `-s` fails today; tracked as dated
     debt on `release-tag-authority`), then `git push origin vX.Y.Z`.

  **What authorizes a release is David tagging it.** The model can propose, gate, and bump; it
  cannot tag. This is DELETION, not a smaller wall — with no verdict anywhere in the release
  path there is nothing to forge, argue past, or `--force`. Two mechanical halves, each
  stating its own scope (§12 — a control carries its denominator):
  - `test_installer.py::test_no_script_creates_a_release_tag` parses every TRACKED
    `.py`/`.sh`/`.yml` (roster derived from `git ls-files`, so a new tool directory or a
    `.github/workflows/*.yml` cannot fall outside it) and REDs the gate if any creates or
    pushes a tag. Covers committed automation; blind to untracked trees such as
    `.Codex/worktrees/*`.
  - `hooks/scripts/tag_guard.py` (PreToolUse/Bash, **BLOCKING**) stops a SESSION typing
    `git tag`, `git push --tags`, `git update-ref refs/tags/…` or `gh release create` —
    including in untracked trees, which is the half the scanner cannot see. It ships
    downstream with `hooks/scripts/`; `tests/` does not.

  **What neither half can do:** bind a human at a terminal, or bind an actor who edits the
  hook. A repo-side check never can. The binding control there is a GitHub `v*` ruleset
  restricting tag creation to `davalst` — dated debt on `release-tag-authority` until armed,
  stated rather than assumed.
- **Historical verdicts stay readable.** `plugins/tdd-playbook/bin/verify_verdict.py` (+
  `_ed25519_verify.py`) is KEPT and DELIBERATELY UNWIRED: stdlib-only, no caller, the sole way
  to check a pre-v1.32 signed CIVerd bundle —
  `python3 plugins/tdd-playbook/bin/verify_verdict.py --sha <sha> --ledger <verdicts.jsonl>`.
  It still has no `--force` and still fails closed, and it is still cross-validated against
  memrebel's golden corpus (`tests/fixtures/civerd_crossvalidation_corpus.json`). It is an
  archive reader, not a gate; **do not re-wire it into the release path** — a consumer gives
  back the exact property the retirement bought.
- Roadmap context: `docs/plans/implementation-plan-2026-07.md` (WS5 — Stagehand-Python
  spike, §5b agent evals, positioning, public scoreboard — is built but NOT started;
  v2.0 is gated on ≥1 month of live calibration history).
