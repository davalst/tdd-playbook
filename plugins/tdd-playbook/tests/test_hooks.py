#!/usr/bin/env python3
"""Planted-input calibration for the TDD Playbook enforcement hooks.

These hooks defend the Playbook's honor-system seams (don't weaken tests, stay
deterministic). Per §13, the ungameable check is that PLANTED violations are actually
caught — a planted weakening that slips past a guard is a BLOCKING failure here.

Self-contained: drives each hook as a subprocess with crafted JSON, asserts exit code
and message. No pytest dependency (the plugin is stack-agnostic). Run:
    python3 tests/test_hooks.py
Exit 0 = all green; non-zero = a guard regressed.
"""
import json
import os
import subprocess
import sys
import tempfile

HOOKS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "hooks", "scripts")

_results = {"pass": 0, "fail": 0}


def run(script, event, env_extra=None):
    env = dict(os.environ)
    # neutralize any developer override so tests see documented defaults
    for k in list(env):
        if k.startswith("TDD_PLAYBOOK_"):
            del env[k]
    if env_extra:
        env.update(env_extra)
    p = subprocess.run(
        [sys.executable, os.path.join(HOOKS, script)],
        input=json.dumps(event), capture_output=True, text=True, env=env, timeout=20,
    )
    return p.returncode, p.stdout, p.stderr


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def edit(path, old, new):
    return {"tool_name": "Edit", "tool_input": {"file_path": path,
            "old_string": old, "new_string": new}}


def write(path, content):
    return {"tool_name": "Write", "tool_input": {"file_path": path, "content": content}}


# ---------------------------------------------------------------- test_weakening_guard
def test_weakening():
    s = "test_weakening_guard.py"
    tf = "tests/test_pay.py"

    # PLANTED: assertion removed -> must warn (exit 1)
    rc, _o, e = run(s, edit(tf, "assert total == 5\nassert ok", "assert ok"))
    check("weaken: dropped assertion is caught", rc == 1 and "assertions dropped" in e, (rc, e))

    # PLANTED: skip marker added -> must warn
    rc, _o, e = run(s, edit(tf, "def test_pay():", "@pytest.mark.skip\ndef test_pay():"))
    check("weaken: added skip is caught", rc == 1 and "skip" in e.lower(), (rc, e))

    # PLANTED: assertion neutered to tautology -> must warn
    rc, _o, e = run(s, edit(tf, "assert charge() == 10", "assert True  # TODO"))
    check("weaken: tautology is caught", rc == 1 and "tautology" in e.lower(), (rc, e))

    # CLEAN: strengthening (added assertion) -> silent (exit 0)
    rc, _o, e = run(s, edit(tf, "assert ok", "assert ok\nassert total == 5"))
    check("weaken: strengthening is NOT flagged", rc == 0 and e == "", (rc, e))

    # NEGATIVE: same weakening on a NON-test file -> silent
    rc, _o, _e = run(s, edit("src/pay.py", "assert total == 5\nx", "x"))
    check("weaken: non-test file ignored", rc == 0, rc)

    # MODE: block promotes to exit 2
    rc, _o, _e = run(s, edit(tf, "assert a\nassert b", "assert a"),
                     {"TDD_PLAYBOOK_HOOK_TESTWEAKEN": "block"})
    check("weaken: block mode -> exit 2", rc == 2, rc)

    # MODE: off silences
    rc, _o, e = run(s, edit(tf, "assert a\nassert b", "assert a"),
                    {"TDD_PLAYBOOK_HOOK_TESTWEAKEN": "off"})
    check("weaken: off mode -> exit 0 silent", rc == 0 and e == "", (rc, e))

    # MultiEdit shape is parsed
    me = {"tool_name": "MultiEdit", "tool_input": {"file_path": tf,
          "edits": [{"old_string": "assert a\nassert b", "new_string": "assert a"}]}}
    rc, _o, e = run(s, me)
    check("weaken: MultiEdit shape handled", rc == 1 and "assertions dropped" in e, (rc, e))


