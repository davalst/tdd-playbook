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
import tempfile
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
    # v1.52.0 (Q2): --suite-args is deprecated; the non-executing-arg refusal now guards mutmut's
    # own pytest_add_cli_args, which the baseline replays. Driven in-process with an injected
    # reader (the reader seam has its own real-mutmut test) and a recording run hook.
    m = load()
    seen = []
    rec = lambda argv, **kw: (seen.append(list(argv)), subprocess.CompletedProcess(argv, 0, "collected 5 items\n5 passed in 1s\n", ""))[1]
    bad_cfg = lambda cwd: m.EffectiveConfig(config_file="setup.cfg", source_paths=["app/"],
                                             pytest_add_cli_args=["--collect-only"])
    rc = m.main(["--scope", "app/", "--max-minutes", "5"], run=rec, config_reader=bad_cfg)
    check("non-executing args inside pytest_add_cli_args are refused BEFORE any baseline runs",
          rc == 1 and seen == [], (rc, seen))

    proc = subprocess.run([sys.executable, BIN, "--scope", "x"],
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
    # the config READER is injected (a stdlib-only CI has no mutmut to ask); the reader's own
    # seam is driven against the real tool in test_effective_config_comes_from_mutmut_itself
    reader = lambda cwd: m.EffectiveConfig(config_file="setup.cfg", source_paths=["app/"])
    cwd = os.getcwd()
    try:
        os.chdir(root)
        rc = m.main(["--scope", "app/", "--max-minutes", "30"], run=rec,
                    config_reader=reader)
        check("main() exits 0 on a clean pass", rc == 0, rc)
        check("main() ACTUALLY INVOKES mutmut (not a print)",
              any(a and a[0] == "mutmut" for a in seen), seen)
        check("the invoked argv is mutmut 3.x's REAL shape (no 2.x flags)",
              all("--paths-to-mutate" not in a and "--runner" not in a
                  for a in seen if a and a[0] == "mutmut"), seen)

        # a scope that disagrees with mutmut's config is refused: mutating a different tree
        # than the one asked about is a score about the wrong code
        seen.clear()
        rc = m.main(["--scope", "other/", "--max-minutes", "30"], run=rec,
                    config_reader=reader)
        check("PLANTED: --scope disagreeing with mutmut's config is REFUSED", rc == 1, rc)
        check("...and mutmut was never reached", not any(a and a[0] == "mutmut" for a in seen), seen)

        # the projection is WIRED, not merely unit-tested
        seen.clear()
        rc = m.main(["--scope", "app/", "--max-minutes", "1",
                     "--expected-mutants", "5000", "--factor", "1000000"], run=rec,
                    config_reader=reader)
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
                   "before trusting a change to mutmut_argv/effective_mutmut_config")
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
    #    (v1.52.0: the reader is now mutmut's OWN loader — `effective_mutmut_config` — the old
    #    cwd-bound `mutmut_config_scope` with its tox.ini branch is deleted.)
    try:
        m.effective_mutmut_config(root)
    except m.ConfigProblem as exc:
        check("REAL: unconfigured mutmut is REFUSED, not invoked", True)
        check("...and the refusal hands over the exact fix", "source_paths" in str(exc), str(exc))
    else:
        check("REAL: unconfigured mutmut is REFUSED, not invoked", False, "no refusal")

    # 2. configured -> the scope comes from mutmut's own config, because 3.x has no flag for it
    with open(os.path.join(root, "setup.cfg"), "w") as fh:
        fh.write("[mutmut]\nsource_paths=app/\n")
    cfg = m.effective_mutmut_config(root)
    check("REAL: configured scope is read from mutmut's own loader",
          cfg.source_paths == ["app"] and cfg.config_file == "setup.cfg", vars(cfg))

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


def test_wrapper_does_not_claim_scoped():
    """v1.51.2 (Codex source-verification of 1.51.1): the docstring stopped claiming 'scoped' but
    the CLI description still said 'Run a scoped mutation pass', and the projection refusal still
    advised 'narrow --scope' — a flag that CHECKS the configured scope and narrows nothing. A
    wrapper must not advise a remedy it cannot perform."""
    m = load()
    import argparse, io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            m.main(["--help"])
        except SystemExit:
            pass
    help_text = buf.getvalue()
    check("CLI description does not say 'scoped'", "scoped mutation pass" not in help_text, help_text[:200])
    check("CLI description says what --scope actually does (check, not narrow)",
          "not narrow" in help_text or "does NOT narrow" in help_text, help_text[:300])
    why = m.projection_problem(10000, 2.0, 5) or ""
    check("projection refusal no longer advises 'narrow --scope'", "narrow --scope" not in why
          and "narrow\n" not in why and "narrow " not in why, why)
    check("projection refusal names remedies the wrapper can act on",
          "--max-minutes" in why and ("only_mutate" in why or "configured scope" in why.lower()
                                      or "config" in why.lower()), why)


