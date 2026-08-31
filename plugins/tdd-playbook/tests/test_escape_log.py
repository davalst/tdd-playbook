#!/usr/bin/env python3
"""Behavioural tests for the escape ledger. Isolated via TDD_PLAYBOOK_YIELD_LOG (G5)."""
import json, os, subprocess, sys, tempfile

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "bin", "escape_log.py")
_r = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _r["pass"] += 1; print("  ok   - %s" % name)
    else:
        _r["fail"] += 1; print("  FAIL - %s  %s" % (name, detail))


def run(log, *args):
    env = dict(os.environ, TDD_PLAYBOOK_YIELD_LOG=log)
    return subprocess.run([sys.executable, BIN] + list(args), capture_output=True,
                          text=True, env=env)


def test_escape_log():
    with tempfile.TemporaryDirectory() as td:
        log = os.path.join(td, "y.jsonl")

        p = run(log, "report")
        check("empty ledger names itself an EMPTY DENOMINATOR, never a clean record",
              "EMPTY DENOMINATOR" in p.stdout, p.stdout)

        check("bad discovery path is refused (rc=2), not silently coerced",
              run(log, "record", "--what", "x", "--caught-by", "vibes").returncode == 2)

        run(log, "record", "--what", "plan-landing lapsed 8 days", "--caught-by", "human",
            "--where", "CLAUDE.md", "--declared-green")
        run(log, "record", "--what", "grep matched its own docstring", "--caught-by", "peer",
            "--where", "cheliped")
        run(log, "record", "--what", "re-dated debt broke a pinned expiry test",
            "--caught-by", "oracle", "--where", "test_capability_registry.py")

        rows = [json.loads(l) for l in open(log) if l.strip()]
        check("rows land as event=escape with the path recorded",
              len(rows) == 3 and all(r["event"] == "escape" for r in rows)
              and {r["caught_by"] for r in rows} == {"human", "peer", "oracle"}, rows)

        out = run(log, "report").stdout
        check("report counts each discovery path", "human    1" in out.replace("  ", " ")
              or "human     1" in out, out)
        check("1 oracle vs 2 people reads as the net NOT catching",
              "NOT catching" in out, out)
        check("work declared green before the defect is surfaced separately",
              "DECLARED GREEN" in out, out)

        # the verdict must be able to flip — otherwise it is decoration
        for i in range(4):
            run(log, "record", "--what", "oracle catch %d" % i, "--caught-by", "oracle")
        out2 = run(log, "report").stdout
        check("verdict FLIPS when the machinery pulls ahead (falsifiable both ways)",
              "NOT catching" not in out2 and "ahead of the person" in out2, out2)

        # --since must actually filter, or the trend line is a lie
        check("--since filters by date", "Escapes: 0" not in run(log, "report",
              "--since", "2099-01-01").stdout and "EMPTY DENOMINATOR"
              in run(log, "report", "--since", "2099-01-01").stdout)


def main():
    print("\n[test_escape_log]"); test_escape_log()
    print("\n%d passed, %d failed" % (_r["pass"], _r["fail"]))
    sys.exit(1 if _r["fail"] else 0)


if __name__ == "__main__":
    main()
