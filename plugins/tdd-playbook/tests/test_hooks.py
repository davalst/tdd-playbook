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

    # PLANTED: assertion removed -> must BLOCK (integrity hook defaults to block; H2)
    rc, _o, e = run(s, edit(tf, "assert total == 5\nassert ok", "assert ok"))
    check("weaken: dropped assertion BLOCKS by default", rc == 2 and "assertions dropped" in e, (rc, e))

    # PLANTED: skip marker added -> must block
    rc, _o, e = run(s, edit(tf, "def test_pay():", "@pytest.mark.skip\ndef test_pay():"))
    check("weaken: added skip is caught", rc == 2 and "skip" in e.lower(), (rc, e))

    # PLANTED: assertion neutered to tautology -> must block
    rc, _o, e = run(s, edit(tf, "assert charge() == 10", "assert True  # TODO"))
    check("weaken: tautology is caught", rc == 2 and "tautology" in e.lower(), (rc, e))

    # CLEAN: strengthening (added assertion) -> silent (exit 0)
    rc, _o, e = run(s, edit(tf, "assert ok", "assert ok\nassert total == 5"))
    check("weaken: strengthening is NOT flagged", rc == 0 and e == "", (rc, e))

    # NEGATIVE: same weakening on a NON-test file -> silent
    rc, _o, _e = run(s, edit("src/pay.py", "assert total == 5\nx", "x"))
    check("weaken: non-test file ignored", rc == 0, rc)

    # MODE: explicit warn demotes to exit 1
    rc, _o, _e = run(s, edit(tf, "assert a\nassert b", "assert a"),
                     {"TDD_PLAYBOOK_HOOK_TESTWEAKEN": "warn"})
    check("weaken: warn mode -> exit 1", rc == 1, rc)

    # MODE: global env can demote too (per-hook default yields to explicit global)
    rc, _o, _e = run(s, edit(tf, "assert a\nassert b", "assert a"),
                     {"TDD_PLAYBOOK_HOOK_MODE": "warn"})
    check("weaken: global warn -> exit 1", rc == 1, rc)

    # MODE: off silences
    rc, _o, e = run(s, edit(tf, "assert a\nassert b", "assert a"),
                    {"TDD_PLAYBOOK_HOOK_TESTWEAKEN": "off"})
    check("weaken: off mode -> exit 0 silent", rc == 0 and e == "", (rc, e))

    # MultiEdit shape is parsed
    me = {"tool_name": "MultiEdit", "tool_input": {"file_path": tf,
          "edits": [{"old_string": "assert a\nassert b", "new_string": "assert a"}]}}
    rc, _o, e = run(s, me)
    check("weaken: MultiEdit shape handled", rc == 2 and "assertions dropped" in e, (rc, e))


def test_weakening_h5_exit_calls():
    s = "test_weakening_guard.py"
    tf = "tests/test_pay.py"

    # PLANTED (H5): sys.exit(0) added to a test -> block (fakes a passing suite)
    rc, _o, e = run(s, edit(tf, "assert ok", "sys.exit(0)\nassert ok"))
    check("H5: sys.exit added to test is caught", rc == 2 and "exit call" in e.lower(), (rc, e))

    # PLANTED (H5): os._exit added to conftest.py (verifier surface) -> block
    rc, _o, e = run(s, edit("conftest.py", "pass", "os._exit(0)"))
    check("H5: os._exit added to conftest is caught", rc == 2 and "exit call" in e.lower(), (rc, e))

    # CLEAN: pre-existing exit call untouched by the edit -> silent
    rc, _o, e = run(s, edit(tf, "sys.exit(0)\nassert a", "sys.exit(0)\nassert a\nassert b"))
    check("H5: pre-existing exit call not re-flagged", rc == 0, (rc, e))


