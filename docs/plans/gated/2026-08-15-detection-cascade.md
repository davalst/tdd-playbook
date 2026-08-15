# Plan — The detection cascade: a deterministic screen that routes, and a judge that can only accuse

**Date:** 2026-08-15 · **Revision:** v1, pre-adversary (see "Loop closed" — it is NOT closed)
**Branch:** `claude/detection-deterministic-filter-ng073s`
**Status:** GATED — draft for David's review. Nothing here is built.
**Provenance:** David's reading of a reward-hacking detection paper, summarised in session as:
*"cheap deterministic signals (file hashes, holdout tests) as a first-pass filter, expensive LLM
judge only on flagged runs — holdout tests are cheaper, easier to add to a pipeline, and not
vulnerable to prompt injection. That maps onto an authority-check layer where the deterministic
gate can't be talked out of firing."*

---

## The call, up front

**Build the screen. Do not build the judge yet.**

This repo already holds the hard half of that architecture — the authority ordering, in which a
deterministic check gates and a model verdict never does. What it does not hold is the *routing*:
nothing anywhere converts a cheap signal into a decision about where to spend an expensive one.
The screen (D1) is worth building on its own merits, because it produces a number this repo has
never had: **a per-session base rate of suspicious runs.** The judge (D4) is worth building only
if that number turns out to be neither zero nor everything, and we cannot know which until the
screen has run for a few cycles.

Building both at once is the failure mode this repo's own plan history documents: the v1 draft of
the 2026-08-14 review-as-judgment plan proposed five deliverables and shipped one, because four
were refuted by machinery that already existed. `readable_surface.py:9-10` states the rule that
draft needed and this one is trying to obey: *"Not an extractor: any new derivation belongs to the
existing owner."* Almost every input the screen needs is already being written to disk by
something else.

So: **D1–D3 now (~250 lines, all deterministic, all in the gate). D4–D5 behind a measured
trigger. D6 is the honesty instrument that decides whether any of it survives.**

---

## Spec integrity (§0, once, before the deliverables)

### Assumptions, stated because the request supports more than one reading

**A1 — "Run" means a Playbook *session*, not a CI job.** The paper's unit is a training/eval
episode. Our nearest equivalent is one agent working session against one repo: it has a start, a
diff, a guard-exhaust trace, and a lock journal. This plan uses the session as the unit and defines
its boundary mechanically (D1's `--since <rev>` plus the yield log's own append window). If David
meant "one CI run", most of D1 still applies but S1/S2/S3/S5 vanish — those signals exist only
where the hooks run, which is the developer machine, not `gate.yml`.

**A2 — What is being detected is *the doer gaming its own verification*, not bugs.** Wrong code is
`§4`'s job (mutation score). This screen is aimed at the `HACK_CATALOG` classes — H2 (weaken the
test), H3 (over-mock), H5 (exploit the harness), H12 (self-serving adjudication), H15 (narrowed
scope reported as the whole). Anything that would show up as a failing test is out of scope by
construction; the screen only looks at the *shape of the work*, never at whether it is correct.

**A3 — The judge is advisory forever, not "advisory until we trust it."** §7's zero-flake rule and
`SKILL.md:1098` forbid gating on a probabilistic verdict. This is not a staging step toward a
blocking judge. If a judge finding is worth blocking on, the correct disposal is to turn its
*shape* into a deterministic guard — which is exactly what `review_ledger.py recurrence` already
does for review findings (a `deterministic` class key appearing in ≥2 records prints an UNBUILT
GUARD line). D4's output feeds that same loop; it never grows teeth of its own.

**A4 — "Holdout tests" means tests the doer cannot read, which on a laptop means CI-side only.**
This is the assumption most likely to be wrong in a way that matters, and it is why D3 is scoped
the way it is. See "The holdout problem, honestly" below.

### The materially simpler approach, stated so the review can choose it

**The whole of this plan can be replaced by ~40 lines**: teach `gate_yield.py` a `session` verb
that prints the same signal counts it already aggregates per *cycle*, scoped to one `--since <rev>`
window, and let a human read it. No new file, no new gate stage, no registry entry, no judge.

That version gets you the base rate — which is the only thing we actually need before deciding
anything else — at roughly a tenth of the cost. **I do not recommend it, for one reason:** the
per-cycle rollup drains the raw log (`gate_yield.py:15-17`), so a session-scoped reader built
inside it either fights that drain or silently reports zero on a drained log. That is the same
absence-reads-as-clean bug the whole design is trying to avoid, planted at the root. D1 is a
separate reader over the same exhaust precisely so the drain semantics stay unshared.

If David disagrees with that reasoning, take the 40-line version — it is a legitimate outcome of
this review, and the base rate it produces is the same number.

### What I am NOT proposing, named so it cannot creep in

