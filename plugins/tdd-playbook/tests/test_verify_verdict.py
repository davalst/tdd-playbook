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
import re
import shutil
import subprocess
import sys
import tempfile
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

    # 2. release-decision layer over the real ledger.
    # The v1.24 roster pin is POLICY layered on top of these decision mechanics; it has
    # its own section (2b) exercising the REAL pin. Here the pin is scoped to the golden
    # ledger's era so freshness/heartbeat/signature mechanics stay independently tested
    # (the golden fixtures are signed — their rosters cannot be extended).
    check("roster pin exists (EXPECTED_REQUIRED + EXPECTED_PRESENT)",
          hasattr(V, "EXPECTED_REQUIRED") and hasattr(V, "EXPECTED_PRESENT"))
    _pin = (getattr(V, "EXPECTED_REQUIRED", None), getattr(V, "EXPECTED_PRESENT", None))
    V.EXPECTED_REQUIRED, V.EXPECTED_PRESENT = ("deps", "tests", "venv"), ()

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

    # restore the REAL pin for its own section
    V.EXPECTED_REQUIRED, V.EXPECTED_PRESENT = _pin

    # 2b. ROSTER PIN (2026-08-03 engine hand-off — verified engine-side: `required` is
    # derived from what RAN, an echo not a contract, so a check silently dropped from
    # root config yields a GREEN verdict with a shorter checks[] that still verifies and
    # still evaluates ok. This pin is the ONLY release-side defense against roster
    # shrink.) The plant is a REAL signed verdict: today's 03d7bc7d run — authentic,
    # fresh, green, staleness present — judged minutes before the engine armed the
    # dataflow check, so it is precisely 'otherwise valid but shorter'.
    short_path = os.path.join(HERE, "fixtures", "civerd_verdict_roster_short.jsonl")
    short_lines = open(short_path).readlines()
    short_sha = json.loads(short_lines[0])["verdict"]["snapshot"]["commit"]
    short_now = datetime(2026, 8, 3, 19, 0, 0, tzinfo=timezone.utc)
    allowed, reason = V.may_release(short_lines, short_sha, now=short_now,
                                    max_age_s=10 ** 9)
    check("roster pin: a signed, fresh, GREEN verdict missing 'dataflow' is REFUSED",
          allowed is False and reason.startswith("roster_shrink"), (allowed, reason))
    check("roster pin: the refusal NAMES the missing check", "dataflow" in reason, reason)
    check("roster pin: refusal is distinct from no-verdict and verdict_not_ok",
          "no_verdict" not in reason and "verdict_not_ok" not in reason, reason)

    # unit-level pin semantics over synthetic snapshots (no signatures involved)
    full = {"required": ["dataflow", "deps", "dryrun", "registry", "tests", "venv",
                         "integrity", "integrity_baseline"],
            "checks": [{"name": n} for n in
                       ("dataflow", "deps", "dryrun", "registry", "tests", "venv",
                        "integrity", "integrity_baseline", "staleness")]}
    check("roster pin: full roster (with engine extras) -> no gaps",
          V.roster_gaps(full) == [], V.roster_gaps(full))
    ran_not_required = {"required": ["deps", "dryrun", "registry", "tests", "venv"],
                        "checks": full["checks"]}
    check("roster pin: check RAN but demoted from required -> gap named",
          V.roster_gaps(ran_not_required) == ["dataflow"],
          V.roster_gaps(ran_not_required))
    no_staleness = {"required": full["required"],
                    "checks": [c for c in full["checks"] if c["name"] != "staleness"]}
    check("roster pin: advisory staleness pinned presence-only — absence is a gap",
          V.roster_gaps(no_staleness) == ["staleness"], V.roster_gaps(no_staleness))

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
    # under the REAL pin the golden ledger's shorter roster must refuse THROUGH the CLI —
    # the shipped binary has no override, so green plumbing is proven via a tmp mirror
    # whose pin constant is scoped to the golden roster (no production bypass exists)
    p = subprocess.run([sys.executable, BIN, "--sha", REAL_SHA, "--ledger", LEDGER,
                        "--max-age-s", huge], capture_output=True, text=True, timeout=30)
    check("CLI: real pin refuses the golden ledger's short roster (exit 1, named)",
          p.returncode == 1 and "roster_shrink" in p.stderr,
          (p.returncode, p.stdout, p.stderr))
    with tempfile.TemporaryDirectory() as td:
        mirror = os.path.join(td, "bin")
        shutil.copytree(os.path.dirname(BIN), mirror)
        mbin = os.path.join(mirror, os.path.basename(BIN))
        src = open(mbin).read()
        assert "EXPECTED_REQUIRED" in src
        src = re.sub(r"EXPECTED_REQUIRED = \([^)]*\)",
                     'EXPECTED_REQUIRED = ("deps", "tests", "venv")', src, count=1)
        src = re.sub(r"EXPECTED_PRESENT = \([^)]*\)", "EXPECTED_PRESENT = ()", src,
                     count=1)
        with open(mbin, "w") as fh:
            fh.write(src)
        p = subprocess.run([sys.executable, mbin, "--sha", REAL_SHA, "--ledger", LEDGER,
                            "--max-age-s", huge], capture_output=True, text=True,
                           timeout=30)
        check("CLI exit 0 for real SHA (era-scoped mirror pin)", p.returncode == 0,
              (p.returncode, p.stdout, p.stderr))
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

    probe_survivor_gaps(d)

    test_probe_collision()

    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


