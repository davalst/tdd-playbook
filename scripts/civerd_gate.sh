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
#                calibration harness (which prints its own check tally)
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
# H15/§12: count what we ran. The final line used to say "ALL suites green" with no number
# anywhere — so a suite renamed off the glob, or a glob that matched nothing, produced a
# byte-identical green. A claim of completeness with an invisible selector is the whole class.
SUITES=0
for t in plugins/tdd-playbook/tests/test_*.py; do
    [ -f "$t" ] || continue
    python3 "$t" || exit 1
    SUITES=$((SUITES + 1))
done
# Fail closed on a vacuous glob: zero suites is not a pass, it is a broken checkout.
if [ "$SUITES" -eq 0 ]; then
    echo "civerd_gate: FAIL — the plugins suite glob matched NOTHING; a gate that ran no" \
         "suites cannot be green" >&2
    exit 1
fi
python3 calibration/test_harness.py || exit 1
# v1.24 (§6c D13a): the repo sweeps ITSELF — this repo's own shipped bins carry literal
# .format( render sites, so under "Tier 1 is mandatory where the flow kind exists" the
# flow kind exists HERE. `all` derives the armed sweeps from the CONFIG (the single
# source of truth — no hardcoded sweep list here). BLOCKING: exit 1 (violation) and 3
# (vacuous — scanning nothing is a real failure, not a pass) both fail the gate.
python3 plugins/tdd-playbook/bin/dataflow_sweeps.py all \
    --config dataflow-sweeps.json || exit 1
# v1.27 (§13 RSI): every gate-surface change must carry a PRE-REGISTERED expected effect.
# Baseline resolution is fail-closed on purpose. `git describe` is tried first, then the
# ledger's own EPOCH (always in history, so it resolves in any full clone); if NEITHER
# resolves we exit 1 rather than skip. A silent skip would leave this gate dark on exactly
# the host that signs the release verdict — the engine runs THIS script on a fresh clone.
LEDGER_BASE="$(git describe --tags --abbrev=0 2>/dev/null || true)"
if [ -z "$LEDGER_BASE" ]; then
    LEDGER_BASE="$(sed -n 's/^EPOCH:[[:space:]]*\([0-9a-f]\{7,40\}\).*/\1/p' \
        docs/calibration/ledger.md 2>/dev/null | head -1)"
fi
if [ -z "$LEDGER_BASE" ]; then
    echo "civerd_gate: FAIL — no ledger baseline (no tag and no EPOCH in ledger.md);" \
         "refusing to skip the ledger check" >&2
    exit 1
fi
python3 calibration/ledger.py check --baseline-rev "$LEDGER_BASE" || exit 1
# v1.29 (item 3): the dev/holdout register must stay well-formed, every in-repo form
# assignment must still hash-match the plant it names (name-keyed authorization over content
# that rule (b) pins — the d5dec34 class), and no holdout id may appear in a gate surface or
# a vendored tree. BLOCKING: a burned holdout plant silently turns the reporting set back
# into the tuning set, which is the one thing the split exists to prevent.
python3 calibration/plant_forms.py check || exit 1
echo "civerd_gate: GREEN — ${SUITES} plugin suites · calibration harness · dataflow sweeps · ledger (baseline ${LEDGER_BASE}) · plant-forms. Each step printed its own denominator above; this line rolls them up and claims nothing they did not."
