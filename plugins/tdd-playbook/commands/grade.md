---
description: Run the Playbook §13 learning loop — grade the just-finished cycle from telemetry vs a named benchmark, propose the smallest tweak.
argument-hint: [scope — e.g. last sprint / N commits / this session]
---

Run the **learning-loop retro** (Playbook §13) over: $ARGUMENTS

Grade the CYCLE (spend → evidence → claims → outcome), not the narration. Rules:
- **Grade from TELEMETRY:** files actually read, greps actually run, tokens in/out net of
  cache, turn count, tests added vs source changed — tool logs and git history, NOT the
  model's account of its own diligence.
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