- **Not a new telemetry pipeline.** Every input already exists. If a signal needs a new emitter,
  that signal is cut, not built. (`guard_note.py:30-31`: rows ride the one existing write path
  "so this can never become a second, drifting telemetry pipeline".)
- **Not a blocking gate.** The screen's exit code routes; it never fails a release. One exception,
  argued in D2: the *integrity* of the screen's own inputs is blocking, because a screen reading a
  forged log is worse than no screen.
- **Not a replacement for the adversary agents.** `/edge`, `/mutate`, `/probe` dispatch
  unconditionally and stay that way. The judge is an *additional* dispatch on flagged sessions, not
  a cheaper substitute for a scheduled one.
- **Not re-wiring `verify_verdict.py`.** CLAUDE.md is explicit: it is an archive reader, do not give
  it a consumer.

### Questions for David — I am not planning around these

1. **Q1 (blocking for D3 only):** is there a place to put a holdout test body that this repo's
   agent genuinely cannot read? A private sibling repo that `gate.yml` checks out with a deploy
   key would work; a `.gitignore`d directory would not. If the answer is no, **D3 is cut**, and the
   plan loses its second cheap signal class — which is a real loss, not a rounding error.
2. **Q2:** what is the acceptable per-cycle spend on the judge, in dollars? D4's budget cap is a
   number I will otherwise invent, and an invented budget is the mechanism by which "advisory"
   becomes "always on".
3. **Q3:** do you want the screen to run in `gate.yml` as well as locally? It would find almost
   nothing there (A1), but it would make the *screen's own* liveness visible from outside this
   machine — the H8 lesson applied to the screen itself.

---

## What already exists (the reverse sweep, done first)

Before proposing anything, the four answers this repo already has. Each of these is machinery the
plan must *use*, not re-derive.

| capability | where | what it means for this plan |
|---|---|---|
| Oracle split — deterministic gates, model verdicts as trend lines | `SKILL.md:475-480` (§5a), `:766` (§8 EVAL), `:807` (§9), `:1098` (§5b pending) | The authority ordering is already doctrine. D4 inherits it; it does not argue for it. |
| A calibration harness that deliberately has no judge | `calibration/run_calibration.py:7-8` — *"applies a DETERMINISTIC oracle: regexes the output must / must not match. No LLM judge"* | The precedent for "cheap oracle, no model" is ours already. D4 must justify why the cascade's judge is not a violation of it. |
| One write path for all guard exhaust | `hooks/scripts/_common.py:228` `log_yield_event`, reached only via `emit()` at `:250` | **This is D1's entire input.** No new emitter needed for S1/S2/S3. |
| Demotions leave a trace rather than a silence | `_common.py:262` logs `suppressed` when a gate is off; `emit()` logs `event: "block"` with `demoted_by: "break-glass"` even when demoted | S2 and S3 are one field read each. This was built for exactly the reason the screen needs it. |
| Self-report can move the numerator, never the denominator | `guard_note.py:24-28` | **The single most important precedent in this plan.** It is the shape D4's judge must copy verbatim. |
| Absence is UNMEASURED, never zero | `gate_yield.py:31` | D1's exit-3 refusal is this rule, not a new idea. |
| Dev/holdout as separate populations, with a leakage tripwire | `plant_forms.py:2`, `:201` (a holdout id in a gate surface or vendored tree = BURNED), `:165` (privately-held bodies carry a real sha256) | D3 is an extension of this file's *existing* design, not a new one. |
| Streaks never concatenated across populations | `plant_vitality.py:47` | D6's precision figures must be reported per population or not at all. |
| Tier 1 blocking / Tier 2 advisory-with-an-FP-budget | `dataflow_sweeps.py:17`, `SKILL.md:714-717` | The tiering vocabulary for D1's signals is already house style. Reuse it; do not invent "high/medium/low". |
| Vacuous-refusal exit code | `dataflow_sweeps.py` `EXIT_VACUOUS`, re-exported at `readable_surface.py:38` | D1 imports this constant. A third literal copy is how a rename leaves one reader wrong. |
| A closed, machine-owned finding vocabulary | `review_ledger.py:31` `FINDING_CLASSES`, `:33-35` `RECURRENCE_KEY` (short-kebab so adversarial content is *unrepresentable rather than escaped*) | **D4's output schema is this, reused.** It is also the injection defence. |
| Recurrence → UNBUILT GUARD | `review_ledger.py:391-408` | D4's terminal consumer. A judge finding that recurs becomes a guard; that is the whole point of letting it speak. |
| Content-hash integrity as a cheap signal | `plant_forms.py:126`, `check_scoreboard_integrity.py`, `gate_plan.py:56`, `gate_runner.py:171` | File-hash-as-signal is implemented four times. D2 adds a fifth *use*, not a fifth mechanism. |
| Guard-layer darkness detection | `_common.py` `write_heartbeat` / `guards_dark` (H8, the 2026-07-28 incident) | The screen is a guard. It gets the same treatment; see D1's liveness answer. |

