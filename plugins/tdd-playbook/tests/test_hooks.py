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


# G5 isolation: every hook invocation in this suite writes its yield event to a temp file,
# never to <repo>/.claude/playbook-yield.jsonl — a test run must not dirty the tree CIVerd's
# diff-integrity watches.
_YIELD_TMP = tempfile.mkdtemp(prefix="hook-yield-")
_YIELD_DEFAULT = os.path.join(_YIELD_TMP, "yield.jsonl")


def run(script, event, env_extra=None):
    env = dict(os.environ)
    # neutralize any developer override so tests see documented defaults
    for k in list(env):
        if k.startswith("TDD_PLAYBOOK_"):
            del env[k]
    env["TDD_PLAYBOOK_YIELD_LOG"] = _YIELD_DEFAULT
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


# ---------------------------------------------------------------- red_lock (auto-lock)
def test_red_lock():
    s = "red_lock.py"

    def bash(cmd, response):
        ev = {"tool_name": "Bash", "tool_input": {"command": cmd}}
        if response is not None:
            ev["tool_response"] = response
        return ev

    def run_in(d, event):
        env = dict(os.environ)
        for k in list(env):
            if k.startswith("TDD_PLAYBOOK_"):
                del env[k]
        env["CLAUDE_PROJECT_DIR"] = d
        p = subprocess.run([sys.executable, os.path.join(HOOKS, s)],
                           input=json.dumps(event), capture_output=True, text=True,
                           cwd=d, env=env, timeout=20)
        return p

    def read_json(d, rel):
        path = os.path.join(d, ".claude", rel)
        if not os.path.isfile(path):
            return {}
        with open(path) as fh:
            return json.load(fh)

    with tempfile.TemporaryDirectory() as d:
        d = os.path.realpath(d)
        os.makedirs(os.path.join(d, "tests"), exist_ok=True)
        tf = os.path.join(d, "tests", "test_new.py")
        with open(tf, "w") as fh:
            fh.write("def test_x():\n    assert False\n")

        # 1. test-file write -> pending recorded
        p = run_in(d, write(tf, "def test_x():\n    assert False\n"))
        pend = read_json(d, "tdd-pending-red.json").get("files", {})
        check("redlock: test-file write records pending",
              p.returncode == 0 and os.path.join("tests", "test_new.py") in pend,
              (p.returncode, pend))

        # 2. non-test write -> NOT pending
        src = os.path.join(d, "app.py")
        with open(src, "w") as fh:
            fh.write("x = 1\n")
        run_in(d, write(src, "x = 1\n"))
        pend = read_json(d, "tdd-pending-red.json").get("files", {})
        check("redlock: source write not pending", "app.py" not in pend, pend)

        # 3. failing test run -> pending file LOCKED + journaled + announced
        p = run_in(d, bash("python -m pytest tests/ -q", "1 failed, 2 passed in 0.1s"))
        lock = read_json(d, "tdd-lock.json").get("files", {})
        pend = read_json(d, "tdd-pending-red.json").get("files", {})
        jpath = os.path.join(d, ".claude", "tdd-lock-journal.jsonl")
        journal = open(jpath).read() if os.path.isfile(jpath) else ""
        check("redlock: red run locks the pending test",
              os.path.join("tests", "test_new.py") in lock and not pend,
              (lock, pend))
        check("redlock: auto-lock journaled + announced",
              "auto_lock_red" in journal and p.returncode == 1
              and "auto-locked" in p.stderr,
              (p.returncode, p.stderr[:120], journal[:120]))

        # 4. the LOCKED file is now defended by test_lock_guard (end-to-end) —
        # ANY edit to a locked file is blocked, so neutral strings suffice.
        env = dict(os.environ)
        for k in list(env):
            if k.startswith("TDD_PLAYBOOK_"):
                del env[k]
        env["CLAUDE_PROJECT_DIR"] = d
        p = subprocess.run([sys.executable, os.path.join(HOOKS, "test_lock_guard.py")],
                           input=json.dumps(edit(tf, "alpha", "beta")),
                           capture_output=True, text=True, cwd=d, env=env, timeout=20)
        check("redlock: guard blocks an edit to the auto-locked test",
              p.returncode == 2 and "TEST-LOCK" in p.stderr, (p.returncode, p.stderr[:120]))

    with tempfile.TemporaryDirectory() as d:
        d = os.path.realpath(d)
        os.makedirs(os.path.join(d, "tests"), exist_ok=True)
        tf = os.path.join(d, "tests", "test_g.py")
        with open(tf, "w") as fh:
            fh.write("def test_g():\n    assert add(1, 1) == 2\n")
        run_in(d, write(tf, "def test_g():\n    assert add(1, 1) == 2\n"))

        # 5. GREEN run -> pending cleared, NO lock
        run_in(d, bash("pytest -q", "3 passed in 0.2s"))
        check("redlock: green run clears pending without locking",
              not read_json(d, "tdd-pending-red.json").get("files", {})
              and not read_json(d, "tdd-lock.json").get("files", {}),
              (read_json(d, "tdd-pending-red.json"), read_json(d, "tdd-lock.json")))

        # 6. a NON-test command with failure text -> nothing happens
        run_in(d, write(tf, "def test_g():\n    assert add(1, 1) == 2\n"))
        run_in(d, bash("cat build.log", "1 failed, something"))
        check("redlock: non-test command never locks",
              not read_json(d, "tdd-lock.json").get("files", {}),
              read_json(d, "tdd-lock.json"))

        # 7. test run with NO tool_response -> fail-open (no lock, pending kept)
        run_in(d, bash("pytest -q", None))
        check("redlock: missing tool_response is fail-open",
              not read_json(d, "tdd-lock.json").get("files", {})
              and read_json(d, "tdd-pending-red.json").get("files", {}),
              (read_json(d, "tdd-lock.json"), read_json(d, "tdd-pending-red.json")))


