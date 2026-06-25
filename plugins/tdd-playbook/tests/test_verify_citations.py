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

    print("\n{} passed, {} failed".format(_r["pass"], _r["fail"]))
    sys.exit(1 if _r["fail"] else 0)


if __name__ == "__main__":
    main()