# ----------------------------------------------------------------------- flaky_guard
def test_flaky():
    s = "flaky_guard.py"
    tf = "tests/test_api.py"

    rc, _o, e = run(s, edit(tf, "x = 1", "import time\ntime.sleep(2)"))
    check("flaky: sleep is caught", rc == 1 and "sleep" in e.lower(), (rc, e))

    rc, _o, e = run(s, edit(tf, "x = 1", "v = random.randint(0, 9)"))
    check("flaky: unseeded randomness is caught", rc == 1 and "random" in e.lower(), (rc, e))

    # seeded in the same block -> not flagged
    rc, _o, _e = run(s, edit(tf, "x = 1", "random.seed(0)\nv = random.randint(0, 9)"))
    check("flaky: seeded randomness NOT flagged", rc == 0, _e)

    rc, _o, e = run(s, edit(tf, "x = 1", "r = requests.get('http://x')"))
    check("flaky: live network is caught", rc == 1 and "network" in e.lower(), (rc, e))

    # Write of a clean test -> silent
    rc, _o, e = run(s, write(tf, "def test_x():\n    assert add(2, 2) == 4\n"))
    check("flaky: clean Write not flagged", rc == 0 and e == "", (rc, e))

    # non-test file with a sleep -> ignored (prod code may legitimately sleep)
    rc, _o, _e = run(s, edit("src/worker.py", "x = 1", "time.sleep(2)"))
    check("flaky: non-test file ignored", rc == 0, _e)


# ----------------------------------------------------------------------- intent_nudge
def test_intent():
    s = "intent_nudge.py"

    rc, o, _e = run(s, {"prompt": "fix the off-by-one bug in the pager"})
    ok = rc == 0 and '"additionalContext"' in o and "TDD Playbook" in o
    check("intent: build/fix prompt injects reminder", ok, (rc, o))

    rc, o, _e = run(s, {"prompt": "thanks!"})
    check("intent: trivial prompt -> no injection", rc == 0 and o.strip() == "", (rc, o))

    rc, o, _e = run(s, {"prompt": "use the TDD Playbook to build the parser"})
    check("intent: already-invoked prompt -> no double", rc == 0 and o.strip() == "", (rc, o))

    rc, o, _e = run(s, {"prompt": "implement the new billing feature"},
                    {"TDD_PLAYBOOK_NUDGE": "off"})
    check("intent: NUDGE=off silences", rc == 0 and o.strip() == "", (rc, o))


# ------------------------------------------------------------- build_completion_reminder
def test_tripwire_reminder():
    s = "build_completion_reminder.py"

    # re-entry guard: stop_hook_active -> always silent (no loop)
    rc, _o, _e = run(s, {"stop_hook_active": True})
    check("tripwire: re-entry guard silent", rc == 0, rc)

    # end-to-end in a throwaway git repo: source-only change must warn
    with tempfile.TemporaryDirectory() as d:
        def git(*a):
            subprocess.run(["git", *a], cwd=d, capture_output=True, text=True)
        git("init", "-q")
        git("config", "user.email", "t@t")
        git("config", "user.name", "t")
        open(os.path.join(d, "app.py"), "w").write("def f():\n    return 1\n")
        git("add", "-A")
        git("commit", "-qm", "init")
        # change source only, no test
        open(os.path.join(d, "app.py"), "w").write("def f():\n    return 2\n")
        env = dict(os.environ)
        for k in list(env):
            if k.startswith("TDD_PLAYBOOK_"):
                del env[k]
        p = subprocess.run(
            [sys.executable, os.path.join(HOOKS, s)],
            input="{}", capture_output=True, text=True, cwd=d, env=env, timeout=20,
        )
        check("tripwire: source-only change warns", p.returncode == 1 and "no test" in p.stderr.lower(),
              (p.returncode, p.stderr))

        # now add a test change too -> silent
        open(os.path.join(d, "test_app.py"), "w").write("def test_f():\n    assert f() == 2\n")
        p = subprocess.run(
            [sys.executable, os.path.join(HOOKS, s)],
            input="{}", capture_output=True, text=True, cwd=d, env=env, timeout=20,
        )
        check("tripwire: source+test change silent", p.returncode == 0, (p.returncode, p.stderr))


def main():
    print("TDD Playbook hook calibration")
    for fn in (test_weakening, test_flaky, test_intent, test_tripwire_reminder):
        print("\n[{}]".format(fn.__name__))
        fn()
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