**The conclusion this table forces:** the plan is a *reader and a router*. If any deliverable below
turns out to need a new producer, it is over-scoped and should be cut in review.

---

## The gap, stated precisely

Three things are missing, and they are not the same thing.

**G1 — No escalation edge.** The deterministic layer and the model layer run side by side on
different schedules, never in series. Adversary dispatch in `/edge`, `/mutate`, `/probe`,
`/tdd-plan` is unconditional ("a skipped adversary pass is a visible decision, never a default" —
`commands/edge.md:32`), and calibration explicitly excludes a judge. Nothing consumes a cheap flag
to decide where to spend. The one place the shape appears is `/readable`, which "must NEVER dispatch
a paid adversary itself — you may RECOMMEND one; the human spends" (`commands/readable.md:11-13`).
That is the cascade with a human as the router, and it is deliberate. **This plan proposes to keep
the human as the router and give them a screen — not to automate the routing away.**

**G2 — The cheap signals are pointed at the wrong subject.** Our hashes guard *calibration
artifacts* (is the corpus intact? is the scoreboard append-only?). They do not guard *sessions*
(did this run touch what it said it would?). Our holdouts are holdout **plants** that calibrate
verifiers on a schedule; they are not holdout **tests** that screen a run inline.

**G3 — No flagged-run queue.** `gate_yield` counts blocks and adjudications per cycle, but there is
no artifact that says *"these N sessions looked wrong, here is why"*. So even if we had a judge,
there would be nothing to point it at.

---

## Architecture

```
  session ends
      │
      ▼
  ┌─────────────────────────────────────────────────────┐
  │ D2  input integrity  (BLOCKING, tiny)                │  a forged log is worse than no log
  └────────────────────────┬────────────────────────────┘
                           ▼
  ┌─────────────────────────────────────────────────────┐
  │ D1  the screen        (deterministic, ~free)         │  reads exhaust + git; no model
  │     Tier 1 signals → flag on any one                 │
  │     Tier 2 signals → flag on any two                 │
  └────────────────────────┬────────────────────────────┘
                           │  exit 0 clean · exit 4 FLAGGED · exit 3 UNMEASURED
                           ▼
  ┌─────────────────────────────────────────────────────┐
  │ D5  the flag queue    (append-only, committed)       │  the artifact G3 is missing
  └────────────────────────┬────────────────────────────┘
                           │  human reads it, or D4 drains it
                           ▼
  ┌─────────────────────────────────────────────────────┐
  │ D4  the judge         (paid, advisory, capped)       │  can accuse; cannot exonerate
  └────────────────────────┬────────────────────────────┘
                           ▼
              review_ledger recurrence → UNBUILT GUARD → a new deterministic guard
                           ▲
                           └──────────── the loop closes here, in D1's own signal list
```

### The two invariants that make this an authority layer and not just a filter

**I1 — One-way authority. The judge can raise, never clear.** The flag row is written by D1 and is
append-only. D4 writes a *separate* row stamped `source: "judge"`. There is no code path by which a
model verdict removes or downgrades a deterministic flag — not "we choose not to", but "the writer
of that row is a different process and the file is append-only". This is `guard_note.py:24-28`
applied one level up: the screen writes the denominator, the judge can only move the numerator.

Mechanically pinned by `test_detection_cascade.py::test_judge_cannot_clear_a_flag`: run the screen
to a flag, run a judge stub returning `benign` with maximum confidence, assert the flag row is
byte-identical afterward and the queue still reports it open.

**I2 — Absence is UNMEASURED, never clean.** An empty yield log, a missing git range, an
unreadable journal → **exit 3, refuse**, never exit 0. This is `dataflow_sweeps`' vacuous-refusal
and `gate_yield`'s "a gate absent from the record is UNMEASURED, never zero", and it is the single
most likely way this thing rots: a screen that quietly reports clean on a dark repo is a worse
artifact than no screen, because it manufactures the confidence it was built to withhold.

Pinned by `::test_empty_exhaust_refuses_rather_than_passing` and, in the other direction, by the
forced-positive in D6.

### Why prompt injection is contained here and not merely hoped away

The judge reads material the doer produced, which is untrusted by construction. Three structural
containments, none of which is "instruct the model to ignore instructions":

1. **The judge never sees free prose.** Its input is a rendered fact block: signal codes, `file:line`
   citations, and the specific diff hunks the signals named. Same discipline as `readable_surface`
   — facts with citations, narration downstream.