def test_lock_shell():
    """F1 (shell channel) + F2 (lock self-protection) for test_lock_guard.py.

    A locked test the agent can rewrite with `sed -i` / `> file` / `git checkout`, or a lock
    file it can `rm`, is a lock in name only. These planted bypasses MUST block; reads and the
    sanctioned unlock MUST pass (a guard that wedges legitimate work is the adoption killer)."""
    s = "test_lock_guard.py"

    def drive(d, event):
        env = dict(os.environ)
        for k in list(env):
            if k.startswith("TDD_PLAYBOOK_"):
                del env[k]
        env["CLAUDE_PROJECT_DIR"] = d
        return subprocess.run([sys.executable, os.path.join(HOOKS, s)],
                              input=json.dumps(event), capture_output=True, text=True,
                              cwd=d, env=env, timeout=20)

    def bash_ev(cmd):
        return {"tool_name": "Bash", "tool_input": {"command": cmd}}

    def setup_lock(d, files=("tests/test_pay.py",)):
        os.makedirs(os.path.join(d, ".claude"), exist_ok=True)
        for f in files:
            fp = os.path.join(d, f)
            os.makedirs(os.path.dirname(fp), exist_ok=True)
            with open(fp, "w") as fh:
                fh.write("def test_pay():\n    assert charge() == 10\n")
        with open(os.path.join(d, ".claude", "tdd-lock.json"), "w") as fh:
            json.dump({"files": {f: {"locked_at": "t"} for f in files}}, fh)

    def block(name, d, ev):
        p = drive(d, ev)
        check(name, p.returncode == 2 and "TEST-LOCK" in p.stderr, (p.returncode, p.stderr[:110]))

    def allow(name, d, ev):
        p = drive(d, ev)
        check(name, p.returncode == 0 and p.stderr == "", (p.returncode, p.stderr[:110]))

    with tempfile.TemporaryDirectory() as d:
        d = os.path.realpath(d)
        setup_lock(d)
        # F1 — shell WRITE bypasses on a locked test must block
        block("lock/sh: sed -i on locked test blocks", d, bash_ev("sed -i 's/10/9/' tests/test_pay.py"))
        block("lock/sh: redirect-overwrite locked test blocks", d, bash_ev('echo "def test_pay(): pass" > tests/test_pay.py'))
        block("lock/sh: append-redirect locked test blocks", d, bash_ev("cat foo >> tests/test_pay.py"))
        block("lock/sh: git checkout -- locked test blocks", d, bash_ev("git checkout -- tests/test_pay.py"))
        block("lock/sh: git checkout . (revert-all) blocks", d, bash_ev("git checkout ."))
        block("lock/sh: git restore . blocks", d, bash_ev("git restore ."))
        block("lock/sh: rm locked test blocks", d, bash_ev("rm tests/test_pay.py"))
        block("lock/sh: mv over locked test blocks", d, bash_ev("mv /tmp/x tests/test_pay.py"))
        block("lock/sh: inline python open(...,'w') blocks", d, bash_ev("python3 -c \"open('tests/test_pay.py','w').write('')\""))
        # F1 — READS and legitimate runs must NOT block (adoption killer if they do)
        allow("lock/sh: cat locked test is allowed", d, bash_ev("cat tests/test_pay.py"))
        allow("lock/sh: run locked test is allowed", d, bash_ev("python -m pytest tests/test_pay.py -q"))
        allow("lock/sh: run + redirect OUTPUT elsewhere is allowed", d, bash_ev("pytest tests/test_pay.py -q > /tmp/out.log"))
        allow("lock/sh: git checkout a branch is allowed", d, bash_ev("git checkout main"))
        # F1 — verifier surface + enforcement via shell
        block("lock/sh: sed -i on conftest blocks (H5)", d, bash_ev("sed -i 's/a/b/' conftest.py"))
        block("lock/sh: rm on a guard hook blocks", d, bash_ev("rm .claude/hooks/scripts/test_lock_guard.py"))
        # F2 — the lock's own state cannot be removed/rewritten to self-unlock
        block("lock/sh: rm tdd-lock.json blocks (F2)", d, bash_ev("rm .claude/tdd-lock.json"))
        block("lock/sh: overwrite tdd-lock.json blocks (F2)", d, bash_ev("echo '{}' > .claude/tdd-lock.json"))
        block("lock/sh: truncate the journal blocks (F2)", d, bash_ev("truncate -s0 .claude/tdd-lock-journal.jsonl"))
        block("lock/edit: editing tdd-lock.json blocks (F2)", d, edit(os.path.join(d, ".claude", "tdd-lock.json"), "a", "b"))
        block("lock/edit: editing hooks.json blocks", d, edit(os.path.join(d, ".claude", "hooks", "hooks.json"), "a", "b"))
        # the SANCTIONED unlock must pass (references tdd_lock.py, not the state file literal)
        allow("lock/sh: journaled unlock via tdd_lock.py is allowed", d,
              bash_ev('python3 /plug/bin/tdd_lock.py unlock --reason "impl done"'))

    with tempfile.TemporaryDirectory() as d2:
        d2 = os.path.realpath(d2)  # NO lock active
        allow("lock/sh: no lock -> rm test is zero-cost allow", d2, bash_ev("rm tests/test_pay.py"))


