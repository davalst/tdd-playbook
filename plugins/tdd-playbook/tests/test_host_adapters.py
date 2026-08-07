#!/usr/bin/env python3
"""Real-process parity checks for the Claude transport over the portable core.

These are host-boundary fixtures (subprocess + Claude-shaped JSON), not source/config
greps.  The first red proves that the current guard cannot see a lock created in a linked
worktree because both still use checkout-local `.claude` state.
"""
import importlib
import json
import os
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(PLUGIN, "bin")
HOOKS = os.path.join(PLUGIN, "hooks", "scripts")
LOCK = os.path.join(BIN, "tdd_lock.py")
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
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          timeout=30, check=True)


def _repo(base):
    main = os.path.join(base, "main")
    side = os.path.join(base, "side")
    os.makedirs(main)
    _git(main, "init", "-q")
    _git(main, "config", "user.email", "test@example.invalid")
    _git(main, "config", "user.name", "Host Adapter Test")
    os.makedirs(os.path.join(main, "tests"))
    with open(os.path.join(main, "tests", "test_pay.py"), "w") as fh:
        fh.write("def test_pay():\n    assert pay() == 2\n")
    with open(os.path.join(main, "pay.py"), "w") as fh:
        fh.write("def pay():\n    return 1\n")
    _git(main, "add", ".")
    _git(main, "commit", "-qm", "fixture")
    _git(main, "worktree", "add", "-qb", "side", side)
    return main, side


def _env(root):
    env = dict(os.environ)
    for key in list(env):
        if key.startswith("TDD_PLAYBOOK_"):
            del env[key]
    env["CLAUDE_PROJECT_DIR"] = root
    env["TDD_PLAYBOOK_YIELD_LOG"] = os.devnull
    return env


def _lock(root, *args):
    return subprocess.run([sys.executable, LOCK, *args], cwd=root, env=_env(root),
                          capture_output=True, text=True, timeout=30)


def _guard(root, event):
    return subprocess.run([sys.executable, GUARD], cwd=root, env=_env(root),
                          input=json.dumps(event), capture_output=True, text=True, timeout=30)


def _edit(path):
    return {"tool_name": "Edit", "tool_input": {
        "file_path": path, "old_string": "alpha", "new_string": "beta"}}


def _bash(command):
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def test_adapter_parity():
    """Claude structured/shell routes consume the same canonical lock across worktrees."""
    core = importlib.import_module("host_contract")
    with tempfile.TemporaryDirectory() as d:
        main, side = _repo(d)
        locked = _lock(main, "lock", "tests/test_pay.py")
        identity = core.resolve_repository(main)
        record = core.read_lock(identity)
        check("claude adapter: CLI creates the canonical versioned lock",
              locked.returncode == 0 and record is not None
              and record["schema_version"] == 1, (locked.returncode, locked.stderr, record))
        check("claude adapter: Git repos no longer create a second vendor-local authority",
              not os.path.exists(os.path.join(main, ".claude", "tdd-lock.json")))

        structured = _guard(side, _edit(os.path.join(side, "tests", "test_pay.py")))
        shell = _guard(side, _bash("sed -i.bak 's/2/1/' tests/test_pay.py"))
        state_attack = _guard(side, _bash("rm '{}'".format(core.lock_path(identity))))
        clean = _guard(side, _edit(os.path.join(side, "pay.py")))
        check("claude adapter: linked-worktree structured write is blocked",
              structured.returncode == 2 and "TEST-LOCK" in structured.stderr,
              (structured.returncode, structured.stderr))
        check("claude adapter: linked-worktree shell write is blocked",
              shell.returncode == 2 and "TEST-LOCK" in shell.stderr,
              (shell.returncode, shell.stderr))
        check("claude adapter: shell cannot delete canonical lock authority",
              state_attack.returncode == 2 and "STATE" in state_attack.stderr,
              (state_attack.returncode, state_attack.stderr))
        check("claude adapter: clean source control remains allowed",
              clean.returncode == 0 and clean.stderr == "", (clean.returncode, clean.stderr))

        status = _lock(side, "status")
        check("claude adapter: status in either worktree sees the same lock",
              status.returncode == 0 and "ACTIVE" in status.stdout, status.stdout)
        unlocked = _lock(side, "unlock", "--class", "phase", "--reason",
                         "linked worktree parity phase is complete and green")
        check("claude adapter: non-owner worktree cannot clear shared authority",
              unlocked.returncode == 1 and "another session" in unlocked.stderr
              and core.read_lock(identity) is not None,
              (unlocked.returncode, unlocked.stderr))
        owner_unlock = _lock(main, "unlock", "--class", "phase", "--reason",
                             "owning worktree parity phase is complete and green")
        check("claude adapter: owner worktree can journal and clear its authority",
              owner_unlock.returncode == 0 and core.read_lock(identity) is None,
              (owner_unlock.returncode, owner_unlock.stderr))


def test_legacy_guard_import():
    """An already-running Claude session with a legacy lock migrates once, then blocks."""
    core = importlib.import_module("host_contract")
    with tempfile.TemporaryDirectory() as d:
        main, _side = _repo(d)
        legacy_dir = os.path.join(main, ".claude")
        os.makedirs(legacy_dir)
        legacy = os.path.join(legacy_dir, "tdd-lock.json")
        with open(legacy, "w") as fh:
            json.dump({"locked_at": "2026-08-07T12:00:00+00:00",
                       "files": {"tests/test_pay.py": "legacy-hash"}}, fh)
        result = _guard(main, _edit(os.path.join(main, "tests", "test_pay.py")))
        check("claude adapter: legacy active lock still blocks during migration",
              result.returncode == 2, (result.returncode, result.stderr))
        check("claude adapter: migration consumes legacy authority exactly once",
              not os.path.exists(legacy) and os.path.exists(legacy + ".migrated")
              and core.read_lock(core.resolve_repository(main)) is not None)


def main():
    print("host adapter calibration")
    for fn in (test_adapter_parity, test_legacy_guard_import):
        try:
            fn()
        except Exception as exc:
            check(fn.__name__ + " executes", False, repr(exc))
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    assert not _results["fail"], "host adapter calibration failed"


if __name__ == "__main__":
    main()