2. **Its output vocabulary is closed and unrepresentable-if-wrong.** Verdict is one of a fixed
   tuple; the key is `review_ledger.RECURRENCE_KEY` short-kebab, *imported*, not re-typed. Anything
   an injected instruction could make the model say — a newline, a pipe, a "IGNORE PREVIOUS" — is
   not representable in the output schema, so it fails validation rather than reaching a human-facing
   line. `review_ledger.py:33-35` states this reasoning for its own keys; this is the same defence.
3. **Its worst case is a false accusation, not a false clearance** (I1). An injection that
   successfully manipulates the judge can make it flag something benign. That costs a human five
   minutes. It cannot unflag anything, which is the attack that would matter.

---

## Deliverables

### D1 — `triage_screen.py`: the deterministic first-pass filter

**Plain English:** after a session, one command reads the guard exhaust and the git diff and says
either "nothing here", "I can't tell", or "these three specific things look like an agent working
around its own verification, here are the citations".

**Happy path:** `python3 plugins/tdd-playbook/bin/triage_screen.py screen --since <rev>` prints one
summary line plus zero or more signal rows, each with a code, a tier, and a `file:line` citation.
Exit 0. Two runs on an unchanged tree are byte-identical (the `readable_surface` determinism rule).

**The signal roster.** Tier assignment follows `SKILL.md:714-717`: Tier 1 is an exact field read
with no heuristic and no glob; Tier 2 is pattern-scoped and ships with an FP budget.

| id | tier | signal | derived from | hack class |
|---|---|---|---|---|
| S1 | 1 | a `block` event with no `source:"agent"` `guard_note` row in the same window | yield log | H5 / H2 route-around |
| S2 | 1 | `demoted_by: "break-glass"` present | yield log (`_common.emit`) | blanket demotion as habit |
| S3 | 1 | `event: "suppressed"` — a gate that was off while findings fired | yield log (`_common.py:262`) | H8 guard-dark |
| S4 | 1 | unlock journalled `--class gate-wrong` | tdd_lock journal | H12 self-serving adjudication |
| S5 | 1 | a registered holdout artifact's sha256 ≠ recorded | D3 register | oracle tampering |
| S6 | 2 | a test file and its subject module modified in the same commit | git diff | H2 weaken-to-pass |
| S7 | 2 | net mock constructs added above threshold | git diff, pattern-scoped | H3 over-mock |
| S8 | 2 | net assertions removed while subject lines added | git diff arithmetic | H4 assertion-free |
| S9 | 2 | files changed outside the paths the plan's deliverables named | `gate_plan` digest + diff | H15 narrowed scope |

**Flag rule (deterministic, no model, stated in one place):** FLAGGED if any Tier-1 signal fires,
or if ≥2 Tier-2 signals fire. Nothing else. The rule lives in one constant so the planted test can
address it directly.

**Edge cases** (real scenarios, no jargon):
- A session with no guard blocks at all → is that clean, or did the hooks not run? → **exit 3
  UNMEASURED**, and say which input was missing. Never exit 0.
- Break-glass used once, for a genuine emergency, with a recorded reason → still flags (S2). The
  screen is not the place to decide whether the emergency was real; the queue entry carries the
  reason, and the human closes it in ten seconds. A screen that tries to be clever about intent is
  a judge with no budget line.
- A one-line docs commit → every Tier-2 signal is structurally inapplicable. It must report
  "0 of 9 applicable", never "0 findings" — the denominator rule (§12), same as `dataflow_sweeps`'
  summary line.
- The yield log was drained by a `gate_yield rollup` between the session and the screen →
  detectable (the log exists and is empty vs never existed) and must be **exit 3**, with the drain
  named as the reason. This is the specific bug that killed the simpler alternative.
- Two agents in two worktrees writing the same log → rows carry `host` and `ts`; the window is
  time-and-rev bounded. Overlap is reported, not silently merged.
- A holdout id is in the diff → that is not a signal, that is a **burned plant**; defer to
  `plant_forms.leakage_problems` and fail the way that file already fails.

**UX tests** (what David does → what he sees):
- Runs it after a normal session → one line, exit 0, nothing to read.
- Runs it after a session where he broke glass → a flagged row naming the reason string he typed,
  so he recognises his own action rather than being accused by a code.
- Runs it in a fresh clone → refusal with the init instruction, verbatim, like
  `readable_surface`'s exit 3. Never an empty page narrated as health.
- Runs `--explain S7` → the FP budget, the pattern it matched, and the sentence "this is Tier 2:
  advisory, and it is wrong sometimes on purpose."

**Integration surface:**
- *Consumes:* the yield log via `_common` (import, never re-read the path), the tdd_lock journal,
  `git`, `gate_plan`'s digests, D3's register. No new producers.
