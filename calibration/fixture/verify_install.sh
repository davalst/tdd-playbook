#!/bin/sh
# Deploy verifier: confirm the signing key is UNREADABLE by the runner user (control: key is 0400,
# owned by the signer, so the process that executes repo code cannot read it). This is the SAFE
# reference form — the probe takes its target as an argument, never touches stdin, never writes, and
# distinguishes "permission denied" (the control held) from any other failure (unknown, not a pass).
KEY="$1"
out=$(sudo -u runner cat "$KEY" 2>&1); rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q 'Permission denied'; then echo "PASS: key unreadable"; else echo "FAIL: control did not hold (rc=$rc)"; fi
