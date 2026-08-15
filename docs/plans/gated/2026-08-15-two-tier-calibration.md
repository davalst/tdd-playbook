# Integrated plan — Two-tier calibration: fixture guard + de-legibilized public corpus + private holdout boundary

**Date:** 2026-08-15 · **Status:** GATED (plan review). Nothing built. Approved as ONE program (David's call), executed safe-first: Part 1 (reversible) ships first; Part 2 (irreversible) is gated on three build-time preconditions, not a second approval.
**Sources:** the private EvilGenie-run findings (fixture-data gap) + `20260815holdoutandtheportableanchor.md` (hidden-answer-key thesis) + a Codex design pass with weighted priorities. Reviewed by 5 fresh-context adversaries; every load-bearing claim re-verified against the tree (corrections marked). Two new architectural facts verified this session: **Docker + `sandbox-exec` are available** (the sandbox is buildable); **a private controller reads the public repo with no deploy key** (public repos are anonymously cloneable) — which removes every holdout secret from the public repo.

## Threat model (fixes the priorities)

The threat is **agent-side test-gaming and answer-key recognition** — not trusted human collaborators. Everything is weighted to: improve measurement quality **now**, add **~zero per-run operator time** (nonzero ongoing system ownership — honestly costed in Part 2), and build a **real private holdout as a minimal automated private-owned boundary**, not a secret-management bureaucracy. (The one human-side item — a second write-capable collaborator `kerry-glitch` on the public repo, `main` unprotected — is worth a look today but is *not* this plan's threat model; noted, not centered.)

## The shape: two tiers

| Tier | Location | Purpose | Trust |
|---|---|---|---|
| **Dev corpus** | public Playbook repo | regression tests, guard tuning, fast iteration | known / tunable — treat like a normal test suite |
| **Holdout corpus** | **separate private repo** (owns corpus + oracle + runner + controller + credential) | unseen evaluation of agent/verifier generalization | independent measurement — treat like an eval set |

A public corpus inevitably loses independence (agents can read it, infer it from prior runs, or meet it in training). De-legibilization is defense-in-depth, not secrecy: **if the scenario or oracle is reachable by the agent, it is not a holdout.** Secrecy comes from the runtime boundary, below. Neither tier authorizes a release (the CIVerd no-authority invariant — holdout is a quality signal, never a gate or signing authority).

---

## Two live items to disposition (not deliverables)

1. `kerry-glitch` has write/push to public `davalst/tdd-playbook`; `main` unprotected, no rulesets (verified). Your call whether expected.
2. ~925 dirs / 90 MB of calibration transcripts in `~/.claude/projects/`, 740 with literal plant text, readable by any Bash session (verified). This is *why* a local-folder holdout is unsafe and why the sandbox boundary (Part 2) is load-bearing — a container run's transcripts never touch the host store.

---

# PART 1 — Public-repo integrity (ships first; immediate measurement-quality; all reversible)

Three of these are the **same fix two documents found twice** — patch once.

**U1 — Lock/guard basename unification (LIVE pre-existing defect; arch-F2).** `test_lock_guard.py:37-54` and `host_contract.py:45-60` already disagree today (`lock-transaction.lock` missing from the Bash-leg set, `pending-red.json` from the Edit-leg set, no parity test) — so each slips one channel now; and `tag_guard.py` (BLOCKING) is in neither → self-editable while locked. Delete the `test_lock_guard` copies, import the three frozensets from `host_contract` (already imported there), add a parity test. **First**, because A depends on adding one name in one place.

**U2 — The `form` scoreboard bug (both plans; arch-F2/integ-#10).** `run_calibration.py:709-711` omits `form` from history meta, so `history_format` silently writes `form dev` even for `--form holdout`. Fix at the **writer contract** (required key via the `meta[k]` splat, not a silent default — the swallow branch is production-dead, test-only-live), update 5 test call sites, land a dated-correction note in `history.md` (pre-fix `form` cells are UNMEASURED, not `dev`).

**A — `fixture_guard` (warn default, scoped to ANSWER-VALUE changes — David's call, resolves warning fatigue).** New `hooks/scripts/fixture_guard.py` (`NAME="fixtureguard"`, PreToolUse Edit+Write and Bash). Scope = `is_test_file` AND `{.json,.yaml,.yml}` OR `/fixtures/|/golden/`, importing `snapshot_path` for the exclusion (arch-F3). **The guard warns only when an EXPECTED VALUE is rewritten or removed — NOT on adding a new case or editing unrelated fields (keeps the signal rare and real; an ignored warn is worse than none).** Mechanics: parse old-vs-new (Edit) or old-file-vs-new-file (Write) as JSON/YAML and warn only if an expected-output/oracle field's value changed or a case was deleted; a pure addition or a metadata edit is silent. Structural gaming shapes stay caught: **delete / overwrite-to-fewer-cases / rename / move / `git rm` / `git mv`** of an existing test-data file warn (rare in normal flow, and value-removing by nature) — via the shared shell-write helper's verb set (`rm`,`mv`,`cp`,`git rm/mv` added to the promoted `_seg_writes`). **New fixture creation stays silent.** Design item: when old/new can't be parsed/compared, fall back to warn-on-structural-change (size shrink / key removal) so an unparseable rewrite still catches the gaming shape without firing on additions — the guard's analysis is a real parse/diff, not the assertion-count heuristic `test_weakening_guard` uses. **The bypass-oriented suite MUST include an unparseable old-or-new case (GLM residual-2): a malformed-JSON/YAML edit is exactly where the fallback can false-positive on a legitimate reformat or slip a real rewrite — test both the malformed-legit-reformat (silent) and the malformed-value-removal (warn), not only the clean structural shapes.**
- Roster pin: replace the three literal sets with ONE `EXPECTED_MODES = {script: mode}`, derive the partition on `resolve_mode` (arch-F9) — fixes the warn-vs-advisory runtime ambiguity too.
- Registry: `activation.default: "on"` (NOT `"warn (on, advisory)"` — that REDs `validate`; arch-F1/integ-#3); warn tier in `summary`; switch names `TDD_PLAYBOOK_HOOK_FIXTUREGUARD=off|block`.
- Prose (integ-#4): edit `README:17-18`, the `README:156-169` "Three tiers" Hook-controls section (this product's `/features`), CLAUDE.md; regen AGENTS.md; extend the pin past its 530-char window.
- Premise correction (arch-F8): "TEST-LOCK blocks this when engaged" is false — add a `fixturedata` surface kind to the lock classifier (post-U1) so data files under a locked test inherit BLOCK, or state the residual hole.
- Adopt the predicate in `build_completion_reminder.classify` (integ-#7) so a fixture edit stops silencing the Tripwire nudge.
- Dark-signal debt (integ-#5): warn rows are minted but unread; ship a dated `integration_debt` with a numeric promote/kill rule.
- HACK_CATALOG: extend H2/H5, **fully neutral provenance** ("observed in a private calibration run, 2026-08-15; artifact archived privately"). Codex is right to call the tests **bypass-oriented**: both-directions planted (edit/delete/rename/move/overwrite/`git rm`/`git mv` each warn; new-file/read/`.snap`/non-test-path each silent), plus §13 replay against the real private tamper diff (scratchpad, chat-only).
- Codex needs nothing (guards family inherits `unavailable`).

**U3 — De-legibilize, SPLIT into two by value (GLM: they are not equal priority).**
- **U3a — answer-announcing prose (do now, regardless of Part 2).** `fixture/tools.py:3-7` literally names the graded answer ("the good-fix plant unifies the two"); `verify_install.sh` announces the safe path (un-tokenizable). This corrupts the **dev** measurement itself — the dev corpus tunes guards, and a fixture that names its own answer means dev calibration is already scoring recognition. High-value independent of Part 2. Fix at the **authoring seam** (`validate_scenario` rule: no fixture explains its own plant); move the `tools.py` prose (shared by 3 scenarios) to ONE home (`plant-forms.md`). Verified: no scenario `edits[].old` anchor touches any docstring — safe.
- **U3b — the deeper token sweep (defer; value depends on Part 2).** The tmpdir/git-identity/commit-message tells (`tdd-cal-`, `cal@tdd-playbook`, `"fixture (plant applied)"`, `scn-val-` — 7 fixture files, not the 4 either plan listed) matter mainly if a holdout runs in this harness. If Part 2 lands with its own sandbox+controller, the public corpus is compromised-by-design anyway and this is polish that also makes the corpus harder for **humans** to maintain. Build the sweep (staged tree + `git log/config` + cwd + `--settings`/argv path, vacuity-guarded via `leakage_problems:207`, red-first vs today's tree) only once Part 2 is decided.

**P — Population partitioning (its OWN deliverable, red-first suite — GLM: the riskiest Part 1 item, do not bury it as a sidecar).** `form`, `model family`, `isolation`, and `network` are new population axes on an append-only record whose **five readers assume one population** (`ledger.bind_entry/baseline_row`, `plant_vitality.scenario_streaks`, `power.comparable_blocks`, `run_calibration.last_kind` → the AMBER×2→BLOCKING-FAIL promotion). A bug here corrupts calibration history **silently**. Extend the existing `form_matches` filter to all four axes across all five readers so a no-playbook / network-denied / different-model result can **never** become the comparator for a normal run. **Not a uniform "mirror" (GLM residual-1): three readers already take a population param; `power.comparable_blocks` (`power.py:84`) and `run_calibration.last_kind` have NONE today — the fix ADDS the parameter there, a signature change, not a filter reuse.** Gets its own red-first suite with a case per reader (a planted cross-population block must fail to bind / fail to promote at each site — including the two that gain the param). Hard precondition for any isolation/holdout run being trustworthy — and for that reason it precedes both baseline-isolation and Part 2.

**Two isolation concepts, kept distinct:**
- *Baseline isolation* (`isolation` scenario field, `--settings` plugin-disable — verified honored this session): measures agent behavior **without the playbook doctrine**. Real gaps to fix: forward the flag through `host_runner.invoke` (integ-#8, else it stops at `run_agent`); the plugin-disable removes hooks+skill but **not the agent brief** the harness feeds via the prompt — record that scope honestly or add a neutral-prompt path (arch-F4/integ-#2); liveness = **zero hook events in the doer yield log**, not a stub-argv proxy; derive the plugin key from identity files (arch-L1). On `--host codex`, refuse or write `not-applicable` — never record a mode that wasn't applied (integ-#6).
- *Secrecy isolation* (the sandbox): Part 2. Different mechanism, different purpose; do not conflate.
- *Network*: build child settings **in code** from the fields (no template cross-product — arch-F5); split `NONEXECUTION_SIGNATURES` into CLI-refusal vs permission-refusal and pass the declared deny set so a denied-tool refusal is a REAL rep across all 7 call sites (integ-#9).

---

# PART 2 — The private holdout boundary (irreversible; lands last, most review; gated on Part 1 green + the sandbox-runner isolation probes passing)

**Gate — THREE build-time preconditions (approved as one program, but Part 2 does not START until all three hold):**
1. Part 1 green on `main`.
2. The sandbox-runner spike (step 6) proves isolation.
3. **The decision the holdout informs is confirmed to still hold, before bodies move.** The load-bearing question GLM is right to force: *what decision changes on holdout data that we can't already make?* The named answer — a real one, not "we'll find out": **the holdout is the only instrument that tells you whether your existing dev scoreboard still measures anything.** Once the public corpus is memorizable, dev recall cannot distinguish detection from recognition (R1); a holdout scoring materially below dev is the signal to stop trusting dev numbers and reinvest in verifiers. It also gates the doer-model-upgrade decision (run a new model against unseen plants before trusting its work). This is the payoff weighed against the cost below.

**The cost, stated honestly (GLM: "zero operator burden" is false).** Zero *per-run operator time*, but **nonzero ongoing system ownership**: model-credential custody in the private controller (a real security responsibility, not a dated-debt footnote), two corpora kept in sync, sandbox/controller upkeep, and metered API spend on every scheduled run. Weigh this against the named decision above.

The `kerry-glitch` collaborator item is a **separate human-side note, not a precondition** — outside this program's threat model, must not gate it. The local transcript pile is technical *evidence* that a local-folder vault is unsafe (hence the sandbox), not a manual-cleanup prerequisite.

**Dependency to document (GLM): Part 2's "no deploy key" advantage assumes the public repo STAYS public.** If it ever goes private, the controller loses anonymous read of `main` and needs a read credential — a fallback path stated now, not discovered later.

**Architecture (Codex, verified buildable): the private repo owns everything and holds the credential; the public repo owns no holdout secret and no holdout workflow.**

```
public main commit (untrusted input)
      │  (anonymous read — no deploy key)
      ▼
private repo: corpus + oracle + runner + controller [holds model credential]
      │ stages an ordinary task from a private scenario × the selected public revision
      ▼
ephemeral sandbox (Docker/sandbox-exec): ONLY the staged repo mounted · NO network ·
      no credentials · no parent fs · no evaluator logs · destroyed after each run
      ▲  the controller BROKERS the model call — the API key never enters the agent's shell env
      ▼
evaluated agent (tools scoped to the sandbox)
      ▼
private result store (detailed) ──▶ optional public AGGREGATE-only summary (recall + CIs; never scenario text/transcripts/oracles/raw output)
```

**Why this is stronger AND simpler than the deploy-key design it replaces:** no holdout secret in the public repo means the security review's #1 finding (secret reachable from `gate.yml`'s `push:["**"]` on an unprotected `main` with a second writer) **cannot occur** — there is nothing to reach. The container also fixes the local-transcript leak (#5): the agent's transcripts live and die in the sandbox, never in the host `~/.claude/projects`. And network-off is a container property, not a settings promise.

**Load-bearing isolation requirement (the whole point):** a private repo alone is not enough. A CLI agent with unrestricted shell + a credential/private checkout in the same environment can read env vars, key files, processes, parent dirs, logs, caches — the security review proved this by reading `~/.claude/projects` this session. So: controller runs **outside** the sandbox and holds the credential; the agent's tool executor runs **inside** an ephemeral container/`sandbox-exec` jail; only the staged repo is mounted; outbound network disabled; no evaluator secrets, private checkout, host home, Docker socket, parent mount, or CI workspace reachable; sandbox destruction guaranteed; the model invocation brokered by the controller.

**Reuse, not new modules (arch-F1/F3/F4):**
- **Loader (arch-F1):** parameterize `run_calibration.load_corpus(dirs=…)`; `author_plants.corpus_scenarios` delegates. A standalone `holdout_source.py` would be a THIRD loader, blinding the 9 universe-composition sites (id-uniqueness, R2 pair quota, quarantine pin) to holdout plants.
- **Hash-drift (arch-F3):** feed the private source's computed shas into `plant_forms.form_problems`'s already-injected `shas` map; keep `PRIVATE` only for genuinely-unresolvable. (The doc's standalone check was self-blocking.)
- **Authoring half (security-E4):** holdout classes assigned **at `--approve`** write to the private store, never `corpus/proposed/`; suppress raw-output prints for holdout.
- **Body containment (arch-F4):** extend `leakage_problems` (already a gate stage) with a whole-tree body scan; re-open the `.claude/worktrees` non-scan decision (premise breaks once bodies can land there).

**Egress as an ALLOW-LIST (security-E1/E2, doc-F8, Codex #5).** In holdout mode, a strict egress policy over stdout, stderr, exceptions, logs, subprocess output, artifacts, caches. The printer today leaks `sc["plant"]` (`:648`), oracle regexes (`:695-696`), and 1500 chars of doer output (`:697`) — a deny-list of "known secret strings" can't catch a paraphrase. Invert: emit ONLY a closed field set `{id,agent,runs,verdict,mode}`; the test captures real stdout and asserts every line matches a template; exception messages describe by digest, never quote. Red-first against today's leaking `:648`.

**Automation & the doctrine reconciliation.** Runs automatically after public `main` changes or on a schedule (weekly, not per-commit). No copying files, no per-run approval, no token, no special command per run. **This is a conscious reversal of the v1.32.0 "calibration is opt-in-and-reactive" position** — chosen then because calibration needed budget + a human + a `claude` binary. An automated private holdout removes the human-in-the-loop objection, and CLAUDE.md's own note says the schedule is "the first thing to bring back" if verifier quality slips. Record it as a deliberate doctrine change. **Burden, honestly (not "zero"):** zero per-run operator time, but nonzero ongoing system ownership — credential custody, two corpora in sync, sandbox/controller upkeep, metered API spend. The doctrine note states that cost, not a "zero-burden" claim.

**No-authority pin — CURRENT POLICY, not a perpetual invariant (GLM's correction).** The mechanism stays: no committed automation wires the holdout score into release authorization, asserting the FACT (the doc's "no holdout component in fixed_stages" is already RED — `plant_forms.py check` IS a fixed stage, correctly: integrity gates, the *score* never does). Real clause: **no gate stage's exit code can be produced by a holdout run's rows** — give holdout its own history file (`host_runner.default_history` precedent) or keep holdout blocks out of `bind_entry`'s authorizing population; extend the scanner to publication (no `upload-artifact`/`cache`/unpinned `uses:`; `tag_guard.workflow_findings` is the home). **But frame the docstring as a dated, revisitable decision, not a law of nature:** if the holdout ever proves the verifier stack is systematically failing, gating on it becomes a rational option — revisiting it requires a conscious review that re-accepts the CIVerd machinery authority regrows. Keep the CIVerd lesson; drop the "perpetual" framing.

---

## Acceptance criteria (the Tripwire anchors — Codex's list, adopted verbatim as the DoD)

1. A holdout body is available to the private controller but **not readable from the child sandbox**.
2. The child agent has **no network** and cannot access credentials, parent dirs, evaluator logs, private checkout, or artifact/cache paths.
3. A **deliberate attempted read** of each of those from inside the child **fails** (planted-probe test).
4. The agent sees only a normal task staging — no scenario/plant/oracle identifiers.
5. The evaluator's output test proves detailed private material **cannot** appear in logs, stderr, artifacts, caches, or public summaries (allow-list, red-first vs a leaky printer).
6. A fixture **edit, delete, rename, move, overwrite, `git rm`, `git mv`** each produce the expected **warn** signal; new-file creation stays silent.
7. Calibration history and all downstream comparators **preserve population separation**.
8. The public suite stays fully useful for development; the private suite reports independently-measured holdout performance.

## Delivery sequence (Codex's 7 steps, mapped)

**Part 1 (reversible, ships regardless of the Part 2 decision):**
1. **U1** lock-policy unification + **U2** scoreboard-form fix.
2. **P** population partitioning (own red-first suite — the riskiest Part 1 item).
3. **A** fixture guard with bypass-oriented regression tests (edit/delete/move/rename/`git rm`/`git mv`).
4. **U3a** answer-announcing-prose fix (baseline isolation + network hygiene ride here too).

**Part 2 (same approval; starts only after the three build-time gate preconditions above):**
5. **U3b** deeper de-legibilization sweep.
6. **SANDBOX-RUNNER SPIKE (mandatory, before ANY real holdout body exists).** The current runtime does not have a controller-brokered sandbox: `host_runner.py:83` starts the CLI as a plain subprocess and `run_calibration.py:326` calls it directly. Docker/`sandbox-exec` being *installed* proves executables exist, not that this agent runtime operates through the intended boundary. The spike must prove, with a **benign synthetic scenario** (no real answer key): the private controller holds the model credential; a real evaluated-agent turn runs through the chosen sandbox; the tool environment sees only the staged task; **planted reads of env vars, parent directories, the private checkout, network, artifacts, and caches each FAIL**; and the agent still completes a benign real task successfully. Only after this passes may steps 7-9 proceed.
7. Private holdout repo + controller (loader reuse via `load_corpus(dirs=…)`, hash via the existing `shas` seam, authoring half at `--approve`) — **real holdout bodies enter only now, on the proven containment from step 6.**
8. Planted isolation + leakage tests wired into CI + local (acceptance criteria 1-5 as standing red-first probes).
9. Automated private evaluation + aggregate-only reporting + the no-authority pin.

Each green phase = checkpoint commit (§11). Part 1 (steps 1-4) ships and is worth shipping on its own. Part 2 (steps 5-9) does not start until Part 1 is green AND the three gate preconditions are met; the spike's isolation probes (step 6) gate steps 7-9, and no irreversible material moves before they pass. Parts 1 and 2 each close with tripwire-auditor + architecture-adversary on the diff → review record → gate → push. Metamorphic guard pilot (doc D4) and public benchmark/starter-kit (doc D6/D7) remain **parked** per your earlier answer; the existing `plant-forms` dated debt (expires 2026-10-15) that already owns the private-repo work is updated/retired in step 7, not duplicated.

## Dated debts to register

- Deploy-key custody is **moot** under this architecture (no key in the public repo). Instead: model-credential handling in the private controller — owner david, revisit ~90 days (your Q2).
- fixture_guard warn→block/kill numeric trigger (integ-#5); `build_completion_reminder` predicate adoption if not taken inline (integ-#7).

## Verification

Inner loop: `test_hooks.py`, `calibration/test_harness.py`, `run_calibration.py --dry-run`. Full: `sh scripts/civerd_gate.sh` (never piped) green at every boundary; `capability_registry validate`; `render_agents/render_reference check`; host-parity re-ack via `test_host_parity.py`. The egress leak-test and de-legibilization sweep each go red-first against today's tree. The sandbox isolation probes (criteria 1-5) run in CI and locally. Tripwire `N/N (+ FLOWS)`; Claims line on each close.

**Scoped secrecy claim (accurate, not absolute):** holdout bodies never enter the public repository, the public CI workspace, the child-agent sandbox, host transcript storage, public logs, artifacts, caches, or public summaries. They may exist only in the private controller's ephemeral private checkout, and are deleted after staging. (The controller *must* read the bodies to stage a task — so "never touch any disk" would be false; the boundary is which disks and which processes, enumerated above.)