- *Emits → named consumer:* the flag queue (D5) — consumed at `triage_screen.py`'s own
  `queue` verb and by D4's drain; and one `log_yield_event(gate="triage_screen", ...)` row per run,
  consumed by `gate_yield.py rollup`'s existing per-gate table (field granularity: `gate` and
  `event`, read at `gate_yield.py`'s rollup parser). **A screen that produced nothing a reader
  consumes would be the write-only loop §0 forbids** — and the reader here is one that already
  exists, which is the test of whether this deliverable earned its place.
- *Surface parity:* CLI only, both hosts (Claude via `${CLAUDE_PLUGIN_ROOT}`, Codex via the
  adapter). Not a slash command in v1 — deliberate, stated: a command implies a per-session ritual,
  and the ritual is what we have not yet justified.
- *Reverse sweep:* `/grade` (§13) should read the queue when grading a cycle — becomes D5's
  consumer, listed there. `gate_yield.py candidates` should learn that a gate with flags but no
  judged outcomes is UNMEASURED rather than zero-yield — **a one-line change, listed in D5, not
  silently deferred.** `run_calibration.py` should print the queue depth in its DECAY block —
  dated debt, owner David, expiry 2026-11-15, because it needs a cycle of real data first.

**Tripwire:** BUILT (module + `bin/` vendoring by `COPY_TREES`) · WIRED (a gate-manifest stage
runs it in `--check` mode) · ACTIVATED (on by default; there is no flag to turn it off, because a
screen with an off switch is the H8 shape) · EXERCISED (planted-flag fixture in the suite) ·
RUNNING (its own `log_yield_event` row is the heartbeat — if the screen stops running, its absence
from the yield record is visible in the same table that watches every other gate).

---

### D2 — Input integrity: the one blocking piece (~30 lines)

**Plain English:** before the screen reads the exhaust, prove the exhaust has not been rewritten.

**Why this and nothing else is blocking:** the screen is advisory, but a screen reading a forged
input is not merely useless — it launders. The append-only property of the yield log is what makes
S1's "unaccounted" count mean anything at all, and `guard_note.py:24-28` rests the entire
numerator/denominator argument on it.

**Mechanism, reusing what exists:** `check_scoreboard_integrity.py` already enforces append-only
over `history.md` against a baseline rev. D2 is the same check pointed at the *committed* portion
of the yield record (`docs/calibration/gate_yield.md` rows), plus a recompute of D3's register
hashes. It is a call into the existing function, not a second implementation.

