---
description: Run the Playbook §13 learning loop — grade the just-finished cycle from telemetry vs a named benchmark, propose the smallest tweak.
argument-hint: [scope — e.g. last sprint / N commits / this session]
---

Run the **learning-loop retro** (Playbook §13) over: $ARGUMENTS

Grade the CYCLE (spend → evidence → claims → outcome), not the narration. Rules:
- **Grade from TELEMETRY — the seam emits the count:** if an OTel export exists (see
  `docs/telemetry.md`), run
  `python3 "$CLAUDE_PROJECT_DIR/.claude/bin/grade_from_otel.py" <export>` and PASTE its block —
  files actually read, greps actually run, tokens net of cache, turns, tests-vs-source
  touched, all measured. If it exits 1 (no telemetry), the card is labeled
  **"narration-grade (telemetry unavailable)"** — never dress an estimate as a measurement.
  Git history supplements either way (tests added vs source changed per commit).
- **Read the TEST-LOCK journal** (`<git-common-dir>/tdd-playbook/events.jsonl`; legacy
  non-Git scratch projects use `.claude/tdd-lock-journal.jsonl`): frequent
  unlocks, or reasons pattern-matching "adjusted test to match output", are honor-system
  breaches (H2) — they cap the grade. Report two counts from the `reason_class` field
  (v1.27): the **`gate-wrong` share** of unlocks (that class is the only one that can retire
  a guard, so a rising share with no matching guard defect is the self-serving-adjudication
  smell), and any entry carrying **`class_mismatch: true`** — a phase-shaped reason claiming
  `gate-wrong`, which the tool records rather than corrects precisely so you can grade it.
  An unclassified-heavy journal is UNMEASURED, not clean. Also flag any entry carrying
  **`forced: true`** — a `unlock --force` that BYPASSED the ownership CAS to release a
  dead/foreign-session or corrupt lock: legitimate as cross-session RECOVERY, but the one
  unlock that skipped ownership, so read its reason and confirm it names a real orphaned-lock
  recovery (not "the other session's lock was in my way while I edited the test"). Likewise an
  entry with **`session_downgrade: true`** — an env-less same-worktree unlock that released a lock
  a real-session-token owner created (the one release the 2026-08-16 deadlock fix newly permits);
  benign for coordinating same-worktree agents, but a rising count with test-weakening-shaped
  reasons is the tell to read.
- **Score claim-evidence LINKAGE, not volume:** more files read must not raise the grade
  unless claims cite them. Count-pumping is marker theater.
- **Benchmark it** against a NAMED reference (e.g. "Claude Code on the same task"), so the
  system improves instead of re-learning.
- **Check the honor-system seams held:** were tests weakened to pass? was red-first faked?
  did any deliverable ship BUILT-but-not-WIRED? did a planted error (if any) survive?
- **Propose the SMALLEST tweak** — one config knob / prompt line / threshold / new hook —
  human-reviewed. Healthy proposals shrink toward noise over time. Also scan AGENTS.md /
  CLAUDE.md for drift: stale skill references, sections grown too verbose to be read.

Output: a short scored card + the single highest-value proposed change. Report-only grades
nobody acts on are theater.