def test_run_bounded_deadline_grace_and_cwd_with_real_children():
    """v1.52.0 D0 / Q3: `run_bounded(argv, deadline_s, cwd=, grace_s=)` — SIGINT to the group at
    deadline-grace, SIGKILL at the deadline, never deadline+grace; `cwd` honoured (mutmut's
    config discovery is cwd-relative). Driven by REAL children: the injected `run` hook returns
    before the Popen path, so a hook-driven test of this exercises nothing."""
    import tempfile, textwrap, time as _t
    m = load()
    d = tempfile.mkdtemp()
    # cwd is honoured
    p = m.run_bounded([sys.executable, "-c", "import os;print(os.getcwd())"], 10, cwd=d, grace_s=1)
    check("run_bounded: cwd is honoured", os.path.realpath(p.stdout.strip()) == os.path.realpath(d), p.stdout)
    check("run_bounded: a prompt child is not marked timed out", getattr(p, "timed_out", None) is False, vars(p))
    graceful = os.path.join(d, "graceful.py")
    with open(graceful, "w") as fh:
        fh.write(textwrap.dedent("""
            import signal, sys, time
            signal.signal(signal.SIGINT, lambda *_: sys.exit(3))
            print("started", flush=True)
            time.sleep(60)
        """))
    t0 = _t.monotonic()
    p = m.run_bounded([sys.executable, graceful], 4, cwd=d, grace_s=2)
    el = _t.monotonic() - t0
    check("graceful child: SIGINT at deadline-grace, child exits with its own code",
          p.returncode == 3 and p.timed_out is True, (p.returncode, getattr(p, "timed_out", None)))
    check("graceful child: returned well before the deadline (SIGINT at ~2s, not at 4s+2s)",
          1.5 <= el < 4.0, el)
    check("graceful child: output captured up to the interrupt", "started" in (p.stdout or ""), p.stdout)
    stubborn = os.path.join(d, "stubborn.py")
    with open(stubborn, "w") as fh:
        fh.write(textwrap.dedent("""
            import signal, time
            signal.signal(signal.SIGINT, signal.SIG_IGN)
            print("started", flush=True)
            time.sleep(60)
        """))
    t0 = _t.monotonic()
    p = m.run_bounded([sys.executable, stubborn], 4, cwd=d, grace_s=2)
    el = _t.monotonic() - t0
    check("stubborn child: SIGKILL at the absolute deadline, not deadline+grace",
          p.timed_out is True and p.returncode < 0 and 3.5 <= el < 6.0, (p.returncode, el))
    check("run_bounded: elapsed seconds are reported", isinstance(getattr(p, "elapsed_s", None), float), vars(p))


def _fixture_repo(pyproject=None, setup_cfg=None, tox_ini=None, scopes=None, extra_files=()):
    """A committed fixture repo: app/calc.py + tests/test_calc.py, optional mutmut configs and
    an optional .tdd-playbook/mutation-scopes.json. Returns its root."""
    import tempfile, textwrap, json
    root = tempfile.mkdtemp()
    os.makedirs(os.path.join(root, "app")); os.makedirs(os.path.join(root, "tests"))
    with open(os.path.join(root, "app", "calc.py"), "w") as fh:
        fh.write("def add(a, b):\n    return a + b\n\n\ndef sub(a, b):\n    return a - b\n")
    with open(os.path.join(root, "app", "fmt.py"), "w") as fh:
        fh.write("def show(x):\n    return str(x)\n")
    with open(os.path.join(root, "tests", "test_calc.py"), "w") as fh:
        fh.write(textwrap.dedent("""
            from app.calc import add, sub
            def test_add():
                assert add(2, 2) == 4
            def test_sub():
                assert sub(3, 1) == 2
        """))
    with open(os.path.join(root, "tests", "test_fmt.py"), "w") as fh:
        fh.write("from app.fmt import show\ndef test_show():\n    assert show(1) == '1'\n")
    if pyproject is not None:
        with open(os.path.join(root, "pyproject.toml"), "w") as fh:
            fh.write(pyproject)
    if setup_cfg is not None:
        with open(os.path.join(root, "setup.cfg"), "w") as fh:
            fh.write(setup_cfg)
    if tox_ini is not None:
        with open(os.path.join(root, "tox.ini"), "w") as fh:
            fh.write(tox_ini)
    if scopes is not None:
        os.makedirs(os.path.join(root, ".tdd-playbook"))
        with open(os.path.join(root, ".tdd-playbook", "mutation-scopes.json"), "w") as fh:
            fh.write(scopes if isinstance(scopes, str) else json.dumps(scopes, indent=1))
    for rel, body in extra_files:
        os.makedirs(os.path.dirname(os.path.join(root, rel)), exist_ok=True)
        with open(os.path.join(root, rel), "w") as fh:
            fh.write(body)
    for a in (["init", "-q"], ["config", "user.email", "t@t"], ["config", "user.name", "t"],
              ["add", "-A"], ["commit", "-q", "-m", "init"]):
        subprocess.run(["git", "-C", root] + a, capture_output=True, text=True, check=True)
    return root


