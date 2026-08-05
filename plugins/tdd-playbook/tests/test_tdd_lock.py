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

    test_reason_class()
    test_reason_class_reaches_the_rollup()

    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


def _fresh(d, name="tests/test_pay.py"):
    """A scratch project with one locked test file; returns its abs path."""
    os.makedirs(os.path.join(d, "tests"), exist_ok=True)
    p = os.path.join(d, name)
    if not os.path.isfile(p):
        # a real assertion, not a tautology: this string is fixture CONTENT, but the
        # weakening guard reads it as source and is right to — keep fixtures honest too
        open(p, "w").write("def test_pay_totals():\n    assert pay(100, 0.2) == 80\n")
    lock_cli(d, "lock", name)
    return p


def test_reason_class():
    """PLANTED (v1.27, pre-fix sha 119e2de): every journaled unlock was reported to the yield
    instrument as a block adjudicated a false positive, so the normal red-first rhythm drove
    `RETIREMENT CANDIDATE: testlock`. `--class` names WHY the lock was released; only
    `gate-wrong` adjudicates.

    The self-grading hazard is the point of the refusals below: the agent picking the class
    is the agent that wants out, so the one class that moves the needle is the one hardest to
    claim, and a phase-shaped reason claiming it is FLAGGED — never silently rewritten."""
    print("\n[unlock reason-class (v1.27)]")
    journal = lambda d: [json.loads(ln) for ln in
                         open(os.path.join(d, ".claude", "tdd-lock-journal.jsonl"))]

    with tempfile.TemporaryDirectory() as d:
        _fresh(d)
        p = lock_cli(d, "unlock", "--reason", "phase boundary — green, re-locking after",
                     "--class", "phase")
        check("unlock --class phase succeeds and is journaled as stated",
              p.returncode == 0 and journal(d)[-1]["reason_class"] == "phase",
              (p.returncode, p.stderr))

    with tempfile.TemporaryDirectory() as d:
        _fresh(d)
        # PLANTED: the exculpatory class claimed on a thin reason
        p = lock_cli(d, "unlock", "--reason", "gate was wrong", "--class", "gate-wrong")
        check("PLANTED thin gate-wrong is REFUSED (exit 1)",
              p.returncode == 1 and "REFUSED" in p.stderr, (p.returncode, p.stderr))
        check("PLANTED thin gate-wrong: lock NOT lifted, nothing journaled",
              os.path.isfile(os.path.join(d, ".claude", "tdd-lock.json"))
              and [e["event"] for e in journal(d)] == ["lock"], journal(d))
        # CONTROL: the same class over the bar is accepted
        p = lock_cli(d, "unlock", "--class", "gate-wrong", "--reason",
                     "the testlock guard blocked an edit to a file that was never locked")
        check("CONTROL: gate-wrong over the bar succeeds",
              p.returncode == 0 and journal(d)[-1]["reason_class"] == "gate-wrong",
              (p.returncode, p.stderr))

    with tempfile.TemporaryDirectory() as d:
        _fresh(d)
        # PLANTED: an invented class must not open a new bucket
        p = lock_cli(d, "unlock", "--reason", "a perfectly fine reason here",
                     "--class", "made-up")
        check("PLANTED invented class rejected by the closed vocabulary (exit 2)",
              p.returncode == 2, (p.returncode, p.stderr))
        check("PLANTED invented class: lock survives",
              os.path.isfile(os.path.join(d, ".claude", "tdd-lock.json")))
        for k in ("phase", "feature-end", "test-wrong", "gate-wrong"):
            reason = ("the gate blocked work it should not have, here is which one and why"
                      if k == "gate-wrong" else "a perfectly fine reason here")
            _fresh(d)
            p = lock_cli(d, "unlock", "--reason", reason, "--class", k)
            check("CONTROL: vocabulary member {} accepted".format(k), p.returncode == 0,
                  (k, p.returncode, p.stderr))

    with tempfile.TemporaryDirectory() as d:
        _fresh(d)
        # PLANTED (self-grading): phase-shaped prose claiming the adjudicating class
        p = lock_cli(d, "unlock", "--class", "gate-wrong", "--reason",
                     "implemented to green and will re-lock once the next batch lands")
        e = journal(d)[-1]
        check("PLANTED phase-shaped gate-wrong is FLAGGED as a mismatch",
              p.returncode == 0 and "MISMATCH" in p.stderr and e.get("class_mismatch") is True,
              (p.returncode, p.stderr, e))
        check("mismatch NEVER rewrites the stated class (no silent fabrication)",
              e["reason_class"] == "gate-wrong", e)

    with tempfile.TemporaryDirectory() as d:
        _fresh(d)
        # CONTROL: the same prose with the honest class draws no flag
        p = lock_cli(d, "unlock", "--class", "phase", "--reason",
                     "implemented to green and will re-lock once the next batch lands")
        check("CONTROL: phase-shaped prose classed phase -> no mismatch flag",
              p.returncode == 0 and "MISMATCH" not in p.stderr
              and "class_mismatch" not in journal(d)[-1], (p.stderr, journal(d)[-1]))

    with tempfile.TemporaryDirectory() as d:
        _fresh(d)
        # back-compat: an old caller with no --class still works, but says it measured nothing
        p = lock_cli(d, "unlock", "--reason", "old caller with no class flag")
        check("back-compat: no --class -> succeeds, recorded UNCLASSIFIED, said out loud",
              p.returncode == 0 and journal(d)[-1]["reason_class"] == "unclassified"
              and "UNCLASSIFIED" in p.stderr, (p.returncode, p.stderr, journal(d)[-1]))


def test_reason_class_reaches_the_rollup():
    """SEAM (§1 v1.26 — test at the seam you don't own): the writer names the field
    `reason_class` and the reader looks for `reason_class`. Every other test here reads only
    what tdd_lock itself wrote, so both sides could be self-consistently wrong and stay green.
    This drives the REAL gate_yield.py rollup and asserts the committed `fp` cell."""
    print("\n[seam: unlock class -> real gate_yield rollup]")
    gy = os.path.join(PLUGIN, "bin", "gate_yield.py")
    for klass, want_fp in (("gate-wrong", 1), ("phase", 0)):
        with tempfile.TemporaryDirectory() as d:
            _fresh(d)
            log = os.path.join(d, "yield.jsonl")
            md = os.path.join(d, "gate_yield.md")
            # clean_env strips TDD_PLAYBOOK_*, so the log MUST be set explicitly here or the
            # unlock drains the developer's real yield log (the 2026-07-28 G5 incident).
            env = clean_env(d)
            env["TDD_PLAYBOOK_YIELD_LOG"] = log
            subprocess.run([sys.executable, LOCK_BIN, "unlock", "--class", klass, "--reason",
                            "the gate blocked work it should not have, naming which and why"],
                           capture_output=True, text=True, env=env, cwd=d, timeout=60)
            check("seam: unlock({}) wrote a raw override row".format(klass),
                  os.path.isfile(log) and '"reason_class"' in open(log).read(),
                  open(log).read() if os.path.isfile(log) else "no log")
            subprocess.run([sys.executable, gy, "rollup", "--log", log, "--md", md,
                            "--date", "2026-09-09"], capture_output=True, text=True,
                           env=env, timeout=60)
            body = open(md).read() if os.path.isfile(md) else ""
            check("seam: real rollup records fp={} for --class {}".format(want_fp, klass),
                  "| 2026-09-09 | testlock | 0 | 0 | 1 | 0 | {} |".format(want_fp) in body,
                  body)


if __name__ == "__main__":
    main()
