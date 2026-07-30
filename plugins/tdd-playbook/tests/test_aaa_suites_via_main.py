#!/usr/bin/env python3
"""Guardrail: make `pytest` HONEST about this repo's script-style suites (CIVerd gate probe finding).

Every suite here uses `check()` — which COUNTS failures and only `main()` sums them and `sys.exit(1)`.
Under bare `pytest` a `test_*` function calls `check()`, the check fails, and the function RETURNS
NORMALLY → pytest reports pass. And the main()-only suites (no `test_*` functions) are collected as
zero tests and never run at all. So `pytest -q plugins/tdd-playbook/tests` can report GREEN over a
genuinely failing suite — a false green (empirically confirmed 2026-07-27 by a planted-error probe of
the CIVerd gate, which runs exactly that command).

This file closes the hole with the ONE construct pytest cannot miss — a raw `assert`: it runs every
sibling suite through its real `main()` (`python3 file.py`) and the calibration harness, asserting
exit 0. Now `pytest` and `python3 file.py` agree, no matter how the suite is invoked. (The proper fix
is ALSO to point CIVerd's `tests` check at the repo's real gate command — the `python3 test_*.py`
loop — not bare pytest; see CLAUDE.md. This guard is the defense-in-depth half.)
"""
import glob
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SELF = os.path.basename(__file__)
# dirname^3: tests -> tdd-playbook -> plugins -> REPO ROOT. The original dirname^2 pointed
# at plugins/, so the calibration/test_harness.py append below resolved to a nonexistent
# path and the isfile guard SILENTLY skipped it — the harness was never in SUITES at all
# (found 2026-07-28 via the engine probe's calibration-gate false-green).
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

# Every script-style suite: the sibling test_*.py files (except this one) + the calibration harness.
SUITES = sorted(f for f in glob.glob(os.path.join(HERE, "test_*.py"))
                if os.path.basename(f) != SELF)
SUITES.append(os.path.join(REPO, "calibration", "test_harness.py"))