def test_effective_config_comes_from_mutmut_itself():
    """v1.52.0 D3 reader: the effective mutmut config is learned FROM MUTMUT (its own loader,
    cwd=repo), never re-implemented. Motivating defects (architecture + integration adversaries,
    2026-09-09): the old reader (`mutmut_config_scope`, rev 60bee33) listed setup.cfg before
    pyproject — the reverse of mutmut's precedence — and consulted tox.ini, which mutmut never
    reads; inert while read-only, lethal once the reader writes."""
    import shutil
    m = load()
    if shutil.which("mutmut") is None:
        unmeasured("effective-config seam (mutmut loader, precedence, tox.ini refusal)",
                   "mutmut is not installed here")
        return
    both = _fixture_repo(pyproject='[tool.mutmut]\nsource_paths = ["app"]\npytest_add_cli_args = ["-p", "no:cacheprovider"]\n',
                         setup_cfg="[mutmut]\nsource_paths=WRONG\n")
    cfg = m.effective_mutmut_config(both)
    check("pyproject [tool.mutmut] WINS over setup.cfg (mutmut's precedence, not ours)",
          cfg.config_file == "pyproject.toml" and cfg.source_paths == ["app"], vars(cfg))
    check("pytest_add_cli_args is READ (D4 must replay it)",
          cfg.pytest_add_cli_args == ["-p", "no:cacheprovider"], cfg.pytest_add_cli_args)
    cfg_only = m.effective_mutmut_config(_fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\ntests_dir=tests/\n"))
    check("setup.cfg is the fallback and is named as the file", cfg_only.config_file == "setup.cfg", vars(cfg_only))
    check("legacy tests_dir is surfaced separately, because mutmut APPENDS it to the selection (Q4)",
          cfg_only.legacy_tests_dir == ["tests/"] and "tests/" in cfg_only.selection, vars(cfg_only))
    try:
        m.effective_mutmut_config(_fixture_repo(tox_ini="[mutmut]\nsource_paths=app\n"))
    except m.ConfigProblem as exc:
        check("tox.ini-only is REFUSED BY NAME (mutmut never reads it)", "tox.ini" in str(exc), str(exc))
    else:
        check("tox.ini-only is REFUSED BY NAME (mutmut never reads it)", False, "no refusal")
    try:
        m.effective_mutmut_config(_fixture_repo())
    except m.ConfigProblem as exc:
        check("unconfigured repo is refused with the exact fix", "source_paths" in str(exc), str(exc))
    else:
        check("unconfigured repo is refused with the exact fix", False, "no refusal")
    check("the old cwd-bound reader with the tox.ini branch is GONE",
          not hasattr(m, "mutmut_config_scope"), dir(m))


def test_scope_mapping_is_the_roster():
    """v1.52.0 D1: `.tdd-playbook/mutation-scopes.json` selects exact sources + pytest selectors
    + a cost line; validated as FACTS (realpath containment against mutmut's parsed
    source_paths, globs against tracked files), never by substring — the `--scope b` replay is
    the motivating artifact (rev 60bee33, mutation_run.py:276 `args.scope not in configured`)."""
    import shutil, json
    m = load()
    if shutil.which("mutmut") is None:
        unmeasured("scope mapping against the real effective config", "mutmut is not installed here")
        return
    good = {"calc": {"sources": ["app/calc.py"], "tests": ["tests/test_calc.py"], "cost": "a survivor here costs money"},
            "all": {"sources": ["app/*"], "tests": ["tests/"], "cost": "everything"}}
    root = _fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\ndo_not_mutate=app/fmt.py\n", scopes=good)
    cfg = m.effective_mutmut_config(root)
    sc = m.resolve_scope(root, "calc", cfg)
    check("a valid scope resolves to exact tracked files + selectors + cost",
          sc.sources == ["app/calc.py"] and sc.tests == ["tests/test_calc.py"] and sc.cost.startswith("a survivor"), vars(sc))
    check("mapping sha256 and counts travel with the scope (anti-narrowing record)",
          len(sc.mapping_sha256) == 64 and sc.source_count == 1, vars(sc))
    try:
        m.resolve_scope(root, "all", cfg)
    except m.ScopeError as exc:
        check("a glob that reaches a do_not_mutate file is refused (mutmut would silently generate zero)",
              "do_not_mutate" in str(exc) and "app/fmt.py" in str(exc), str(exc))
    else:
        check("a glob that reaches a do_not_mutate file is refused", False)
    try:
        m.resolve_scope(root, "nope", cfg)
    except m.ScopeError as exc:
        check("unknown scope name is refused LISTING the names", "calc" in str(exc) and "all" in str(exc), str(exc))
    else:
        check("unknown scope name is refused LISTING the names", False)
    # PLANTED: the substring class — 'b' is inside 'app' but is not a path under source_paths
    for bad_sources, label in ([["b"], "substring of a source path"], [["../app/calc.py"], "parent traversal"],
                               [[os.path.join(root, "app", "calc.py")], "absolute path"],
                               [["tests/test_calc.py"], "outside mutmut's source_paths"],
                               [["app/nothing*"], "glob matching no tracked file"], [[], "empty sources"]):
        r2 = _fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\n",
                           scopes={"x": {"sources": bad_sources, "tests": ["tests/"], "cost": "c"}})
        try:
            m.resolve_scope(r2, "x", m.effective_mutmut_config(r2))
        except m.ScopeError:
            check("PLANTED sources {} are refused".format(label), True)
        else:
            check("PLANTED sources {} are refused".format(label), False, bad_sources)
    # SURVIVOR-DRIVEN (Phase 2 targeted mutants, 2026-09-09): a containment check weakened toward
    # substring survived because every planted source was refused EARLIER (untracked); this
    # tracked file's path CONTAINS the source dir's name and sits outside it.
    r2b = _fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\n",
                        scopes={"x": {"sources": ["tests/app_helpers.py"], "tests": ["tests/"], "cost": "c"}},
                        extra_files=[("tests/app_helpers.py", "X = 1\n")])
    try:
        m.resolve_scope(r2b, "x", m.effective_mutmut_config(r2b))
    except m.ScopeError as exc:
        check("PLANTED tracked file whose path contains the source dir NAME but is outside it is refused",
              "outside" in str(exc), str(exc))
    else:
        check("PLANTED tracked file whose path contains the source dir NAME but is outside it is refused", False)
    for bad_entry, label in ([{"sources": ["app/calc.py"], "tests": [], "cost": "c"}, "empty tests"],
                             [{"sources": ["app/calc.py"], "tests": ["tests/"]}, "missing cost line"],
                             # SURVIVOR-DRIVEN: the blank-cost branch was reachable only past the
                             # missing-key check; a present-but-blank cost must refuse on its own
                             [{"sources": ["app/calc.py"], "tests": ["tests/"], "cost": "   "}, "blank cost line"]):
        r3 = _fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\n", scopes={"x": bad_entry})
        try:
            m.resolve_scope(r3, "x", m.effective_mutmut_config(r3))
        except m.ScopeError:
            check("PLANTED entry with {} is refused".format(label), True)
        else:
            check("PLANTED entry with {} is refused".format(label), False)
    # duplicate keys: json.loads is last-wins and silent — the loader must refuse
    r4 = _fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\n",
                       scopes='{"x": {"sources": ["app/calc.py"], "tests": ["tests/"], "cost": "c"},\n "x": {"sources": ["app/fmt.py"], "tests": ["tests/"], "cost": "c"}}')
    try:
        m.load_scopes(r4)
    except m.ScopeError as exc:
        check("PLANTED duplicate scope name is refused (JSON last-wins would hide it)", "duplicate" in str(exc).lower(), str(exc))
    else:
        check("PLANTED duplicate scope name is refused", False)
    try:
        m.load_scopes(_fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\n"))
    except m.ScopeError as exc:
        check("missing mapping is refused WITH a scaffold to copy (never written)",
              "mutation-scopes.json" in str(exc) and '"sources"' in str(exc) and '"cost"' in str(exc), str(exc))
    else:
        check("missing mapping is refused WITH a scaffold", False)
    # roster gap: the selector collects nothing -> the §4b amended wording, not a whole-folder fallback
    r5 = _fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\n",
                       scopes={"calc": {"sources": ["app/calc.py"], "tests": ["tests/test_calc.py::test_nothing"], "cost": "c"}})
    n, problem = m.collect_selection(r5, ["tests/test_calc.py::test_nothing"], [])
    check("a selector collecting zero tests is reported as a ROSTER gap, by wording",
          n == 0 and problem and "roster gap" in problem.lower() and "not a gate defect" in problem.lower(), (n, problem))
    n, problem = m.collect_selection(r5, ["tests/test_calc.py"], ["-p", "no:cacheprovider"])
    check("collect_selection counts the mapped tests with pytest_add_cli_args replayed", n == 2 and problem is None, (n, problem))


