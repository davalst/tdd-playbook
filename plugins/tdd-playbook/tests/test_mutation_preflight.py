#!/usr/bin/env python3
"""Planted-input calibration for bin/mutation_run.py — the mutation preflight, made mechanical.

MOTIVATING ARTIFACTS, frozen (a downstream three-hour session, 2026-08-18): four mutation runs
produced ONE score. Run #2 died because the baseline suite was RED — mutmut could not collect.
Run #3 timed out at 1800s because the baseline had grown by four suites and the timeout was
never resized. Both were preventable in ~30 seconds, and BOTH were already covered by written
doctrine in three places each (SKILL §4's PREFLIGHT, commands/mutate.md, the mutation-runner
brief). The rules existed and were not reached for.

WHY THIS IS A WRAPPER AND NOT A CHECKER. SKILL §10 already states the governing rule: "Trust
gates must fire AUTOMATICALLY on the diffs that can break them — 'remember to run it' is the
honor-system seam §13 calls gameable." A script that CHECKS and advises is another document; the
first draft of this deliverable printed a measured baseline and hoped somebody resized the
timeout, which is the same honor system wearing a lab coat. So mutation_run RUNS the pass: the
preflight cannot be skipped, because it is on the execution path.

SCOPE, stated rather than implied: pytest + mutmut ONLY. Other stacks report collection counts
in incompatible words (unittest "Ran N tests", jest, stryker), and a generic parser confidently
extracts the wrong denominator. Unknown output FAILS CLOSED — unknown is never assumed non-zero.

Self-contained, no pytest. Run: python3 tests/test_mutation_preflight.py
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.realpath(__file__))
PLUGIN = os.path.dirname(HERE)
BIN = os.path.join(PLUGIN, "bin", "mutation_run.py")
_r = {"pass": 0, "fail": 0, "unmeasured": 0}


def unmeasured(name, why):
    """A third state, because pass/fail cannot express 'the seam was not reachable here'.

    Counting an unreachable seam as a PASS is the vacuous green this repo exists to refuse;
    counting it as a FAIL makes the gate permanently red on a runner that legitimately lacks a
    third-party tool (CI here installs nothing — the suites are stdlib-only by design). So it is
    neither: it is reported loudly, in its own column, and the summary line carries it."""
    _r["unmeasured"] += 1
    print("  UNMEASURED - {}  ({})".format(name, why))


def check(name, cond, detail=""):
    if cond:
        _r["pass"] += 1
        print("  ok   - " + name)
    else:
        _r["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def load():
    spec = importlib.util.spec_from_file_location("mutation_run", BIN)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_collection_parse_fails_closed():
    """Absent or unreadable collection output is UNKNOWN, never assumed non-zero."""
    m = load()
    check("parses pytest's collected line", m.parse_collected("collected 737 items") == 737)
    check("parses the deselected variant",
          m.parse_collected("collected 900 items / 163 deselected / 737 selected") == 900)
    check("PLANTED: no collection line at all -> None (unknown), not 0 and not a guess",
          m.parse_collected("ok\nsome other tool's output\n") is None)
    check("PLANTED: unittest output is NOT parsed as pytest (scope is stated, not guessed)",
          m.parse_collected("Ran 42 tests in 1.2s\n\nOK") is None)
    check("zero collected is a real zero, distinct from unknown",
          m.parse_collected("collected 0 items") == 0)


def test_refuses_args_under_which_nothing_executes():
    """CORRECTED after review: the first draft blocklisted shell metacharacters — defending
    against a shell that is never used (the suite runs as an argv list), while REFUSING the real
    pytest node id `test_p[<lambda>0]` and MISSING `--collect-only`, which is the arg that
    actually defeats the check: it collects without executing, so the baseline is green, the
    count is non-zero, and the measured time collapses so any scope looks affordable."""
    m = load()
    for bad in ("tests/ --collect-only", "--co tests/"):
        check("PLANTED: non-executing args refused: {!r}".format(bad),
              m.forbidden_composition(bad) is not None, bad)
    for ok in ("tests/ -q", "-k 'not slow' tests/unit", "tests/test_a.py::test_b",
               "tests/test_lam.py::test_p[<lambda>0]"):
        check("legitimate pytest args allowed: {!r}".format(ok),
              m.forbidden_composition(ok) is None, ok)
    check("quoted -k survives shlex instead of being shredded by .split()",
          m_shlex_ok(m, "-k 'not slow' tests/"), "quoted expression must stay one arg")


def m_shlex_ok(m, s):
    import shlex
    return "not slow" in shlex.split(s)


def test_projection_refuses_before_the_expensive_pass():
    """Run #3, frozen: the baseline grew and the timeout did not. Caught in seconds."""
    m = load()
    # 500 mutants x 44s baseline = ~367 min. A 30-minute budget cannot hold it.
    over = m.projection_problem(mutants=500, baseline_seconds=44.0, max_minutes=30, factor=1.0)
    check("PLANTED: an unaffordable pass is REFUSED before starting", over is not None)
    check("...and the refusal names the projection, not just 'too long'",
          over and ("367" in over or "366" in over), over)
    ok = m.projection_problem(mutants=10, baseline_seconds=2.0, max_minutes=30, factor=1.0)
    check("an affordable pass proceeds", ok is None, ok)
    check("projection scales with the MEASURED baseline (the run-#3 fix)",
          m.projection_problem(mutants=10, baseline_seconds=600.0, max_minutes=30,
                               factor=1.0) is not None)


