#!/usr/bin/env python3
"""Planted transport checks for the Codex TEST-LOCK vertical slice.

These fixtures use Codex's documented PreToolUse wire shape.  The host itself is calibrated
separately; this suite proves the adapter parses that wire shape into the shared policy and
keeps paired clean controls for both mutation routes.
"""
import importlib
import json
import os
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(PLUGIN, "bin")
ADAPTER = os.path.join(PLUGIN, "adapters", "codex", "pre_tool_test_lock.py")
LOCK = os.path.join(BIN, "tdd_lock.py")
sys.path.insert(0, BIN)

_results = {"pass": 0, "fail": 0}


def check(name, condition, detail=""):
    if condition:
        _results["pass"] += 1
        print("  ok   - " + name)
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          timeout=30, check=True)


def _repo(base):
    root = os.path.join(base, "repo with spaces")
    os.makedirs(os.path.join(root, "tests"))
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Codex Adapter Test")
    with open(os.path.join(root, "tests", "test_pay.py"), "w") as fh:
        fh.write("def test_pay():\n    assert pay() == 2\n")
    with open(os.path.join(root, "pay.py"), "w") as fh:
        fh.write("def pay():\n    return 1\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "fixture")
    return root


def _env(root):
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("TDD_PLAYBOOK_") or key.startswith("CLAUDE_"):
            del env[key]
    env["TDD_PLAYBOOK_PROJECT_ROOT"] = root
    env["TDD_PLAYBOOK_YIELD_LOG"] = os.devnull
    return env


def _run(root, event):
    return subprocess.run([sys.executable, ADAPTER], cwd=root, env=_env(root),
                          input=json.dumps(event), capture_output=True, text=True, timeout=30)


def _patch(path):
    return {"session_id": "codex-probe", "cwd": ".", "hook_event_name": "PreToolUse",
            "tool_name": "apply_patch", "tool_input": {
                "command": "*** Begin Patch\n*** Update File: {}\n@@\n-old\n+new\n*** End Patch".format(path)}}


def _bash(command):
    return {"session_id": "codex-probe", "cwd": ".", "hook_event_name": "PreToolUse",
            "tool_name": "Bash", "tool_input": {"command": command}}


def test_codex_test_lock_routes():
    core = importlib.import_module("host_contract")
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        locked = subprocess.run(
            [sys.executable, LOCK, "lock", "tests/test_pay.py"], cwd=root, env=_env(root),
            capture_output=True, text=True, timeout=30)
        check("codex adapter: fixture lock is canonical and active",
              locked.returncode == 0
              and core.read_lock(core.resolve_repository(root)) is not None,
              (locked.returncode, locked.stderr))

        structured = _run(root, _patch("tests/test_pay.py"))
        structured_control = _run(root, _patch("pay.py"))
        shell = _run(root, _bash("sed -i.bak 's/2/1/' tests/test_pay.py"))
        shell_control = _run(root, _bash("python3 -m pytest tests/test_pay.py"))
        check("codex adapter: planted apply_patch write is blocked before execution",
              structured.returncode == 2 and "TEST-LOCK" in structured.stderr,
              (structured.returncode, structured.stderr))
        check("codex adapter: paired clean source patch is allowed",
              structured_control.returncode == 0 and structured_control.stderr == "",
              (structured_control.returncode, structured_control.stderr))
        check("codex adapter: planted Bash write is blocked before execution",
              shell.returncode == 2 and "TEST-LOCK" in shell.stderr,
              (shell.returncode, shell.stderr))
        check("codex adapter: paired read-only test command is allowed",
              shell_control.returncode == 0 and shell_control.stderr == "",
              (shell_control.returncode, shell_control.stderr))


def test_codex_patch_path_security():
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        subprocess.run([sys.executable, LOCK, "lock", "tests/test_pay.py"], cwd=root,
                       env=_env(root), check=True, capture_output=True, text=True, timeout=30)
        traversal = _run(root, _patch("../outside.py"))
        delete_lock = _run(root, _patch(".git/tdd-playbook/active-lock.json"))
        check("codex adapter: planted patch traversal fails closed",
              traversal.returncode == 2 and "outside" in traversal.stderr.lower(),
              (traversal.returncode, traversal.stderr))
        check("codex adapter: patch cannot delete the canonical lock authority",
              delete_lock.returncode == 2 and "STATE" in delete_lock.stderr,
              (delete_lock.returncode, delete_lock.stderr))


def main():
    print("Codex host adapter calibration")
    for fn in (test_codex_test_lock_routes, test_codex_patch_path_security):
        try:
            fn()
        except Exception as exc:
            check(fn.__name__ + " executes", False, repr(exc))
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    assert not _results["fail"], "Codex adapter calibration failed"


if __name__ == "__main__":
    main()
