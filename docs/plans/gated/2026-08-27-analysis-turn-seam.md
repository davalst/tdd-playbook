# REVISED build plan — close the ANALYSIS-turn enforcement gap

**Supersedes:** `tdd-playbook-analysis-seam-plan.md` (2026-08-27).
**Revised:** 2026-08-27, after four Playbook adversaries + an independent Codex panel review.
**Repo:** `davalst/tdd-playbook` @ `86d5504` / v1.45.0.
**Status:** AWAITING DAVID'S APPROVAL. Nothing built.

---

## §R.0 — What survived review, in one paragraph

The **diagnosis is correct and verified**: 14 of 18 hook bindings sit behind a write or a
shell matcher, and the two `Stop` hooks are inert on a read-only turn, so an analysis turn is
unpoliced. `Stop` is also the **right event** — it is the earliest moment at which "this output
asserts P about X" and "this session opened X" both exist. But **all three deliverables landed
downstream of machinery this repo already ships**, and **D2's detection rule was measurably
false against the real host**. The revision keeps the goal, moves the seams, folds two guards
into one, and ships at `off` behind an instrument that can actually justify a promotion.

---

## §R.1 — The five findings that forced a restructure

Each was found independently by two or more reviewers, and each was re-verified at source by me.

**F1 — D2 could never have fired. Measured, not argued.**
D2 keyed on `tool_use` named **`Task`** with an exact-match `subagent_type`. I parsed the 40
most recently modified real transcripts: **47 of 47 dispatch records are named `Agent`; zero
are named `Task`** — and the majority carry a `tdd-playbook:` prefix
(`tdd-playbook:architecture-adversary` ×7, `tdd-playbook:claims-verifier` ×5). D2 as drafted
recognises no dispatch ever, so it would flag **every compliant plan turn** and report clean on
every non-compliant one. The repo already paid for this exact lesson and wrote it down:
`docs/telemetry.md:31` — *"the dispatch tool is **`Agent`**, NOT `Task`. `grade_from_otel.py`
was specified against `Task` and would have counted zero dispatches forever while its own
fixtures passed."* Found by `claims-verifier`, `edge-case-adversary`, and
`architecture-adversary` independently.

**F2 — "This turn" does not exist in the machinery the plan reuses.**
Exactly two transcript consumers exist: `build_completion_reminder.py:75` (forward scan of the
*whole file*, no delimiter) and `capture.py:265` (backward scan for the *last* assistant line).
Neither can say "this turn". So E6/E18 ("read in an EARLIER turn → FLAG") are unimplementable
as cited — and worse, session-scoping **inverts the silent rows**: one `Read` at hour zero
silences the guard for a ten-hour session, while the plan's own diagnostic case (13 greps, 2
reads) is a per-turn ratio. The obvious boundary is also wrong: tool *results* are stored as
`type:"user"` lines, so "everything after the last user message" yields a window with no reads
and flags everything.