# ---------------------------------------------------------------- yield event log (R4/D4)
def test_yield_logging():
    """PLANTED (D4): every guard outcome flows through _common.emit(), so ONE logging call
    there gives the yield instrument its data — a guard silently absent from the log would
    read as zero-yield, which is a retirement trigger. Logging must never break enforcement."""
    s = "test_weakening_guard.py"
    tf = "tests/test_pay.py"
    weaken = edit(tf, "assert total == 5\nassert ok", "assert ok")

    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "y.jsonl")
        rc, _o, _e = run(s, weaken, env_extra={"TDD_PLAYBOOK_YIELD_LOG": log})
        rows = [json.loads(ln) for ln in open(log)] if os.path.isfile(log) else []
        check("yield: block event logged with gate + event + findings",
              rc == 2 and len(rows) == 1 and rows[0].get("gate") == "testweaken"
              and rows[0].get("event") == "block" and rows[0].get("findings", 0) >= 1,
              (rc, rows))

        def rows_of():
            return [json.loads(ln) for ln in open(log)] if os.path.isfile(log) else []

        rc, _o, _e = run(s, weaken, env_extra={"TDD_PLAYBOOK_YIELD_LOG": log,
                                               "TDD_PLAYBOOK_HOOK_TESTWEAKEN": "warn"})
        rows = rows_of()
        check("yield: warn-mode event logged as warn",
              rc == 1 and len(rows) == 2 and rows[1].get("event") == "warn", (rc, rows))

        # a CLEAN pass adds no row (the log records friction, not traffic)
        rc, _o, _e = run(s, edit(tf, "assert ok", "assert ok\nassert total == 5"),
                         env_extra={"TDD_PLAYBOOK_YIELD_LOG": log})
        rows = rows_of()
        check("yield: clean pass logs nothing", rc == 0 and len(rows) == 2, (rc, rows))

        # PLANTED: an unwritable log path (parent is a FILE) must never weaken enforcement
        with open(os.path.join(d, "nope"), "w") as fh:
            fh.write("a file, not a dir")
        rc, _o, e = run(s, weaken,
                        env_extra={"TDD_PLAYBOOK_YIELD_LOG": os.path.join(d, "nope", "x",
                                                                          "y.jsonl")})
        check("yield: unwritable log never breaks the block",
              rc == 2 and "assertions dropped" in e, (rc, e))

    # G5: the suite's own runs land in the temp default, not the repo tree
    check("yield: suite isolation — temp default log received this suite's events",
          os.path.isfile(_YIELD_DEFAULT) and os.path.getsize(_YIELD_DEFAULT) > 0,
          _YIELD_DEFAULT)

    # PLANTED (hole 2, 2026-07-28): demotion-to-off must not be a SILENT kill switch — a
    # finding suppressed by off-mode leaves a 'suppressed' trace in the yield log, so a
    # muzzled gate is distinguishable from a quiet one
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "y.jsonl")
        rc, _o, _e = run(s, weaken, env_extra={"TDD_PLAYBOOK_YIELD_LOG": log,
                                               "TDD_PLAYBOOK_HOOK_TESTWEAKEN": "off"})
        rows = [json.loads(ln) for ln in open(log)] if os.path.isfile(log) else []
        check("suppressed: off-mode finding still leaves a trace (muzzled != quiet)",
              rc == 0 and len(rows) == 1 and rows[0].get("event") == "suppressed"
              and rows[0].get("gate") == "testweaken", (rc, rows))
        # a clean pass under off-mode logs nothing (no findings -> nothing suppressed)
        rc, _o, _e = run(s, edit(tf, "assert ok", "assert ok\nassert x == 1"),
                         env_extra={"TDD_PLAYBOOK_YIELD_LOG": log,
                                    "TDD_PLAYBOOK_HOOK_TESTWEAKEN": "off"})
        rows = [json.loads(ln) for ln in open(log)]
        check("suppressed: clean pass under off-mode logs nothing",
              rc == 0 and len(rows) == 1, (rc, rows))

    # PLANTED (hole 2): this repo's committed settings must carry no standing demotions —
    # an env-block demotion is the persistent, invisible variant of the kill switch
    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(HOOKS))))
    demotions = []
    for rel in (".claude/settings.json", ".claude/settings.local.json"):
        sp = os.path.join(repo_root, rel)
        if os.path.isfile(sp):
            try:
                envblock = json.load(open(sp)).get("env", {}) or {}
            except ValueError:
                envblock = {}
            demotions += ["{}: {}={}".format(rel, k, v) for k, v in envblock.items()
                          if k.startswith("TDD_PLAYBOOK_HOOK")]
    check("no standing guard demotions in committed settings env blocks",
          demotions == [], demotions)


def main():
    print("TDD Playbook hook calibration")
    for fn in (test_weakening, test_weakening_h5_exit_calls, test_overmock, test_snapshot,
               test_flaky, test_intent, test_tripwire_reminder, test_red_lock,
               test_lock_shell, test_yield_logging):
        print("\n[{}]".format(fn.__name__))
        fn()
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
