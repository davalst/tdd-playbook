"""Self-contained OS confinement for holdout eval runs (Part 2, 2026-08-15).

The evaluated agent must not READ the holdout answer key. This reuses the PROVEN macOS
`sandbox-exec` (Seatbelt) profile SHAPE from cheliped's `cheliped/verify/sandbox_exec.py` —
NOT by importing it (tdd-playbook is vendored into other repos and cannot depend on cheliped
being present), but as a small local helper using the same SBPL shape — plus the one holdout
addition: DENY READS of the answer-key directory. `(allow default)` reads everything; a
trailing `(deny file-read* (subpath <answer-dir>))` overrides it for that path (SBPL
last-match-wins, verified empirically before this landed).

Subscription note: the evaluated `claude` runs on the HOST under this profile — its login is
in the macOS Keychain, so it authenticates there (not in a container), the credential never
enters a place the agent could exfiltrate it to, and the run costs nothing (subscription, not
metered API). Proven two-directionally by the confinement calibration in test_harness: a real
`claude -p` completed a benign task AND could not read a decoy answer key; removing the
read-deny makes it readable again (the rule is load-bearing).
"""
import os
import shutil

# The device writes cheliped's _default_writable grants — a shell/CLI needs them or its
# redirects fail under `(deny file-write*)`.
_SAFE_DEV_WRITES = ("/dev/null", "/dev/stdout", "/dev/stderr")


def _real(p):
    try:
        return os.path.realpath(p)
    except Exception:
        return p


def seatbelt_profile(workspace, *, deny_read, writable_extra=(), deny_network=False):
    """An SBPL profile: allow everything, deny ALL writes, re-allow writes to the workspace +
    tmp + the /dev devices, optionally deny network, then DENY READS of each `deny_read`
    subpath (the answer key). macOS resolves symlinks, so subpaths use the real path."""
    lines = ["(version 1)", "(allow default)", "(deny file-write*)"]
    seen = set()
    for p in [workspace, "/private/tmp", "/tmp", *writable_extra]:
        r = _real(p)
        if r in seen:
            continue
        seen.add(r)
        lines.append('(allow file-write* (subpath "%s"))' % r)
    for dev in _SAFE_DEV_WRITES:
        lines.append('(allow file-write* (literal "%s"))' % dev)
    if deny_network:
        lines.append("(deny network*)")
    for p in deny_read:
        lines.append('(deny file-read* (subpath "%s"))' % _real(p))
    return "\n".join(lines)


def sandbox_exec_available():
    return shutil.which("sandbox-exec") is not None


def confined_argv(cmd, workspace, *, deny_read, writable_extra=(), deny_network=False):
    """Wrap `cmd` (a list) in `sandbox-exec` with the holdout profile. macOS only — the caller
    MUST check sandbox_exec_available() and REFUSE to run a holdout unconfined (an unconfined
    run leaves the answer key readable, which defeats the entire point). Linux confinement
    (bwrap/firejail/landlock) is cheliped's tier ladder; add it here when a Linux holdout host
    exists, never a silent unconfined fallback."""
    if not deny_read:
        raise ValueError("confined_argv refuses an empty deny_read: a holdout run with nothing "
                         "read-denied would expose the answer key")
    prof = seatbelt_profile(workspace, deny_read=deny_read,
                            writable_extra=writable_extra, deny_network=deny_network)
    return ["sandbox-exec", "-p", prof, *cmd]
