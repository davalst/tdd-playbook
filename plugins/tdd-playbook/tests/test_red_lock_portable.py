#!/usr/bin/env python3
"""Planted seam test: Claude auto-red producer -> canonical lock -> linked-worktree guard."""
import importlib
import json
import os
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(PLUGIN, "bin")
HOOKS = os.path.join(PLUGIN, "hooks", "scripts")
RED_LOCK = os.path.join(HOOKS, "red_lock.py")
GUARD = os.path.join(HOOKS, "test_lock_guard.py")
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
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True, timeout=30)


def _repo(base):
    main, side = os.path.join(base, "main"), os.path.join(base, "side")
    os.makedirs(os.path.join(main, "tests"))
    _git(main, "init", "-q")
    _git(main, "config", "user.email", "test@example.invalid")
    _git(main, "config", "user.name", "Auto Red Test")
    with open(os.path.join(main, "tests", "test_new.py"), "w") as fh:
        fh.write("def test_new():\n    assert False\n")
    _git(main, "add", ".")
    _git(main, "commit", "-qm", "fixture")
    _git(main, "worktree", "add", "-qb", "side", side)
    return main, side


def _run(script, root, event):
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("TDD_PLAYBOOK_"):
            del env[key]
    env["CLAUDE_PROJECT_DIR"] = root
    env["TDD_PLAYBOOK_YIELD_LOG"] = os.devnull
    # redlock defaults OFF since v1.32.0 (0 blocks / 1 warn across all recorded history).
    # This suite calibrates its BEHAVIOR, so it opts in — retiring a guard must not silently
    # delete its coverage. Whether it is ON by default is pinned separately, in
    # test_hooks.py::test_retired_advisory_defaults.
    if os.path.basename(script) == "red_lock.py":
        env["TDD_PLAYBOOK_HOOK_REDLOCK"] = "warn"
    return subprocess.run([sys.executable, script], cwd=root, env=env,
                          input=json.dumps(event), capture_output=True, text=True, timeout=30)


def test_auto_red_reaches_shared_authority():
    core = importlib.import_module("host_contract")
    with tempfile.TemporaryDirectory() as d:
        main, side = _repo(d)
        test_path = os.path.join(main, "tests", "test_new.py")
        wrote = _run(RED_LOCK, main, {"tool_name": "Write", "tool_input": {
            "file_path": test_path, "content": "def test_new():\n    assert False\n"}})
        red = _run(RED_LOCK, main, {"tool_name": "Bash",
            "tool_input": {"command": "pytest -q"}, "tool_response": "1 failed in 0.1s"})
        identity = core.resolve_repository(main)
        record = core.read_lock(identity)
        check("auto-red: test edit records pending without an error", wrote.returncode == 0,
              (wrote.returncode, wrote.stderr))
        check("auto-red: failing run creates the canonical lock",
              red.returncode == 1 and record is not None
              and "tests/test_new.py" in record["files"], (red.returncode, red.stderr, record))
        check("auto-red: no vendor-local active authority is created",
              not os.path.exists(os.path.join(main, ".claude", "tdd-lock.json")))
        guarded = _run(GUARD, side, {"tool_name": "Edit", "tool_input": {
            "file_path": os.path.join(side, "tests", "test_new.py"),
            "old_string": "False", "new_string": "True"}})
        check("auto-red: linked-worktree consumer blocks the produced lock",
              guarded.returncode == 2 and "TEST-LOCK" in guarded.stderr,
              (guarded.returncode, guarded.stderr))
        rows = core.read_events(identity)
        check("auto-red: canonical journal records the producer event",
              any(row.get("event") == "auto_lock_red" for row in rows), rows)


def main():
    print("portable auto-red calibration")
    try:
        test_auto_red_reaches_shared_authority()
    except Exception as exc:
        check("test_auto_red_reaches_shared_authority executes", False, repr(exc))
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    assert not _results["fail"], "portable auto-red calibration failed"


if __name__ == "__main__":
    main()
