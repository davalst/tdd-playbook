#!/bin/sh
# civerd_gate.sh — THE blessed gate entrypoint. No arguments is the complete,
# authorizing checkpoint/release plan consumed by CIVerd. `affected` is explicitly
# non-authorizing; a sole suite-directory argument preserves the planted liveness seam.
set -u
cd "$(dirname "$0")/.."
exec python3 plugins/tdd-playbook/bin/gate_runner.py "$@"
