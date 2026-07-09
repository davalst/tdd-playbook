#!/usr/bin/env python3
"""Planted-input calibration for the TEST-LOCK (bin/tdd_lock.py + test_lock_guard.py).

The lock is the mechanical form of §1's iron rule (HACK_CATALOG H2/H5) — so the planted
attack here is the documented one: while a lock is active, an edit to the locked test (or
to conftest.py) must be BLOCKED (exit 2). Self-contained, no pytest. Run:
    python3 tests/test_tdd_lock.py
"""
import json
import os
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_BIN = os.path.join(PLUGIN, "bin", "tdd_lock.py")
GUARD = os.path.join(PLUGIN, "hooks", "scripts", "test_lock_guard.py")

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def clean_env(root):
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("TDD_PLAYBOOK_"):
            del env[k]
    env["CLAUDE_PROJECT_DIR"] = root
    return env


def lock_cli(root, *args):
    return subprocess.run([sys.executable, LOCK_BIN, *args],
                          capture_output=True, text=True, cwd=root, env=clean_env(root),
                          timeout=30)


def guard(root, file_path, env_extra=None):
    env = clean_env(root)
    if env_extra:
        env.update(env_extra)
    event = {"tool_name": "Edit", "tool_input": {
        "file_path": file_path, "old_string": "a", "new_string": "b"}}
    return subprocess.run([sys.executable, GUARD], input=json.dumps(event),
                          capture_output=True, text=True, cwd=root, env=env, timeout=30)


def main():
    print("TEST-LOCK calibration")
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "tests"))
        test_file = os.path.join(d, "tests", "test_pay.py")
        with open(test_file, "w") as fh:
            fh.write("def test_charge():\n    assert charge() == 10\n")
        with open(os.path.join(d, "conftest.py"), "w") as fh:
            fh.write("# fixtures\n")
        with open(os.path.join(d, "pay.py"), "w") as fh:
            fh.write("def charge():\n    return 10\n")

        # no lock -> guard is free and silent
        p = guard(d, test_file)
        check("no lock: edit passes (exit 0)", p.returncode == 0 and p.stderr == "",
              (p.returncode, p.stderr))

        # lock the test
        p = lock_cli(d, "lock", "tests/test_pay.py")
        check("lock records the file", p.returncode == 0 and "LOCKED 1" in p.stdout,
              (p.returncode, p.stdout, p.stderr))
        p = lock_cli(d, "status")
        check("status shows the active lock", "ACTIVE" in p.stdout and "test_pay.py" in p.stdout,
              p.stdout)

        # PLANTED (H2): editing the locked test must BLOCK
        p = guard(d, test_file)
        check("H2: edit to LOCKED test is BLOCKED (exit 2)",
              p.returncode == 2 and "TEST-LOCK" in p.stderr, (p.returncode, p.stderr))

        # relative path form is caught too
        p = guard(d, "tests/test_pay.py")
        check("H2: relative-path edit is BLOCKED", p.returncode == 2, (p.returncode, p.stderr))

        # PLANTED (H5): editing conftest.py during an active lock must BLOCK
        p = guard(d, os.path.join(d, "conftest.py"))
        check("H5: conftest edit during lock is BLOCKED",
              p.returncode == 2 and "verifier surface" in p.stderr, (p.returncode, p.stderr))

        # source edits stay free — the lock must never wedge implementation
        p = guard(d, os.path.join(d, "pay.py"))
        check("source edit stays free during lock", p.returncode == 0, (p.returncode, p.stderr))

        # unlock without a reason is REFUSED
        p = lock_cli(d, "unlock", "--reason", "meh")
        check("unlock without a real reason refused", p.returncode == 1 and "REFUSED" in p.stderr,
              (p.returncode, p.stderr))

        # unlock with a reason: journaled, lock lifted, guard free again
        p = lock_cli(d, "unlock", "--reason", "green — implementation complete")
        check("reasoned unlock succeeds", p.returncode == 0, (p.returncode, p.stderr))
        journal = os.path.join(d, ".claude", "tdd-lock-journal.jsonl")
        entries = [json.loads(ln) for ln in open(journal)]
        check("journal holds lock + unlock with the reason",
              [e["event"] for e in entries] == ["lock", "unlock"]
              and entries[1]["reason"].startswith("green"), entries)
        p = guard(d, test_file)
        check("after unlock: edit passes again", p.returncode == 0, (p.returncode, p.stderr))

        # mode demotion works (warn)
        lock_cli(d, "lock", "tests/test_pay.py")
        p = guard(d, test_file, {"TDD_PLAYBOOK_HOOK_TESTLOCK": "warn"})
        check("TESTLOCK=warn demotes to exit 1", p.returncode == 1, (p.returncode, p.stderr))

    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
