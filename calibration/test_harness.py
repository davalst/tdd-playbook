#!/usr/bin/env python3
"""Planted-input calibration OF the calibration harness (yes — turtles, but checked ones).

The harness's oracle is deterministic string-matching over the agent's output, so it can be
proven with a STUB `claude` binary and zero model spend: a stub that outputs a WRONG verdict
must FAIL the scenario (the harness can fail), a stub that outputs the right verdict must
PASS (the harness can succeed), and --dry-run must validate the shipped scenarios.
Self-contained, no pytest. Run: python3 calibration/test_harness.py
"""
import datetime
import json
import os
import stat
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(HERE, "run_calibration.py")
sys.path.insert(0, HERE)

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def make_stub(d, text):
    """A fake `claude` that ignores its args and prints canned output."""
    path = os.path.join(d, "claude-stub")
    with open(path, "w") as fh:
        fh.write("#!/bin/sh\ncat <<'EOF'\n{}\nEOF\n".format(text))
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    return path


def run(claude_bin, *extra):
    return subprocess.run(
        [sys.executable, RUNNER, "--scenario", "false-negative-claim",
         "--claude-bin", claude_bin, "--history", "", *extra],
        capture_output=True, text=True, timeout=300,
    )


def make_sequence_stub(d, outputs, name="claude-stub-seq"):
    """A fake `claude` that emits outputs[call#-1] (last one repeats), counting calls in an
    absolute file so the count survives the fresh staging cwd of every rep."""
    ctr = os.path.join(d, name + ".calls")
    lines = ["#!/bin/sh",
             'n=$(cat "{0}" 2>/dev/null || echo 0); n=$((n+1)); printf %s "$n" > "{0}"'.format(ctr),
             'case "$n" in']
    for i, out in enumerate(outputs, 1):
        pat = str(i) if i < len(outputs) else "*"
        lines.append("{}) cat <<'EOF'\n{}\nEOF\n;;".format(pat, out))
    lines.append("esac")
    path = os.path.join(d, name)
    with open(path, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    return path, ctr


# Canned outputs for the false-negative-claim oracle (must_match: REFUTED + confirmed-0 count;
# must_not_match: nonzero confirmed count).
OUT_RIGHT = ("**VERDICT: REFUTED** — authorize() is called at cli.py:15 and cli.py:21.\n"
             "Claims checked: 1 · confirmed: 0 · refuted: 1\n"
             "Recommendation: revise because the dead-code claim is false.")
OUT_MISSED = "Everything looks fine; the audit reads plausibly. Recommendation: publish."
OUT_HEDGED = ("**VERDICT: REFUTED** — but I could not complete the sweep, so no counts.\n"
              "Recommendation: revise.")
OUT_WRONGLINE = ("**VERDICT: REFUTED** (partially)\n"
                 "Claims checked: 2 · confirmed: 1 · refuted: 1\nRecommendation: publish.")


def _history_format_tests():
    """PLANTED: the shared history parser (D0) — one module owns the format, and the freshness
    gate must not be satisfiable by INVALID rows (a run where nothing was calibrated)."""
    print("\n[history_format module]")
    try:
        import history_format as hfmt
    except ImportError as e:
        check("history_format module exists", False, e)
        return
    legacy = ("# Calibration history\n\n"
              "| date | model | scenario | agent | verdict |\n|---|---|---|---|---|\n"
              "| 2026-07-09 | haiku | s1 | a1 | PASS |\n"
              "| 2026-07-10 | haiku vs fable-5 | s2 | a2 | **BLOCKING FAIL** |\n"
              "| 2026-07-12 | haiku | s3 | a3 | INVALID — env failure: doer never ran |\n")
    rows = hfmt.parse_rows(legacy)
    check("parse_rows: legacy 5-col rows parsed (runs/mode None)",
          len(rows) == 3 and rows[0]["scenario"] == "s1" and rows[0]["runs"] is None, rows)
    check("parse_rows: verdict kinds classified",
          [r["kind"] for r in rows] == ["PASS", "BLOCKING", "INVALID"],
          [r.get("kind") for r in rows])
    check("latest_run_date: PLANTED stale-masking INVALID row is skipped",
          hfmt.latest_run_date(legacy) == datetime.date(2026, 7, 10),
          hfmt.latest_run_date(legacy))
    check("latest_run_date: all-INVALID -> None (never calibrated)",
          hfmt.latest_run_date("| 2026-07-12 | h | s | a | INVALID — x |\n") is None)

    with tempfile.TemporaryDirectory() as d:
        hp = os.path.join(d, "history.md")
        meta = {"date": "2026-08-10", "model": "haiku", "repo_sha": "abc1234",
                "selected": 1, "total": 14, "shipped": 10, "corpus": 4, "controls": 1,
                "recall": (0, 1), "fp": (0, 0)}
        hfmt.append_run_block(hp, meta, [
            {"date": "2026-08-10", "model_cell": "haiku", "scenario": "s9", "agent": "a9",
             "runs": "1/3", "mode": "found-but-hedged", "verdict": "AMBER"},
        ])
        txt = open(hp).read()
        check("append_run_block: run header carries sha + selected-of-total + recall/FP",
              "### Run 2026-08-10" in txt and "abc1234" in txt and "selected 1 of 14" in txt
              and "recall 0/1" in txt and "FP 0/0" in txt, txt)
        check("append_run_block: 7-col table with its own separator row",
              "| date | model | scenario | agent | runs | mode | verdict |" in txt
              and "|---|---|---|---|---|---|---|" in txt, txt)
        check("append_run_block: no legacy 5-col header on a fresh file",
              "| date | model | scenario | agent | verdict |" not in txt, txt)
        parsed = hfmt.parse_rows(txt)
        check("round-trip: new row parsed with runs/mode/kind",
              len(parsed) == 1 and parsed[0]["runs"] == "1/3"
              and parsed[0]["mode"] == "found-but-hedged" and parsed[0]["kind"] == "AMBER", parsed)


def _staleness_invalid_tests():
    """PLANTED (D1): a scoreboard whose newest rows are INVALID must read STALE, not fresh."""
    cs = os.path.join(HERE, "check_staleness.py")

    def run_cs(text, as_of):
        with tempfile.TemporaryDirectory() as d:
            hist = os.path.join(d, "history.md")
            with open(hist, "w") as fh:
                fh.write(text)
            return subprocess.run(
                [sys.executable, cs, "--history", hist, "--as-of", as_of],
                capture_output=True, text=True, timeout=30)

    rows = ("| 2026-07-01 | haiku | s | a | PASS |\n"
            "| 2026-07-27 | haiku | s | a | INVALID — env failure: doer never ran |\n")
    check("staleness: PLANTED newest-row-INVALID does not extend freshness (stale)",
          run_cs(rows, "2026-07-20").returncode == 1, run_cs(rows, "2026-07-20").returncode)
    check("staleness: INVALID-skip keeps the older PASS date (fresh within window)",
          run_cs(rows, "2026-07-10").returncode == 0, run_cs(rows, "2026-07-10").returncode)


def _d1_repeat_tests(d):
    """PLANTED (D1): N=1 was a spot check — the runner must sample, distinguish AMBER from PASS,
    classify failure modes mechanically, and promote a repeated AMBER."""
    print("\n[D1 repeat sampling / verdict states]")

    def run_hist(claude_bin, hist, *extra):
        return subprocess.run(
            [sys.executable, RUNNER, "--scenario", "false-negative-claim",
             "--claude-bin", claude_bin, "--history", hist, *extra],
            capture_output=True, text=True, timeout=300)

    # default --repeat 3: the stub must be invoked exactly 3 times
    stub, ctr = make_sequence_stub(d, [OUT_RIGHT], "stub-count3")
    hp = os.path.join(d, "h-count.md")
    p = run_hist(stub, hp)
    calls = open(ctr).read() if os.path.isfile(ctr) else "0"
    check("--repeat defaults to 3 (stub invoked 3x)", calls == "3", calls)
    check("3/3 -> PASS + exit 0", p.returncode == 0 and "PASS" in p.stdout,
          (p.returncode, p.stdout[-300:]))
    check("PASS row records runs 3/3",
          "| 3/3 |" in open(hp).read(), open(hp).read())

    # 1 right out of 3 -> AMBER, nonzero exit BY DEFAULT (no --strict to remember)
    stub, _ = make_sequence_stub(d, [OUT_MISSED, OUT_RIGHT, OUT_MISSED], "stub-amber")
    hp = os.path.join(d, "h-amber.md")
    p = run_hist(stub, hp)
    txt = open(hp).read()
    check("PLANTED lucky-roll: 1/3 -> AMBER (not PASS), exit nonzero",
          p.returncode == 1 and "AMBER" in txt and "| 1/3 |" in txt,
          (p.returncode, txt))

    # 0/3 -> BLOCKING FAIL with mode column
    stub, _ = make_sequence_stub(d, [OUT_MISSED], "stub-missed")
    hp = os.path.join(d, "h-missed.md")
    p = run_hist(stub, hp)
    txt = open(hp).read()
    check("0/3 -> BLOCKING FAIL, mode missed-entirely",
          p.returncode == 1 and "BLOCKING FAIL" in txt and "missed-entirely" in txt, txt)

    stub, _ = make_sequence_stub(d, [OUT_HEDGED], "stub-hedged")
    hp = os.path.join(d, "h-hedged.md")
    run_hist(stub, hp)
    check("partial must_match -> mode found-but-hedged",
          "found-but-hedged" in open(hp).read(), open(hp).read())

    stub, _ = make_sequence_stub(d, [OUT_WRONGLINE], "stub-wrongline")
    hp = os.path.join(d, "h-wrongline.md")
    run_hist(stub, hp)
    check("must_not_match hit -> mode wrong-verdict-line (takes precedence)",
          "wrong-verdict-line" in open(hp).read(), open(hp).read())

    # --repeat 1 reproduces today's single-roll behavior
    stub, ctr = make_sequence_stub(d, [OUT_RIGHT], "stub-r1")
    p = run_hist(stub, os.path.join(d, "h-r1.md"), "--repeat", "1")
    calls_r1 = open(ctr).read() if os.path.isfile(ctr) else "0"
    check("--repeat 1 parity: single invocation, PASS",
          p.returncode == 0 and calls_r1 == "1", (p.returncode, calls_r1))

    # env failure: nonzero exit + empty stdout on every rep -> INVALID, never BLOCKING
    envfail = os.path.join(d, "stub-envfail")
    with open(envfail, "w") as fh:
        fh.write("#!/bin/sh\necho 'permission refused' >&2\nexit 1\n")
    os.chmod(envfail, os.stat(envfail).st_mode | stat.S_IEXEC)
    hp = os.path.join(d, "h-envfail.md")
    p = run_hist(envfail, hp)
    txt = open(hp).read()
    check("all-reps env failure -> INVALID (excluded from n), exit nonzero",
          p.returncode == 1 and "INVALID" in txt and "BLOCKING" not in txt, (p.returncode, txt))

    # mechanical AMBER -> BLOCKING promotion: prior AMBER row for the same scenario id
    try:
        import history_format as hfmt
    except ImportError as e:
        check("promotion tests need history_format", False, e)
        return
    hp = os.path.join(d, "h-promote.md")
    hfmt.append_run_block(hp, {"date": "2026-07-27", "model": "haiku", "repo_sha": "0000000",
                               "selected": 1, "total": 14, "shipped": 10, "corpus": 4,
                               "controls": 1, "recall": (0, 1), "fp": (0, 0)},
                          [{"date": "2026-07-27", "model_cell": "haiku",
                            "scenario": "false-negative-claim", "agent": "claims-verifier",
                            "runs": "1/3", "mode": "found-but-hedged", "verdict": "AMBER"}])
    stub, _ = make_sequence_stub(d, [OUT_MISSED, OUT_RIGHT, OUT_MISSED], "stub-promote")
    p = run_hist(stub, hp)
    txt = open(hp).read()
    check("PLANTED persistent AMBER: second consecutive AMBER promotes to BLOCKING",
          p.returncode == 1 and "AMBER×2" in txt, txt)

    # ...but a prior INVALID row must NOT promote
    hp = os.path.join(d, "h-nopromote.md")
    hfmt.append_run_block(hp, {"date": "2026-07-27", "model": "haiku", "repo_sha": "0000000",
                               "selected": 1, "total": 14, "shipped": 10, "corpus": 4,
                               "controls": 1, "recall": (0, 1), "fp": (0, 0)},
                          [{"date": "2026-07-27", "model_cell": "haiku",
                            "scenario": "false-negative-claim", "agent": "claims-verifier",
                            "runs": "0/0", "mode": "env-failure", "verdict": "INVALID"}])
    stub, _ = make_sequence_stub(d, [OUT_MISSED, OUT_RIGHT, OUT_MISSED], "stub-nopromote")
    p = run_hist(stub, hp)
    txt = open(hp).read()
    check("prior INVALID does not promote (stays AMBER)",
          "AMBER×2" not in txt and "AMBER" in txt, txt)


def _unified_validator_tests():
    """PLANTED (D0): two disagreeing validators were the parallel-list bug one level up —
    run_calibration must own ONE validate_scenario, with KNOWN_AGENTS derived from the
    filesystem roster minus the tree-touching exclusion."""
    print("\n[unified scenario validator]")
    import run_calibration as rc
    if not hasattr(rc, "validate_scenario"):
        check("run_calibration.validate_scenario exists", False, "missing")
        return
    good = {"id": "uv-good", "agent": "claims-verifier", "plant": "p", "task": "t",
            "must_match": ["X"]}
    check("unified: valid scenario validates", rc.validate_scenario(good, set()) == [],
          rc.validate_scenario(good, set()))
    check("unified: unknown agent rejected",
          any("unknown agent" in p for p in
              rc.validate_scenario(dict(good, agent="nope"), set())))
    check("unified: tree-touching agent rejected even though its .md exists",
          any("unknown agent" in p for p in
              rc.validate_scenario(dict(good, agent="planted-error-probe"), set())))
    check("unified: script-adversary accepted (derived roster, not a frozen list)",
          rc.validate_scenario(dict(good, agent="script-adversary"), set()) == [])
    check("unified: duplicate id rejected",
          any("duplicate id" in p for p in rc.validate_scenario(good, {"uv-good"})))


def _check_staleness():
    """Planted-input calibration of check_staleness.py (F5): a stale scoreboard MUST be detected.
    A staleness gate that can't fail on a planted-old date is theater (§13). Deterministic via
    injected --as-of; no real clock, no history.md dependency (uses a temp file)."""
    cs = os.path.join(HERE, "check_staleness.py")

    def run(text, as_of, max_age="14", warn=False, missing=False):
        with tempfile.TemporaryDirectory() as d:
            hist = os.path.join(d, "history.md")
            if not missing:
                with open(hist, "w") as fh:
                    fh.write(text)
            args = [sys.executable, cs, "--history", hist, "--as-of", as_of, "--max-age-days", max_age]
            if warn:
                args.append("--warn-only")
            return subprocess.run(args, capture_output=True, text=True, timeout=30)

    rows = ("| date | model | scenario | agent | result |\n"
            "| 2026-07-10 | haiku | s | a | PASS |\n"
            "| 2026-07-27 | haiku | s | a | PASS |\n")  # latest = 2026-07-27
    check("staleness: fresh (5 days) -> exit 0", run(rows, "2026-08-01").returncode == 0)
    check("staleness: PLANTED stale (30 days) -> exit 1 + STALE",
          run(rows, "2026-08-26").returncode == 1 and "STALE" in run(rows, "2026-08-26").stderr)
    check("staleness: exactly at threshold -> fresh",
          run(rows, "2026-08-10").returncode == 0)  # 14 days
    check("staleness: one past threshold -> stale",
          run(rows, "2026-08-11").returncode == 1)  # 15 days
    check("staleness: missing history -> exit 1 never_calibrated",
          run(rows, "2026-08-01", missing=True).returncode == 1)
    check("staleness: no dated rows -> exit 1",
          run("| header only |\n", "2026-08-01").returncode == 1)
    check("staleness: future-dated latest -> exit 1 (broken scoreboard)",
          run(rows, "2026-07-01").returncode == 1)
    check("staleness: --warn-only never hard-fails on stale",
          run(rows, "2026-09-01", warn=True).returncode == 0)
    check("staleness: bad --as-of -> exit 2",
          run(rows, "not-a-date").returncode == 2)


def main():
    print("Calibration-harness calibration")
    _check_staleness()
    _history_format_tests()
    _staleness_invalid_tests()
    _unified_validator_tests()
    with tempfile.TemporaryDirectory() as d1d:
        _d1_repeat_tests(d1d)

    # dry-run over the real shipped scenarios must validate
    p = subprocess.run([sys.executable, RUNNER, "--dry-run"],
                       capture_output=True, text=True, timeout=300)
    check("shipped scenarios pass dry-run", p.returncode == 0 and "0 problem(s)" in p.stdout,
          (p.returncode, p.stdout, p.stderr))

    with tempfile.TemporaryDirectory() as d:
        # PLANTED: an agent that gets it WRONG (confirms the false claim) must FAIL
        wrong = make_stub(d, "Verdict: CONFIRMED — authorize() is indeed dead code.\n"
                             "Recommendation: publish because the sweep found nothing.")
        p = run(wrong)
        check("wrong verdict -> BLOCKING FAIL (harness can fail)",
              p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-400:]))

        # an agent that gets it RIGHT must PASS. The stub is contract-faithful: it carries
        # the claims-verifier's MANDATED summary line — the machine-readable channel the
        # oracle is anchored to (free prose legitimately uses 'confirmed' as an English word).
        right = make_stub(d, "Claim REFUTED: authorize() is called at cli.py:16 and cli.py:22 "
                             "(grep swept every reference site).\n"
                             "Claims checked: 1 · confirmed 0 · refuted 1 · demoted to leads 0\n"
                             "Recommendation: revise because the negative claim is false.")
        p = run(right)
        check("right verdict -> PASS", p.returncode == 0 and "PASS" in p.stdout,
              (p.returncode, p.stdout[-400:]))

        # PLANTED: an agent whose output contains BOTH (hedging) must FAIL on must_not_match
        hedge = make_stub(d, "Possibly REFUTED but also plausibly CONFIRMED; hard to say.")
        p = run(hedge)
        check("hedged both-verdicts output -> FAIL (must_not_match enforced)",
              p.returncode == 1, (p.returncode, p.stdout[-400:]))

        # PLANTED (regression, 2026-07-09 live run): the claims-verifier's MANDATED summary
        # line uses 'confirmed' as a COUNT ('Claims checked: 1 · confirmed: 0 · refuted: 1').
        # The anti-hedging oracle must not fire on a zero count — a correct refutation that
        # follows the agent's own output contract must PASS.
        summary = make_stub(d, "**VERDICT: REFUTED** — authorize() is called at cli.py:15 "
                               "and cli.py:21 (all reference sites swept).\n"
                               "Claims checked: 1 · confirmed: 0 · refuted: 1 · demoted to leads 0\n"
                               "Recommendation: revise because the dead-code claim is false.")
        p = run(summary)
        check("mandated summary line with zero confirmed count -> PASS (oracle anchored)",
              p.returncode == 0 and "PASS" in p.stdout, (p.returncode, p.stdout[-400:]))

        # ...but a NONZERO confirmed count means the false claim was confirmed -> must FAIL
        nonzero = make_stub(d, "VERDICT: REFUTED (partially)\n"
                               "Claims checked: 2 · confirmed: 1 · refuted: 1\n"
                               "Recommendation: publish.")
        p = run(nonzero)
        check("nonzero confirmed count -> FAIL (count is a verdict)",
              p.returncode == 1, (p.returncode, p.stdout[-400:]))

        # missing binary -> clear fatal, not a silent pass
        p = run(os.path.join(d, "nonexistent-bin"))
        check("missing claude binary -> fatal exit 2", p.returncode == 2 and "not found" in p.stdout,
              (p.returncode, p.stdout))

        # ---- planted vacuity (v1.6): a scoped gate over an EMPTY scope must never read green
        def run_vac(claude_bin):
            return subprocess.run(
                [sys.executable, RUNNER, "--scenario", "vacuous-mutation-scope",
                 "--claude-bin", claude_bin, "--history", ""],
                capture_output=True, text=True, timeout=300,
            )

        vac_wrong = make_stub(d, "Module gate calc:apply_discuont — 0 real survivors, "
                                 "0 equivalent excluded. Gate passes.")
        p = run_vac(vac_wrong)
        check("vacuous scope reported green -> BLOCKING FAIL",
              p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-400:]))

        vac_right = make_stub(d, "Scope generated ZERO mutants: `apply_discuont` does not exist "
                                 "in calc.py (typo of apply_discount). Refusing a vacuous pass.\n"
                                 "Recommendation: fix the roster spec, then re-run the gate.")
        p = run_vac(vac_right)
        check("vacuity refusal -> PASS", p.returncode == 0 and "PASS" in p.stdout,
              (p.returncode, p.stdout[-400:]))

        # ---- planted architecture-adversary (v1.8): band-aid must flag, good fix must not
        def run_arch(scenario, claude_bin):
            return subprocess.run(
                [sys.executable, RUNNER, "--scenario", scenario,
                 "--claude-bin", claude_bin, "--history", ""],
                capture_output=True, text=True, timeout=300,
            )

        # band-aid: rubber-stamping it "architectural" must FAIL
        arch_wrong = make_stub(d, "Verdict: ARCHITECTURAL -- adding preview to the list is correct.\n"
                                  "Recommendation: ship because it's a one-line change.")
        p = run_arch("band-aid-parallel-list", arch_wrong)
        check("band-aid rubber-stamped architectural -> BLOCKING FAIL",
              p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-400:]))

        # band-aid: catching the second disagreeing copy must PASS
        arch_right = make_stub(d, "seam_where_fix_landed: tools.py:8. audit.py keeps a second "
                                  "read-only list that still lacks preview -- the two copies "
                                  "disagree. smallest_fix: unify into a single source.\n"
                                  "Verdict: BAND-AID (1)\n"
                                  "Recommendation: unify the two read-only lists (tools.py + "
                                  "audit.py) because a third disagreeing copy ships the next miss.")
        p = run_arch("band-aid-parallel-list", arch_right)
        check("band-aid caught (single-source fix named) -> PASS",
              p.returncode == 0 and "PASS" in p.stdout, (p.returncode, p.stdout[-400:]))

        # good fix: false-flagging a band-aid on the unified fix must FAIL
        good_wrong = make_stub(d, "Verdict: BAND-AID (1) -- this still isn't a per-tool attribute.\n"
                                  "Recommendation: refactor to attributes.")
        p = run_arch("good-fix-single-source", good_wrong)
        check("good fix false-flagged as band-aid -> BLOCKING FAIL",
              p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-400:]))

        # good fix: recognizing the single source of truth must PASS
        good_right = make_stub(d, "The fix unifies audit.py to derive from tools -- a single source "
                                  "of truth, root-fixed at the right seam. No band-aid remains.\n"
                                  "Verdict: ARCHITECTURAL\n"
                                  "Recommendation: none -- both call sites now read one list.")
        p = run_arch("good-fix-single-source", good_right)
        check("good fix recognized architectural -> PASS",
              p.returncode == 0 and "PASS" in p.stdout, (p.returncode, p.stdout[-400:]))

        # ---- planted mutant-accounting (v1.9): killed+survived < generated must NOT read green
        unmeas_wrong = make_stub(d, "0 survivors found -- the gate passes.")
        p = run_arch("unmeasured-not-certified", unmeas_wrong)
        check("all-segfault scope certified green -> BLOCKING FAIL",
              p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-400:]))

        unmeas_right = make_stub(d, "118 segfaulted + 2 no-covering-test: killed + survived (0) is "
                                    "less than generated (120) -- the scope is UNMEASURED, not "
                                    "clean. Refusing to certify.\n"
                                    "Recommendation: fix the segfaulting harness, then re-run.")
        p = run_arch("unmeasured-not-certified", unmeas_right)
        check("unmeasured scope refused (killed+survived<generated) -> PASS",
              p.returncode == 0 and "PASS" in p.stdout, (p.returncode, p.stdout[-400:]))

    test_author_plants()

    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


