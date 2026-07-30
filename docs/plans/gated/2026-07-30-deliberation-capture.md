# Plan — 2026-07-30-deliberation-capture

Authored 2026-07-30 via plan_block.py. Status lives in the block; `satisfied` is cosmetic to
the engine and `abandoned` is the ratifier's word alone (root-owned store on the box).

## Spec integrity

Ratified CIVerd brief (deliberation capture). Reading followed: capture is EVIDENCE
COLLECTION, not enforcement — conveyed ≠ ratified; only David closes. Simpler-approach
check: relying on Claude Code's own transcript files was rejected in the brief itself
(session-scoped, prunable, no append-only posture, no redaction pass). Key assumption made
explicit: hooks fire only on machines where the plugin is enrolled — coverage is PARTIAL by
design (cloud sandboxes, Cheli/GLM, un-enrolled machines), which is why the v2 matcher must
label unmatched spans "unattributed," never "David's own words."

## Deliverables

- `hooks/scripts/capture.py` — UserPromptSubmit (human turn) + Stop (assistant final via
  backward chunked transcript scan to the last assistant boundary; `truncated: true` if the
  cap is hit — never a partial presented as full). Registered in hooks.json with explicit
  `--event` args; payload `hook_event_name` is a cross-check only. Fail open, always exit 0,
  never stdout. O_CREAT|O_EXCL per-(session, event-instance) sentinel dedupes double
  registration (plugin+vendored topology) without swallowing a deliberately repeated
  identical prompt.
- Store: `TDD_PLAYBOOK_DELIBERATION_DIR` env-or-default `~/.claude/deliberation/`, dir 0700
  files 0600, per-day JSONL, one fully-built line per os.write; sidecar
  `.capture-errors.log`. Schema whitelist: ts, session_id, cwd, repo, sha, direction, text,
  sha256, schema, redactions — NO status field (effective status derives from closure
  records; missing = open). sha256 over POST-redaction text only; redactions always
  present, 0 when none.
- `bin/deliberation.py` — `close` (appends closure records, event-sourced, never rewrites;
  the only emitter of the closure shape) + `stats` (records/day, bytes/day, redactions).
- Activation: `TDD_PLAYBOOK_HOOK_CAPTURE=on` OR enrollment marker
  `~/.claude/deliberation/ENABLED` (written BY THE BUILD on David's machine — consent is
  the commission). Env `off` BEATS the marker (named test — the answer-key protection:
  David's machine is exactly the one that is both enrolled and runs live calibration).
  `calibration/_child_env()` sets the off-env for BOTH nested-claude spawn sites
  (run_calibration.run_agent AND author_plants.cmd_author — the plant-authoring
  adversary's output IS the answer key). Doctor gains an informational capture ON/OFF
  line so "is it recording?" is always answerable.

## Unenforceable deliverables (prose)

- Access rule: the store is honour-system, labeled not locked; it sits inside CC's trust
  domain (leak-#3 applies). Open/closed is a label, not an ACL.
- Volume estimate reported to David after a live session (stats verb output, not a guess).
- Store posture doc + the guard_env hand-off line (S1b: when the engine's expected-wiring
  check lands, capture.py must be in the root-owned list or it reads as unexpected wiring).
- Enrollment debt (expires 2026-08-31): every machine David works on shows capture: ON in
  doctor, or the debt is consciously re-dated — never silently dark (David's directive:
  OFF is only ever a scheduled state).

## Predicates

The engine evaluates these against the tree it judges — see the weaker-truth semantics in
plan_block.py's header before reading them as stronger promises than they are.

```civerd-plan
version: 1
repo: tdd-playbook
status: active
predicates:
  - file_exists: plugins/tdd-playbook/hooks/scripts/capture.py
  - test_passes: plugins/tdd-playbook/tests/test_capture.py::test_capture_writes_a_record
  - test_passes: plugins/tdd-playbook/tests/test_capture.py::test_unwritable_store_never_blocks_the_prompt
  - test_passes: plugins/tdd-playbook/tests/test_capture.py::test_hooks_json_registers_capture
```