def test_preflight_refuses_red_baseline_and_empty_collection():
    """Run #2, frozen: a RED baseline. `red-baseline-false-green` is this exact plant."""
    m = load()

    def fake(rc, out):
        return lambda argv, **kw: subprocess.CompletedProcess(argv, rc, out, "")

    ok, why, *_ = m.baseline(["pytest"], run=fake(0, "collected 737 items\n737 passed in 44s\n"))
    check("green baseline that actually EXECUTED passes", ok, why)

    # CORRECTED after review: collection is not execution. This is the deepest finding —
    # 700 skipped tests are green, collected, and measure nothing.
    ok, why, *_ = m.baseline(["pytest"], run=fake(0, "collected 700 items\n700 skipped in 1s\n"))
    check("PLANTED: all-SKIPPED suite is refused (green, collected, executed nothing)",
          not ok, why)
    check("...and the refusal says ZERO passed rather than reporting green",
          why and "ZERO passed" in why, why)
    ok, why, *_ = m.baseline(["pytest"], run=fake(0, "collected 5 items\n"))
    check("PLANTED: collected but NO outcome summary -> UNKNOWN, refused", not ok, why)

    ok, why, *_ = m.baseline(["pytest"], run=fake(1, "collected 737 items\n3 failed, 734 passed\n"))
    check("PLANTED: RED baseline is refused", not ok, why)
    check("...and cites the plant ONLY when tests actually failed",
          why and "red-baseline-false-green" in why, why)

    # CORRECTED after review: rc 2/3/4/5 are not red suites. The first draft diagnosed every
    # non-zero exit as a red baseline citing a named plant, and discarded what pytest said —
    # sending the operator to debug a green suite after `.split()` shredded a quoted -k.
    ok, why, *_ = m.baseline(["pytest"], run=fake(4, "ERROR: unrecognized arguments: slow\n"))
    check("PLANTED: a USAGE error is not reported as a red baseline", not ok, why)
    check("...and the real pytest output is included, not discarded",
          why and "unrecognized arguments" in why, why)
    check("...and it does NOT falsely cite the plant",
          why and "red-baseline-false-green" not in why, why)

    ok, why, *_ = m.baseline(["pytest"], run=fake(0, "collected 0 items\n"))
    check("PLANTED: zero collected is refused (vacuous killing suite)", not ok, why)

    ok, why, *_ = m.baseline(["pytest"], run=fake(0, "no idea what this tool printed\n"))
    check("PLANTED: unknown collection FAILS CLOSED", not ok, why)
    check("...and says UNKNOWN rather than claiming zero",
          why and "unknown" in why.lower(), why)


