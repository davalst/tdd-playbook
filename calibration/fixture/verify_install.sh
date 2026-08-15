#!/bin/sh
# Deploy verifier: confirm the signing key is unreadable by the runner user. Takes its target
# as an argument, never reads stdin, never writes; fails closed — only an explicit
# "Permission denied" counts as a pass, any other outcome is a failure.
KEY="$1"
out=$(sudo -u runner cat "$KEY" 2>&1); rc=$?
if [ "$rc" -ne 0 ] && printf '%s' "$out" | grep -q 'Permission denied'; then echo "PASS: key unreadable"; else echo "FAIL: control did not hold (rc=$rc)"; fi
