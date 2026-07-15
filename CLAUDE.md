# CLAUDE.md — standing memory for the TDD Playbook repo

## STANDING REQUIREMENT — calibration is not optional (§13 decay principle)

Every gate in this plugin is a decaying asset; the calibration schedule IS the product.
The scoreboard (`docs/calibration/history.md`) must show a live cadence before v2.0 ships.

**Weekly (needs a real `claude` binary — David runs or schedules this):**
```bash
python3 calibration/run_calibration.py            # cheap model, hard caps; appends history
```
- A plant surviving to a clean verdict is a **BLOCKING failure** — fix the agent, never the
  plant. File it, fix it, re-run before anything else ships.
- `--dry-run` is the free CI-safe validation; it does NOT count as calibration.
- Run as a NON-root user — the very first attempt logged INVALID because it ran under root, where
  the headless doer couldn't run (see `TDD_PLAYBOOK_CALIBRATION_ARGS` in `run_calibration.py`'s
  header for the sandbox-args env knob).
- Status as of 2026-07-15: **seeded and clean.** Last live run 2026-07-09 —
  4/4 plants caught after two agent-fix rounds (commit `8adaf99`); the suite has since grown to
  5 scenarios (added `vacuous-mutation-scope` → `mutation-runner`), so the next run re-baselines
  at 5/5. Next run due ~2026-07-23 (14-day cadence). If `docs/calibration/history.md` is missing
  or its last entry is stale >14 days, raise it with David proactively in any session that touches
  this repo — but READ `history.md` first; do not repeat the stale-status error of claiming it was
  never seeded.
- **Still owed (separate from the run cadence): the corpus has not grown** —
  `calibration/corpus/approved/` is empty, so calibration still runs only the original
  hand-written scenarios. The co-evolution step (`author_plants.py` below) is the outstanding gap.

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

## STANDING PROMPT — refreshing downstream repos (vendored `.claude/` copies)

When David asks to update a repo that carries the vendored Playbook (or after any release
here), use/give this prompt in THAT repo's session:

```
Refresh the vendored TDD Playbook in this repo to the latest version and adopt its new
mechanisms.

1. REFRESH: Clone https://github.com/davalst/tdd-playbook (shallow is fine) to a temp
   directory and run: python3 <clone>/scripts/install_into_repo.py <this repo's root>
   The installer is reconciling: it prunes stale playbook hooks from .claude/settings.json
   and adds current ones (test_lock_guard, snapshot_guard, overmock_guard). My own
   non-playbook hooks must survive — verify that before committing.

2. VERIFY: Confirm .claude/bin/ contains tdd_lock.py, with_snapshot.py, grade_from_otel.py,
   and capability_registry.py; confirm .claude/settings.json has the PreToolUse guards;
   confirm the vendored SKILL.md mentions TEST-LOCK, the decay principle, and the ACTIVATED
   Tripwire leg (§6a wiring liveness).

3. SEED THE REGISTRY (if this repo has no capabilities.json yet — don't wait for the next
   feature; the existing features are the ones already dark): run
   `python3 .claude/bin/capability_registry.py init`, then replace the example entry with
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
   never been / not recently been live-calibrated" — cite the playbook CLAUDE.md standing
   requirement. This is David's action in the tdd-playbook repo (needs a real `claude`
   binary and budget), NOT something to run in this repo — your job is to make the
   staleness impossible to miss, not to run it.

   Then delete the temp clone, commit .claude/ (+ capabilities.json) as
   "chore: refresh vendored TDD Playbook to v<version>", and push.

5. ADOPT — these change how you work in this repo from now on:
   - Integrity guards BLOCK by default (test weakening, snapshot auto-updates, exit calls
     in tests). If one blocks you, that's the system working — fix the source, don't look
     for a way around it. Demotion is TDD_PLAYBOOK_HOOK_<NAME>=warn, but ask me first.
   - Use /tdd-lock after committing red tests for feature work; unlock only via /tdd-unlock
     with a real journaled reason.
   - /edge, /mutate, /probe — and now /tdd-plan and /integration-audit — end by dispatching
     their adversary agents and must report "Loop closed: yes/no".
   - Plans carry an INTEGRATION SURFACE per deliverable (consumes / emits→named consumer /
     surface parity / reverse sweep / activation) so features never ship as islands; a
     write-only loop becomes owned, dated integration debt, never a silent deferral.
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
`claude plugin marketplace update david-tools && claude plugin update tdd-playbook@david-tools`

## Release discipline for THIS repo

- Every mechanical change ships with a planted-input test (a planted violation that slips
  past a check is a failure). Suites: `plugins/tdd-playbook/tests/test_*.py` +
  `calibration/test_harness.py`; scenario sanity: `calibration/run_calibration.py --dry-run`.
- Release gate before any version bump: all suites green, `hooks.json`/`plugin.json`/
  `marketplace.json` parse, `capability_registry.py validate` passes on this repo's own
  `capabilities.json` (we eat the §6a dogfood — enforced MECHANICALLY by
  `test_capability_registry.py::test_own_registry` on every suite run with the real date,
  so expired integration debt fails the tests, not just the checklist),
  and a scratch-repo `install_into_repo.py` run proving cloud parity (new bins + hooks
  present, `${CLAUDE_PLUGIN_ROOT}` rewritten).
- Version bumps update BOTH `plugins/tdd-playbook/.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`, plus CHANGELOG.md.
- Roadmap context: `docs/plans/implementation-plan-2026-07.md` (WS5 — Stagehand-Python
  spike, §5b agent evals, positioning, public scoreboard — is built but NOT started;
  v2.0 is gated on ≥1 month of live calibration history).
