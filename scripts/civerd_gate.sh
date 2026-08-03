#!/bin/sh
# civerd_gate.sh — THE blessed gate entrypoint. CIVerd's `tests` check and the
# planted_probe suite_cmd exec THIS script; nothing else is the gate.
#
# Origin (2026-07-28, probe run 2): the gate command and the real gate had silently
# diverged — pytest collects ~0 items from calibration/'s script-style suites, the python3
# loop never included calibration/, and test_aaa was inert under `python3 file.py` — so
# check_scoreboard_integrity's 12 planted tests existed but NEVER RAN in the gate (the
# v1.15 false-green class, one layer up). A shell loop in prose config can't be linted;
# this file can be probed, planted-tested, and diffed.
#
# Usage: civerd_gate.sh [suite_dir]
#   no arg    -> the FULL gate: every plugins test suite via its real main() + the
#                calibration harness (110 planted checks)
#   suite_dir -> run only test_*.py in that dir (the planted-test hook: a failing suite
#                MUST fail the gate — see test_aaa_suites_via_main.py)
set -u

if [ "${1:-}" != "" ]; then
    for t in "$1"/test_*.py; do
        python3 "$t" || exit 1
    done
    exit 0
fi

cd "$(dirname "$0")/.."
for t in plugins/tdd-playbook/tests/test_*.py; do
    python3 "$t" || exit 1
done
python3 calibration/test_harness.py || exit 1
# v1.24 (§6c D13a): the repo sweeps ITSELF — this repo's own shipped bins carry literal
# .format( render sites, so under "Tier 1 is mandatory where the flow kind exists" the
# flow kind exists HERE. BLOCKING: exit 1 (violation) and 3 (vacuous — scanning nothing
# is a real failure, not a pass) both fail the gate; only 0 proceeds.
python3 plugins/tdd-playbook/bin/dataflow_sweeps.py render-pairing \
    --config dataflow-sweeps.json || exit 1
echo "civerd_gate: ALL suites green (plugins loop + calibration harness + dataflow self-sweep)"
