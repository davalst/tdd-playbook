#!/usr/bin/env python3
"""Planted-input calibration for gate_yield (R4-lean: the retirement instrument).

The doctrine only ever measured whether gates are strong enough — never whether they still
earn their friction. gate_yield derives per-gate yield from the ONE event log the hooks and
the lock already write, rolls it up once per calibration cycle into a COMMITTED record, and
prints retirement candidates only from >=2 committed cycles (a fresh clone must never make a
healthy gate look like a zero-yield candidate). Absent data is UNMEASURED, never a fabricated
zero. Self-contained, no pytest. Run: python3 tests/test_gate_yield.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PLUGIN))
GY = os.path.join(PLUGIN, "bin", "gate_yield.py")

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def run_gy(*args, env_extra=None):
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("TDD_PLAYBOOK_"):
            del env[k]
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, GY, *args], capture_output=True, text=True,
                          env=env, timeout=60)


def seed_raw(path, lines):
    with open(path, "w") as fh:
        for ln in lines:
            fh.write((json.dumps(ln) if isinstance(ln, dict) else ln) + "\n")


def main():
    print("gate_yield calibration")
    if not os.path.isfile(GY):
        check("bin/gate_yield.py exists", False, "missing")
        print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
        sys.exit(1)

    with tempfile.TemporaryDirectory() as d:
        raw = os.path.join(d, "raw.jsonl")
        md = os.path.join(d, "gate_yield.md")

        # rollup aggregates the raw log into one committed row per gate, then drains it
        seed_raw(raw, [
            {"ts": "t", "source": "hook", "gate": "testweaken", "event": "block",
             "findings": 1},
            {"ts": "t", "source": "hook", "gate": "testweaken", "event": "block",
             "findings": 2},
            {"ts": "t", "source": "hook", "gate": "flaky", "event": "warn", "findings": 1},
            {"ts": "t", "source": "hook", "gate": "testlock", "event": "block",
             "findings": 1},
            "this line is not json (PLANTED corruption)",
            {"ts": "t", "source": "testlock", "gate": "testlock", "event": "override",
             "reason": "r"},
        ])
        p = run_gy("rollup", "--log", raw, "--md", md, "--date", "2026-07-27")
        body = open(md).read() if os.path.isfile(md) else ""
        check("rollup: exit 0 with per-gate rows",
              p.returncode == 0 and "| 2026-07-27 | testweaken | 2 | 0 | 0 |" in body
              and "| 2026-07-27 | testlock | 1 | 0 | 1 |" in body
              and "| 2026-07-27 | flaky | 0 | 1 | 0 |" in body,
              (p.returncode, body, p.stdout, p.stderr))
        check("rollup: PLANTED corrupt line skipped with a warning, run not failed",
              "corrupt" in (p.stdout + p.stderr).lower()
              or "skipped" in (p.stdout + p.stderr).lower(), (p.stdout, p.stderr))
        check("rollup: raw log drained (cycles stay disjoint)",
              not os.path.isfile(raw) or open(raw).read().strip() == "",
              open(raw).read() if os.path.isfile(raw) else "gone")

        # a second cycle appends (committed record only GROWS)
        seed_raw(raw, [
            {"ts": "t", "source": "hook", "gate": "testlock", "event": "block",
             "findings": 1},
            {"ts": "t", "source": "testlock", "gate": "testlock", "event": "override",
             "reason": "r"},
        ])
        run_gy("rollup", "--log", raw, "--md", md, "--date", "2026-08-10")
        body = open(md).read()
        check("rollup: second cycle appends, first cycle intact",
              "| 2026-07-27 | testweaken |" in body
              and "| 2026-08-10 | testlock | 1 | 0 | 1 |" in body, body)

        # candidates: testlock has 2 cycles of friction with every block overridden ->
        # candidate; testweaken has friction but no adjudication -> NOT a candidate;
        # a gate absent from the record is UNMEASURED, never zero-yield
        p = run_gy("candidates", "--md", md)
        check("candidates: 2 cycles all-overridden -> retirement candidate",
              p.returncode == 0 and "RETIREMENT CANDIDATE" in p.stdout
              and "testlock" in p.stdout, (p.returncode, p.stdout, p.stderr))
        check("candidates: unadjudicated friction is NOT a candidate",
              "RETIREMENT CANDIDATE: testweaken" not in p.stdout, p.stdout)
        check("candidates: absent gates stated as unmeasured, not zero",
              "unmeasured" in p.stdout.lower(), p.stdout)

    with tempfile.TemporaryDirectory() as d:
        md = os.path.join(d, "gate_yield.md")
        with open(md, "w") as fh:
            fh.write("| date | gate | blocks | warns | overrides |\n|---|---|---|---|---|\n"
                     "| 2026-08-10 | testlock | 3 | 0 | 3 |\n")
        p = run_gy("candidates", "--md", md)
        check("candidates: ONE cycle is never enough (fresh-clone protection)",
              p.returncode == 0 and "RETIREMENT CANDIDATE" not in p.stdout, p.stdout)

        p = run_gy("candidates", "--md", os.path.join(d, "nope.md"))
        check("candidates: no committed record -> unmeasured, exit 0",
              p.returncode == 0 and "unmeasured" in p.stdout.lower(),
              (p.returncode, p.stdout))

        p = run_gy("rollup", "--log", os.path.join(d, "nope.jsonl"), "--md", md,
                   "--date", "2026-08-11")
        check("rollup: no raw log -> unmeasured note, exit 0, record untouched",
              p.returncode == 0 and "unmeasured" in p.stdout.lower()
              and "2026-08-11" not in open(md).read(), (p.returncode, p.stdout))

    # run_calibration carries the candidate report on the existing cadence (never fails the
    # run): a stubbed scenario run must end with a yield section either way
    with tempfile.TemporaryDirectory() as d:
        stub = os.path.join(d, "claude-stub")
        with open(stub, "w") as fh:
            fh.write("#!/bin/sh\ncat <<'EOF'\n**VERDICT: REFUTED** — authorize() is called "
                     "at cli.py:15 and cli.py:21.\nClaims checked: 1 · confirmed: 0 · "
                     "refuted: 1\nRecommendation: revise.\nEOF\n")
        os.chmod(stub, 0o755)
        md = os.path.join(d, "gate_yield.md")
        with open(md, "w") as fh:
            fh.write("| date | gate | blocks | warns | overrides |\n|---|---|---|---|---|\n"
                     "| 2026-07-27 | testlock | 3 | 0 | 3 |\n"
                     "| 2026-08-10 | testlock | 2 | 0 | 2 |\n")
        env = dict(os.environ)
        env["TDD_PLAYBOOK_YIELD_MD"] = md
        # isolation: never drain a developer's real raw log through this test
        env["TDD_PLAYBOOK_YIELD_LOG"] = os.path.join(d, "no-raw.jsonl")
        p = subprocess.run(
            [sys.executable, os.path.join(REPO, "calibration", "run_calibration.py"),
             "--scenario", "false-negative-claim", "--claude-bin", stub, "--history", "",
             "--repeat", "1"],
            capture_output=True, text=True, env=env, timeout=300)
        check("run_calibration: prints the retirement-candidate mirror of DECAY WARNING",
              p.returncode == 0 and "RETIREMENT CANDIDATE" in p.stdout and
              "testlock" in p.stdout, (p.returncode, p.stdout[-600:]))
        env["TDD_PLAYBOOK_YIELD_MD"] = os.path.join(d, "absent.md")
        p = subprocess.run(
            [sys.executable, os.path.join(REPO, "calibration", "run_calibration.py"),
             "--scenario", "false-negative-claim", "--claude-bin", stub, "--history", "",
             "--repeat", "1"],
            capture_output=True, text=True, env=env, timeout=300)
        check("run_calibration: absent yield record -> unmeasured line, run still green",
              p.returncode == 0 and "unmeasured" in p.stdout.lower(),
              (p.returncode, p.stdout[-400:]))

    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