def probe_survivor_gaps(d):
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



def test_probe_collision():
    """CIVerd engine finding, 2026-08-05: `planted_probe` writes ordinary kind:"run"
    ledger entries, so a GREEN probe verdict at a release sha is indistinguishable from a
    CI verdict to a last-match-wins reducer — and for ~5 hours a green probe outranked a
    RED CI verdict at the same sha.

    Fixture is REAL signed data, not a mock: sha 976364f carries a RED CI verdict
    (gate_cmd 'venv && deps && tests && ...', 02:00) AND a GREEN probe verdict
    (gate_cmd 'planted_probe', 12:46). Both directions the engine named are pinned:
      1. a green PROBE must never authorize a release (nor mask the CI verdict);
      2. a probe must never trigger a spurious roster_shrink on an otherwise-valid
         release — probe snapshots carry probe.<slug> rows and none of the roster."""
    led = os.path.join(HERE, "fixtures", "civerd_probe_collision.jsonl")
    lines = open(led).readlines()
    sha = "976364fd1655dd90fab9f79b3a389ef0cca880b4"
    snaps = [(json.loads(l).get("verdict") or {}).get("snapshot") or {} for l in lines]
    ci = next(s for s in snaps if "tests" in str(s.get("gate_cmd") or ""))
    probe = next(s for s in snaps if s.get("gate_cmd") == "planted_probe")

    # the discriminator itself — positive identification, not last-wins
    check("probe collision: CI entry identified as a release-deciding verdict",
          V.is_ci_verdict(ci), ci.get("gate_cmd"))
    check("probe collision: probe entry is NOT a release-deciding verdict",
          not V.is_ci_verdict(probe), probe.get("gate_cmd"))
    check("probe collision: both entries are kind=run at the SAME sha (why kind cannot "
          "discriminate)",
          ci.get("kind") == probe.get("kind") == "run"
          and ci.get("commit") == probe.get("commit") == sha)

    # direction 1: the green probe must not authorize; the CI verdict's REAL state governs
    allowed, reason = V.may_release(lines, sha, now=datetime(2026, 8, 5, 13, 0, 0,
                                                             tzinfo=timezone.utc),
                                    max_age_s=10 ** 9)
    check("probe collision: green probe does NOT authorize a release", allowed is False,
          (allowed, reason))
    check("probe collision: refusal reports the CI verdict's real state (verdict_not_ok), "
          "not a probe-induced roster_shrink",
          reason == "verdict_not_ok", reason)

    # direction 2: a probe alone can never stand in for a CI verdict — fails CLOSED
    probe_only = [l for l in lines
                  if ((json.loads(l).get("verdict") or {}).get("snapshot") or {})
                  .get("gate_cmd") != ci.get("gate_cmd")]
    allowed2, reason2 = V.may_release(probe_only, sha,
                                      now=datetime(2026, 8, 5, 13, 0, 0,
                                                   tzinfo=timezone.utc),
                                      max_age_s=10 ** 9)
    check("probe collision: probe-only ledger -> no_verdict_for_commit (fails closed)",
          allowed2 is False and reason2 == "no_verdict_for_commit", (allowed2, reason2))

    # a REAL roster shrink on a REAL CI entry must still fail LOUD and NAMED — the probe
    # fix must not swallow the v1.25 pin
    shrunk = copy.deepcopy(ci)
    shrunk["required"] = [r for r in shrunk.get("required", []) if r != "dataflow"]
    shrunk["checks"] = [c for c in shrunk.get("checks", []) if c.get("name") != "dataflow"]
    check("probe collision: roster pin still fires on a genuine CI shrink",
          V.roster_gaps(shrunk) == ["dataflow"], V.roster_gaps(shrunk))

if __name__ == "__main__":
    main()
