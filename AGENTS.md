<!-- GENERATED FILE — do not edit by hand.
     Source: CLAUDE.md + HOST_NOTES in plugins/tdd-playbook/bin/render_agents.py
     Regenerate: python3 plugins/tdd-playbook/bin/render_agents.py render
     A hand edit fails the gate (test_reference_docs), it does not merge quietly. -->
# AGENTS.md — Codex instructions for the TDD Playbook repo

This repo's engineering doctrine is host-neutral and lives in `CLAUDE.md`. It is reproduced
below **verbatim** so the two can never disagree. Only the facts in this section differ when
the host is Codex rather than Claude Code.

## What differs on Codex

- **Vendored install path.** Codex assets land in `.codex/tdd-playbook/` (lowercase), not
  `.claude/`. Install with `python3 scripts/install_into_repo.py --host codex <repo>`, or
  `--host all` for a repo used from both.
- **Guard coverage is PARTIAL and that is deliberate, not an oversight.** Only
  `lock_guard` has a Codex adapter (`adapters/codex/pre_tool_test_lock.py`). Every other
  guard — including `tag_guard`, which reserves release tags for the owner — is `unavailable`
  on Codex per `docs/architecture/host-parity-policy.json`, tracked as dated debt on the
  `test-lock` capability. So on Codex the session-side half of release-tag authority is
  ABSENT: the tracked-script scanner still applies, the Bash-seam guard does not.
- **Codex config is trust-gated by the host.** Review the generated project hook, trust the
  repository and the hook when prompted, then run
  `python3 .codex/tdd-playbook/bin/tdd.py doctor`. A file existing is not proof of
  activation — the adapter reports prevention only after a real-host planted block and its
  paired clean control have been recorded.
- **`claude` is a product name, not a host name.** Where the doctrine below says a step needs
  "a real `claude` binary" — calibration, the headless doer — it means the Claude CLI, on
  every host including this one. That is not a stale reference to fix; an earlier
  hand-maintained mirror "corrected" it to "Codex binary" and made the instruction wrong.

---

## CALIBRATION — OPT-IN AND REACTIVE (changed in v1.32.0; read the reversal note)

**There is no weekly clock any more, and no staleness gate on releases.** Calibration stays in
the repo, fully working, as tooling you reach for — not a cadence that must be satisfied.

**Run it WHEN a verifier misbehaves**, which is when it actually tells you something:
- an adversary or verifier agent misses something it should have caught, or flags something it
  should not have;
- a doer-model upgrade lands (the verifier-strength policy — never let the thing generating
  code outrun the thing checking it);
- a gate/guard is changed in a way you want proven against a planted defect.

```bash
python3 calibration/run_calibration.py            # cheap model, hard caps; appends history.md
                                                  # 3 reps/scenario; PASS only at k/k, AMBER is
                                                  # nonzero and promotes to BLOCKING on a repeat
python3 calibration/run_calibration.py --dry-run  # free, CI-safe; NOT a calibration run
python3 calibration/check_staleness.py            # still works; no longer gates anything
python3 plugins/tdd-playbook/bin/capability_registry.py doctor   # dark-feature inventory
```
- A plant surviving to a clean verdict is still a **BLOCKING failure** — fix the agent, never the
  plant. That rule did not become optional; only the schedule did.
