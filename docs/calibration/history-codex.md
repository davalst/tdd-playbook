# Codex verifier calibration history

No live verifier-agent calibration has landed yet. The portable runner and dry-run scenario
validation exist, but absence of a live paired run is `UNMEASURED`, never PASS.

Run the first bounded live calibration separately from Claude's scoreboard:

```bash
python3 calibration/run_calibration.py --host codex --model <model>
```

This file intentionally does not borrow recall or false-positive numbers from
`docs/calibration/history.md`. Host-boundary TEST-LOCK calibration is recorded separately in
`docs/calibration/host-history.md`; it proves interception behavior, not verifier-agent quality.
