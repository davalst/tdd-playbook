#!/usr/bin/env python3
"""mutation_run — runs a scoped mutation pass with its preflight ON THE EXECUTION PATH.

SKILL §4 has required a preflight for a long time, stated in three places (§4, commands/mutate.md,
the mutation-runner brief). In a downstream three-hour session on 2026-08-18 it was skipped anyway
and four runs produced ONE score: #2 died on a RED baseline, #3 timed out at 1800s because the
baseline had grown by four suites and the timeout was never resized. ~1.5 of 3 hours, to two
checks costing thirty seconds.

§10 says why writing it a fourth time would not help: "Trust gates must fire AUTOMATICALLY on the
diffs that can break them — 'remember to run it' is the honor-system seam §13 calls gameable."
So this INVOKES the mutation tool. A tool that checks and advises is another document.

WHAT IT COVERS: §4's (b) collection and (c) green baseline. Roster integrity (a) and tracer
attribution (d) remain the operator's, unchanged in the brief. This ADDS; it replaces no rule.

SCOPE: pytest + mutmut only, and it refuses anything else rather than guessing a denominator.

CORRECTED 2026-08-19 after a script-adversary review returned UNSAFE(9) on the first draft. The
findings are load-bearing and each is now a test:
  * the draft never invoked mutmut — it printed advice and exited 0 under four documents saying
    the pass "cannot be skipped". A wrapper that only prints is the failure its own docstring
    indicted.
  * `rc==0 and collected>0` is NOT evidence anything RAN. An all-skipped suite is green and
    collected and measures nothing; `--collect-only` defeats both checks at once AND collapses
    the measured baseline, so any scope would then look affordable. Outcome is parsed now, and
    `--collect-only` is refused.
  * every non-zero pytest exit was diagnosed as "RED baseline" citing a named plant, discarding
    what pytest actually said. rc 2/3/4/5 are not red suites. The real output is reported.
  * the shell-metacharacter blocklist defended against a shell that is never used, while
    refusing legitimate node ids like `test_p[<lambda>0]`. shlex now, and the blocklist covers
    what actually breaks a run.
  * the child inherited stdin (an invisible hang behind capture_output) and `subprocess.run`'s
    timeout kills only the direct child, orphaning xdist workers — the origin session's 15-minute
    cost, reproduced by construction. New session + process-group kill now.
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import signal
import subprocess
import sys
import time

_COLLECTED = re.compile(r"collected (\d+) item")
# The OUTCOME, not the collection. "5 passed", "3 failed, 2 passed", "no tests ran".
_PASSED = re.compile(r"(\d+) passed")
_FAILED = re.compile(r"(\d+) (?:failed|error)")
_NO_TESTS = re.compile(r"no tests ran", re.I)
# A summary that exists but reports no passes — "700 skipped in 1s" — is ZERO passed, which is a
# different (and more useful) refusal than "I could not read the summary".
_OTHER_OUTCOME = re.compile(r"\d+ (?:skipped|deselected|xfailed|xpassed|warning)")
# Args that make a "green baseline" meaningless because nothing executes.
_NON_EXECUTING = ("--collect-only", "--co")


def parse_collected(text):
    """Collected count, or None for UNKNOWN. Never coerced to zero — unmeasured is not empty."""
    m = _COLLECTED.search(text or "")
    return int(m.group(1)) if m else None


def parse_passed(text):
    """Tests that actually PASSED, or None if the summary is unreadable. Collection is not
    execution: 700 skipped tests are green and collected and measure nothing."""
    if _NO_TESTS.search(text or ""):
        return 0
    m = _PASSED.search(text or "")
    if m:
        return int(m.group(1))
    return 0 if _OTHER_OUTCOME.search(text or "") else None


def forbidden_composition(suite_args):
    """Why these args cannot serve as a baseline, or None.

    Deliberately NOT a shell-metacharacter blocklist: the suite runs as an argv list and never
    reaches a shell, so `;`/`>`/backtick have no meaning here — while `test_p[<lambda>0]` is a
    real pytest node id the old blocklist refused. What matters is args under which nothing
    executes, because those defeat the check itself."""
    try:
        parts = shlex.split(suite_args or "")
    except ValueError as exc:
        return "cannot parse --suite-args ({}); quote it as you would for a shell".format(exc)
    for part in parts:
        if part in _NON_EXECUTING:
            return ("refusing `{}` in --suite-args: it collects without executing, so a GREEN "
                    "baseline would prove nothing and the measured time would make any scope "
                    "look affordable".format(part))
    return None


def projection_problem(mutants, baseline_seconds, max_minutes, factor=1.0):
    """Refuse an unaffordable pass BEFORE it starts, naming the projection.

    STATED LIMIT: this is only as good as the measured baseline. A near-instant suite makes
    every scope look affordable — which is precisely why `--collect-only` is refused upstream,
    and why a baseline that collected tests but passed none is refused rather than timed. Those
    two refusals are what keep this number honest; the projection alone cannot police itself."""
    projected = (mutants * baseline_seconds * factor) / 60.0
    if projected > max_minutes:
        return ("refusing before the expensive pass: {} mutants x {:.1f}s measured baseline "
                "projects ~{} minutes, over the {}-minute budget. Raise --max-minutes, narrow "
                "--scope, or speed the suite — but know the number first"
                .format(mutants, baseline_seconds, round(projected), max_minutes))
    return None


def run_bounded(argv, timeout, run=None):
    """Run in its OWN process group with stdin closed, and kill the GROUP on timeout.

    subprocess.run's timeout kills the direct child only; pytest-xdist workers and anything the
    tests spawned survive as orphans. stdin is closed because capture_output hides a prompt, so
    a suite that hits breakpoint()/--pdb would hang invisibly for the whole budget."""
    if run is not None:                      # injected for tests
        return run(argv, capture_output=True, text=True, timeout=timeout)
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, start_new_session=True)
    try:
        out, _ = proc.communicate(timeout=timeout)
        return subprocess.CompletedProcess(argv, proc.returncode, out, "")
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()
        proc.communicate()
        raise


def baseline(suite_argv, run=None, timeout=None):
    """(ok, why, seconds, collected) — green AND actually executed."""
    started = time.time()
    try:
        proc = run_bounded(suite_argv, timeout, run=run)
    except subprocess.TimeoutExpired:
        return False, ("baseline exceeded its {}s bound — UNMEASURED, never assumed green "
                       "(child process group killed)".format(timeout)), time.time() - started, None
    except (OSError, ValueError) as exc:
        return False, "baseline suite could not be run: {}".format(exc), 0.0, None
    seconds = time.time() - started
    text = (proc.stdout or "") + (proc.stderr or "")
    tail = text.strip()[-1200:]
    if proc.returncode != 0:
        failed = _FAILED.search(text)
        cause = ("the suite is RED ({} failing) — a mutation score measured against it is "
                 "meaningless (the `red-baseline-false-green` plant)".format(failed.group(1))
                 if failed else
                 "pytest exited {} — that is NOT necessarily a red suite (2=interrupted, "
                 "3=internal, 4=usage/ini, 5=no tests). What pytest said:".format(proc.returncode))
        return False, "baseline refused — {}\n{}".format(cause, tail), seconds, None
    collected = parse_collected(text)
    if collected is None:
        return False, ("UNKNOWN collection — no pytest `collected N items` line. This wrapper "
                       "supports pytest + mutmut only and fails closed rather than guessing a "
                       "denominator. Output was:\n{}".format(tail)), seconds, None
    if collected == 0:
        return False, ("zero tests collected — a vacuous killing suite reports 0 survivors and "
                       "sails every guard (§4: `generated > 0 != measured`)"), seconds, 0
    passed = parse_passed(text)
    if passed is None:
        return False, ("UNKNOWN outcome — {} collected but no `N passed` summary, so nothing "
                       "proves a test EXECUTED. Output was:\n{}".format(collected, tail)), \
            seconds, collected
    if passed == 0:
        return False, ("{} collected but ZERO passed — a suite that executes nothing is green "
                       "and measures nothing (all-skipped is the common shape). UNMEASURED, "
                       "never green".format(collected)), seconds, collected
    return True, "", seconds, collected


def mutmut_argv(scope, suite_args):
    return ["mutmut", "run", "--paths-to-mutate", scope, "--runner",
            "python -m pytest -x -q " + suite_args]


def main(argv=None, run=None):
    parser = argparse.ArgumentParser(
        prog="mutation_run.py",
        description=("Run a scoped mutation pass with its preflight ON the execution path. "
                     "pytest + mutmut ONLY; other stacks are refused, never guessed. Covers "
                     "SKILL §4's collection and green-baseline checks; roster integrity and "
                     "tracer attribution remain the operator's."))
    parser.add_argument("--scope", required=True)
    parser.add_argument("--suite-args", default="")
    parser.add_argument("--max-minutes", type=int, default=None)
    parser.add_argument("--baseline-timeout", type=int, default=None,
                        help="bound for the CHEAP baseline (default: a fifth of --max-minutes)")
    parser.add_argument("--expected-mutants", type=int, default=None,
                        help="enables the projection; without it the hard bound still applies")
    parser.add_argument("--factor", type=float, default=1.0)
    parser.add_argument("--dry-run", action="store_true", help="preflight only")
    args = parser.parse_args(argv)

    problem = forbidden_composition(args.suite_args)
    if problem:
        print("mutation_run: " + problem, file=sys.stderr)
        return 1
    if args.max_minutes is None:
        print("mutation_run: --max-minutes is REQUIRED. An unbounded pass is how a run times "
              "out at 1800s having measured nothing.", file=sys.stderr)
        return 1

    bound = args.baseline_timeout or max(60, (args.max_minutes * 60) // 5)
    suite_argv = [sys.executable, "-m", "pytest"] + shlex.split(args.suite_args)
    ok, why, seconds, collected = baseline(suite_argv, run=run, timeout=bound)
    if not ok:
        print("mutation_run: REFUSED — {}".format(why), file=sys.stderr)
        return 1
    print("mutation_run: baseline GREEN — {} collected, {:.1f}s measured".format(collected, seconds))

    if args.expected_mutants is not None:
        proj = projection_problem(args.expected_mutants, seconds, args.max_minutes, args.factor)
        if proj:
            print("mutation_run: REFUSED — " + proj, file=sys.stderr)
            return 1
    else:
        print("mutation_run: projection SKIPPED (no --expected-mutants) — unmeasured, not "
              "assumed affordable; the {}-minute hard bound still applies".format(args.max_minutes))
    if args.dry_run:
        return 0

    mut = mutmut_argv(args.scope, args.suite_args)
    print("mutation_run: invoking " + " ".join(mut))
    try:
        proc = run_bounded(mut, args.max_minutes * 60, run=run)
    except subprocess.TimeoutExpired:
        print("mutation_run: mutation pass exceeded {} minutes — UNMEASURED; process group "
              "killed, no orphans".format(args.max_minutes), file=sys.stderr)
        return 1
    except OSError as exc:
        print("mutation_run: mutmut could not be run ({}) — refusing rather than reporting a "
              "score nothing produced".format(exc), file=sys.stderr)
        return 1
    sys.stdout.write(proc.stdout or "")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