- Run as a NON-root user (the first attempt logged INVALID under root, where the headless doer
  cannot run; see `TDD_PLAYBOOK_CALIBRATION_ARGS` in `run_calibration.py`'s header).
- `docs/calibration/history.md` and the corpus stay in-repo and append-only. They cost nothing at
  rest and they are the record any future run is compared against.

**THE REVERSAL, STATED PLAINLY, because §13 argues the opposite.** This file used to open
"calibration is not optional; the calibration schedule IS the product," and SKILL.md §13 still
makes that argument: every gate is a decaying asset, and a fixed check does not stay effective as
model capability grows. That reasoning is not withdrawn. What changed is the honest read of six
cycles of evidence: the schedule produced obligations faster than it produced findings — ten
calibration debts accumulated against three ever-scored improvements — and a cadence nobody can
meet stops being a control and becomes a source of RED that gets re-dated. Opt-in keeps the
instrument and drops the pretence.

**What this trades away, so it is a decision and not a drift:** nothing now notices if the
verifiers decay quietly. Under the clock, a stale scoreboard was loud. Now the trigger is a human
noticing a verifier behaved badly — which is exactly the honor-system seam §13 calls gameable. The
compensating position is that a MISS is still a blocking failure when found, the corpus only
grows, and the doer-upgrade trigger remains. If verifier quality visibly slips, the schedule is
the first thing to bring back.

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
   and adds current ones (the four BLOCKING guards: weakening_guard, lock_guard,
   snapshot_guard, tag_guard; plus the opt-in overmock/exhaustive/flaky/red_lock,
   which ship OFF since v1.32.0 on 31 warns / 0 blocks (two more were DELETED in v1.47.0 —
   see the CHANGELOG: a dark guard nobody will ever switch on is worse than none); plus
   the warn-by-default
   fixture_guard, which warns when an expected answer in a test-data file is rewritten or a
   case removed). My own non-playbook hooks must survive — verify that before committing.

2. VERIFY: Confirm .claude/bin/ contains tdd_lock.py, with_snapshot.py, grade_from_otel.py,
   capability_registry.py, and dataflow_sweeps.py (with its _debt.py sibling); confirm
   .claude/settings.json has the PreToolUse guards; confirm the vendored SKILL.md mentions
   TEST-LOCK, the decay principle, the ACTIVATED Tripwire leg (§6a wiring liveness),
   §6c Dataflow Liveness, and the §1 seam rule + §6c family parity sweep (v1.26).

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
     And RECORD the block (§12, v1.28): `python3 .claude/bin/guard_note.py record --gate
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
     (`.claude/bin/dataflow_sweeps.py` — render-pairing/exemption-prose blocking,
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
`claude plugin marketplace update david-tools && claude plugin update tdd-playbook@david-tools`

## THE POSTURE — the playbook is SILENT until it has something real to say

Removed 2026-08-18: the rule that every non-metadata commit be covered by a closed review
record. It was the one obligation that fired on EVERY commit, and its output was unconsumed —
205 findings, 57% keyed, 12 UNBUILT-GUARD keys, and zero guards built from any of them.

The hooks already had the right posture: four block, five are off, and they speak only when
something is actually wrong. The doctrine had the opposite one — produce artifacts BEFORE you
may proceed. These are now things you REACH FOR when they have something to say, not tolls:

- **A review record** — when a review actually finds something. Optional never means unchecked:
  a record that IS written still gets the full schema (`review_ledger.py validate`).
- **The full §0 plan** — for genuinely multi-deliverable or risky work. A one-liner is the
  default; a plan nobody needed is not evidence of rigour. **BUT WHEN A PLAN IS WRITTEN IT
  LANDS IN THE REPO** (`docs/plans/gated/YYYY-MM-DD-<workstream>.md`, `commands/tdd-plan.md`),
  committed with the work. That half was NEVER made optional and is not on this list.
  Restored 2026-08-29 after it lapsed: the 2026-08-18 change above was about REVIEW RECORDS,
  and the §0 plan was swept into the same "reach for it" sentence as collateral. Measured
  cost of the lapse — **zero plans committed across the 18 commits from 2026-08-21 to
  2026-08-29**, including a multi-deliverable feature, a new adversary and two guard
  deletions; every plan written in that window went to a scratch directory outside the repo,
  unversioned and undiffable. A plan in a chat scrollback is not a spec, it is a memory. And
  a mechanical spec-vs-implementation check was designed in that same window and died partly
  because its input — a committed plan — had stopped being produced.
- **Adversary dispatch** — on request, or before a release.
- **`index.json` / `current-state.md` bookkeeping** — follows records being optional.

STATED COST, with eyes open: `recurrence` may become sporadic or purely historical. There is no
replacement trigger — the authoring briefs specify fields *when* a record is written and never
required one. That is accepted, not papered over.

WHAT DID NOT CHANGE, and does not: the four blocking hooks, TEST-LOCK, planted-input tests,
red-first, the blessed gate, rule (d) gate-surface journaling (an anti-gaming control, not
bookkeeping), the capability registry, and the version bump (the plugin-cache shipping channel).
The partner keeps watching. It just stops asking you to file proof that it did.

## Release discipline for THIS repo

- Every mechanical change ships with a planted-input test (a planted violation that slips
  past a check is a failure). Suites: `plugins/tdd-playbook/tests/test_*.py` +
  `calibration/test_harness.py` — run them ONLY via `sh scripts/civerd_gate.sh`, the ONE
  blessed gate entrypoint (probe run 2, 2026-07-28: the prose loop and the engine's gate
  command silently diverged and calibration/'s 110 checks never ran in the gate; a script
  can be probed and planted-tested, a prose command cannot). Scenario sanity:
  `calibration/run_calibration.py --dry-run`.
- Release gate before any version bump: all suites green, `hooks.json`/`plugin.json`/
  `marketplace.json` parse, `capability_registry.py validate` passes on this repo's own
  `capabilities.json` (we eat the §6a dogfood — enforced MECHANICALLY by
  `test_capability_registry.py::test_own_registry` on every suite run with the real date,
  so expired integration debt fails the tests, not just the checklist),
  `calibration/check_scoreboard_integrity.py --baseline-rev <previous release tag>` exits 0
  (history append-only, corpus immutable, oracles never weakened unjournaled, and — v1.22
  rule (d) — gate surfaces [SKILL `##` sections, agents/*.md, commands/*.md] never removed
  without a `calibration/gate-changes.md` entry; ALSO enforced mechanically:
  `test_harness.py` runs it against the latest tag on every suite run),
  and a scratch-repo `install_into_repo.py` run proving cloud parity (new bins + hooks
  present, `${CLAUDE_PLUGIN_ROOT}` rewritten, `.claude/.gitignore` written), plus
  `python3 scripts/install_into_repo.py --doctor .` on THIS repo (H8 guards-liveness:
  a commit postdating the last guard heartbeat means the release was built guard-dark —
  the 2026-07-28 incident; also catches standing demotions and version skew).
