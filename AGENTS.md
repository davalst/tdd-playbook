# AGENTS.md — standing memory for the TDD Playbook repo

## STANDING REQUIREMENT — calibration is not optional (§13 decay principle)

Every gate in this plugin is a decaying asset; the calibration schedule IS the product.
The scoreboard (`docs/calibration/history.md`) must show a live cadence before v2.0 ships.

**Staleness is now MECHANICAL, not a memory (audit finding F5).** The 14-day cadence is enforced by
`calibration/check_staleness.py` — it reads `history.md`, finds the most recent dated run, and exits
nonzero when it is missing or older than the threshold (`--as-of` injects the date for tests). The
release gate runs it `--warn-only` (loud, doesn't wedge a code release on a calibration chore), and
CIVerd runs it as a `staleness` check so the independent engine flags decay on its daily timer.
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
                                                  # read ON on this machine, and dark-inventory
                                                  # shows if plan-authoring still awaits the
                                                  # repos.yml arming — OFF here is a due task
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
   and adds current ones (test_lock_guard, snapshot_guard, overmock_guard, and the
   advisory exitcode_guard + exhaustive_claim_guard). My own
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
- Version bumps update BOTH `plugins/tdd-playbook/.Codex-plugin/plugin.json` and
  `.Codex-plugin/marketplace.json`, plus CHANGELOG.md.
- **CIVerd release gate (audit finding F4).** The release TAG is created ONLY by
  `scripts/release_verify.py`, and only after the shipped `verify_verdict.py` returns 0 for the
  release SHA — a fresh, signed, GREEN CIVerd run verdict from a live engine, verified against the
  vendored issuer key with a stdlib-only Ed25519 verifier (no third-party deps — the plugin is
  stdlib-only by invariant, and CIVerd's runner installs only pytest). CIVerd signs a verdict
  AFTER a commit lands, so this gates the release SHA you actually ship (not its parent — the
  parent skips the agent-written bump commit). There is NO bypass flag: `push → CIVerd signs →
  scripts/release_verify.py --wait-s … → tag only on exit 0`. A checklist line is a wish; this
  script is the control. Cross-validated against memrebel's golden corpus
  (`tests/fixtures/civerd_crossvalidation_corpus.json`) — canonicalization + all reason strings
  must match the reference implementation exactly. NOTE: `verify_verdict.py` shipped IN v1.12.0, so
  v1.12.0 itself can't be tag-gated by it; the tag-gate is the standing control from v1.13.0 on.
- Roadmap context: `docs/plans/implementation-plan-2026-07.md` (WS5 — Stagehand-Python
  spike, §5b agent evals, positioning, public scoreboard — is built but NOT started;
  v2.0 is gated on ≥1 month of live calibration history).
