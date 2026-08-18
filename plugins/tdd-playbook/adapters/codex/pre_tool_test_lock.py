#!/usr/bin/env python3
"""Codex PreToolUse transport for the shared TEST-LOCK policy.

Codex sends `apply_patch` as a patch string in `tool_input.command`, unlike Claude's
structured edit fields.  This adapter extracts only target paths, delegates decisions to
the host-neutral core, and retains the already-calibrated shell heuristic as a compatibility
dependency until the broader guard-family extraction.  Exit 2 is Codex's documented
pre-execution deny path.
"""
import json
import os
import re
import sys

PLUGIN = os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
sys.path.insert(0, os.path.join(PLUGIN, "bin"))
sys.path.insert(0, os.path.join(PLUGIN, "hooks", "scripts"))

from _common import emit, read_event  # noqa: E402
from host_contract import (ContractError, import_legacy_lock, policy_decision,  # noqa: E402
                           read_lock, record_capability_observation,
                           resolve_repository)
from lock_guard import _msg, bash_findings  # noqa: E402

NAME = "testlock"
_PATCH_TARGET = re.compile(
    r"^\*\*\* (?:Add|Update|Delete) File:\s*(.+?)\s*$|^\*\*\* Move to:\s*(.+?)\s*$",
    re.MULTILINE)


def project_root(event):
    return os.path.realpath(os.environ.get("TDD_PLAYBOOK_PROJECT_ROOT")
                            or event.get("cwd") or os.getcwd())


def active_lock(identity, event):
    session = event.get("session_id") or "codex-hook"
    import_legacy_lock(identity, session)
    return read_lock(identity)


def patch_targets(command):
    targets = []
    for match in _PATCH_TARGET.finditer(command or ""):
        target = match.group(1) or match.group(2)
        if target:
            targets.append(target)
    return targets


def patch_findings(command, identity, lock):
    targets = patch_targets(command)
    if not targets:
        return ["TEST-LOCK active: Codex apply_patch input had no parseable target; "
                "refusing an unclassified write instead of bypassing policy."]
    try:
        result = policy_decision(identity, lock, {"kind": "write", "targets": targets})
    except ContractError as exc:
        return ["TEST-LOCK: unsafe/outside repository patch target refused: {}".format(exc)]
    if result["decision"] == "block":
        return _msg(result["surface"], result["target"])
    return []


def record_observation(identity, lock, event, route, findings):
    """Best-effort local evidence; enforcement must survive an unwritable journal."""
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "adapter.json")) as fh:
            version = json.load(fh)["adapter_version"]
        record_capability_observation(
            identity, host="codex",
            host_version=(event.get("host_version")
                          or os.environ.get("TDD_PLAYBOOK_HOST_VERSION") or "unreported"),
            adapter_version=version, run_id=lock["session_id"], route=route,
            outcome="blocked" if findings else "allowed")
    except (ContractError, OSError, ValueError, KeyError):
        pass


def main():
    event = read_event()
    root = project_root(event)
    try:
        identity = resolve_repository(root)
        lock = active_lock(identity, event)
    except ContractError as exc:
        emit(NAME, ["TEST-LOCK canonical state is invalid — failing closed: {}".format(exc)])
        return
    if not lock:
        return
    tool = event.get("tool_name")
    command = (event.get("tool_input") or {}).get("command", "")
    if tool == "Bash":
        findings = bash_findings(command, lock, root)
        record_observation(identity, lock, event, "shell", findings)
        emit(NAME, findings)
    elif tool == "apply_patch":
        findings = patch_findings(command, identity, lock)
        record_observation(identity, lock, event, "structured_edit", findings)
        emit(NAME, findings)
    else:
        emit(NAME, ["TEST-LOCK active: unsupported Codex write route {!r}; refusing "
                    "unclassified mutation.".format(tool)])


if __name__ == "__main__":
    main()
