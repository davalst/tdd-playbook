# TDD Playbook — Comprehensive Implementation Plan (v1.3 → v2.0 arc)

**Date:** 2026-07-08 · **Role:** CTO / senior dev · **Written for:** David, in plain language
**Source:** `docs/recommendations/world-class-recommendation-analysis-2026-07.md` (R1–R14),
plus two follow-up investigations David requested (§A and §B below).
**Format note:** this plan practices §0 — every deliverable has plain-English intent,
acceptance criteria, and a named proof method (DIFF-VERIFIABLE / EXTERNAL-STATE / etc., per §6).

---

## A. Does the roadmap close the "Verification Horizon" gap? Honest answer: two-thirds, and this plan closes the rest

The paper's claim decomposes into three implications. Scoring the R1–R14 roadmap against each:

1. **"Verification, not generation, is the bottleneck."** ✅ Closed — this is the Playbook's
   entire thesis, and the roadmap concentrates investment exactly there (locks, guards,
   calibrated verifiers, mutation outcomes).
2. **"Every static gate decays as models get smarter."** ✅ Closed for *detection*. Planted-error
   calibration on a schedule (R1), floors that only rise, and the public scoreboard (R14) mean a
   decayed gate is *noticed* — a gate that stops catching plants is a blocking failure, not
   silent rot. R10 names the principle in doctrine.
