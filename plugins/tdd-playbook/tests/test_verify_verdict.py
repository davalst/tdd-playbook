#!/usr/bin/env python3
"""Planted-input calibration for bin/verify_verdict.py — the CIVerd hub-side release gate.

Two layers, both must be able to FAIL (§13):
  1. FACTS layer, cross-validated against memrebel's golden corpus (the reference implementation):
     every canonical()/stable_json() vector and all 10 bundle_cases must reproduce memrebel's
     EXACT accept/reject and reason string. This catches a diverging reimplementation — most
     plausibly a wrong canonicalizer, which real ASCII fixtures cannot surface (the UTF-16 trap).
  2. RELEASE-decision layer over a whole ledger (may_release): a fresh signed GREEN run verdict for
     the exact SHA with a live engine passes; every absence/tamper is its own RED reason.
Plus: no --force exists, the CLI plumbing, and a planted canonicalizer bug must turn the corpus RED.
Self-contained, stdlib only. Run:  python3 tests/test_verify_verdict.py
"""
import copy
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
BIN = os.path.join(os.path.dirname(HERE), "bin", "verify_verdict.py")
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "bin"))
import verify_verdict as V  # noqa: E402

CORPUS = os.path.join(HERE, "fixtures", "civerd_crossvalidation_corpus.json")
LEDGER = os.path.join(HERE, "fixtures", "civerd_verdicts.jsonl")
REAL_SHA = "31fa8ac4f0b31e5cd2e3a0523d2d2eacbc8c5e9b"
# A time a few minutes after the fixture verdict's as_of, so freshness is deterministic.
NOW = datetime(2026, 7, 27, 20, 30, 0, tzinfo=timezone.utc)

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def _corpus():
    with open(CORPUS) as fh:
        return json.load(fh)


def _facts(bundle, pinned):
    try:
        V.verify_facts(bundle, pinned=pinned)
        return (True, None)
    except V.Refused as e:
        return (False, e.reason)


def main():
    print("test_verify_verdict — memrebel golden corpus + release-decision + no-force + CLI")
    d = _corpus()

    # 1a. serialization vectors — exact bytes vs memrebel
    for v in d["canonical_vectors"]:
        got = V.canonical(v["input"]).decode("utf-8")
        check("canonical == memrebel: {}".format(v["expected"]), got == v["expected"], got)
    for v in d["stable_json_vectors"]:
        got = V.stable_json(v["input"]).decode("utf-8")
        check("stable_json == memrebel: {}".format(v["expected"]), got == v["expected"], got)

    # 1b. all 10 bundle cases — exact accept/reject + reason string vs memrebel
    for c in d["bundle_cases"]:
        got = _facts(c["bundle"], c["issuer_key"])
        exp = (c["expected"]["facts_ok"], c["expected"]["reason"])
        check("bundle case {}: {}".format(c["name"], exp), got == exp, got)

    # 2. release-decision layer over the real ledger
    lines = open(LEDGER).readlines()

    def mr(ledger, sha, max_age=86400):
        return V.may_release(ledger, sha, now=NOW, max_age_s=max_age)

    check("happy path -> allowed", mr(lines, REAL_SHA) == (True, "ok"))
    check("wrong SHA -> no_verdict_for_commit",
          mr(lines, "dead" + REAL_SHA[4:]) == (False, "no_verdict_for_commit"))
    check("stale -> stale", mr(lines, REAL_SHA, max_age=1) == (False, "stale"))
    check("empty ledger -> no_verdict_for_commit", mr([], REAL_SHA) == (False, "no_verdict_for_commit"))
    check("garbage lines -> no_verdict_for_commit",
          mr(["\n", "not json\n"], REAL_SHA) == (False, "no_verdict_for_commit"))

    hb = [l for l in lines if json.loads(l)["verdict"]["snapshot"]["kind"] == "heartbeat"]
    check("heartbeat cannot satisfy a real-SHA request (check-11 trap)",
          mr(hb, REAL_SHA) == (False, "no_verdict_for_commit"))

    runline = [l for l in lines if json.loads(l)["verdict"]["snapshot"]["kind"] == "run"]
    check("run present but no live heartbeat -> engine_silent",
          mr(runline, REAL_SHA) == (False, "engine_silent"))

    # a forged ok-flip breaks the signature -> caught at the facts layer, never a silent pass
    run = json.loads(runline[0])
    forged = copy.deepcopy(run); forged["verdict"]["claimed_report"]["ok"] = False
    check("forged ok=false is caught (sig invalid)",
          mr([json.dumps(forged)] + hb, REAL_SHA) == (False, "claimed_report_signature_invalid"))

    # future-dated verdict must not extend its own validity
    check("future-dated -> stale",
          V.may_release(lines, REAL_SHA, now=datetime(2020, 1, 1, tzinfo=timezone.utc),
                        max_age_s=86400) == (False, "stale"))

    # 3. NO --force / --override exists — a bad release is unbuildable, not discouraged.
    # Check for an actual option DEFINITION (a mere comment mentioning it is fine, and intended).
    src = open(BIN).read()
    defines_force = any(
        ('add_argument(' in ln) and ('"--force"' in ln or "'--force'" in ln
                                      or '"--override"' in ln or "'--override'" in ln)
        for ln in src.splitlines()
    )
    check("no --force/--override option is defined", not defines_force)
    p = subprocess.run([sys.executable, BIN, "--sha", REAL_SHA, "--force",
                        "--ledger", LEDGER], capture_output=True, text=True, timeout=30)
    check("--force is rejected by argparse (exit 2)", p.returncode == 2, (p.returncode, p.stderr))

    # 4. CLI plumbing (freshness made deterministic with a huge max-age; policy is tested above)
    huge = "999999999999"
    p = subprocess.run([sys.executable, BIN, "--sha", REAL_SHA, "--ledger", LEDGER,
                        "--max-age-s", huge], capture_output=True, text=True, timeout=30)
    check("CLI exit 0 for real SHA", p.returncode == 0, (p.returncode, p.stdout, p.stderr))
    p = subprocess.run([sys.executable, BIN, "--sha", "deadbeef", "--ledger", LEDGER,
                        "--max-age-s", huge], capture_output=True, text=True, timeout=30)
    check("CLI exit 1 + reason for unknown SHA",
          p.returncode == 1 and "no_verdict_for_commit" in p.stderr, (p.returncode, p.stderr))
    p = subprocess.run([sys.executable, BIN, "--sha", REAL_SHA, "--ledger",
                        os.path.join(HERE, "does-not-exist.jsonl")],
                       capture_output=True, text=True, timeout=30)
    check("CLI exit 1 for unreadable ledger", p.returncode == 1, (p.returncode, p.stderr))

    # 5. PLANT: break the canonicalizer to code-point sort; the UTF-16 corpus vector must go RED.
    # If it stays green, the golden vector is theater.
    orig = V._jcs
    try:
        def naive(o):  # sort by code point instead of UTF-16 code units
            if isinstance(o, dict):
                items = sorted(o.items(), key=lambda kv: kv[0])
                return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + naive(v)
                                      for k, v in items) + "}"
            return orig(o)
        V._jcs = naive
        trap = [v for v in d["canonical_vectors"] if "𐀀" in v["expected"]][0]
        broke = V.canonical(trap["input"]).decode("utf-8") != trap["expected"]
        check("planted code-point canonicalizer breaks the UTF-16 vector (vector is real)", broke)
    finally:
        V._jcs = orig

    test_probe_survivor_gaps(d)

    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