# ---------------------------------------------------------------------- overmock_guard
def test_overmock():
    s = "overmock_guard.py"
    tf = "tests/test_api.py"

    # PLANTED (H3): net-new mock in a test edit -> warn (advisory tier)
    rc, _o, e = run(s, edit(tf, "resp = client.get('/x')",
                            "with mock.patch('api.client.get') as m:\n    resp = m()"))
    check("H3: net-new mock is flagged (warn)", rc == 1 and "net-new mock" in e, (rc, e))

    # PLANTED (H3): jest.mock in a Write of a new test file -> warn
    rc, _o, e = run(s, write("src/__tests__/api.test.ts",
                             "jest.mock('../client');\ntest('x', () => {});"))
    check("H3: jest.mock in new test file flagged", rc == 1 and "net-new mock" in e, (rc, e))

    # CLEAN: mock count unchanged (refactor around an existing mock) -> silent
    rc, _o, e = run(s, edit(tf, "m = mock.patch('a')", "m = mock.patch('a')  # moved"))
    check("H3: unchanged mock count silent", rc == 0, (rc, e))

    # CLEAN: mock REMOVED -> silent (strengthening)
    rc, _o, e = run(s, edit(tf, "m = mock.patch('a')\nx", "x"))
    check("H3: removed mock silent", rc == 0, (rc, e))

    # NEGATIVE: non-test file with mocks (a test helper lib) -> ignored
    rc, _o, _e = run(s, edit("src/factory.py", "x", "m = mock.patch('a')"))
    check("H3: non-test file ignored", rc == 0, rc)


# ----------------------------------------------------------------------- vibe_test_guard
def test_vibetest():
    s = "vibe_test_guard.py"
    tf = "tests/test_vibe.py"

    # PLANTED (H4): a NEW test file with a test but ZERO assertions -> warn (advisory tier).
    # This is the case the weakening guard is structurally blind to (no old side to diff).
    rc, _o, e = run(s, write(tf, "def test_a():\n    result = compute()\n    print(result)\n"))
    check("H4: assertion-free new test file flagged (warn)",
          rc == 1 and "zero assertions" in e.lower(), (rc, e))

    # CLEAN: a bare `assert` statement is a real assertion -> silent
    rc, _o, e = run(s, write(tf, "def test_a():\n    assert compute() == 4\n"))
    check("H4: assert statement counts -> silent", rc == 0 and e == "", (rc, e))

    # CLEAN: unittest assertEqual (assert<Word>(...) form) counts -> silent
    rc, _o, e = run(s, write(tf, "class TestX(unittest.TestCase):\n"
                                 "    def test_a(self):\n        self.assertEqual(compute(), 4)\n"))
    check("H4: assertEqual counts -> silent", rc == 0 and e == "", (rc, e))

    # CLEAN: pytest.raises context manager IS the assertion -> silent (no false positive)
    rc, _o, e = run(s, write(tf, "def test_raises():\n    with pytest.raises(ValueError):\n        boom()\n"))
    check("H4: pytest.raises counts -> silent", rc == 0 and e == "", (rc, e))

    # NEGATIVE: a fixture/helper file with NO test declarations is not a vibe test -> silent
    rc, _o, e = run(s, write("tests/conftest.py",
                             "import pytest\n@pytest.fixture\ndef db():\n    return object()\n"))
    check("H4: fixture file (no test decls) not flagged", rc == 0 and e == "", (rc, e))

    # NEGATIVE: non-test source file with no asserts -> ignored
    rc, _o, _e = run(s, write("src/app.py", "def f():\n    return 1\n"))
    check("H4: non-test source file ignored", rc == 0, _e)

    # SCOPE: an Edit (fragment, not whole file) is the weakening guard's job, not this one -> silent
    rc, _o, e = run(s, edit(tf, "assert x == 1", "y = 2"))
    check("H4: Edit is out of scope for the vibe guard -> silent", rc == 0 and e == "", (rc, e))

    # MODE: off silences
    rc, _o, e = run(s, write(tf, "def test_a():\n    compute()\n"),
                    {"TDD_PLAYBOOK_HOOK_VIBETEST": "off"})
    check("H4: off mode -> exit 0 silent", rc == 0 and e == "", (rc, e))

    # MODE: opt-in block promotes to exit 2
    rc, _o, _e = run(s, write(tf, "def test_a():\n    compute()\n"),
                     {"TDD_PLAYBOOK_HOOK_VIBETEST": "block"})
    check("H4: block mode -> exit 2", rc == 2, _e)


