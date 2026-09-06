# Tripwire reminder — turn-scoped, TEST-LOCK-aware, routed to the agent

**Status:** APPROVED by David 2026-09-06 ("execute this new plan"). Building.
**Date:** 2026-09-06
**Origin:** cheliped proposal `docs/playbook-proposals/tripwire-reminder-vs-test-lock.md`
(2026-09-06), verified in this repo, then cross-reviewed by Codex (gpt-5.6-sol, read-only
`codex exec`, 9 findings, 8 accepted in full, 1 line-number drift).

## The problem, VERIFIED before the solution (§0)

`build_completion_reminder.py` (Stop hook) fires "source changed with NO test change this
turn" on EVERY implementing turn of the workflow the playbook itself prescribes: red test →
commit → `/tdd-lock` → implement. Reproduced in a scratch repo 2026-09-06: test committed
and locked, source edited, transcript listing BOTH edits → exit 1, names only the source.

Root cause (the proposal's own explanation was wrong): the reminder intersects
`git status --porcelain` (uncommitted only, line 41) with EVERY edit in the whole session
transcript (lines 93–117). A COMMITTED test edit leaves the git-status leg and vanishes from
the intersection. The lock is not involved; a turn boundary is not involved; the message's
"this turn" is a misnomer (the walk is session-wide).

Second defect, already on record for the deleted `cite_guard` (CHANGELOG 1.46.0/1.47.0):
`_common.emit` routes warn (exit 1 + stderr) to the OPERATOR and block (exit 2) to CLAUDE.
The reminder's audience is the agent, which never sees it.

Third: README.md:78-79 says the plugin + vendored combination "is harmless — Claude Code
de-dupes by name". The current hook docs contain no such statement (sweep of
code.claude.com/docs/en/hooks for dedup/identical/same-command: only the async no-dedup
line), the two registrations carry DIFFERENT command paths, and cheliped observed the
double print live. The README claim is unsupported and contradicted.

## Prior-art sweep

- `transcript.current_turn()` (transcript.py:238) already exists, built for the cite guard
  for exactly the session-vs-turn reason its docstring records. The reminder never adopted it.
- `host_contract.read_lock` / `resolve_repository` are the one lock authority (lock_guard.py
  uses them). No second reader is being written.
- No existing test commits a test file before the source edit (test_hooks.py:686, :1749 —
  both commit only "init"), so the suite is blind to the defect.

## What is NOT being built, and why (Codex findings folded in)

- **D (doctor check for double registration) — DEFERRED as dated debt.** Codex F6/F7: the
  plugin-cache probe only proves directories exist (install_into_repo.py:216), not
  enablement, trust, or that a running process loaded either registration; and there is no
  safe automatic fix — removing the vendored copy breaks cloud (README:61), disabling the
  plugin darkens every repo (user-scope, HACK_CATALOG H8). A static check can only say
  "risk", not "double firing". Recorded on `install-doctor` as integration debt with a review
  date; README corrected now (D4).
- **Symbol-reference inference / "test committed after source's last commit".** Both are
  correlation proxies, language-specific, and cannot establish that a test covers the
  changed behaviour (Codex, closing section). Not built.
- **Branching on event name inside `emit`.** Codex F3: `emit` is the transport for every
  guard including the Codex adapter (adapters/codex/pre_tool_test_lock.py:19). Routing is an
  EXPLICIT argument only the reminder passes.
- **A Codex-host Stop adapter.** host-parity.json marks the reminder `unavailable` on Codex.
  Unchanged.
- **The "say whether files are uncommitted" suggestion.** Every file the reminder names comes
  from `git status`, so all are uncommitted by construction; the suggestion is vacuous as
  stated.

## Deliverables

### D1 — the predicate: turn-scoped edits + lock as the only cross-turn evidence

`build_completion_reminder.py`:
- SOURCE: uncommitted (`git status`) ∩ edited THIS TURN (`transcript.current_turn`). A
  source edit from an earlier turn is not this turn's business (the read-only-turn fix of
  1.46.0 stays true and becomes exact).
- TESTS this turn: test files edited THIS TURN, **regardless of commit state** — the
  transcript is the evidence, not `git status`.
- LOCK evidence (cross-turn, cross-session): an active canonical TEST-LOCK counts as "tests
  authored for this feature" ONLY if ALL of:
  1. `source_worktree_id` == this worktree's id (Codex F2: locks are shared across linked
     worktrees by design; `_validate_lock` checks repo + common-dir only);
  2. the lock's `head` is this HEAD or an ANCESTOR of it (`git merge-base --is-ancestor`).
     NOT strict equality — Codex asked for equality, but the playbook's own git rule
     checkpoints mid-feature, and every checkpoint would silently void the lock evidence and
     bring the false positive straight back. Ancestor-or-equal rejects the stale/other-branch
     lock while surviving forward commits on the same line;
  3. at least one locked path passes `is_test_file` AND its on-disk sha256 still equals the
     lock entry (the lock records hashes; a locked test that was edited around the guard is
     not evidence).
- Transcript status honesty: `UNREADABLE` or `CAPPED` → the whole-tree fallback (existing
  behaviour; absent evidence is UNMEASURED, never zero). A malformed lock (`ContractError`)
  is NO evidence, never silence (Codex F8): the reminder keeps its predicate and logs an
  `unmeasured` yield row with `reason: lock-unreadable`.
