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
- Status as of 2026-07-08: **history has never been seeded** — the first live run is still
  owed. If `docs/calibration/history.md` is missing or stale >14 days, raise it with David
  proactively in any session that touches this repo.

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

2. VERIFY: Confirm .claude/bin/ contains tdd_lock.py, with_snapshot.py, and
   grade_from_otel.py; confirm .claude/settings.json has the PreToolUse guards; confirm
   the vendored SKILL.md mentions TEST-LOCK and the decay principle. Then delete the temp
   clone, commit .claude/ as "chore: refresh vendored TDD Playbook to v<version>", and push.

3. ADOPT — these change how you work in this repo from now on:
   - Integrity guards BLOCK by default (test weakening, snapshot auto-updates, exit calls
     in tests). If one blocks you, that's the system working — fix the source, don't look
     for a way around it. Demotion is TDD_PLAYBOOK_HOOK_<NAME>=warn, but ask me first.
   - Use /tdd-lock after committing red tests for feature work; unlock only via /tdd-unlock
     with a real journaled reason.
   - /edge, /mutate, and /probe end by dispatching their adversary agents and must report
     "Loop closed: yes/no".
   - Every new mock in a test needs a one-line justification.
   - Flaky quarantines need an owner and an expiry date.

4. REPORT: Tripwire-style summary — what was refreshed, what was verified (file paths),
   the commit sha, and anything from my repo-local testing conventions that conflicts with
   the new defaults (stricter rule wins; flag conflicts, don't resolve silently).
```

Local-machine plugin installs update separately (no prompt needed):
`claude plugin marketplace update david-tools && claude plugin update tdd-playbook@david-tools`

## Release discipline for THIS repo

- Every mechanical change ships with a planted-input test (a planted violation that slips
  past a check is a failure). Suites: `plugins/tdd-playbook/tests/test_*.py` +
  `calibration/test_harness.py`; scenario sanity: `calibration/run_calibration.py --dry-run`.
- Release gate before any version bump: all suites green, `hooks.json`/`plugin.json`/
  `marketplace.json` parse, and a scratch-repo `install_into_repo.py` run proving cloud
  parity (new bins + hooks present, `${CLAUDE_PLUGIN_ROOT}` rewritten).
- Version bumps update BOTH `plugins/tdd-playbook/.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`, plus CHANGELOG.md.
- Roadmap context: `docs/plans/implementation-plan-2026-07.md` (WS5 — Stagehand-Python
  spike, §5b agent evals, positioning, public scoreboard — is built but NOT started;
  v2.0 is gated on ≥1 month of live calibration history).