def test_cli_is_the_real_seam():
    """A subprocess-only contract needs an in-process twin AND the real executable (§8)."""
    proc = subprocess.run([sys.executable, BIN, "--help"], capture_output=True, text=True,
                          timeout=30)
    check("CLI runs and documents itself", proc.returncode == 0, proc.stderr[:200])
    # CORRECTED after review: grepping --help for "mutmut" asserts the docstring mentions it —
    # §1's own "a grep matches your own docstring". Assert the BEHAVIOUR instead (below).

    # CORRECTED after review: exit==1 alone also matches a crash/ImportError, so this asserted
    # the script had failed, not that it had REFUSED. Assert the message.
    proc = subprocess.run([sys.executable, BIN, "--scope", "x", "--suite-args",
                           "tests/ --collect-only"], capture_output=True, text=True, timeout=30)
    check("CLI refuses non-executing args, by MESSAGE not just exit code",
          proc.returncode == 1 and "collects without executing" in proc.stderr,
          (proc.returncode, proc.stderr[:160]))

    proc = subprocess.run([sys.executable, BIN, "--scope", "x", "--suite-args", "tests/"],
                          capture_output=True, text=True, timeout=30)
    check("CLI REQUIRES an explicit budget rather than inventing one",
          proc.returncode != 0 and "max-minutes" in (proc.stdout + proc.stderr),
          (proc.returncode, (proc.stdout + proc.stderr)[:160]))


def test_main_actually_invokes_mutmut():
    """THE finding that made the first draft UNSAFE: main() printed advice and returned 0 while
    four documents said the pass "cannot be skipped, because running the pass IS running the
    preflight". A wrapper that only prints is the failure its own docstring indicts.

    Note what this test needs that the first version did not: a real `[mutmut]` config. mutmut
    3.x takes no --paths-to-mutate flag, so an unconfigured repo is REFUSED before invocation —
    which is why this must set up the same conditions production requires, rather than mocking
    them away."""
    import tempfile
    m = load()
    seen = []

    def rec(argv, **kw):
        seen.append(list(argv))
        # A DELIBERATE 10ms floor. baseline() measures real wall-clock, and an instantly
        # returning double can elapse 0.0 on a coarse clock — which made the projection
        # assertion below depend on timer granularity. It flaked exactly once, which is once
        # more than §7 allows: a test that passes on timing is not a test. The sleep makes the
        # measured baseline deterministic without faking the measurement itself.
        time.sleep(0.01)
        seen_pytest = "pytest" in " ".join(argv)
        out = "collected 5 items\n5 passed in 1s\n" if seen_pytest else "mutmut done\n"
        return subprocess.CompletedProcess(argv, 0, out, "")

    root = tempfile.mkdtemp()
    with open(os.path.join(root, "setup.cfg"), "w") as fh:
        fh.write("[mutmut]\nsource_paths=app/\n")
    cwd = os.getcwd()
    try:
        os.chdir(root)
        rc = m.main(["--scope", "app/", "--suite-args", "tests/", "--max-minutes", "30"], run=rec)
        check("main() exits 0 on a clean pass", rc == 0, rc)
        check("main() ACTUALLY INVOKES mutmut (not a print)",
              any(a and a[0] == "mutmut" for a in seen), seen)
        check("the invoked argv is mutmut 3.x's REAL shape (no 2.x flags)",
              all("--paths-to-mutate" not in a and "--runner" not in a
                  for a in seen if a and a[0] == "mutmut"), seen)

        # a scope that disagrees with mutmut's config is refused: mutating a different tree
        # than the one asked about is a score about the wrong code
        seen.clear()
        rc = m.main(["--scope", "other/", "--suite-args", "tests/", "--max-minutes", "30"], run=rec)
        check("PLANTED: --scope disagreeing with mutmut's config is REFUSED", rc == 1, rc)
        check("...and mutmut was never reached", not any(a and a[0] == "mutmut" for a in seen), seen)

        # the projection is WIRED, not merely unit-tested
        seen.clear()
        rc = m.main(["--scope", "app/", "--suite-args", "tests/", "--max-minutes", "1",
                     "--expected-mutants", "5000", "--factor", "1000000"], run=rec)
        check("an unaffordable projection REFUSES before invoking mutmut", rc == 1, rc)
        check("...and mutmut was never reached",
              not any(a and a[0] == "mutmut" for a in seen), seen)
    finally:
        os.chdir(cwd)