def test_every_suite_passes_via_main():
    """Run each suite through its own main() and assert exit 0 — a raw assert so pytest cannot
    silently pass over a check()-based failure the way it does when it calls the test_ functions."""
    failures = []
    for suite in SUITES:
        if not os.path.isfile(suite):
            continue
        r = subprocess.run([sys.executable, suite], capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            failures.append("{} -> exit {}\n{}".format(
                os.path.basename(suite), r.returncode, (r.stdout + r.stderr)[-1500:]))
    assert not failures, "suite(s) failed via main() but pytest would have missed it:\n" + \
                         "\n".join(failures)


def test_guard_can_detect_a_failing_suite():
    """§13 calibrate-the-checker: prove this guard CAN fail — a suite that exits nonzero must be
    observed as nonzero (otherwise the guard above is theater)."""
    with tempfile.TemporaryDirectory() as d:
        bad = os.path.join(d, "bad.py")
        with open(bad, "w") as fh:
            fh.write("import sys\nsys.exit(1)\n")
        r = subprocess.run([sys.executable, bad], capture_output=True, text=True, timeout=30)
        assert r.returncode != 0, "guard cannot observe a nonzero exit — it would be theater"


def test_no_pytest_uncollectable_test_functions():
    """LIVE incident (CIVerd gate RED at 5abe347): a `def test_*(arg)` with a required
    parameter passes under `python3 file.py` (main() calls it with the arg) but ERRORS under
    pytest ('fixture not found') — a gate RED invisible to the main() path. Every function
    pytest can collect from these suites must be callable with zero arguments."""
    import ast
    bad = []
    for suite in SUITES:
        if not os.path.isfile(suite):
            continue
        tree = ast.parse(open(suite).read())
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
                nreq = (len(node.args.posonlyargs) + len(node.args.args)
                        - len(node.args.defaults))
                if nreq > 0:
                    bad.append("{}::{} requires {} arg(s)".format(
                        os.path.basename(suite), node.name, nreq))
    assert not bad, ("pytest-collectable test functions with required args (they ERROR "
                     "under pytest while main() passes): " + "; ".join(bad))


def _uninvoked_test_functions(source):
    """Module-level `def test_*` names never referenced elsewhere in their own module —
    the check()-style orphan: present for the AST (and for the engine's `test_passes`
    predicate) but never called by main(), so it never runs."""
    import ast
    tree = ast.parse(source)
    defs = {n.name for n in tree.body
            if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")}
    refs = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and not isinstance(node.ctx, ast.Store):
            refs.add(node.id)
        elif isinstance(node, ast.Attribute):
            refs.add(node.attr)
    return sorted(defs - refs)


def test_every_test_function_is_invoked():
    """lift/ratchet-briefs D0 (arch-F9): in check()-style suites a `def test_*` that
    main() never calls satisfies the engine's `test_passes` predicate (AST presence +
    unskipped + gate-green) while NEVER RUNNING — the third recurrence of the
    pytest-false-green class. Every module-level test_ function must be referenced inside
    its own module. This upgrades every current and future `test_passes` predicate in this
    repo from "exists" to "runs"."""
    orphans = []
    for suite in SUITES:
        if not os.path.isfile(suite):
            continue
        with open(suite) as fh:
            for name in _uninvoked_test_functions(fh.read()):
                orphans.append("{}::{}".format(os.path.basename(suite), name))
    assert not orphans, ("test functions that EXIST but are never invoked (they satisfy "
                         "test_passes while never running): " + "; ".join(orphans))


def test_runs_guard_can_detect_an_orphan():
    """§13 calibrate-the-checker: a PLANTED orphaned test_ function must be flagged."""
    planted = ("def test_real():\n    pass\n\n"
               "def test_orphan():\n    pass\n\n"
               "def main():\n    test_real()\n\n"
               "if __name__ == '__main__':\n    main()\n")
    found = _uninvoked_test_functions(planted)
    assert found == ["test_orphan"], found


def test_civerd_gate_script_is_the_real_gate():
    """The v1.15 class recurred one layer up: the aaa-guard made pytest honest about THESE
    suites, but the engine's gate command never ran calibration/'s script-style suites at
    all (pytest collects ~0 items from them) — check_scoreboard_integrity read as
    'essentially untested' while its 12 planted tests sat unexecuted. The fix is ONE blessed
    entrypoint the engine execs: scripts/civerd_gate.sh. Behaviorally: it must exist, run a
    suite directory, and FAIL when any suite in it fails."""
    gate = os.path.join(REPO, "scripts", "civerd_gate.sh")
    assert os.path.isfile(gate), "scripts/civerd_gate.sh missing — the gate has no blessed entrypoint"
    assert os.access(gate, os.X_OK), "civerd_gate.sh is not executable"
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "test_ok.py"), "w") as fh:
            fh.write("import sys\nsys.exit(0)\n")
        r = subprocess.run(["sh", gate, d], capture_output=True, text=True, timeout=60)
        assert r.returncode == 0, "gate script fails a passing suite dir: " + r.stdout + r.stderr
        with open(os.path.join(d, "test_bad.py"), "w") as fh:
            fh.write("import sys\nsys.exit(1)\n")
        r = subprocess.run(["sh", gate, d], capture_output=True, text=True, timeout=60)
        assert r.returncode != 0, "PLANTED failing suite not caught — the gate script is theater"


if __name__ == "__main__":
    # Standalone runner (2026-07-28): without this the file was INERT under `python3 file.py`
    # — the exact vehicle of the calibration/-gate false-green. Runs the cheap guards; the
    # expensive every-suite pass is exactly what the invoking gate loop already is, and
    # civerd_gate.sh runs calibration/test_harness.py explicitly. Failure propagates via a
    # bare assert (uncaught -> exit 1) — deliberately NO exit call, per the H5 guard: an
    # assert cannot fake a passing suite, an exit call can.
    failures = []
    for fn in (test_guard_can_detect_a_failing_suite,
               test_no_pytest_uncollectable_test_functions,
               test_every_test_function_is_invoked,
               test_runs_guard_can_detect_an_orphan,
               test_civerd_gate_script_is_the_real_gate):
        try:
            fn()
            print("  ok   - " + fn.__name__)
        except AssertionError as e:
            failures.append("{}: {}".format(fn.__name__, e))
            print("  FAIL - " + fn.__name__)
    assert not failures, "\n".join(failures)
    print("aaa guards green (every-suite pass is the invoking gate loop itself)")