3. **"Verification must CO-EVOLVE with the generator."** ⚠️ Only partially closed by R1–R14 —
   and this is the honest gap. Detection tells you a gate decayed; co-evolution makes the gates
   *get stronger as the models do*. Three static assets in the current design would themselves
   decay:
   - the **planted-error corpus** is hand-authored and fixed — a frozen plant library is itself
     a static gate (a stronger doer model eventually "knows" our plants' shapes);
   - the **guard regexes** encode a 2026 hack catalog — new hack patterns (each new system card
     documents new ones) won't be in them;
   - there is no **adversary ratchet** — nothing guarantees the thing generating challenges for
     our verifiers keeps pace with the thing generating code.

   **This plan adds Workstream 4 ("Co-evolution") to close implication 3:** a *generative* plant
   corpus (an adversary agent authors new plants every calibration cycle; the corpus only
   grows), a versioned **hack catalog** with a quarterly refresh ritual wired to a scheduled
   reminder (new system cards / METR / papers → new guard patterns), and a **verifier-strength
   policy** (calibration always measures verifier recall against the *current* doer model, with
   plants authored by the strongest model available). That is co-evolution made mechanical —
   as close as any fixed team can get to the paper's moving target, and it turns the §13 line
   "the floor only rises" from a rule about thresholds into a rule about the whole arms race.

So: R1–R14 alone = detection without adaptation. This plan = both. After Workstream 4, the
answer to your question is **yes — closed, by design rather than by vigilance.**

## B. The §5a engine investigation — verified against primary sources today

What I confirmed (Stagehand docs/repo, browser-use's Browser Harness repo; the changelog page
itself blocks fetches, corroborated via search extracts):

1. **browser-use has pivoted, and the pivot is doctrinally disqualifying for probe duty.**
   CLI 3.0 (July 1, 2026) is powered by "Browser Harness": instead of a fixed action menu, the
   agent gets a **thin, editable CDP harness and writes arbitrary Python** against the browser
   ("complete freedom... one websocket to Chrome, nothing between"), and **persists self-written
   helpers across runs** (`agent-workspace/agent_helpers.py`, accumulating domain skills).
   Judged by §5a's own hygiene rules, that's three strikes:
   - §5a requires an **enumerated action space with dangerous actions excluded**; arbitrary
     Python execution is the opposite of an enumerated action space.
   - Page content is a **prompt-injection surface**; an injected instruction that can write
     Python *and persist it into a helper file that future runs load* upgrades injection from
     a per-run risk to a **persistent-compromise** risk.
   - A **self-modifying harness** breaks run-to-run comparability — the §5a trend line (success
     rate over N runs) assumes the probe itself held still.
   The classic fixed-action `browser-use` library still exists, but it's now the legacy layer of
   a company whose flagship is the harness. Verdict: **demote browser-use to "legacy option —
   version-pinned, no new adoption"** in the §5a table; never point Browser Harness at probe duty.
2. **Stagehand v3's Python SDK voids the constraint that made browser-use our Python pick.**
   The July 4 evaluation blessed browser-use for Python repos because Stagehand's local
   operation was TS-only (Python was a thin cloud client). The current `stagehand-python` README
   ships **local-browser examples** (with and without Playwright) and claims the v3 headline
   features — auto-caching + self-healing ("remembers previous actions, runs without LLM
   inference") — with the v3 CDP-native architecture underneath. If cache parity holds, the
   §5a story simplifies beautifully: **one blessed engine family for both TS and Python repos**,
   same committed-cache/"UI drift = cache diff in the PR" mechanism everywhere.
3. **Confidence and the required check.** Local support: confirmed from the repo. **Act-cache
   parity in Python: claimed in the README but not yet verified at code level** — and community
   threads earlier in the SDK's life asked for caching support, so parity may be recent or
   partial. Our own evaluation standard (the July 4 doc cloned full source and cited file:line)
   applies: **do not re-bless until a half-day code-level spike confirms** (a) cache write/read
   + LLM-free replay in Python, (b) attach to a harness-owned browser over CDP, (c) cache-file
   format is committable/diffable. That spike is Deliverable 5.1 below, and it must produce an
   addendum to `docs/evaluations/` in the same cited style.

Bonus validation: our engine-agnostic OBSERVE/ACT/EVIDENCE/ORACLE contract means this entire
market shift lands as **a driver-table edit, not a doctrine change**. The abstraction earned
its keep within four days of being written.

---

## C. The plan

**Shape:** 6 workstreams ≈ 6 sprints, each Playbook-sized (reviewable plan → red tests →
Tripwire → checkpoint). Total ≈ **18–24 dev-days** spread over ~6–8 weeks at solo-dev pace.
Versioning: WS1+WS2 ship as **v1.3.0** ("the integrity release"), WS3+WS4 as **v1.4.0**
("the co-evolution release"), WS5 lands **v1.5.0**; v2.0 is reserved for when the public
scoreboard has ≥1 month of real calibration history (the moat, provable).

**Standing rules for every deliverable below** (so I don't repeat them): red-first tests in the
plugin's zero-dependency planted-input style (`tests/`), CHANGELOG entry, README touch if
user-visible, `install_into_repo.py` keeps vendoring it correctly (cloud parity is a release
gate — run the installer against a scratch repo and diff), version bump at workstream close.

---

### Workstream 0 — Decisions & scaffolding (½ day, do first)

| # | Deliverable | Detail | Proof |
|---|---|---|---|
| 0.1 | **License decision** | Pick MIT or Apache-2.0 (my recommendation: **Apache-2.0** — the patent grant costs nothing and reads more serious to teams). Add `LICENSE`, update `plugin.json`. | DIFF-VERIFIABLE |
| 0.2 | **`docs/HACK_CATALOG.md` skeleton** | The versioned catalog of known agent test-gaming behaviors (the 6-mode taxonomy from the research: hardcode outputs · edit/delete tests · over-mock · assertion-free coverage · harness exploitation (`sys.exit(0)`, pytest patching, conftest) · architectural fakery). Every guard regex added later cites a catalog entry ID. | DIFF-VERIFIABLE |
| 0.3 | **Calibration directory layout** | `calibration/` (fixture repo + runner + corpus) and `docs/calibration/` (results) created with READMEs so later workstreams have a home. | DIFF-VERIFIABLE |

### Workstream 1 — "Practice what we preach" (R2, R1, R3, R6 · ~4–5 days)

*Goal: every claim the README makes about our own rigor becomes mechanically true.*

| # | Deliverable | Detail | Acceptance criteria | Proof |
|---|---|---|---|---|
| 1.1 | **Mechanical revert safety** (`bin/with_snapshot.py` + worktree doctrine) | Wrapper records tree state (`git status` + hash) at start, verifies identical at end, exit non-zero + loud message otherwise. The four tree-touching agents (`mutation-runner`, `planted-error-probe`, `ux-probe-calibrator`, `red-first-verifier`) rewritten to (a) prefer `git worktree add` isolation, (b) invoke the wrapper when working in-tree. | Planted test: a scripted "agent crash mid-plant" leaves the wrapper reporting dirty; clean run reports clean. Agents' prose updated to call the tool, not promise the outcome. | DIFF-VERIFIABLE + planted test |
| 1.2 | **Agent structural tests** (`tests/test_agents.py`) | Zero-dependency script: for each of the 7 agents assert frontmatter parses, `tools:` matches doctrine (Edit ONLY on the four sanctioned agents), forced `Recommendation:` contract present, output-contract section present. | Planted test: a fixture agent file missing the Recommendation line must fail. | DIFF-VERIFIABLE + planted test |
| 1.3 | **Agent behavioral calibration harness** (`calibration/run_calibration.py` + fixture repo) | A tiny known-good Python package in `calibration/fixture/`. Runner drives each verifier agent headlessly (`claude -p`, cheap model, capped) against planted scenarios: never-red test → `red-first-verifier` must say NOT VERIFIED; unwired deliverable → `tripwire-auditor` RED; false negative claim → `claims-verifier` REFUTED; missing boundary test → `edge-case-adversary` names it. Scheduled weekly (GH Actions `schedule` or local cron per §10's cost rule); results appended to `docs/calibration/history.md`. **A plant surviving = blocking failure** (§13 verbatim). | Each agent catches its plant on the current model; a deliberately broken agent prompt (fixture) fails the harness — proving the harness itself can fail. | EXTERNAL-STATE (named probe: the weekly run + history file) |
| 1.4 | **Close the command→agent loops** (`/edge`, `/mutate`, `/probe`) | `/edge` ends by dispatching `edge-case-adversary`; `/mutate` ends by dispatching `planted-error-probe`; `/probe` requires a `ux-probe-calibrator` PROBE VERIFIED before first-run results are trusted. Every command's output contract gains a `Loop closed: yes/no + why` line. | Command files contain the dispatch instruction + output line; structural test asserts the line exists in all three. | DIFF-VERIFIABLE |
| 1.5 | **Integrity hooks default to `block`** | `test_weakening_guard` default becomes `block` (per-hook env vars remain the opt-down; nudges and `flaky_guard` stay `warn`). Mode resolution in `_common.py` gains a per-hook default map. | Existing planted tests updated: weakening event with no env vars → exit 2. README hook-controls section updated. | DIFF-VERIFIABLE + planted test |

### Workstream 2 — "Lock the tests" (R4, R5, + small debts · ~4–5 days)

*Goal: the two top documented attack vectors — edit-the-test and over-mock — are mechanically constrained.*

| # | Deliverable | Detail | Acceptance criteria | Proof |
|---|---|---|---|---|
| 2.1 | **TEST-LOCK** (`bin/tdd_lock.py` + `test_lock_guard.py` PreToolUse hook + `/tdd-lock` `/tdd-unlock` commands + §1 doctrine) | `tdd_lock.py lock <files…>` records path+hash+timestamp in `.claude/tdd-lock.json` (after the red commit). PreToolUse(Edit\|MultiEdit\|Write) hook **exits 2** on any locked path — including `conftest.py`, pytest plugins/config when locked (they're verifier surface). `unlock` requires `--reason`, appends to a lock journal consumed later by `/grade`. `/tdd-plan` offers the lock step once red tests are committed. | Planted tests: edit locked test → blocked; edit after reasoned unlock → allowed; unlock without reason → refused; journal contains the reason. Doctrine: §1 gains the lock as the mechanical form of the iron rule. | DIFF-VERIFIABLE + planted tests |
| 2.2 | **Guard extensions from the hack catalog** | New detections, each citing a HACK_CATALOG id: (a) `sys.exit(`/`os._exit(` newly added to a test file or conftest → block-tier; (b) **mock-delta**: net-new `mock`/`patch`/`MagicMock`/`monkeypatch.setattr`/`jest.mock` in a test edit → warn "justify each new mock" (MSR 2026: agents over-mock 36% vs 26%); (c) **snapshot protection**: PostToolUse warn on `.snap`/`__snapshots__` bulk changes + PreToolUse(Bash) block on `-u`/`--update-snapshots`/`--ci=false` snapshot-update invocations. | One planted-input test per pattern (positive + clean-negative), in `test_hooks.py` style. | DIFF-VERIFIABLE + planted tests |
| 2.3 | **Small-debt burn-down** | (a) `verify_citations.py`: minimum-quote-length + non-unique-quote warning (a 1-word quote can't verify); (b) `flaky_guard`: tighten seed-suppression (match suppressor to the specific finding type; `@pytest.fixture` alone no longer silences wall-clock); (c) `install_into_repo.py`: prune hooks the plugin no longer ships (reconcile, not just append); (d) Stop-hook reminder reads the turn's edits where available rather than whole-tree status. | Each fix lands with a planted regression test that fails on the old behavior (§1 iron rule applied to ourselves). | DIFF-VERIFIABLE + planted tests |

### Workstream 3 — "Sharper metal" (R7, R9, R10 · ~3 days)

| # | Deliverable | Detail | Proof |
|---|---|---|---|
| 3.1 | **Mutation v2 — diff-scoped + ACH-style** | §4 + `/mutate` + `mutation-runner` updated: (a) per-PR mutation runs **diff-scoped** (Stryker `--incremental`/`--since`, pitest history, mutmut on changed files) on critical modules — survivors surfaced in review Google-style, not a repo-wide KPI; (b) new **targeted-mutant mode**: generate 3–5 plausible, concern-specific mutants (auth bypass, rounding, permission drop) and require tests that kill them — mutation as test *generator* (Meta ACH pattern); (c) hard rule in doctrine: **mutant generation stays out of the implementing agent's context** (visible verifiers get gamed — METR). | DIFF-VERIFIABLE |
| 3.2 | **Cheap doctrine wins** | Five one-to-three-line additions: snapshot policy (agents never auto-approve); Schemathesis when an OpenAPI/GraphQL schema exists (§3/§9); affected-tests inner loop + full suite at checkpoint (§10); quarantine entries get owner + expiry, expired = suite failure (§7); every new mock needs a one-line justification (§1). | DIFF-VERIFIABLE |
| 3.3 | **The decay principle named** (R10) | §13 preamble: *"Every gate is a decaying asset; verification must co-evolve with the generator; the calibration schedule is not maintenance — it IS the product."* Cited (Verification Horizon 2606.26300; METR). | DIFF-VERIFIABLE |

### Workstream 4 — "Co-evolution + real telemetry" (R15-new, R8 · ~4–5 days)

*Goal: close Verification Horizon implication 3 (see §A) and make §13 grade from real data.*

| # | Deliverable | Detail | Acceptance criteria | Proof |
|---|---|---|---|---|
| 4.1 | **Generative plant corpus** (`calibration/corpus/`) | Each calibration cycle, an **adversary agent on the strongest available model** authors 1–2 NEW plants per category (false claim, weakened test, wiring gap, UX defect) — human-reviewed, then added. **The corpus only grows** (the "floor only rises" rule applied to the arms race). Runner samples fresh + historical plants each cycle. Plants are versioned with the model that authored them, so recall trends are attributable. | A cycle's report shows ≥1 never-seen-before plant exercised; corpus files carry author-model metadata. | EXTERNAL-STATE (weekly run) |
| 4.2 | **Hack-catalog refresh ritual** | Quarterly scheduled reminder (Routine/cron): review new model system cards, METR updates, and reward-hacking literature → new HACK_CATALOG entries → new guard patterns (each with planted tests, per WS2 discipline). Catalog is versioned; guards cite entry IDs, so "which hacks are we blind to" is a diffable question. | First refresh executed as part of this workstream (seeding entries from the July 2026 research corpus). | DIFF-VERIFIABLE + EXTERNAL-STATE (the schedule) |
| 4.3 | **Verifier-strength policy** (doctrine, §13) | Calibration measures verifier recall **against the current doer model**; plants authored by ≥ the doer's tier; a doer-model upgrade *requires* a calibration run before trust transfers. One paragraph, big consequence. | DIFF-VERIFIABLE |
| 4.4 | **OTel-real `/grade`** (`bin/grade_from_otel.py` + collector recipe) | Recipe doc for `CLAUDE_CODE_ENABLE_TELEMETRY=1` + a local OTLP file exporter; script computes §13 metrics mechanically (files read, greps run, tokens net of cache, turns, tests-added vs source-changed); `/grade` pastes the script's output — **the seam emits the count** (§12's rule, applied to §13). Degrades gracefully: no telemetry → `/grade` says "narration-grade, telemetry unavailable" instead of pretending. Don't hard-bind unstable `gen_ai.*` attributes. | Planted test: a fixture OTLP export yields known counts; `/grade` output contract includes the script summary line. | DIFF-VERIFIABLE + planted test |

### Workstream 5 — "Strategy: engines, evals, position" (R11, R12-resolved, R13, R14 · ~4 days)

| # | Deliverable | Detail | Proof |
|---|---|---|---|
| 5.1 | **Stagehand-Python verification spike** (½ day, gate for 5.2) | Clone `browserbase/stagehand-python`, verify at code level with file:line citations: local act-cache write/read + LLM-free replay; CDP attach to a harness-owned browser; committable/diffable cache format. Output: addendum to `docs/evaluations/` in the July-4 style. | EXTERNAL-STATE → becomes DIFF-VERIFIABLE (the addendum) |
| 5.2 | **§5a driver-table update** | Contingent on 5.1: **Stagehand becomes the blessed engine for BOTH TS and Python repos** (one cache-diff-in-PR story everywhere). **browser-use demoted to legacy** — version-pinned, existing probes keep working, no new adoption; **Browser Harness explicitly forbidden for probe duty** with the three-strike rationale (§B above: arbitrary code ≠ enumerated action space; persistent self-written helpers = durable injection surface; self-modifying harness breaks trend comparability). If 5.1 fails: browser-use stays, pinned harder, with a dated re-check note. Either way the doctrine change is a table edit — record that as evidence the contract design works. | DIFF-VERIFIABLE |
| 5.3 | **§5b agent-eval discipline** (the pending open upgrade — research settles it) | New section: deterministic-oracle evals gate; LLM-judge evals trend, never gate; judges use **0–5 rubrics** with **periodic human-agreement calibration** (<~65% agreement = noise, drop the judge); grade **outcomes not paths**, process checks reserved for shortcut detection; DeepEval as the pytest-native harness suggestion. Close the §5a↔§5b mirror note; remove the "pending discussion" flag (this document is the discussion). | DIFF-VERIFIABLE |
| 5.4 | **Positioning & distribution** | README: honest one-table comparison vs obra/superpowers (methodology breadth) and nizos/tdd-guard (single-hook enforcement) — we are the *calibrated verification layer* and compose with either; SHA-pinned install guidance (2026 hook-provenance hygiene — cite the PyPI SessionStart-hook worm; our planted-input-tested, warn-transparent hooks are a trust asset, say so); license badge from 0.1. | DIFF-VERIFIABLE |
| 5.5 | **Public calibration scoreboard** (`docs/calibration/`) | Auto-appended by the WS1/WS4 runs: per-guard and per-agent planted-defect catch rate, corpus size + newest-plant date, mutation floors, last-run dates. The claim no competitor can make: *"our verifiers are tested weekly against plants they've never seen; here are the numbers."* Ship v2.0 when it shows ≥1 month of history. | EXTERNAL-STATE (the running history) |

---

## D. Dependencies, risks, and how we'll know it worked

**Dependency spine:** 0 → 1 → 2 → {3, 4} → 5. Only real hard edges: 1.3 (harness) before 4.1
(corpus feeds the harness); 0.2 (catalog) before 2.2 (guards cite entries); 5.1 before 5.2.
WS3 can run parallel to WS4 if time is tight.

**Top risks & mitigations:**
1. **Headless agent calibration cost/flakiness (1.3, 4.1).** Mitigate: cheap model, hard step/
   token caps, weekly not per-commit, N≥2 runs before declaring a BLOCKING GAP (§5a's own N≥3
   spirit), and the oracle is deterministic (did the forced `Recommendation:` line name the
   plant — string check, not judge).
2. **Block-by-default friction (1.5, 2.1).** A false-positive block on a legitimate test
   refactor is the adoption killer. Mitigate: the unlock path is one command with a reason;
   warn-mode remains one env var away; ship with a week of dogfooding on this repo before
   tagging v1.3.0.
3. **Stagehand parity disappoints (5.1).** Cheap by design: half a day, and the fallback
   (pinned browser-use, dated re-check) is pre-written into 5.2.
4. **Scope creep — the plan is the spec.** §6's reverse check applies to this plan itself:
   at each workstream close, every changed line traces to a numbered deliverable above, or it
   gets mentioned, not done.

**Success criteria for the whole arc (the plan's own Tripwire):**
- Every README rigor claim about our own tooling is backed by a running planted-input check
  (WS1) — *BUILT + WIRED + EXERCISED, applied to ourselves*;
- The two top documented attack vectors are blocked by default, not warned about (WS2);
- A gate that decays is detected within one calibration cycle, and the challenge corpus
  provably grew that cycle (WS4) — the Verification Horizon answer;
- `docs/calibration/history.md` shows ≥4 consecutive weekly runs with zero surviving plants
  (or filed blocking failures) before v2.0 is tagged.

**Sources for §B verification:** [stagehand-python repo](https://github.com/browserbase/stagehand-python) ·
[Stagehand v3 announcement](https://www.browserbase.com/blog/stagehand-v3) ·
[browser-use/browser-harness repo](https://github.com/browser-use/browser-harness) ·
[Browser Use CLI 3.0 changelog](https://browser-use.com/changelog/1-7-2026) (fetch-blocked; via search extracts) ·
[Stagehand Python docs](https://docs.stagehand.dev/v3/sdk/python) (fetch-blocked; via search extracts + repo).
Fetch-blocked items are flagged per §12 — the 5.1 spike re-verifies them at code level before any doctrine change.
