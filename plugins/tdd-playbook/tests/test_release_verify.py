#!/usr/bin/env python3
"""Planted-input calibration for scripts/release_verify.py — the executable release gate (D5).

The security property: there is NO path to a release tag without a green signed verdict for the
exact SHA. This proves it — a red verdict refuses (exit 1) and creates no tag; only a green one
clears; the poll loop is deterministic (no real sleep); and no bypass flag exists.
Self-contained, stdlib only. Run:  python3 tests/test_release_verify.py
"""
import atexit
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))              # plugins/tdd-playbook/tests
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))  # repo root
SCRIPT = os.path.join(REPO, "scripts", "release_verify.py")
LEDGER = os.path.join(HERE, "fixtures", "civerd_verdicts.jsonl")
REAL_SHA = "31fa8ac4f0b31e5cd2e3a0523d2d2eacbc8c5e9b"
sys.path.insert(0, os.path.join(REPO, "scripts"))
import release_verify as R  # noqa: E402


def _mirror_with_era_pin():
    """A tmp mirror of release_verify + the verifier tree whose roster pin is scoped to
    the golden ledger's era. The SHIPPED verifier has no override (that is the point);
    green-path orchestration is proven against the mirror, refusal against the real one.
    Returns the mirrored release_verify.py path."""
    td = tempfile.mkdtemp(prefix="rv-mirror-")
    atexit.register(shutil.rmtree, td, ignore_errors=True)
    os.makedirs(os.path.join(td, "scripts"))
    shutil.copy2(SCRIPT, os.path.join(td, "scripts", "release_verify.py"))
    shutil.copytree(os.path.join(REPO, "plugins", "tdd-playbook", "bin"),
                    os.path.join(td, "plugins", "tdd-playbook", "bin"))
    vb = os.path.join(td, "plugins", "tdd-playbook", "bin", "verify_verdict.py")
    src = open(vb).read()
    assert "EXPECTED_REQUIRED" in src, "roster pin missing from verify_verdict.py"
    src = re.sub(r"EXPECTED_REQUIRED = \([^)]*\)",
                 'EXPECTED_REQUIRED = ("deps", "tests", "venv")', src, count=1)
    src = re.sub(r"EXPECTED_PRESENT = \([^)]*\)", "EXPECTED_PRESENT = ()", src, count=1)
    with open(vb, "w") as fh:
        fh.write(src)
    return os.path.join(td, "scripts", "release_verify.py")

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True, timeout=60)


def main():
    print("test_release_verify — no tag without a green verdict")
    HUGE = "999999999999"  # deterministic freshness; policy tested in test_verify_verdict

    # RED: unknown SHA -> refused, exit 1, and the word REFUSED (never a silent tag)
    p = run("--sha", "deadbeef", "--ledger", LEDGER, "--max-age-s", HUGE)
    check("red verdict -> exit 1", p.returncode == 1, (p.returncode, p.stderr))
    check("red verdict -> REFUSED, tag NOT created", "REFUSED" in p.stderr and "NOT created" in p.stderr)

    # v1.24 ROSTER PIN reaches the TAG PATH: the SHIPPED script over the golden ledger
    # (signed, green, but pre-dataflow roster) must refuse — no tag on a shrunk roster
    p = run("--sha", REAL_SHA, "--ledger", LEDGER, "--max-age-s", HUGE, "--dry-run")
    check("roster shrink -> REFUSED at the tag path (exit 1, named)",
          p.returncode == 1 and "roster_shrink" in (p.stderr + p.stdout),
          (p.returncode, p.stdout, p.stderr))

    # GREEN paths: proven against the era-scoped mirror (no override exists in the
    # shipped verifier — a real green needs a full-roster signed verdict, which the
    # engine only started emitting 2026-08-03)
    mirror = _mirror_with_era_pin()

    def mrun(*args):
        return subprocess.run([sys.executable, mirror, *args], capture_output=True,
                              text=True, timeout=60)

    # GREEN + --dry-run: verifies, reports the tag it WOULD create, creates nothing
    p = mrun("--sha", REAL_SHA, "--ledger", LEDGER, "--max-age-s", HUGE, "--dry-run")
    check("green + dry-run -> exit 0", p.returncode == 0, (p.returncode, p.stderr))
    check("green + dry-run -> 'would create tag'", "would create tag" in p.stdout, p.stdout)

    # --no-tag also verifies without tagging
    p = mrun("--sha", REAL_SHA, "--ledger", LEDGER, "--max-age-s", HUGE, "--no-tag")
    check("green + no-tag -> exit 0, no tag", p.returncode == 0 and "skipped: no-tag" in p.stdout)

    # deterministic poll: a permanently-red verify loops to the deadline WITHOUT real sleep,
    # then returns red. Injected clock advances one unit per call; sleep records calls.
    ticks = {"t": 0}

    def clock():
        ticks["t"] += 1
        return ticks["t"]

    slept = []
    ok, _ = R.verify_with_wait("deadbeef", 10 ** 12, LEDGER, wait_s=3, poll_s=99,
                               sleep=lambda s: slept.append(s), clock=clock)
    check("wait loop on red returns not-ok", ok is False)
    check("wait loop polled >1 time then gave up", len(slept) >= 1, slept)
    check("wait loop never called real time.sleep (injected)", all(s == 99 for s in slept))

    # green resolves immediately (no polling needed) — era-scoped mirror module, since
    # the real pin correctly refuses the golden ledger's roster
    import importlib.util
    spec = importlib.util.spec_from_file_location("release_verify_mirror", mirror)
    MR = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(MR)
    slept2 = []
    ok, _ = MR.verify_with_wait(REAL_SHA, 10 ** 12, LEDGER, wait_s=3, poll_s=99,
                                sleep=lambda s: slept2.append(s), clock=clock)
    check("green resolves without polling", ok is True and slept2 == [], slept2)

    # no bypass flag defined
    src = open(SCRIPT).read()
    defines_bypass = any(
        "add_argument(" in ln and ('"--force"' in ln or "'--force'" in ln
                                   or '"--override"' in ln or "'--override'" in ln)
        for ln in src.splitlines()
    )
    check("no --force/--override bypass defined", not defines_bypass)

    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