def test_narrow_config_rewrites_a_copy_and_reads_back():
    """v1.52.0 D3 writer (Q4): line-anchored rewrite of the file mutmut actually reads, in a
    DISPOSABLE copy only — set only_mutate + pytest_add_cli_args_test_selection (inserting
    absent keys), neutralise legacy tests_dir (mutmut appends it to the selection), leave
    paths_to_mutate as the deprecated root, preserve do_not_mutate and pytest_add_cli_args —
    then READ BACK through mutmut and assert the keys took. Unsupported shapes are refused with
    a concrete migration instruction, and the legacy list shape is named as one of them."""
    import shutil, hashlib
    m = load()
    if shutil.which("mutmut") is None:
        unmeasured("config writer + read-back against real mutmut", "mutmut is not installed here")
        return

    def sha(path):
        with open(path, "rb") as fh:
            return hashlib.sha256(fh.read()).hexdigest()

    scopes = {"calc": {"sources": ["app/calc.py"], "tests": ["tests/test_calc.py"], "cost": "c"}}
    # --- setup.cfg with legacy tests_dir and an existing only_mutate and pytest_add_cli_args
    root = _fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\ntests_dir=tests/\nonly_mutate=app/fmt.py\n"
                                   "do_not_mutate=app/never.py\npytest_add_cli_args=-p\n    no:cacheprovider\n",
                         scopes=scopes)
    cfg = m.effective_mutmut_config(root); sc = m.resolve_scope(root, "calc", cfg)
    copy = tempfile.mkdtemp(); shutil.rmtree(copy); shutil.copytree(root, copy)
    before = sha(os.path.join(root, "setup.cfg"))
    rep = m.narrow_config(copy, cfg, sc)
    after = m.effective_mutmut_config(copy)
    check("setup.cfg copy: only_mutate is the scope's sources (read back through mutmut)",
          after.only_mutate == ["app/calc.py"], vars(after))
    check("setup.cfg copy: selection is the scope's tests and legacy tests_dir no longer widens it",
          after.selection == ["tests/test_calc.py"] and after.legacy_tests_dir == [], vars(after))
    check("setup.cfg copy: do_not_mutate and pytest_add_cli_args preserved",
          after.do_not_mutate == ["app/never.py"] and after.pytest_add_cli_args == ["-p", "no:cacheprovider"], vars(after))
    check("the REAL config is untouched (sha256 equal)", sha(os.path.join(root, "setup.cfg")) == before)
    check("the report names the file, the keys set, and the neutralised tests_dir",
          rep.config_file == "setup.cfg" and "tests_dir" in " ".join(rep.notes) and rep.real_sha256 == before, vars(rep))

    # --- pyproject with the keys ABSENT: inserted; paths_to_mutate legacy root stays
    root2 = _fixture_repo(pyproject='[tool.mutmut]\npaths_to_mutate = ["app"]\npytest_add_cli_args = ["-p", "no:cacheprovider"]\n\n[tool.other]\nx = 1\n',
                          scopes=scopes)
    cfg2 = m.effective_mutmut_config(root2); sc2 = m.resolve_scope(root2, "calc", cfg2)
    copy2 = tempfile.mkdtemp(); shutil.rmtree(copy2); shutil.copytree(root2, copy2)
    m.narrow_config(copy2, cfg2, sc2)
    after2 = m.effective_mutmut_config(copy2)
    check("pyproject copy: absent keys are INSERTED under [tool.mutmut], not appended to another table",
          after2.only_mutate == ["app/calc.py"] and after2.selection == ["tests/test_calc.py"], vars(after2))
    check("pyproject copy: paths_to_mutate stays as the deprecated root; other tables untouched",
          after2.source_paths == ["app"] and "[tool.other]" in open(os.path.join(copy2, "pyproject.toml")).read())

    # --- unsupported shape: a multi-line array for a key we must rewrite -> refuse + migration text
    root3 = _fixture_repo(pyproject='[tool.mutmut]\nsource_paths = ["app"]\nonly_mutate = [\n  "app/fmt.py",  # keep\n]\n',
                          scopes=scopes)
    cfg3 = m.effective_mutmut_config(root3); sc3 = m.resolve_scope(root3, "calc", cfg3)
    copy3 = tempfile.mkdtemp(); shutil.rmtree(copy3); shutil.copytree(root3, copy3)
    try:
        m.narrow_config(copy3, cfg3, sc3)
    except m.ConfigProblem as exc:
        text = str(exc)
        check("multi-line array for a rewritten key is REFUSED (no general TOML writer)", True)
        check("...with a concrete migration instruction naming the key and the one-line form",
              "only_mutate" in text and "one line" in text.lower(), text)
        check("...and the legacy paths_to_mutate + tests_dir list shape is named as unsupported too",
              "tests_dir" in text and "paths_to_mutate" in text, text)
    else:
        check("multi-line array for a rewritten key is REFUSED", False, "no refusal")
    check("the real pyproject is untouched after a refusal",
          open(os.path.join(root3, "pyproject.toml")).read() == open(os.path.join(copy3, "pyproject.toml")).read())