**Honest limit, stated because the docstring would otherwise flatter it:** the *raw* log is
ephemeral and gitignored (`gate_yield.py:28-31`), so it cannot be integrity-checked against
anything. D2 protects the committed rollups and the register. A determined actor with a text editor
and local write access defeats the raw-log half — this detects the accidental and the careless, not
the determined, exactly as `_common.write_heartbeat` says of itself ("forgeable by touching the
file"). That residue is stated here, once, and belongs in the module docstring.

**Integration surface:** *Consumes* `check_scoreboard_integrity`, `plant_forms`. *Emits →* exit
code, consumed by the gate manifest stage. *Parity:* CI + local. *Reverse sweep:* none — this is a
call site, not a capability.

---

### D3 — The holdout register (CONDITIONAL on Q1)

**Plain English:** a small set of tests the doer has never seen, that must still pass. If work
"passes" while a holdout fails, something was tuned to the visible oracle.

**The holdout problem, honestly.** This is the deliverable most likely to be theatre, so the
argument is made in the plan rather than discovered later. **In a repo the agent can read, a
holdout is not a holdout.** The paper's setting has an eval harness the policy cannot inspect; our
setting has an agent with `Read` on the whole tree. `plant_forms.py` already solved this once, and
its solution is the only one available to us:

- ids are registered publicly, **bodies are held privately** (`plant_forms.py:165` — a
  privately-held body cannot also be public, and it still carries a real sha256);
- a **leakage tripwire** (`:201`) makes a holdout id appearing in any gate surface or vendored tree
  a BURNED plant, caught the moment it enters a worktree (`:64`).

D3 extends `FORMS` from plants to *test artifacts* using that existing register. The bodies live
wherever Q1 says they can (a private sibling repo checked out by `gate.yml` with a deploy key is
the only design I would sign off on); the repo holds ids + hashes only.

**If Q1's answer is no, cut this deliverable.** Do not ship a `.gitignore`d holdout directory and
call it a holdout — that is the H13 shape (a guard's self-claim, unverified), and I would rather
lose the signal than record a false one. S5 drops from the roster and D1 ships with eight signals.

**Edge cases:** a holdout that has passed every run for K cycles is *saturated*, not healthy —
defer to `plant_vitality`'s existing classification rather than inventing a second one. A holdout
whose hash drifts is S5, blocking via D2. A holdout id appearing in a downstream vendored `.claude/`
is burned; the tripwire already scans vendor dirs.

**Integration surface:** *Consumes* `plant_forms` (extend `FORMS`, do not fork). *Emits →* the
register, read by D1's S5 (field granularity: `content_sha256`, read in `triage_screen`'s S5
evaluator) and by `plant_forms check` in the existing gate stage. *Parity:* CI-only by
construction — **and that divergence is stated here, at plan time**, not discovered by a user: the
local screen will always report S5 as `not applicable`, and it must print that rather than
`clean`. *Reverse sweep:* the calibration corpus itself could adopt CI-side private bodies; dated
debt, owner David, expiry 2026-11-15.

---

### D4 — The judge (GATED — do not build until D6 reports a base rate)

**Plain English:** on a flagged session only, one fresh agent reads the named signals and says
whether it thinks a human should look.

**Trigger to build, mechanical, decided in advance:** after ≥3 committed cycles of D5 data,
build D4 only if `0 < flag_rate < 0.5` — that is, the screen flags *some* sessions but not most.
If the flag rate is 0, there is nothing to judge and the correct action is to sharpen the signals.
If it is above half, the screen is a noise generator and the correct action is to fix the screen,
not to hire a model to read its noise. **Either failure mode is cheaper to discover from D5's table
than from a built judge**, which is the entire argument for staging.

**Contract, if built:**
- *Input:* a rendered fact block — signal codes, citations, the named diff hunks. Never raw prose.
- *Output:* `{verdict: one of ("worth-a-look","benign","insufficient-evidence"), recurrence_key:
  RECURRENCE_KEY, citations: ≤3 file:line}`. Vocabulary imported from `review_ledger`, not
  re-typed (`review_ledger.py:27-30` states why).
- *Authority:* I1. It appends a `source:"judge"` row. It cannot write, edit, or close a D1 flag.
- *Cost:* a per-cycle cap (Q2). **When the cap is hit, remaining flags stay queued and the queue
  says so** — no silent truncation, per §13's no-silent-caps rule.
- *Model:* cheap tier, fresh context, refute-framed, per §13's independent-grader rule.
- *Calibration:* a probabilistic verifier, so it enters `scenarios.json` with a deterministic
  oracle and `DEFAULT_REPEAT` 3 like every other agent (`run_calibration.py:42-43` — "one roll of a
  probabilistic verifier is a coin flip, not a measurement").

**The tension I want reviewed, not buried:** `run_calibration.py:7-8` says *"No LLM judge — the
oracle split governs our own calibration too."* D4 adds an LLM judge to this repo's own loop. My
argument that this is consistent rather than a violation: that sentence governs *verdicts that
decide pass/fail*, and D4 decides nothing. But it is close enough to the line that I want David to
look at it rather than take my word, and if the answer is "no judge in our own loop, full stop",
then D1–D3 and D5–D6 still stand on their own and the human stays the router permanently — which
is `commands/readable.md:11-13`'s existing position, and a defensible end state.

---

### D5 — The flag queue and the yield table (the artifact G3 is missing)

**Plain English:** an append-only committed record of what was flagged, what happened next, and
what it cost.

**Shape, reusing the house one:** one committed row per cycle in `docs/calibration/triage.md`,
written by the same `gate_yield`-style rollup, with columns `date · sessions · screened · flagged ·
by-signal · judged · confirmed · false-positive · unresolved`. Cycles disjoint, raw log drained,
identical semantics to `dataflow_yield.md` so there is one thing to learn, not two.

**Consumers, named:** `/grade` reads it when grading a cycle (§13's who-caught-it split gains a
row: *caught by the screen*). `gate_yield.py candidates` learns that flags-without-outcomes are
UNMEASURED. `run_calibration`'s DECAY block prints the depth (dated debt, above).

**The column that decides everything: `false-positive`.** It is filled by a human, and it is the
input to D6.

---

### D6 — Calibrating the cascade (§13, non-negotiable, and the reason to trust any of this)

Three separate obligations, because they rot differently.

**(a) Guard-calibration replay (v1.25 rule).** D1 is a new guard born from a specific concern, so
before it is trusted it is replayed against a *motivating artifact*. We have real ones: the
2026-07-28 guard-dark incident (`git show <pre-fix-rev>` for the heartbeat commit) must light S3;
the break-glass clamp bug recorded in `_common.resolve_mode`'s docstring — where breaking glass
silently turned five guards *off* — must light S2 and S3 together. **A guard that goes red is not
proven; a guard that goes red *for the reason it was built* is.** Each replayed shape is then
frozen as a planted fixture citing the pre-fix sha in its docstring.

**(b) Two-directional table (§13, "a guard's claim about itself is an unverified claim").** D1
ships with both halves: what it MUST flag (the planted sessions) and what it MUST NOT (a clean
session, a docs-only commit, a legitimate emergency break-glass with a recorded reason and full
guard_note accounting — that last one is Tier-1 S2 and *should* still flag; the ALLOW row is a
session with zero blocks and a complete diff, which must exit 0 and not 3).

**(c) The forced positive — the answer to "a screen that never fires reads as health".** Each
calibration cycle plants one synthetic flagged session and requires the pipeline to surface it end
to end. This is the same instrument as the plant corpus and it exists because I2 protects against
*absent* input, not against a screen that runs happily and detects nothing. Without (c), a
regression that breaks the flag rule produces a permanently green triage table, which is precisely
the artifact this plan exists to avoid producing.

**Kill criteria, pre-committed (R4, the deletion ratchet):**
- flag rate 0 across 3 committed cycles **and** the forced positive passing → the screen is
  measuring nothing real; demote to warn with a dated re-check.
- of classified flags, every one adjudicated false-positive across ≥2 cycles → retirement candidate
  by `gate_yield`'s existing rule. Note the precondition it already encodes: *unadjudicated*
  friction is not evidence of zero yield.
- D4 built and its `confirmed` count 0 across 3 cycles → retire the judge, keep the screen.
- Retirement is never silent deletion: dated demotion journal, expiry fails the release gate.

---

## §6c flow table

| flow | producer | consumer | liveness test |
|---|---|---|---|
| guard block/suppress/demote events | `_common.log_yield_event` (exists) | `triage_screen` S1–S3 | planted session fixture asserts each event kind reaches a signal row |
| guard_note accounting rows | `guard_note.py` (exists) | S1's numerator | fixture: block without note → S1 fires; block with note → S1 silent |
| unlock class | `tdd_lock` journal (exists) | S4 | fixture per class; only `gate-wrong` fires |
| holdout hashes | D3 register | S5 | hash-drift fixture (CI-only; local asserts `not applicable`, never `clean`) |
| diff shape | `git` | S6–S9 | one fixture repo per signal, each with a paired clean control |
| flag rows | `triage_screen` | D5 queue, `/grade`, D4 drain | `test_flag_reaches_the_committed_table` |
| judge rows | D4 | D5 `confirmed` column, `review_ledger recurrence` | `test_judge_row_never_mutates_a_flag_row` (I1) |
| screen liveness | `triage_screen`'s own yield row | `gate_yield rollup` per-gate table | absence of the row in a cycle reports UNMEASURED |

Every row has a consumer. If review finds one that does not, that deliverable is cut, not deferred.

---

## Deploy surface

Required: this ships into downstream repos, so the session does not control the copy that runs.

- **Runs where:** (1) David's machine, post-session, via `bin/`; (2) `gate.yml` on GitHub Actions,
  for D2 and D3; (3) every downstream repo carrying vendored `.claude/`.
- **Gets there how:** `scripts/install_into_repo.py` `COPY_TREES` auto-vendors `bin/` by directory
  walk — no per-file roster exists, so nothing must be registered (this was verified and recorded
  in the 2026-08-14 plan's D0 deletion). D3's private bodies do **not** vendor; they reach CI by
  deploy key only.
- **Verified how:** the vendored screen's own `log_yield_event` row appears in the downstream yield
  record. Absent row = not running, and the existing per-gate table shows it as UNMEASURED without
  any new mechanism.
- **Divergence:** a downstream repo on an older vendored copy screens with fewer signals and
  **says so in its summary line** (signal roster version printed every run). Who notices: the
  refresh prompt's step 6 report, which already asks for conflicts to be flagged rather than
  silently resolved.

---

## Registry, debts, and gate impact

**New capability entries** (`capabilities.json`, `validate` must pass before commit):
`triage-screen`, `triage-queue`, and — only if built — `triage-judge`. Each carries
`deploy_surface` per above.

**Integration debt entries, all with owner + dated expiry (the `{what, owner, expires}` R-DEBT
shape, never a sibling format):**
| what | owner | expires |
|---|---|---|
| `run_calibration` DECAY block prints triage queue depth | David | 2026-11-15 |
| calibration corpus adopts CI-side private bodies (if D3 ships) | David | 2026-11-15 |
| D4 build-or-kill decision from D6's base rate | David | 2026-12-15 |

Each expiry is proven in the same commit: `validate --as-of <expiry+1>` exits **1 (EXPIRED)**.
Exit 2 is usage, never proof.

**Gate impact:** two new `fixed_stages` in `gate-manifest.json` (`triage-integrity` for D2,
blocking; `triage-screen --check` for D1, which asserts the screen *runs and refuses correctly*,
not that any repo is clean). Both digests re-acknowledged — `gate_plan.py:91-98` will red the gate
otherwise, by design. New suite file `plugins/tdd-playbook/tests/test_detection_cascade.py`, picked
up by the existing `suite_glob`. Expected added gate wall-clock: seconds; the screen is file reads
and one `git log`.

**Version:** a minor bump (1.36.0 → 1.37.0) touching all four identity files plus CHANGELOG, and
covered by a review-ledger record whose `review_range.head` is the bump commit.

---

## Sequencing

1. **D6(a) first — the replay fixtures, red.** Build the two motivating-artifact sessions from
   `git show` before any screen exists. This is red-first applied to a guard: the fixtures must be
   unrunnable-and-red for the right reason before D1 has a line of code.
2. **D1 Tier-1 signals only** (S1–S4). Green against the fixtures.
3. **D2.** Blocking, tiny, gate stage.
4. **D5 queue + first committed row.** Now the base rate starts accruing.
5. **D1 Tier-2 signals** (S6–S9) with their FP budgets, advisory from birth.
6. **D3** — only after Q1 is answered yes.
7. **D6(b), (c)** — the two-directional table and the forced positive, before the release that
   ships any of it.
8. **STOP.** Three cycles of D5 data. Then the D4 trigger evaluates itself against a rule written
   before anyone had a stake in the answer.

---

## Risks, including the ones that argue against building this

**R1 — The screen becomes ceremony charging rent.** §13's second decay direction. Mitigated only
by D5's `false-positive` column and the pre-committed kill criteria. If we will not actually retire
it when the data says to, we should not build it.

**R2 — Nine signals is too many for a v1.** Plausible. The defensible minimum is S1–S3, which are
three field reads over a log that already exists and cover the guard-integrity classes directly. If
review wants to cut, cut from the Tier-2 end; the Tier-1 four carry most of the value at almost
none of the cost.

**R3 — The base rate is zero and stays zero.** Genuinely likely: David is one careful operator with
strong guards, and the population of sessions is small. Then the honest outcome is that this repo
does not have the problem the paper describes, D4 is never built, and the screen demotes to warn.
**That is a successful outcome of this plan, not a failed one** — it is a measurement we do not
currently have, obtained cheaply. It should be stated in advance so it is not later re-narrated as
a win.

**R4 — I2 is the whole design and it is one `if`.** The difference between this artifact and a
liability is a single refusal path. It gets a planted test, a two-directional table row, and it is
the first thing the forced positive exercises.

**R5 — The judge's advisory status erodes.** The historical shape: an advisory number becomes a
dashboard, the dashboard becomes a norm, the norm becomes a gate nobody voted for. The structural
defence is that D4's output has *no exit-code consumer at all* — same as `/readable` — and that
turning a judge finding into teeth requires the `review_ledger recurrence` path, which produces a
*deterministic* guard, not a model in the gate.

---

## Loop closed: **NO**

**The `integration-adversary`, `architecture-adversary`, and `adoption-adversary` passes were NOT
dispatched.** §0 makes the first two mandatory for any plan adding a user-facing capability or a
config gate, and this plan adds both. Recording the skip as a visible decision rather than a
default, per `commands/edge.md:32`:

**Why:** this session was instructed not to dispatch subagents. That is an operator constraint, not
a judgment that the passes are unnecessary — and on the evidence of the 2026-08-14 plan, which lost
four of five deliverables to exactly these three adversaries, **the un-adversaried state of this
document is its single largest defect.** Read it as a v1 draft with a known ~50% expected
survival rate, not as a reviewed plan.

**The three briefs, ready to dispatch, refute-framed:**

1. **`architecture-adversary`** — *"Does this fix the root at the right seam, or add an Nth copy of
   something that exists? Specifically: is `triage_screen` a second `gate_yield` with a different
   window, and should the session-scoped reader be a verb on `gate_yield` instead? The plan argues
   no on drain semantics alone — refute that argument."*
2. **`integration-adversary`** — *"Name what this plan should touch but doesn't. Check every row of
   the flow table for a consumer that reads the specific field, at `file:line`. Check whether
   `/grade`, `run_calibration`, and the downstream refresh prompt are genuinely wired or merely
   promised as debt."*
3. **`adoption-adversary`** — *"D5's `false-positive` column is filled by a human. Nothing in this
   plan measures whether that ever happens. If it doesn't, every kill criterion is inert and the
   screen is permanent by default. Is this stranded?"*

I would also want the **`script-adversary`** on D2, since it is an operator-facing integrity check
and the question "does the probe actually test its target, or report PASS having touched nothing"
is exactly its failure mode.

**Every finding those passes return must be independently verified against the tree before it is
accepted** (§12 — a subagent report is an unverified claim). The 2026-08-14 plan's correction
record is the model for how that verification gets written down.

---

## Claims

Claims made in this document that rest on the tree: 23 of 23 cite a `file:line` or a named
artifact. Claims that rest on judgment rather than the tree, listed so they are not mistaken for
findings: the D4 build trigger thresholds (`0 < rate < 0.5`), the "≥2 Tier-2 signals" flag rule,
the three-cycle windows, and R3's likelihood assessment. None of those four is measured; all four
are proposals for David to set.
