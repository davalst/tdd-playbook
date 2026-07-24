#!/usr/bin/env python3
"""Planted-input calibration for bin/with_snapshot.py (mechanical revert safety).

Per §13: the check must be able to FAIL. A planted un-reverted change that verify calls
clean is a blocking failure of the wrapper. Self-contained, no pytest. Run:
    python3 tests/test_with_snapshot.py
"""
import os
import subprocess
import sys
import tempfile

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "bin", "with_snapshot.py")

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def run(cwd, *args):
    return subprocess.run([sys.executable, BIN, *args],
                          capture_output=True, text=True, cwd=cwd, timeout=30)


def make_repo(d):
    def git(*a):
        subprocess.run(["git", *a], cwd=d, capture_output=True, text=True)
    git("init", "-q")
    git("config", "user.email", "t@t")
    git("config", "user.name", "t")
    with open(os.path.join(d, "mod.py"), "w") as fh:
        fh.write("def f():\n    return 1\n")
    git("add", "-A")
    git("commit", "-qm", "init")


def main():
    print("with_snapshot calibration")

    with tempfile.TemporaryDirectory() as d:
        make_repo(d)

        # clean begin -> verify cycle passes
        p = run(d, "begin")
        check("begin records", p.returncode == 0 and "recorded" in p.stdout, (p.returncode, p.stderr))
        p = run(d, "verify")
        check("clean tree verifies", p.returncode == 0 and "clean" in p.stdout, (p.returncode, p.stderr))

        # verify without begin -> loud failure (no silent pass)
        p = run(d, "verify")
        check("verify without snapshot fails loudly", p.returncode == 1 and "NO SNAPSHOT" in p.stderr,
              (p.returncode, p.stderr))

        # PLANTED: un-reverted plant must be caught
        run(d, "begin")
        with open(os.path.join(d, "mod.py"), "w") as fh:
            fh.write("def f():\n    return 2\n")   # the plant, never reverted
        p = run(d, "verify")
        check("planted un-reverted change is caught",
              p.returncode == 1 and "NOT RESTORED" in p.stderr, (p.returncode, p.stderr))
        # failure keeps the snapshot for forensics -> restoring then re-verifying passes
        with open(os.path.join(d, "mod.py"), "w") as fh:
            fh.write("def f():\n    return 1\n")
        p = run(d, "verify")
        check("restore then re-verify passes", p.returncode == 0, (p.returncode, p.stderr))

        # PLANTED: a stray NEW file (e.g. crashed agent's scratch) is caught
        run(d, "begin")
        with open(os.path.join(d, "stray.tmp"), "w") as fh:
            fh.write("leftover")
        p = run(d, "verify")
        check("stray new file is caught", p.returncode == 1 and "stray.tmp" in p.stderr,
              (p.returncode, p.stderr))
        os.remove(os.path.join(d, "stray.tmp"))
        run(d, "verify")

        # pre-existing dirt is FINE as long as it's identical at verify time
        with open(os.path.join(d, "mod.py"), "a") as fh:
            fh.write("# wip\n")
        run(d, "begin")
        p = run(d, "verify")
        check("pre-existing dirt preserved verifies clean", p.returncode == 0, (p.returncode, p.stderr))

        # PLANTED: same file dirty before and after but with DIFFERENT content -> caught
        run(d, "begin")  # tree currently has '# wip' appended
        with open(os.path.join(d, "mod.py"), "a") as fh:
            fh.write("# extra line the agent forgot to remove\n")
        p = run(d, "verify")
        check("content drift within an already-dirty file is caught",
              p.returncode == 1 and "CONTENT differs" in p.stderr, (p.returncode, p.stderr))

    # ---- preflight: refuse a revert-based pass over uncommitted tracked work (v1.8.1)
    with tempfile.TemporaryDirectory() as d3:
        make_repo(d3)

        # clean committed tree -> preflight passes (safe for a git-checkout revert)
        p = run(d3, "preflight")
        check("preflight clean tree passes", p.returncode == 0 and "preflight clean" in p.stdout,
              (p.returncode, p.stdout, p.stderr))

        # PLANTED: uncommitted TRACKED change -> refuse loudly (a checkout would clobber it)
        with open(os.path.join(d3, "mod.py"), "w") as fh:
            fh.write("def f():\n    return 99  # uncommitted work\n")
        p = run(d3, "preflight")
        check("preflight refuses uncommitted tracked change",
              p.returncode == 1 and "REFUSING" in p.stderr and "mod.py" in p.stderr,
              (p.returncode, p.stderr))

        # staged-but-uncommitted also refused (a checkout HEAD -- . would clobber it)
        subprocess.run(["git", "add", "mod.py"], cwd=d3, capture_output=True, text=True)
        p = run(d3, "preflight")
        check("preflight refuses staged uncommitted change", p.returncode == 1,
              (p.returncode, p.stderr))

        # commit it -> clean again -> preflight passes
        subprocess.run(["git", "commit", "-qm", "work"], cwd=d3, capture_output=True, text=True)
        p = run(d3, "preflight")
        check("preflight passes once committed", p.returncode == 0, (p.returncode, p.stderr))

        # untracked-only files do NOT block (git checkout leaves them alone)
        with open(os.path.join(d3, "scratch.tmp"), "w") as fh:
            fh.write("untracked")
        p = run(d3, "preflight")
        check("preflight ignores untracked-only files", p.returncode == 0,
              (p.returncode, p.stdout, p.stderr))

    # not a git repo -> usage error, not a crash
    with tempfile.TemporaryDirectory() as d2:
        p = run(d2, "begin")
        check("non-repo exits 2", p.returncode == 2 and "not a git repository" in p.stderr,
              (p.returncode, p.stderr))

    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
