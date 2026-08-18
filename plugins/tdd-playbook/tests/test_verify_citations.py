#!/usr/bin/env python3
"""Planted-input calibration for verify_citations (the §12 claims gate).

The gate exists to catch fabricated/wrong evidence. So the ungameable check is that PLANTED
bad citations are actually caught and a real one passes. A fabricated citation that the gate
marks VERIFIED is a BLOCKING failure here. Self-contained; no pytest. Run:
    python3 tests/test_verify_citations.py
"""
import os
import subprocess
import sys
import tempfile

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "bin", "verify_citations.py")
_r = {"pass": 0, "fail": 0}


def run(findings_text, files):
    """Write a temp source tree + findings doc; run the verifier; return (rc, stdout)."""
    d = tempfile.mkdtemp()
    for rel, content in files.items():
        p = os.path.join(d, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True) if os.path.dirname(rel) else None
        with open(p, "w") as fh:
            fh.write(content)
    fpath = os.path.join(d, "FINDINGS.md")
    with open(fpath, "w") as fh:
        fh.write(findings_text)
    p = subprocess.run([sys.executable, BIN, fpath, "--base", d],
                       capture_output=True, text=True, timeout=20)
    return p.returncode, p.stdout


def check(name, cond, detail=""):
    if cond:
        _r["pass"] += 1
        print("  ok   - " + name)
    else:
        _r["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


SRC = "def login(u, p):\n    if not u:\n        return False\n    return check(u, p)\n"


def main():
    print("verify_citations calibration\n")
    absence_checks()

    # 1. valid citation, no quote -> VERIFIED, exit 0
    rc, out = run("Bug in `src/auth.py:3`.", {"src/auth.py": SRC})
    check("valid citation verifies", rc == 0 and "verified 1" in out, (rc, out))

    # 2. PLANTED: nonexistent file -> UNRESOLVED, exit 1
    rc, out = run("See `src/ghost.py:3`.", {"src/auth.py": SRC})
    check("nonexistent file caught", rc == 1 and "unresolved 1" in out, (rc, out))

    # 3. PLANTED: line out of range -> UNRESOLVED, exit 1
    rc, out = run("See `src/auth.py:999`.", {"src/auth.py": SRC})
    check("out-of-range line caught", rc == 1 and "out of range" in out, (rc, out))

    # 4. quote that matches the cited line -> VERIFIED
    rc, out = run('`src/auth.py:3`: "return False"', {"src/auth.py": SRC})
    check("matching quote verifies", rc == 0 and "verified 1" in out, (rc, out))

    # 5. PLANTED: quote does NOT match the line -> MISMATCH, exit 1
    rc, out = run('`src/auth.py:3`: "return True"', {"src/auth.py": SRC})
    check("fabricated quote caught (MISMATCH)", rc == 1 and "mismatch 1" in out, (rc, out))

    # 6. line range within bounds -> VERIFIED
    rc, out = run("`src/auth.py:1-4` is the function.", {"src/auth.py": SRC})
    check("valid range verifies", rc == 0 and "verified 1" in out, (rc, out))

    # 7. no citations -> clean exit 0
    rc, out = run("This finding cites nothing in particular.", {"src/auth.py": SRC})
    check("no citations -> clean exit 0", rc == 0 and "Citations: 0" in out, (rc, out))

    # 8. mixed: one good + one bad -> exit 1, counts right, names the bad one
    rc, out = run("Good `src/auth.py:3`; bad `src/auth.py:999`.", {"src/auth.py": SRC})
    check("mixed doc: exit 1 + correct counts",
          rc == 1 and "verified 1" in out and "unresolved 1" in out and "DEMOTE" in out, (rc, out))

    # 9. whitespace-normalized quote match
    rc, out = run('`src/auth.py:2`: "if   not u:"', {"src/auth.py": SRC})
    check("whitespace-normalized quote verifies", rc == 0 and "verified 1" in out, (rc, out))

    # 10. prose that looks numeric but isn't a citation is ignored (no false positive)
    rc, out = run("We support Python 3.11 and step 3:1 of the plan.", {"src/auth.py": SRC})
    check("non-citation prose not flagged", rc == 0, (rc, out))

    # 11. PLANTED: a tiny fragment quote "verifies" trivially -> flagged weak (gate holds,
    #     but the weakness is visible; regression: old version printed nothing)
    rc, out = run('`src/auth.py:3`: "return"', {"src/auth.py": SRC})
    check("short-fragment quote flagged weak", rc == 0 and "weak-quote 1" in out
          and "<10 chars" in out, (rc, out))

    # 12. PLANTED: a quote matching many lines is not uniquely identifying -> flagged weak
    multi = "x = check(u, p)\ny = check(u, p)\nz = check(u, p)\n"
    rc, out = run('`src/multi.py:2`: "= check(u, p)"', {"src/multi.py": multi})
    check("non-unique quote flagged weak", rc == 0 and "weak-quote 1" in out
          and "matches 3 lines" in out, (rc, out))

    # 13. a healthy long unique quote carries no weak flag
    rc, out = run('`src/auth.py:4`: "return check(u, p)"', {"src/auth.py": SRC})
    check("long unique quote not flagged", rc == 0 and "weak-quote" not in out, (rc, out))

    print("\n{} passed, {} failed".format(_r["pass"], _r["fail"]))
    sys.exit(1 if _r["fail"] else 0)



def absence_checks():
    """A NEGATIVE must be citable, or the gate is blind exactly where doctrine is strictest.

    §12 demands MORE evidence for a negative than a positive ("never called / unreachable"
    needs an exhaustive sweep). The tooling provided LESS: a positive cites `file:line` and
    gets resolved; a negative cites NOTHING, so this tool had nothing to check and could not
    see the claim at all. Doctrine strictest, mechanism absent.

    Origin (2026-08-18, live): I told David "MemStruct has no capability registry." It has
    ten, authored 2026-07-21, validating clean — inferred from unrelated missing tooling,
    never checked, and a debt record written about a problem that did not exist. The
    claims-verifier brief already opens with this exact failure ("8 findings, 4 false — every
    false one an unverified NEGATIVE about a file never read"), so doctrine was not missing.
    It was unenforced.

    Form: `(absent: <path>)`. The tool RE-RUNS the check — if the path exists, the finding is
    REFUTED. The inverse of what it already does for presence, at the same seam."""
    print()
    # PLANTED, frozen from the live incident: absence asserted about a file that is there
    rc, out = run("F1: this repo has no registry (absent: capabilities.json).",
                  {"capabilities.json": "{}\n"})
    check("PLANTED: absence claim about a file that EXISTS is refuted",
          rc == 1 and "refuted" in out.lower(), (rc, out[:160]))
    check("PLANTED: the refusal names the path that disproved it",
          "capabilities.json" in out, out[:160])

    # the honest negative
    rc, out = run("F2: no dataflow config (absent: dataflow-sweeps.json).",
                  {"capabilities.json": "{}\n"})
    check("a TRUE absence claim verifies", rc == 0 and "absence claims: 1 \u00b7 verified 1" in out.lower(),
          (rc, out[:160]))

    # counted, never silently ignored — invisibility is the failure being fixed
    check("absence claims are in the denominator", "absence" in out.lower(), out[:160])

    # a directory counts as present (the MemStruct shape was a file, but docs/reviews/ is a dir)
    rc, out = run("F3: no reviews here (absent: docs).", {"docs/x.md": "x\n"})
    check("PLANTED: absence claim about an existing DIRECTORY is refuted",
          rc == 1 and "refuted" in out.lower(), (rc, out[:160]))

    # no regression: docs with only ordinary citations behave exactly as before
    rc, out = run("Bug in `src/auth.py:3`.", {"src/auth.py": SRC})
    check("presence-only docs are unaffected by the new form",
          rc == 0 and "verified 1" in out, (rc, out[:160]))


if __name__ == "__main__":
    main()