# ---------------------------------------------------------------------- snapshot_guard
def test_snapshot():
    s = "snapshot_guard.py"

    def bash(cmd):
        return {"tool_name": "Bash", "tool_input": {"command": cmd}}

    # PLANTED (H5): snapshot auto-update invocations -> BLOCK
    for cmd in ("npx jest -u", "vitest run --update-snapshots", "jest --updateSnapshot",
                "pytest --snapshot-update", "UPDATE_SNAPSHOTS=1 npm test"):
        rc, _o, e = run(s, bash(cmd))
        check("H5: '{}' blocked".format(cmd), rc == 2 and "snapshot" in e.lower(), (rc, e))

    # CLEAN: plain test runs untouched
    for cmd in ("npx jest", "pytest -q", "npm test -- --coverage", "git status -u"):
        rc, _o, e = run(s, bash(cmd))
        check("clean: '{}' passes".format(cmd), rc == 0, (rc, e))

    # PLANTED (H5): direct edit of a .snap / __snapshots__ file -> BLOCK
    rc, _o, e = run(s, edit("src/__snapshots__/App.test.js.snap", "old", "new"))
    check("H5: __snapshots__ edit blocked", rc == 2 and "re-approval" in e, (rc, e))
    rc, _o, e = run(s, write("tests/output.snap", "expected"))
    check("H5: .snap write blocked", rc == 2, (rc, e))

    # CLEAN: ordinary file edit passes
    rc, _o, e = run(s, edit("src/app.py", "a", "b"))
    check("clean: ordinary edit passes", rc == 0, (rc, e))


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

    # REGRESSION (old bug): a mere @pytest.fixture in the block must NOT suppress a
    # wall-clock warning — a fixture proves nothing about time control
    rc, _o, e = run(s, edit(tf, "x = 1",
                            "@pytest.fixture\ndef now_fixture():\n    return datetime.now()"))
    check("flaky: fixture does not suppress wall-clock", rc == 1 and "wall-clock" in e, (rc, e))

    # a REAL clock control in the same block still suppresses
    rc, _o, _e = run(s, edit(tf, "x = 1",
                             "@freeze_time('2026-01-01')\ndef test_t():\n    d = datetime.now()"))
    check("flaky: freeze_time suppresses wall-clock", rc == 0, _e)

    # monkeypatching the CLOCK suppresses; monkeypatching something else does not
    rc, _o, _e = run(s, edit(tf, "x = 1",
                             "monkeypatch.setattr(time, 'time', lambda: 0)\nt = time.time()"))
    check("flaky: monkeypatched clock suppresses", rc == 0, _e)
    rc, _o, e = run(s, edit(tf, "x = 1",
                            "monkeypatch.setattr(api, 'fetch', fake)\nt = time.time()"))
    check("flaky: unrelated monkeypatch does NOT suppress", rc == 1 and "wall-clock" in e, (rc, e))

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

    def fired(o):
        return '"additionalContext"' in o and "TDD Playbook" in o

    with tempfile.TemporaryDirectory() as sd:
        def go(prompt, sid, extra=None):
            env = {"TDD_PLAYBOOK_NUDGE_STATE_DIR": sd}
            env.update(extra or {})
            ev = {"prompt": prompt}
            if sid is not None:
                ev["session_id"] = sid
            return run(s, ev, env)

        rc, o, _e = go("fix the off-by-one bug in the pager", "s1")
        check("intent: build/fix prompt injects reminder", rc == 0 and fired(o), (rc, o))

        rc, o, _e = go("thanks!", "s1")
        check("intent: trivial prompt -> no injection", rc == 0 and o.strip() == "", (rc, o))

        rc, o, _e = go("use the TDD Playbook to build the parser", "s-alone")
        check("intent: already-invoked prompt -> no double", rc == 0 and o.strip() == "", (rc, o))

        rc, o, _e = go("implement the new billing feature", "s-off",
                       {"TDD_PLAYBOOK_NUDGE": "off"})
        check("intent: NUDGE=off silences", rc == 0 and o.strip() == "", (rc, o))

        # PLANTED (duplicate registration): the SAME prompt in the SAME session — a second
        # invocation (plugin + vendored settings both registered) must stay silent
        rc, o, _e = go("fix the off-by-one bug in the pager", "s1")
        check("intent: duplicate registration -> second invocation silent",
              rc == 0 and o.strip() == "", (rc, o))

        # damping: a DIFFERENT build prompt in the same session within the interval -> silent
        rc, o, _e = go("implement the new billing feature", "s1")
        check("intent: within damp interval -> silent", rc == 0 and o.strip() == "", (rc, o))

        # interval=0 disables damping: different prompts each fire...
        rc, o, _e = go("implement the new billing feature", "s2",
                       {"TDD_PLAYBOOK_NUDGE_INTERVAL": "0"})
        check("intent: interval=0 first prompt fires", rc == 0 and fired(o), (rc, o))
        rc, o, _e = go("refactor the parser module now", "s2",
                       {"TDD_PLAYBOOK_NUDGE_INTERVAL": "0"})
        check("intent: interval=0 next prompt fires again", rc == 0 and fired(o), (rc, o))
        # ...but the SAME prompt is still deduped (duplicate registration protection)
        rc, o, _e = go("refactor the parser module now", "s2",
                       {"TDD_PLAYBOOK_NUDGE_INTERVAL": "0"})
        check("intent: interval=0 same prompt still deduped",
              rc == 0 and o.strip() == "", (rc, o))

        # meta-discussion exclusion: decision/opinion questions must NOT trigger, even
        # when they contain intent verbs like "implement" or "review"
        rc, o, _e = go("should we implement this centrally? any thoughts on improvements?",
                       "s3")
        check("intent: 'should we implement' meta-question -> silent",
              rc == 0 and o.strip() == "", (rc, o))
        rc, o, _e = go("what do you think about the code review — is the roster too big?",
                       "s3")
        check("intent: 'what do you think' meta-question -> silent",
              rc == 0 and o.strip() == "", (rc, o))

        # session isolation: a different session fires fresh
        rc, o, _e = go("fix the off-by-one bug in the pager", "s4")
        check("intent: new session fires fresh", rc == 0 and fired(o), (rc, o))

        # no session_id (older host): still fires via fallback key, never crashes
        with tempfile.TemporaryDirectory() as sd2:
            rc, o, _e = run(s, {"prompt": "fix the crash in the auth path"},
                            {"TDD_PLAYBOOK_NUDGE_STATE_DIR": sd2})
            check("intent: missing session_id still fires (fallback key)",
                  rc == 0 and fired(o), (rc, o))

    # unwritable state dir: FAIL OPEN — the nudge must fire rather than crash or block
    rc, o, _e = run(s, {"prompt": "fix the crash in the auth path", "session_id": "s5"},
                    {"TDD_PLAYBOOK_NUDGE_STATE_DIR": "/nonexistent/nope/really-not-here"})
    check("intent: unwritable state dir fails OPEN (fires)", rc == 0 and fired(o), (rc, o))


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

        # REGRESSION (old bug): tree has BOTH changes, but the TRANSCRIPT shows this
        # session only edited source — a pre-existing test change elsewhere must no
        # longer silence the reminder
        def transcript(paths):
            tp = os.path.join(d, "transcript.jsonl")
            with open(tp, "w") as fh:
                for pth in paths:
                    fh.write(json.dumps({"type": "assistant", "message": {"content": [
                        {"type": "tool_use", "name": "Edit",
                         "input": {"file_path": os.path.join(d, pth)}}]}}) + "\n")
            return tp

        ev = json.dumps({"transcript_path": transcript(["app.py"])})
        p = subprocess.run([sys.executable, os.path.join(HOOKS, s)],
                           input=ev, capture_output=True, text=True, cwd=d, env=env, timeout=20)
        check("tripwire: session-only source edit warns despite unrelated test change",
              p.returncode == 1 and "no test" in p.stderr.lower(), (p.returncode, p.stderr))

        # transcript shows source+test edited by the session -> silent
        ev = json.dumps({"transcript_path": transcript(["app.py", "test_app.py"])})
        p = subprocess.run([sys.executable, os.path.join(HOOKS, s)],
                           input=ev, capture_output=True, text=True, cwd=d, env=env, timeout=20)
        check("tripwire: session source+test edits silent", p.returncode == 0,
              (p.returncode, p.stderr))

        # unreadable transcript falls back to whole-tree behavior (silent here: tree has tests)
        ev = json.dumps({"transcript_path": os.path.join(d, "nope.jsonl")})
        p = subprocess.run([sys.executable, os.path.join(HOOKS, s)],
                           input=ev, capture_output=True, text=True, cwd=d, env=env, timeout=20)
        check("tripwire: missing transcript falls back to whole tree", p.returncode == 0,
              (p.returncode, p.stderr))


def main():
    print("TDD Playbook hook calibration")
    for fn in (test_weakening, test_weakening_h5_exit_calls, test_overmock, test_vibetest,
               test_snapshot, test_flaky, test_intent, test_tripwire_reminder):
        print("\n[{}]".format(fn.__name__))
        fn()
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
