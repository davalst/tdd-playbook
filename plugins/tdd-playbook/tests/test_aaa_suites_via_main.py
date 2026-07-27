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
REPO = os.path.dirname(os.path.dirname(HERE))

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
