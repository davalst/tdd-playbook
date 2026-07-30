#!/usr/bin/env python3
"""Planted-input calibration for bin/plan_block.py — the plan-authoring half of the CIVerd
plan-predicate seam.

The engine parses `civerd-plan` blocks deterministically and FAILS CLOSED; the consumer
defines the format, we conform. plan_block.py must therefore refuse in the AUTHOR'S hands
anything the engine would red (the anti-normalizePatternType rule), and its local rules may
drift only in the STRICT direction. The conformance corpus's expected verdicts are blessed
by the ENGINE'S own code path (`civerd plan-check`), never by our reading — a self-authored
verdict certifies the author's own reading (CIVerd-CTO amendment 1).

Self-contained, no pytest. Run: python3 tests/test_plan_block.py
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
PB = os.path.join(PLUGIN, "bin", "plan_block.py")
CORPUS = os.path.join(HERE, "fixtures", "plan_block_corpus.json")

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def run_pb(*args, cwd=None):
    return subprocess.run([sys.executable, PB, *args], capture_output=True, text=True,
                          cwd=cwd, timeout=60)


def scaffold(d, slug, *extra):
    return run_pb("scaffold", "--slug", slug, "--repo", "tdd-playbook", *extra, cwd=d)


def main():
    print("plan_block authoring calibration")
    if not os.path.isfile(PB):
        check("bin/plan_block.py exists", False, "missing")
        print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
        sys.exit(1)

    with tempfile.TemporaryDirectory() as d:
        # brief test 1 (red-first): an approved plan lands in the WORKING repo, not ~/.claude
        p = scaffold(d, "2026-07-30-demo", "--predicate",
                     "file_exists:plugins/tdd-playbook/hooks/scripts/capture.py")
        target = os.path.join(d, "docs", "plans", "gated", "2026-07-30-demo.md")
        check("scaffold writes into the working repo's docs/plans/gated/",
              p.returncode == 0 and os.path.isfile(target), (p.returncode, p.stderr))
        body = open(target).read() if os.path.isfile(target) else ""
        check("scaffold: exactly one civerd-plan fence",
              body.count("```civerd-plan") == 1, body[:200])
        check("scaffold: status is active", "status: active" in body, body[:400])
        check("scaffold: prose section for unenforceable deliverables present",
              "Unenforceable deliverables" in body, body[:400])

        # brief test 2: round-trip — validate parses the emitted block and re-emission is
        # byte-identical (the block, not the prose)
        v = run_pb("validate", target, cwd=d)
        check("validate: emitted block round-trips clean", v.returncode == 0,
              (v.returncode, v.stdout, v.stderr))

        # brief test 6 + boundary AT the limit (their mutation lesson): "plan."+slug <= 64
        ok59 = scaffold(d, "s" * 59)
        at60 = scaffold(d, "s" * 60)
        check("slug boundary: 59 accepted (plan.+59 == 64)", ok59.returncode == 0,
              (ok59.returncode, ok59.stderr))
        check("slug boundary: 60 refused AT the limit", at60.returncode != 0
              and "64" in (at60.stderr + at60.stdout), (at60.returncode, at60.stderr))

        # charset + collision
        bad = scaffold(d, "bad slug!")
        check("slug charset violation refused", bad.returncode != 0, bad.returncode)
        dup = scaffold(d, "2026-07-30-demo")
        check("slug collision with existing plan refused", dup.returncode != 0,
              dup.returncode)

    with tempfile.TemporaryDirectory() as d:
        # brief test 3: empty predicate list refused at authoring, with a reason
        p = scaffold(d, "2026-07-30-empty")
        check("empty predicate list refused with a reason", p.returncode != 0
              and "predicate" in (p.stderr + p.stdout).lower(), (p.returncode, p.stderr))

        # brief test 4: unknown predicate type refused at AUTHORING, never emitted
        p = scaffold(d, "2026-07-30-unk", "--predicate", "line_coverage:80")
        check("unknown predicate type refused in the author's hands", p.returncode != 0
              and "line_coverage" in (p.stderr + p.stdout), (p.returncode, p.stderr))

        # brief test 5: satisfied/abandoned structurally unemittable — no argument path
        for word in ("satisfied", "abandoned"):
            p = scaffold(d, "2026-07-30-" + word, "--predicate",
                         "suite_min:1", "--status", word)
            check("status {} unemittable (no argument path exists)".format(word),
                  p.returncode != 0, (p.returncode, p.stderr))

        # engine-exact argument grammar (strict-superset rule): bad shapes refused
        for pred in ("test_passes:no-double-colon", "symbol_referenced:9starts-with-digit",
                     "file_exists:has space.py", "suite_min:notanint",
                     "suite_min:1234567890"):
            p = scaffold(d, "2026-07-30-g" + str(abs(hash(pred)) % 1000), "--predicate", pred)
            check("engine-grammar refusal: {}".format(pred), p.returncode != 0,
                  (p.returncode, p.stderr))

        # >64 predicates refused (engine MAX_PREDICATES)
        many = []
        for i in range(65):
            many += ["--predicate", "suite_min:{}".format(i + 1)]
        p = scaffold(d, "2026-07-30-many", *many)
        check("65 predicates refused (engine cap 64, boundary-aware)", p.returncode != 0,
              (p.returncode, p.stderr))

    # conformance corpus: engine-blessed verdicts, replayed through OUR validator
    check("conformance corpus fixture exists", os.path.isfile(CORPUS), CORPUS)
    if os.path.isfile(CORPUS):
        corpus = json.load(open(CORPUS))
        check("corpus is stamped with the blessing engine version",
              bool(corpus.get("blessed_by_engine_version")), corpus.keys())
        agree = True
        with tempfile.TemporaryDirectory() as d:
            for case in corpus.get("cases", []):
                path = os.path.join(d, "case.md")
                with open(path, "w") as fh:
                    fh.write(case["plan_markdown"])
                v = run_pb("validate", path, cwd=d)
                ours = "valid" if v.returncode == 0 else "invalid"
                if ours == "valid" and case["engine_verdict"] != "valid":
                    agree = False  # we accepted what the engine rejects — the UNSAFE drift
                    print("    DRIFT(unsafe): {} — ours=valid engine={}".format(
                        case["name"], case["engine_verdict"]))
        check("no unsafe drift: we never accept what the engine rejects", agree)

    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