def test_probe_survivor_gaps(d):
    """CIVerd probe run 2 (2026-07-28) planted flip_boolop + constant_return here and this
    suite stayed green. Local sweep triage: malformed-TYPE guards (non-list records,
    non-dict snapshot/claimed_report — the or->and flip lets truthy wrong-typed values
    through to the wrong reason code, and reason strings are contractual vs memrebel) and
    the ledger-acquisition helpers were unasserted. Each test verified to FAIL under its
    mutant (mutation red-first — the probe chose the targets, not the author)."""
    ok = next(c for c in d["bundle_cases"] if c["expected"]["facts_ok"])

    # (a) records must be a LIST — a truthy dict/str must refuse as `malformed`, never
    # leak through to count_mismatch or a crash
    for bad_records in ({"0": "rec"}, "records-as-string", 7):
        b = copy.deepcopy(ok["bundle"])
        b["records"] = bad_records
        got = _facts(b, ok["issuer_key"])
        check("probe-gap: non-list records ({}) -> malformed".format(type(bad_records).__name__),
              got == (False, "malformed"), got)

    # (b) snapshot AND claimed_report must each be dicts — a truthy non-dict on either
    # side of the `or` must refuse as `malformed`
    for field in ("snapshot", "claimed_report"):
        b = copy.deepcopy(ok["bundle"])
        b["verdict"][field] = "not-a-dict"
        got = _facts(b, ok["issuer_key"])
        check("probe-gap: non-dict verdict.{} -> malformed".format(field),
              got == (False, "malformed"), got)

    # (c) _cache_dir: honors XDG_CACHE_HOME and names the civerd-verdicts dir (a constant
    # return would break every ledger fetch silently)
    import tempfile
    old_xdg = os.environ.get("XDG_CACHE_HOME")
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["XDG_CACHE_HOME"] = tmp
        try:
            got = V._cache_dir()
            check("probe-gap: _cache_dir = $XDG_CACHE_HOME/civerd-verdicts",
                  got == os.path.join(tmp, "civerd-verdicts"), got)

            # (d) fetch_ledger returns the ACTUAL ledger lines (offline: a local origin
            # cloned into the cache path takes the pull branch; no network, no gh)
            origin = os.path.join(tmp, "origin")
            os.makedirs(origin)
            with open(os.path.join(origin, "verdicts.jsonl"), "w") as fh:
                fh.write('{"row":1}\n{"row":2}\n')

            def git(cwd, *a):
                subprocess.run(["git", "-C", cwd, *a], capture_output=True, timeout=30)
            git(origin, "init", "-q")
            git(origin, "config", "user.email", "t@t")
            git(origin, "config", "user.name", "t")
            git(origin, "add", "-A")
            git(origin, "commit", "-qm", "ledger")
            subprocess.run(["git", "clone", "-q", origin,
                            os.path.join(tmp, "civerd-verdicts")],
                           capture_output=True, timeout=30)
            lines = V.fetch_ledger()
            check("probe-gap: fetch_ledger returns the real ledger lines",
                  lines == ['{"row":1}\n', '{"row":2}\n'], lines)
        finally:
            if old_xdg is None:
                os.environ.pop("XDG_CACHE_HOME", None)
            else:
                os.environ["XDG_CACHE_HOME"] = old_xdg


if __name__ == "__main__":
    main()