def test_baseline_replays_pytest_add_cli_args_and_names_domination():
    """v1.52.0 D4 (Q2): the wrapper's baseline runs the SAME selection AND the same non-selection
    arguments mutmut will (`pytest_add_cli_args`); `--collect-only` there collapses the baseline
    and is refused; a baseline over a fifth of the budget is named as a GATE misconfiguration."""
    m = load()
    cfg = m.EffectiveConfig(config_file="setup.cfg", source_paths=["app"], pytest_add_cli_args=["-p", "no:cacheprovider", "-W", "error"])
    sc = m.Scope("calc", ["app/calc.py"], ["tests/test_calc.py", "tests/test_x.py::TestY"], "c", "0" * 64)
    argv = m.baseline_argv(cfg, sc, python="PY")
    check("baseline argv = python -m pytest + pytest_add_cli_args + mapped selectors, in that order",
          argv == ["PY", "-m", "pytest", "-p", "no:cacheprovider", "-W", "error", "tests/test_calc.py", "tests/test_x.py::TestY"], argv)
    bad = m.EffectiveConfig(config_file="setup.cfg", source_paths=["app"], pytest_add_cli_args=["--collect-only"])
    check("PLANTED: --collect-only inside pytest_add_cli_args is refused (it defeats the baseline)",
          m.forbidden_add_args(bad.pytest_add_cli_args) is not None)
    check("ordinary add args pass", m.forbidden_add_args(["-p", "no:cacheprovider"]) is None)
    msg = m.baseline_dominates(70.0, max_minutes=5)
    check("a baseline over a fifth of the budget is NAMED as the gate's misconfiguration, not the module's",
          msg and "GATE is misconfigured" in msg and "not the module" in msg, msg)
    check("a proportionate baseline is not flagged", m.baseline_dominates(10.0, max_minutes=5) is None)
    check("the share is reported as a number (for the record and the /mutate line)",
          abs(m.baseline_share(70.0, max_minutes=5) - 70.0 / 300.0) < 1e-9)