- Message reword: *"uncommitted source edited this turn with no test edit this turn and no
  matching active TEST-LOCK: …"* — says exactly what was observed and what was not.

**Integration surface.** Consumes: transcript.current_turn (records + status),
host_contract.resolve_repository/read_lock, git. Emits → `emit` (D2) → the agent's context;
yield log rows (`warn` / `unmeasured`) → gate_yield.py. Surface parity: Codex host
unavailable (unchanged). Reverse sweep: no other caller of the reminder's functions
(grep `build_completion_reminder` → hooks.json, test_hooks.py, installer roster). Activation:
on by default, unchanged.

**Known limits, stated.** (a) A lock held on feature A's tests silences untested source for
feature B written hours later under the same lock. Accepted: the lock is deliberately held for
the feature's duration and its release is journaled; the alternative (no cross-turn evidence)
is the defect being fixed. (b) The docs say the transcript may lag the in-memory turn when a
hook fires; a missing final edit turns into a false NEGATIVE (source not yet recorded) or, if
the test was edited last, a false positive. Pre-existing exposure; unchanged.

### D2 — routing: warn-class Stop findings reach the agent

`_common.emit(name, lines, feedback_event=None)`:
- `feedback_event == "Stop"` and resolved mode `warn` → after the EXISTING mode resolution,
  break-glass handling and `log_yield_event` (Codex F5: the yield path is the sole telemetry
  and must not be bypassed), print
  `{"hookSpecificOutput": {"hookEventName": "Stop", "additionalContext": <header+body>}}`
  to stdout and exit 0. Per the hook docs this reaches Claude as "Stop hook feedback", no
  operator error notice, and continues the conversation under `stop_hook_active` and the
  8-continuation cap — the reminder's re-entry guard already exits 0 on `stop_hook_active`.
- The config-knob tail ("set TDD_PLAYBOOK_HOOK_X=off to silence") is NOT sent to the agent:
  telling the model how to silence a guard is the H-class disable-the-guard vector.
- `block` unchanged (stderr, exit 2). `off` unchanged. Non-Stop callers unchanged (the kwarg
  defaults to None; the Codex adapter and every other guard see byte-identical behaviour).
- Only `build_completion_reminder` passes the kwarg.

Cost stated: each fire now costs the agent a continuation. That is the point (the agent
writes the test) and it is why D1 lands and is green BEFORE D2 is enabled.

### D3 — red-first tests (test_hooks.py)

New `test_tripwire_lock_and_turn_evidence`:
- committed test + locked + source edit, transcript shows both → SILENT (the motivating
  defect; scratch-repo shape frozen);
- committed test, NO lock, test edited this turn + source edit → SILENT (transcript evidence
  alone suffices);
- source edit this turn, test edited in an EARLIER turn (uncommitted), no lock → WARNS
  (Codex F1: session-wide evidence must not carry without a lock);
- TWINS that must still warn: lock from another worktree id; lock whose head is not an
  ancestor of HEAD; lock on a non-test file; locked test whose on-disk hash no longer matches;
- malformed lock → WARNS and a yield row `unmeasured` / `lock-unreadable`;
- "silent" is asserted as exit 0 AND empty stdout — under D2, exit 0 alone no longer
  distinguishes silence from a fire (vacuity guard).

New `test_emit_stop_feedback_routing`: Stop+warn → stdout JSON, exit 0, exactly ONE warn
yield row, no knob tail in the payload; Stop+block → stderr + exit 2; non-Stop warn → stderr
+ exit 1 (unchanged contract); off → silent; reminder re-entry → nothing.

Existing reminder assertions move to the new contract via two helpers, `_tripwire_fired` /
`_tripwire_silent` — a contract change, not a weakening; the checks get STRICTER (silence
now requires empty stdout).

### D4 — README correction

README.md:78-79: replace the de-dupe claim with the measured fact and the debt pointer.

### D5 — integration debt + bookkeeping

`capabilities.json` → `install-doctor.integration_debt`: `double-registration-risk-doctor`,
owner david, review 2026-11-30. CHANGELOG 1.49.0; four identity files; current-state regen.

## Edge cases (§2)

Not a git repo / git missing → silent (unchanged). Empty transcript → current_turn returns
COMPLETE with no records → nothing edited this turn → silent. Lock present but repo identity
cannot resolve (`ContractError` from resolve_repository) → no lock evidence. HEAD unborn
(`head` None in identity) → ancestor check fails closed → no lock evidence. Renamed paths in
git status → existing `a -> b` handling. Fixture-data edits → neither test nor source
(unchanged, integ-#7).

## Tripwire (§6) — filled at completion

| deliverable | BUILT | WIRED | ACTIVATED | EXERCISED |
|---|---|---|---|---|
| D1 predicate | build_completion_reminder.py | hooks.json Stop (unchanged) | default on | test_tripwire_lock_and_turn_evidence |
| D2 routing | _common.emit(feedback_event) | reminder passes it | warn default | test_emit_stop_feedback_routing |
| D3 tests | test_hooks.py | main() roster | — | civerd_gate |
| D4 README | README.md | — | — | (prose) |
| D5 debt | capabilities.json | validate in gate | — | test_own_registry |