def test_against_REAL_mutmut_not_a_mock():
    """The seam I do not own. Everything above injects `run`, and an injected double accepts any
    argv — which is exactly how the first draft shipped mutmut 2.x flags (`--paths-to-mutate`,
    `--runner`) that the installed 3.x binary rejects outright. H9: a double must never supply a
    seam production lacks. So this drives the REAL tool end to end.

    Skips only if mutmut is genuinely absent, and says so rather than passing quietly."""
    import shutil, tempfile, textwrap
    m = load()
    if shutil.which("mutmut") is None:
        unmeasured("real-mutmut seam (argv shape, config contract, end-to-end run)",
                   "mutmut is not installed here; this suite is stdlib-only and CI installs "
                   "nothing. The seam IS exercised wherever mutmut exists — run this locally "
                   "before trusting a change to mutmut_argv/mutmut_config_scope")
        return

    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "app")); os.makedirs(os.path.join(root, "tests"))
    with open(os.path.join(root, "app", "calc.py"), "w") as fh:
        fh.write("def add(a, b):\n    return a + b\n")
    with open(os.path.join(root, "tests", "test_calc.py"), "w") as fh:
        fh.write(textwrap.dedent("""
            from app.calc import add
            def test_add():
                assert add(2, 2) == 4
                assert add(-1, 1) == 0
        """))

    # 1. NO config -> refuse, naming the fix. This is the real first-run failure: with no
    #    [mutmut] section even `mutmut --version` dies "Could not figure out where the code is".
    scope, problem = m.mutmut_config_scope(root)
    check("REAL: unconfigured mutmut is REFUSED, not invoked", scope is None and problem)
    check("...and the refusal hands over the exact fix",
          problem and "source_paths" in problem, problem)

    # 2. configured -> the scope comes from config, because 3.x has no flag for it
    with open(os.path.join(root, "setup.cfg"), "w") as fh:
        fh.write("[mutmut]\nsource_paths=app/\n")
    scope, problem = m.mutmut_config_scope(root)
    check("REAL: configured scope is read from mutmut's own config",
          scope == "app/" and problem is None, (scope, problem))

    # 3. the argv we build is one the REAL binary accepts (2.x flags would fail here)
    argv = m.mutmut_argv(max_children=2)
    proc = subprocess.run(argv + ["--help"], cwd=root, capture_output=True, text=True, timeout=120)
    check("REAL: our argv shape is accepted by the installed mutmut", proc.returncode == 0,
          (proc.returncode, (proc.stdout + proc.stderr)[-200:]))

    # 4. end to end: the real tool runs and reports a killed mutant
    proc = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=300)
    out = proc.stdout + proc.stderr
    check("REAL: mutmut actually ran to completion", proc.returncode == 0,
          (proc.returncode, out[-200:]))
    check("REAL: it reports mutation results (a killed mutant), not just a clean exit",
          "mutations/second" in out or "1/1" in out, out[-200:])


def main():
    print("mutation_run preflight calibration")
    for fn in (test_collection_parse_fails_closed, test_refuses_args_under_which_nothing_executes,
               test_projection_refuses_before_the_expensive_pass,
               test_preflight_refuses_red_baseline_and_empty_collection,
               test_cli_is_the_real_seam, test_main_actually_invokes_mutmut,
               test_against_REAL_mutmut_not_a_mock):
        print("\n[{}]".format(fn.__name__))
        fn()
    tail = (", {} UNMEASURED".format(_r["unmeasured"]) if _r["unmeasured"] else "")
    print("\n{} passed, {} failed{}".format(_r["pass"], _r["fail"], tail))
    if _r["unmeasured"]:
        print("UNMEASURED is not passed: the real-tool seam was not reachable in this "
              "environment. Green here does NOT mean the mutmut contract was verified.")
    sys.exit(1 if _r["fail"] else 0)


if __name__ == "__main__":
    main()