def test_suite_args_is_a_migration_refusal():
    """v1.52.0 Q2: `--suite-args` is deprecated OUTRIGHT — in this release it exists only to
    emit a migration refusal naming the mapping (selection) and mutmut's pytest_add_cli_args
    (non-selection options); removed next release."""
    m = load()
    why = m.suite_args_migration("tests/ -q")
    check("any --suite-args value is refused with the migration instruction",
          why and "mutation-scopes.json" in why and "pytest_add_cli_args" in why and "deprecated" in why.lower(), why)
    check("an empty --suite-args is not an error (the flag merely exists this release)",
          m.suite_args_migration("") is None)
    proc = subprocess.run([sys.executable, BIN, "--scope", "x", "--suite-args", "tests/", "--max-minutes", "5"],
                          capture_output=True, text=True, timeout=30)
    check("CLI: --suite-args refuses BEFORE any baseline or config read, by message",
          proc.returncode == 1 and "mutation-scopes.json" in proc.stderr, (proc.returncode, proc.stderr[:200]))


def _hold_lock_in_child(lock_path, seconds=30):
    """A REAL child process holding an exclusive flock on `lock_path` — liveness is the FACT
    that the lock is held, never a pid (F5)."""
    import textwrap
    code = textwrap.dedent("""
        import fcntl, sys, time
        fh = open(sys.argv[1], "a+")
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        print("held", flush=True)
        time.sleep(float(sys.argv[2]))
    """)
    p = subprocess.Popen([sys.executable, "-c", code, lock_path, str(seconds)],
                         stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == "held"
    return p


def test_literal_clean_and_disposable_worktree_lifecycle():
    """v1.52.0 D2 (Q5 literal clean, Q6 lock-first): refuse on ANY dirty tracked or non-ignored
    untracked file; one uniquely named detached worktree per run under the common dir; a
    provenance marker; a per-run flock as the liveness fact; remove exactly that worktree;
    a leftover path is never reused; cleanup failure names the retained path."""
    import shutil, json as _json
    m = load()
    root = _fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\n",
                         scopes={"calc": {"sources": ["app/calc.py"], "tests": ["tests/test_calc.py"], "cost": "c"}})
    ident = m.repo_identity(root)
    check("identity comes from host_contract.resolve_repository (root, common dir, state dir, head)",
          ident["root"] == os.path.realpath(root) and ident["state_dir"].endswith("tdd-playbook") and len(ident["head"]) == 40, ident)
    check("a clean committed tree passes the literal-clean check", m.check_clean(root) is None)
    with open(os.path.join(root, "tests", "conftest.py"), "w") as fh:
        fh.write("x = 1\n")
    why = m.check_clean(root)
    check("PLANTED untracked conftest.py (not a test_*.py, not under a selector) is REFUSED — literal clean",
          why and "tests/conftest.py" in why and "commit the kill test" in why.lower(), why)
    os.unlink(os.path.join(root, "tests", "conftest.py"))
    with open(os.path.join(root, "app", "calc.py"), "a") as fh:
        fh.write("# edit\n")
    why = m.check_clean(root)
    check("PLANTED dirty tracked file is REFUSED naming it", why and "app/calc.py" in why, why)
    subprocess.run(["git", "-C", root, "checkout", "--", "app/calc.py"], check=True)

    wt = m.Worktree.create(ident, run_id="run-a", scope_name="calc")
    try:
        check("worktree lives under <common>/tdd-playbook/mutation-worktrees/<run_id>",
              wt.path == os.path.join(ident["state_dir"], "mutation-worktrees", "run-a") and os.path.isdir(wt.path), wt.path)
        head_in_wt = subprocess.run(["git", "-C", wt.path, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        check("worktree is detached at the exact HEAD", head_in_wt == ident["head"] and
              subprocess.run(["git", "-C", wt.path, "symbolic-ref", "-q", "HEAD"], capture_output=True).returncode != 0)
        marker = _json.load(open(os.path.join(wt.path, ".tdd-playbook-mutation-run.json")))
        check("provenance marker carries run_id, scope, head, started",
              marker["run_id"] == "run-a" and marker["scope"] == "calc" and marker["head"] == ident["head"] and "started" in marker, marker)
        probe = subprocess.run([sys.executable, "-c",
                                "import fcntl,sys; fh=open(sys.argv[1],'a+');\n"
                                "try:\n fcntl.flock(fh.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB); print('free')\n"
                                "except OSError: print('held')", wt.lock_path], capture_output=True, text=True)
        check("the per-run lock is HELD for the run's life (another process cannot take it)",
              probe.stdout.strip() == "held", probe.stdout)
        try:
            m.Worktree.create(ident, run_id="run-a", scope_name="calc")
        except m.WorktreeProblem as exc:
            check("a leftover/duplicate path is REFUSED by name, never reused", "run-a" in str(exc), str(exc))
        else:
            check("a leftover/duplicate path is REFUSED by name, never reused", False)
    finally:
        wt.remove()
    check("remove() deletes exactly that worktree and its registration",
          not os.path.exists(wt.path) and "run-a" not in subprocess.run(["git", "-C", root, "worktree", "list"], capture_output=True, text=True).stdout)
    # cleanup failure: an injected failing remover -> CleanupFailed carrying the retained path
    wt2 = m.Worktree.create(ident, run_id="run-b", scope_name="calc")
    try:
        wt2.remove(runner=lambda argv: subprocess.CompletedProcess(argv, 1, "", "simulated: busy"))
    except m.CleanupFailed as exc:
        check("cleanup failure raises with the RETAINED path and the manual command",
              exc.path == wt2.path and "git worktree remove --force" in m.retained_line(exc.path) and exc.path in m.retained_line(exc.path), str(exc))
    else:
        check("cleanup failure raises with the RETAINED path", False)
    wt2.remove()


def test_repo_lock_and_stale_worktrees():
    """v1.52.0 D2b + Q6: one run per repository, enforced with an advisory lock acquired BEFORE
    listing or reaping; stale = marker-bearing AND lock-free; listing is the default, deletion
    only under --reap-stale; a live child's worktree is never touched; foreign dirs are named
    and left; a retained forensic path is never auto-deleted."""
    import shutil, json as _json
    m = load()
    root = _fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\n",
                         scopes={"calc": {"sources": ["app/calc.py"], "tests": ["tests/test_calc.py"], "cost": "c"}})
    ident = m.repo_identity(root)
    with m.repo_lock(ident, scope_name="calc", run_id="holder") as lock:
        check("repo lock file lives at <state>/mutation.lock", lock.path == os.path.join(ident["state_dir"], "mutation.lock"))
        probe = subprocess.run([sys.executable, BIN, "--scope", "calc", "--max-minutes", "5"],
                               cwd=root, capture_output=True, text=True, timeout=60)
        check("a second invocation REFUSES immediately, naming the holder's scope",
              probe.returncode == 1 and "another mutation run" in probe.stderr and "calc" in probe.stderr, probe.stderr[:300])
    # stale vs live vs foreign
    stale = m.Worktree.create(ident, run_id="stale-1", scope_name="calc"); stale.release_lock()
    live = m.Worktree.create(ident, run_id="live-1", scope_name="calc"); live.release_lock()
    child = _hold_lock_in_child(live.lock_path)
    foreign = os.path.join(ident["state_dir"], "mutation-worktrees", "not-ours"); os.makedirs(foreign)
    try:
        report = m.list_stale(ident)
        check("marker-bearing + lock-free is STALE", [w.run_id for w in report.stale] == ["stale-1"], vars(report))
        check("marker-bearing + lock HELD by a real process is LIVE, not stale", [w.run_id for w in report.live] == ["live-1"], vars(report))
        check("a dir without our marker is FOREIGN: named, never touched", report.foreign == [foreign], vars(report))
        text = m.stale_lines(report)
        check("default output LISTS stale worktrees with the exact manual command, deleting nothing",
              "stale-1" in text and "git worktree remove --force" in text and os.path.isdir(stale.path), text)
        reaped = m.reap_stale(ident, report)
        check("--reap-stale removes exactly the stale set", reaped == [stale.path] and not os.path.exists(stale.path)
              and os.path.isdir(live.path) and os.path.isdir(foreign), reaped)
        # a RETAINED forensic path is marked and never auto-reaped
        kept = m.Worktree.create(ident, run_id="kept-1", scope_name="calc"); kept.release_lock()
        m.mark_retained(kept.path, "simulated cleanup failure")
        report2 = m.list_stale(ident)
        check("a retained forensic path is listed separately and excluded from reaping",
              [w.run_id for w in report2.retained] == ["kept-1"] and not any(w.run_id == "kept-1" for w in report2.stale), vars(report2))
        check("reap_stale leaves the retained path", m.reap_stale(ident, report2) == [] and os.path.isdir(kept.path))
        kept.remove(force=True)
    finally:
        child.kill(); child.wait()
        for w in (live,):
            try:
                w.remove(force=True)
            except Exception:
                pass
        shutil.rmtree(foreign, ignore_errors=True)


def test_reset_plan_shared_scope_knows_the_mutation_artifacts():
    """v1.52.0 D2 reverse sweep: reset_plan --shared must plan the three new common-dir
    artifacts, else --shared reports clean while leaving them forever."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("reset_plan", os.path.join(os.path.dirname(BIN), "reset_plan.py"))
    rp = importlib.util.module_from_spec(spec); spec.loader.exec_module(rp)
    m = load()
    root = _fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\n")
    ident = m.repo_identity(root)
    for rel in ("mutation-worktrees", "mutation-runs"):
        os.makedirs(os.path.join(ident["state_dir"], rel), exist_ok=True)
    with open(os.path.join(ident["state_dir"], "mutation.lock"), "w") as fh:
        fh.write("")
    paths = {t["path"] for t in rp.plan(root, scopes=["shared"])}
    for rel in ("mutation-worktrees", "mutation-runs", "mutation.lock"):
        check("reset --shared plans {}".format(rel), os.path.join(ident["state_dir"], rel) in paths, sorted(paths))


def test_main_runs_both_halves_in_the_worktree_for_real():
    """v1.52.0 Phase 4 wiring, driven END TO END against the REAL mutmut: mapping -> literal
    clean -> repo lock -> worktree at HEAD -> narrowed copy config -> baseline in the worktree
    with pytest_add_cli_args -> mutmut in the worktree -> cleanup. The real config is untouched
    and no worktree is left behind."""
    import shutil, hashlib
    m = load()
    if shutil.which("mutmut") is None:
        unmeasured("end-to-end scoped run against real mutmut", "mutmut is not installed here")
        return
    root = _fixture_repo(setup_cfg="[mutmut]\nsource_paths=app\npytest_add_cli_args=-p\n    no:cacheprovider\n",
                         scopes={"calc": {"sources": ["app/calc.py"], "tests": ["tests/test_calc.py"], "cost": "c"}})
    before = hashlib.sha256(open(os.path.join(root, "setup.cfg"), "rb").read()).hexdigest()
    proc = subprocess.run([sys.executable, BIN, "--scope", "calc", "--max-minutes", "10"],
                          cwd=root, capture_output=True, text=True, timeout=900)
    out = proc.stdout + proc.stderr
    check("REAL: a scoped run completes green", proc.returncode == 0, out[-600:])
    check("REAL: the first lines name the scope, the worktree, and the narrowed config",
          "scope calc:" in out and "mutation-worktrees" in out and "only_mutate=['app/calc.py']" in out, out[:800])
    check("REAL: the baseline ran the mapped selection with pytest_add_cli_args replayed (2 tests collected)",
          "2 collected" in out, out[:800])
    check("REAL: the real config is untouched",
          hashlib.sha256(open(os.path.join(root, "setup.cfg"), "rb").read()).hexdigest() == before)
    ident = m.repo_identity(root)
    left = os.listdir(os.path.join(ident["state_dir"], "mutation-worktrees")) if os.path.isdir(os.path.join(ident["state_dir"], "mutation-worktrees")) else []
    check("REAL: no worktree is left behind and none is registered",
          left == [] and "mutation-worktrees" not in subprocess.run(["git", "-C", root, "worktree", "list"], capture_output=True, text=True).stdout, left)
    check("REAL: mutmut reported mutation results for the narrowed module only",
          "app/calc.py" in out and "app/fmt.py" not in out, out[-600:])


def main():
    print("mutation_run preflight calibration")
    for fn in (test_collection_parse_fails_closed, test_refuses_args_under_which_nothing_executes,
               test_projection_refuses_before_the_expensive_pass,
               test_preflight_refuses_red_baseline_and_empty_collection,
               test_cli_is_the_real_seam, test_main_actually_invokes_mutmut,
               test_against_REAL_mutmut_not_a_mock,
               test_wrapper_does_not_claim_scoped,
               test_run_bounded_deadline_grace_and_cwd_with_real_children,
               test_effective_config_comes_from_mutmut_itself, test_scope_mapping_is_the_roster,
               test_narrow_config_rewrites_a_copy_and_reads_back,
               test_baseline_replays_pytest_add_cli_args_and_names_domination,
               test_suite_args_is_a_migration_refusal,
               test_literal_clean_and_disposable_worktree_lifecycle,
               test_repo_lock_and_stale_worktrees,
               test_reset_plan_shared_scope_knows_the_mutation_artifacts,
               test_main_runs_both_halves_in_the_worktree_for_real):
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