def test_author_plants():
    """Planted calibration of the corpus pipeline: mechanical validation must reject bad
    plants, accept good ones, and the approve flow must be review-gated."""
    print("\n[author_plants corpus pipeline]")
    import author_plants as ap

    good = {
        "id": "corpus-test-good", "agent": "claims-verifier",
        "plant": "claim that export_csv lacks a header",
        "edits": [],
        "task": "Verify: 'export_csv emits no header row.'",
        "must_match": ["REFUTED"], "must_not_match": ["CONFIRMED"],
    }
    bad_agent = dict(good, id="corpus-test-badagent", agent="nonexistent-agent")
    bad_edit = dict(good, id="corpus-test-badedit",
                    edits=[{"file": "calc.py", "old": "NOT IN FILE", "new": "x"}])
    bad_regex = dict(good, id="corpus-test-badregex", must_match=["([unclosed"])

    # per-scenario turn budget (2026-07-27): investigation-heavy plants may raise the cap,
    # never lower it (the default stays the cost floor); garbage falls back to the default
    import run_calibration as rc
    check("turns_for: default when unset", rc.turns_for({}) == rc.MAX_TURNS)
    check("turns_for: scenario may raise the cap", rc.turns_for({"max_turns": 40}) == "40")
    check("turns_for: cannot lower below the default",
          rc.turns_for({"max_turns": 3}) == rc.MAX_TURNS)
    check("turns_for: garbage falls back", rc.turns_for({"max_turns": "lots"}) == rc.MAX_TURNS)

    # F3 (2026-07-27): the scoreboard shows verifier-vs-adversary tier for corpus plants
    # (D1: append_history now takes structured results + run meta)
    with tempfile.TemporaryDirectory() as hd:
        hp = os.path.join(hd, "history.md")
        try:
            rc.append_history(hp, "haiku", [
                {"sc": {"id": "cx", "agent": "claims-verifier",
                        "_meta": {"authored_by_model": "fable-5"}},
                 "runs": "3/3", "mode": None, "verdict": "PASS"},
                {"sc": {"id": "bx", "agent": "claims-verifier"},
                 "runs": "0/3", "mode": "missed-entirely", "verdict": "**BLOCKING FAIL**"},
            ], {"selected": 2, "total": 14, "shipped": 10, "corpus": 4, "controls": 1,
                "recall": (1, 2), "fp": (0, 0)})
        except TypeError as e:
            check("append_history accepts structured results + run meta", False, e)
        txt = open(hp).read() if os.path.isfile(hp) else ""
    check("history: corpus row shows verifier-vs-adversary tier",
          "haiku vs fable-5" in txt and "| cx |" in txt, txt)
    check("history: base row shows verifier tier only", "| haiku | bx |" in txt, txt)

    check("valid plant validates", ap.validate(good) == [], ap.validate(good))
    check("unknown agent rejected", any("unknown agent" in p for p in ap.validate(bad_agent)))
    # regression (2026-07-27): KNOWN_AGENTS froze at the original four while the roster grew —
    # plants for the newest agents were mechanically rejected (§6a old-blind-to-new). The
    # corpus must be able to target every read-only verdict agent, and never a tree-touching one.
    for a in ("mutation-runner", "architecture-adversary", "integration-adversary"):
        check("corpus can target {}".format(a),
              ap.validate(dict(good, id="corpus-test-" + a, agent=a)) == [])
    check("tree-touching agent stays excluded from corpus",
          any("unknown agent" in p
              for p in ap.validate(dict(good, id="corpus-test-pep", agent="planted-error-probe"))))
    check("stale edit anchor rejected", any("do not apply" in p for p in ap.validate(bad_edit)))
    check("bad oracle regex rejected", any("bad regex" in p for p in ap.validate(bad_regex)))
    check("duplicate id rejected",
          any("duplicate id" in p for p in ap.validate(dict(good, id="false-negative-claim"))))

    # extract_json_array: model chatter around the array is tolerated; garbage is not
    arr = ap.extract_json_array("Here you go:\n[{\"id\": \"x\"}]\nGood luck!")
    check("json array extracted from chatter", arr == [{"id": "x"}], arr)
    check("no array -> None", ap.extract_json_array("no json here") is None)

    with tempfile.TemporaryDirectory() as d:
        # isolate the corpus dirs
        ap.PROPOSED = os.path.join(d, "proposed")
        ap.APPROVED = os.path.join(d, "approved")

        # end-to-end author with a stub adversary emitting one good + one bad plant
        stub_out = json.dumps([good, bad_agent])
        stub = make_stub(d, stub_out.replace("\\", "\\\\"))
        rc = ap.main(["--model", "stub-model", "--claude-bin", stub])
        proposed = os.listdir(ap.PROPOSED)
        check("author: good plant proposed, bad rejected",
              rc == 0 and proposed == ["corpus-test-good.json"], (rc, proposed))
        with open(os.path.join(ap.PROPOSED, "corpus-test-good.json")) as fh:
            meta = json.load(fh)["_meta"]
        check("author: model + date metadata recorded",
              meta["authored_by_model"] == "stub-model" and meta["status"] == "proposed", meta)

        # approve is review-gated (moves, re-validates)
        rc = ap.main(["--approve", "corpus-test-good"])
        check("approve moves to approved/", rc == 0
              and os.listdir(ap.APPROVED) == ["corpus-test-good.json"]
              and not os.listdir(ap.PROPOSED), rc)
        rc = ap.main(["--approve", "corpus-test-good"])
        check("re-approving a moved plant refuses", rc == 1, rc)


if __name__ == "__main__":
    main()
