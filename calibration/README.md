# Calibration — proving the Playbook's own verifiers work

The Playbook's loudest rule is "a probe that never fails a plant is theater" (§13). This
directory applies that rule to the Playbook itself: the enforcement **hooks** are calibrated
by `plugins/tdd-playbook/tests/test_hooks.py` (deterministic, every run); the verification
**agents** are calibrated here (behavioral, scheduled — they need a live model).

Layout:
- `fixture/` — a tiny known-good Python package with tests; the arena the agents are
  dropped into. Deliberately boring: the *plants* provide the challenge.
- `scenarios.json` — the planted scenarios: for each agent, what is planted in the fixture
  and what the agent's forced `Recommendation:` / verdict line MUST name to pass.
- `run_calibration.py` — the runner. Applies a scenario's plant to a temp copy of the
  fixture, drives the agent headlessly (`claude -p`, cheap model, hard caps), and applies a
  DETERMINISTIC oracle: did the verdict line name the plant? (String check — no LLM judge;
  the oracle split applies to our own calibration too.)
- `corpus/` — the generative plant corpus (co-evolution): adversary-authored plants, added
  every cycle, never removed. Each plant records the model that authored it.

Cadence: **weekly** (scheduled), and mandatory after any agent-prompt change or doer-model
upgrade (§13 verifier-strength policy). **A plant surviving to a clean verdict is a BLOCKING
failure** — fix the agent (or the harness), never the plant. Results append to
`docs/calibration/history.md` — the public scoreboard.

Run: `python3 calibration/run_calibration.py [--agent NAME] [--dry-run]`
(`--dry-run` validates scenarios/fixture/corpus without spending model calls — used in CI.)