**F3 — The decay contract cannot measure its own named metric.**
Found by all four reviewers. `log_yield_event` writes `{ts, source, host, gate, event,
findings}` — **no session id, no turn id** — so "how many fires were followed by a corrective
read in the next turn" has no supplier. Worse, `emit(NAME, [])` hits `if not lines:
sys.exit(0)` **before** any logging, so clean runs write no row: there is **no denominator**,
and a blind host, a missing transcript, a timed-out hook and a genuinely-verified turn are all
byte-identical (namely, absent). And `gate_yield.py:162` pins `GATE_EVENTS = ("block", "warn",
"override", "suppressed", "response")` — the plan's own `capped` and `blind-host` events would
be written and **silently dropped by their named consumer**. §0.5 was prose with no mechanical
trigger, against the repo's standing rule that deferrals need dated mechanical triggers.

**F4 — The eight "must stay silent" tests would all have passed for the wrong reason.**
`doctor.py` **does not exist in this repo**, and `test_hooks.py::run()` sets no `cwd` and no
`CLAUDE_PROJECT_DIR`. So E2, E4, E5 and E11 would every one go green on the *"file doesn't
exist → silent"* branch, with the citation logic they claim to calibrate never executed. The
plan's §4a vacuity test would not have caught it: asserting "this fixture contains no read"
reads the fixture the test just wrote — it proves the author's intent, not that the guard
parsed anything.

**F5 — D3 was the anti-duplication deliverable and would have shipped the fifth copy.**
Four tool-name sets already exist **and already disagree**: `grade_from_otel.py:30` includes
`NotebookEdit`; `build_completion_reminder.py:94`, `red_lock.py:208` and `fixture_guard.py:155`
do not. `grade_from_otel.py:28-29` already defines `READ_TOOLS` and `SEARCH_TOOLS` — the exact
read-vs-search distinction D1 is founded on. D3 would have refactored one of four onto a new
fifth definition and left the disagreement live.

---

## §R.2 — Corrections to the original's own premises

| Original claim | Corrected |
|---|---|
| "an analysis turn passes through all **18** bindings untouched" | **17 of 18.** `session_edited_paths` returns `paths or None`; a read-only turn returns `None`, the `if session is not None` narrowing at `build_completion_reminder.py:117` is skipped, and the hook falls through to whole-tree `git status`. On a **dirty tree** it fires *"source changed with NO test change this turn"* on a turn that changed nothing. **This is a live pre-existing misattribution bug — see D4.** |
| V8: "`capabilities.json` (32 entries)" | **33** at HEAD. Minor — but it falsifies the plan's blanket *"RE-VERIFIED … every load-bearing fact still holds"*, so that blanket should not be trusted on the other rows without the per-row check I ran. |
| §0.6: "Full `python3 tests/test_hooks.py`" | **`sh scripts/civerd_gate.sh`, unpiped, `rc` captured.** CLAUDE.md's standing rule: the suites run ONLY via the one blessed entrypoint. A gate runner concretely exists (`bin/gate_runner.py`, driven by `gate-manifest.json`); the hedge was unnecessary. |
| D1's motivating message example | Does not satisfy D1's own reference rule. The rule accepts `path/to/file.ext` or `file.ext:123`; the example is a **bare basename** (`doctor.py reads the readable field`). |
| §0.4 "Registers into" | Incomplete. Two gates hard-fail: `test_guard_roster_derived_and_pinned` asserts `partition == EXPECTED_MODES` by **dict equality**, and `host_parity.py:150` raises `ParityError` on an unacknowledged inventory digest. Also needs `CLAUDE.md`, `README.md`, `host-parity-policy.json`, regenerated `host-parity.json`. |

---

## §R.3 — The revised deliverables

### D0 (NEW, ships FIRST) — `transcript.py`: one reader, one vocabulary

A **sibling module**, not `_common.py` bloat — `_common.py` is the mode/emit layer, and
`host_contract.py:5-8` states the doctrine: *"It does not know Claude/Codex event JSON …
those are adapter transport concerns."*

Owns, and nothing else owns:
- Bounded JSONL traversal with an env-tunable cap, reusing `capture.py`'s proven backward-scan
  shape and its `truncated` convention (**not** a second, conflicting 50 MB/`capped` convention).
- `last_assistant_text` — moved from `capture.py`, which keeps importing it.
- **`current_turn()`** — the boundary primitive that does not exist today. Scans back from the
  final assistant message to the last user message **whose content is a string, not a
  `tool_use_id` block**. Returns `complete | capped | unreadable` — never a silent partial.
- **ONE tool vocabulary** — `READ_TOOLS`, `SEARCH_TOOLS`, `EDIT_TOOLS`, `DISPATCH_TOOLS` —
  with `grade_from_otel.py`, `build_completion_reminder.py`, `red_lock.py` and
  `fixture_guard.py` **re-pointed at it in this same change**, resolving the `NotebookEdit`
  disagreement explicitly rather than inheriting it.
- Dispatch recognition: `name == "Agent"`, `subagent_type` matched **after stripping an
  optional `<plugin>:` prefix**, against the live `agents/*.md` roster. Non-roster types
  (`Explore`) are dispatches-of-unknown-remit, not non-dispatches. The code comment cites
  `docs/telemetry.md:31` and `test_grade_from_otel.py::test_subagent_dispatch_counting` so this
  cannot regress a third time.

**Host vocabulary stays OUT.** No Cheliped tool names in shared code until `cheliped` exists in
`host_parity.HOSTS`, `runtime_host()` and `adapters/cheliped/`. Today `HOSTS = ("claude",
"codex")` and `test_host_parity.py:66` asserts set equality **per asset** — adding a third
host's vocabulary to a two-host model would corrupt the very `gate_yield` evidence that decides
these guards' fate.

### D1 (REVISED) — `cite_guard`: one guard, two rules, one transcript pass

**Folded: D2 no longer exists as a separate script.** The two differ only in a text predicate
over an identical parse; as two scripts, `Stop` goes from 2 processes to 4 and the transcript is
opened up to six times per turn. `emit(name, lines)` already takes a list. One review date, one
kill condition — which is what the original §0.5 wanted anyway when it said *"do not tune it
twice."*

**Rule A — the unread citation.** Refounded on `bin/verify_citations.py`, which is already
*"the mechanical half of the §12 claims discipline"*: it parses `path:line` from prose with the
false-positive guard D1 would have re-derived, resolves quotes, and refutes negatives. D1's
genuinely new logic is one line of set arithmetic — *claimed paths ∖ read paths*. Shell reads
are classified by `lock_guard.py`'s existing splitter, which already encodes *"sed/perl only
rewrite in place with `-i`; without it they are readers."*

**Rule B — the false loop-closure self-report.** Keyed on the **declared token**, not on plan
shape: `commands/tdd-plan.md:66` (and `edge.md`, `mutate.md`, `probe.md`,
`integration-audit.md`) require the turn to emit `Loop closed: yes (…)`. A turn that prints that
line with **no dispatch in the transcript** is a false self-report — near-zero false positives,
covers five commands instead of one, and is exactly the *"announced is not executed"* defect the
original's E17 wanted. This replaces the "two or more §0 markers" detector, which would have
flagged every review turn, every quoted plan, `/readable` (whose contract at `readable.md:11-13`
**forbids** the remedy D2 would demand), and the release turn.

**Scope decision (needs your call — see §R.5):** turn-scoped via `current_turn()`, with E6/E18
retained; or session-scoped, with E6/E18 dropped and the message saying so.

### D2 (NEW, replaces the old D3) — make the instrument able to justify a verdict

Without this, §0.5 is unfalsifiable prose and the guard can never earn a promotion.
- Add `session_id` (and turn ordinal) to `log_yield_event` — small, and it benefits every guard.
- Log **clean runs**, so there is a denominator. Absent data is UNMEASURED, never zero —
  `_common.py:47-48` already states this doctrine; the yield instrument currently violates it.
- Extend `GATE_EVENTS` to accept `capped`, `blind`, `unmeasured`, so the honesty events the
  guard emits are not dropped by their own consumer.
- Emit `blind` when the transcript is structurally incapable of answering (Cheliped's
  `Edit`-only shim, an empty transcript, a cap hit) — **never clean**.

### D3 (NEW) — fix the misattribution bug found during review

`build_completion_reminder.py` reports *"source changed with NO test change **this turn**"* on a
read-only turn when the tree is dirty from an earlier turn. Red-first regression test, then fix.
Unrelated to the guards, found by the review, cheap.

### D4 — Registration, complete this time

`hooks.json` · `_DEFAULT_MODES` · `EXPECTED_MODES` in `test_hooks.py` · `capabilities.json` ·
`host-parity-policy.json` digest re-acknowledgement · regenerated `host-parity.json` (Claude
*supported*, Codex *unavailable* — `portable-host-contracts.md` already lists `Stop` as not
migrated) · `CLAUDE.md` · `README.md` · regenerated `AGENTS.md`. **Expect two RED tests at this
step — that is the sweeps working. Do not "fix" them by loosening a pin.**

---

## §R.4 — Mode: `off`, not `warn`

The original shipped both at `warn`. Three independent objections, all sound:

1. **The message can't reach its reader.** `_common.py:8-11`: exit 1 (warn) → *"first line of
   stderr is shown to the **user**"*; exit 2 (block) → *"stderr is fed back to **Claude**"*.
   D1's remedy (*"Open the file, or mark the claim inherited"*) is addressed to the agent, which
   at `warn` never sees it, and the turn is already over.
2. **The promotion condition was unsatisfiable by construction.** §0.5 allowed promotion to
   `block` *"only on evidence of a false claim caught **before publication**"* — but at `warn`
   the claim is always already published. The guard could never generate its own promotion
   evidence.
3. **v1.32.0 is the precedent.** Five guards retired on 31 warnings and zero blocks. Shipping
   two more `warn`-default guards *before* the instrument that could tell a useful warning from
   wallpaper is how you get the sixth and seventh.

**So: ship at `off`, opted-in, as a measured pilot**, with D2's instrument live. Promote to
`warn` on a real-output corpus and a stated false-positive budget; promote to `block` never,
until the one-byte-`Read` bypass (`Read(file, offset=1, limit=1)`, `cat X > /dev/null`) is
closed — a blocking gate with a one-line bypass is an H-class shape this repo catalogs.

Dark-by-default is itself a Playbook finding, so it is booked honestly: a **dated
`integration_debt` entry** in `capabilities.json` with an owner and an expiry that REDs the
suite, not a prose deferral.

---

## §R.5 — Four decisions that are yours, not mine

These are doctrine, and guessing would be the plan committing its own diagnosis.

1. **Does a subagent's read count as the turn's read?** Subagent transcripts live in a
   **separate** `<session>/subagents/agent-*.jsonl` sidecar (verified — the directories exist).
   So a `claims-verifier` that opens a file and reports back leaves **no read record in
   `transcript_path`**. As drafted, D1 flags the relayed finding — meaning Rule B rewards
   dispatching an adversary and Rule A punishes it. Follow the sidecars, or treat a relayed
   claim as its own category?
2. **Turn-scoped or session-scoped?** (F2.) Turn-scoped is truer to the defect and costs a new
   primitive; session-scoped is cheap and lets one early read silence a ten-hour session.
3. **Does a tool printing a fact count as reading the file?** E12 pulls `.md`/`.json` in scope,
   and in this repo nearly every turn asserts something about `SKILL.md` or `capabilities.json`
   — often from `capability_registry.py doctor` output rather than a `Read`.
4. **Cheliped C1 landed mid-review, and is half-wired.** See §R.8 — this is now a finding,
   not an open question, but the *response* is still your call.

---

## §R.6 — Tests: the twin rule

**Every silent row must be paired with a one-field-mutated twin asserted to exit 1, in the same
test, from the same fixture builder** — `silent_rc == 0 and flag_rc == 1`. A fixture that stops
reaching the detector then kills its twin and reds the suite. This replaces §0.3's
exit-0-and-silence assertions, which are the guard's default behaviour and prove nothing.

Plus: real-transcript fixtures (commit one redacted CC `Stop` transcript — `tests/fixtures/`
holds five files and **none is a transcript**, so every transcript fixture in the repo is
self-authored on both sides of the seam); a vacuity test that asserts the **read-set** and
**claim-extraction** are each non-empty on the positive twin, not merely that the fixture
lacks the word "Read"; the cap tested via an env knob against a 2 KB body in milliseconds (the
`test_capture.py:231-243` pattern), never a 50 MB write inside a 15-second hook timeout;
`stop_hook_active` re-entry (both existing `Stop` hooks guard it; the plan never mentioned it,
and the finding text itself names a file and asserts a property of it — a self-quoting loop);
and `PYTHONHASHSEED` determinism, since both rules subtract sets.

---

## §R.7 — Order

1. **D0** `transcript.py` + re-point the four divergent vocabularies. No behaviour change;
   existing hook tests stay green. Pin dispatch recognition against a **real** capture.
2. **D2** instrument (`session_id`, clean-run rows, extended `GATE_EVENTS`, `blind`).
3. **D3** the misattribution regression test → fix.
4. **D1** tests red (twin rule) → guard green, at `off`.
5. **D4** registration; expect the two RED gates.
6. `sh scripts/civerd_gate.sh > /tmp/gate.out 2>&1; rc=$?` — never piped.
7. `architecture-adversary` on the **diff**; `tripwire-auditor` before reporting done.
8. **Planted-defect probe**: a transcript claiming a property of a file it never read, and one
   claiming `Loop closed` with no dispatch. Each must fire and **name the specific
   file/adversary** — not merely "found something".


---

## §R.8 — LATE-BREAKING: Cheliped C1 landed during this review (verified read-only, 2026-08-27)

`cheliped/ccbridge/transcript_shim.py` was rewritten while this review was running. It now
projects `ctx.tool_calls_this_run` through `transcript_tool_event` (real tool records, not just
edits), redacts-then-truncates, caps at 400 records and **announces the cap**, and carries
`payload["_agent"]` so a guard can tell a parent's call from a subagent's. That last field
answers §R.5 decision 1 **for Cheliped** — but not for Claude Code, where subagent reads live in
a separate `subagents/agent-*.jsonl` sidecar. The two hosts solve it differently.

**Two consequences for this plan, both verified at source:**

**F6 — WITHDRAWN (corrected 2026-08-27).** I reported the answer leg as built-but-unwired,
having read `hook_bridge.py` at a moment when `bridged_stop` called `synthesize_transcript(ctx)`
with no `answer=`. Cheliped's commit `9d331568` landed the wiring after that read: `bridged_stop`
now takes `answer` and passes `answer=answer`, sourced `agent_turn.py:155 → lifecycle.py:851 →
hook_bridge.py:422`. Verified directly. The consequence for THIS plan is the inverse of what I
wrote: Cheliped Stop turns now carry real assistant text, so the guard will run there with live
input rather than an empty world — which makes F7 load-bearing rather than hypothetical.

**F7 — the hosts now genuinely disagree on the dispatch tool name.**
`transcript_tool_event:139` maps `ask_<slug>` → **`"Task"`** with a bare, un-slugified
`subagent_type`. The real Claude Code host emits **`"Agent"`** with a `tdd-playbook:`-prefixed
`subagent_type` (47/47 measured). Cheliped's side was written against the ORIGINAL plan's
assumption — which was false for Claude Code, and which Cheliped has now made true for itself.

Neither host is wrong; but a guard written to one name goes dark on the other. **D0's dispatch
recognition must accept `Agent` OR `Task`, and match `subagent_type` both namespaced and bare**
— and its test must pin both shapes against real captures from each host, not one synthetic
fixture. This is exactly the divergence the original D3 gestured at and got backwards.