- Version bumps update ALL FOUR identity files —
  `plugins/tdd-playbook/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
  `plugins/tdd-playbook/adapters/claude/adapter.json` and `…/adapters/codex/adapter.json` —
  plus CHANGELOG.md. (`test_installer.py::test_release_version_identity` pins all four EQUAL;
  this line said "BOTH … and …" until v1.32.0, naming two of the four. The mechanism was
  right and the doctrine was stale — which is the direction to expect, and why the pin, not
  this sentence, is the control.)
- **Releasing (v1.32.0 onward — the CIVerd wall is retired).** A release is: the blessed gate
  green on the commit you are shipping → version bumped in all four identity files → **David**
  creates the tag → push. There is no verdict, no engine, no polling, and no script that
  creates a tag.
  1. `sh scripts/civerd_gate.sh > /tmp/gate.out 2>&1; rc=$?` — **never pipe it**; a piped `$?`
     is `tail`'s, not the gate's (§4a: a discarded exit code is a discarded truth). `rc` must
     be `0`. **NOTHING ENFORCES THIS NOW.** `exitcode_guard` used to, and this line promised
     it would "say so" — it was DELETED in v1.47.0 (701 warnings, zero acted on, plus a
     command-global `$?` read that made it fire on unrelated status reads), and the promise
     outlived the mechanism by a day. Redirect to a file and read `rc`; the discipline is
     yours. A replacement was designed and rejected by four reviews — the honest record of
     why is in CHANGELOG 1.47.0, and an unguarded rule stated plainly beats a guard nobody
     kept.
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

  **The tag instruction is the LAST thing the agent emits, and emitting it ENDS the span.**
  Twice on 2026-08-17 the agent handed over the tag command and then kept committing — once
  finding a real defect minutes later, once folding in follow-up work — so David tagged a
  commit that was current when he read the message and stale by the time he ran it, and in both
  cases the CHANGELOG section for that version had since been edited to describe work the tag
  cannot contain (`changelog-claims-a-tree-it-is-not-in`, recorded twice). The rule is not "write
  the notes more carefully": once the tag command is given, anything further becomes the NEXT
  patch version with its own section. Never retro-edit a section whose tag exists — a tagged
  section is a claim about a specific tree, and a released tree does not change. If work might
  still be in flight, do not emit the tag command yet; say what remains instead.

  **What authorizes a release is David tagging it.** The model can propose, gate, and bump; it
  cannot tag. This is DELETION, not a smaller wall — with no verdict anywhere in the release
  path there is nothing to forge, argue past, or `--force`. Two mechanical halves, each
  stating its own scope (§12 — a control carries its denominator):
  - `test_installer.py::test_no_script_creates_a_release_tag` parses every TRACKED
    `.py`/`.sh`/`.yml` (roster derived from `git ls-files`, so a new tool directory or a
    `.github/workflows/*.yml` cannot fall outside it) and REDs the gate if any creates or
    pushes a tag. Covers committed automation; blind to untracked trees such as
    `.claude/worktrees/*`.
  - `hooks/scripts/tag_guard.py` (PreToolUse/Bash, **BLOCKING**) stops a SESSION typing
    `git tag`, `git push --tags`, `git update-ref refs/tags/…` or `gh release create` —
    including in untracked trees, which is the half the scanner cannot see. It ships
    downstream with `hooks/scripts/`; `tests/` does not.

  **What neither half can do:** bind a human at a terminal, or bind an actor who edits the
  hook. A repo-side check never can. The binding control there is a GitHub `v*` ruleset
  restricting tag creation to `davalst` — dated debt on `release-tag-authority` until armed,
  stated rather than assumed.
- **Review records carry a finding taxonomy (v1.36.0 — review-as-judgment-surface).**
  Findings in `docs/reviews/` records dated on/after 2026-08-15 REQUIRE
  `class: deterministic|judgment` (could a machine have caught it?) and a short-kebab
  `recurrence_key` (REUSE keys when the same defect shape recurs), optional
  `catalog_row: H<n>` membership-checked against `docs/HACK_CATALOG.md`'s Guard ↔ entry
  map.

  **The recurrence epoch, v1.45 (2026-08-20).** The old list claimed twelve unbuilt
  guards and could not be trusted: it had no way to see a guard that had been BUILT (four
  of its items were guards misfiring, and `tag_guard` was fixed here in v1.42, so it
  nagged forever); one key held five unrelated findings; and `catalog_row` was present on
  6 of 205 findings, two of the three load-bearing ones naming the wrong row. Retroactively
  sorting that needs judgment nobody can supply honestly, so it was **retired wholesale**:
  findings before `RECURRENCE_EPOCH` are HISTORICAL — readable, reported as a count, never
  counted toward a verdict. **The records are not deleted**; they stop DRIVING the verdict,
  which is a different thing.

  Forward, the answer moves to authoring time: every finding on/after the epoch must say
  **what would have caught this** — `guard: {kind: hook|test|none, ref, why}` — and
  `validate` REFUSES it otherwise. `none` is a first-class answer; the BLANK was the
  problem. The ref is RESOLVED, not merely non-empty. `recurrence` then prints
  `UNBUILT GUARD` / `GUARDED` / `GUARD DARK` computed from the SHIPPED default mode (never
  `resolve_mode`, which reads env vars and would make the rendered file machine-dependent),
  and `render_reference.py` renders the inventory into `docs/reference/current-state.md`
  — because `recurrence`'s only code reader is the opt-in calibration run, so a report
  fixed only there would still be dark. The six authoring briefs carry the contract,
  needle-pinned to `review_ledger.FINDING_CLASSES`.
- **Historical verdicts stay readable.** `plugins/tdd-playbook/bin/verify_verdict.py` (+
  `_ed25519_verify.py`) is KEPT and DELIBERATELY UNWIRED: stdlib-only, no caller, the sole way
  to check a pre-v1.32 signed CIVerd bundle —
  `python3 plugins/tdd-playbook/bin/verify_verdict.py --sha <sha> --ledger <verdicts.jsonl>`.
  It still has no `--force` and still fails closed, and it is still cross-validated against
  memrebel's golden corpus (`tests/fixtures/civerd_crossvalidation_corpus.json`). It is an
  archive reader, not a gate; **do not re-wire it into the release path** — a consumer gives
  back the exact property the retirement bought.
- Roadmap context: `docs/plans/implementation-plan-2026-07.md` (WS5 — Stagehand-Python
  spike, positioning, public scoreboard — is planned but NOT started; v2.0 is gated on
  ≥1 month of live calibration history). **WS5 row 5.3, §5b agent evals, LANDED
  2026-08-17** (`docs/plans/gated/2026-08-17-adversary-accountability.md`, Phase 2) —
  written by generalizing `calibration/` rather than an external rig, with R11's
  refinements folded in and the `## Open upgrade` IOU retired under rule (d). Its
  load-bearing rule is NARROWER than the IOU promised: blocking is agent-path
  INDEPENDENCE, not "deterministic oracle", because a deterministic check of a stochastic
  subject is still a flaky gate.
