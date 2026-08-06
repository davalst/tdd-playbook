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
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)

# Yield isolation (the G5 class, second occurrence 2026-07-28): every run_calibration
# subprocess in this suite triggers the end-of-run gate_yield rollup, which with default
# paths DRAINS the repo's real event log into the repo's real committed record — test
# exhaust masquerading as calibration-cycle data. All subprocesses inherit these.
_YIELD_ISO = tempfile.mkdtemp(prefix="cal-yield-iso-")
os.environ["TDD_PLAYBOOK_YIELD_LOG"] = os.path.join(_YIELD_ISO, "raw.jsonl")
os.environ["TDD_PLAYBOOK_YIELD_MD"] = os.path.join(_YIELD_ISO, "gate_yield.md")
_REPO_YIELD_MD = os.path.join(os.path.dirname(HERE), "docs", "calibration", "gate_yield.md")
_REPO_YIELD_MD_BEFORE = (open(_REPO_YIELD_MD, "rb").read()
                         if os.path.isfile(_REPO_YIELD_MD) else None)

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


def _d2_control_tests():
    """PLANTED (D2/R2): a suite with one clean control measures recall and calls it quality —
    a verifier that flags everything scores 13/14. Controls must be structurally enforced:
    schema rules in THE validator, pairing as a set-level invariant on the release-gate path
    (a plant hand-dropped into scenarios.json or corpus/approved/ must be caught there, not
    only at --approve)."""
    print("\n[D2 paired controls]")
    import run_calibration as rc

    plant = {"id": "d2-plant", "agent": "claims-verifier", "plant": "p", "task": "t",
             "must_match": ["REFUTED"]}
    control = {"id": "d2-control", "agent": "claims-verifier", "plant": "clean control",
               "task": "t", "must_match": ["CONFIRMED"], "must_not_match": ["REFUTED"],
               "control_for": "d2-plant"}

    check("control: valid pair member validates",
          rc.validate_scenario(control, set()) == [], rc.validate_scenario(control, set()))
    no_alarm = {k: v for k, v in control.items() if k != "must_not_match"}
    check("control missing must_not_match (alarm verdict) rejected",
          any("must_not_match" in p for p in rc.validate_scenario(no_alarm, set())),
          rc.validate_scenario(no_alarm, set()))
    selfref = dict(control, control_for="d2-control")
    check("control_for self-reference rejected",
          any("self" in p for p in rc.validate_scenario(selfref, set())),
          rc.validate_scenario(selfref, set()))

    if not hasattr(rc, "pairing_problems"):
        check("run_calibration.pairing_problems exists (set-level invariant)", False, "missing")
        return
    check("pairing: unpaired non-grandfathered plant flagged",
          any("unpaired" in p for p in rc.pairing_problems([plant])),
          rc.pairing_problems([plant]))
    check("pairing: paired plant clean", rc.pairing_problems([plant, control]) == [],
          rc.pairing_problems([plant, control]))
    orphan = dict(control, id="d2-orphan", control_for="no-such-plant")
    check("pairing: control referencing unknown plant flagged",
          any("unknown" in p for p in rc.pairing_problems([orphan])),
          rc.pairing_problems([orphan]))

    # the grandfather list is SELF-CLEANING: every entry must be a real plant that still
    # lacks a control — a paired or vanished id left in the list fails here, so the list
    # can only shrink as the backfill lands
    all_real = rc.load_scenarios() + rc.load_corpus()
    real_ids = {s["id"] for s in all_real}
    paired_ids = {s.get("control_for") for s in all_real if s.get("control_for")}
    stale_gf = [i for i in rc.GRANDFATHERED_PLANT_IDS
                if i not in real_ids or i in paired_ids]
    check("grandfather list self-cleaning (entries exist and are still unpaired)",
          stale_gf == [], stale_gf)
    check("shipped suite passes the pairing invariant (grandfather covers the rest)",
          rc.pairing_problems(all_real) == [], rc.pairing_problems(all_real))
    check("activation: good-fix-single-source is control_for band-aid-parallel-list",
          any(s["id"] == "good-fix-single-source"
              and s.get("control_for") == "band-aid-parallel-list"
              for s in rc.load_scenarios()))

    # PLANTED (hole 3, 2026-07-28): the pair quota must not be bypassable by ADDING a plant
    # id to the grandfather list — the set is pinned exactly; it may only lose members
    check("grandfather list pinned to the 4 pre-quota corpus plants (shrink-only)",
          rc.GRANDFATHERED_PLANT_IDS == {
              "csv-escape-fixed-at-call-site", "dead-export-claim-cmd-indirection",
              "shadowed-import-vacuous-suite", "special-case-bypasses-both-copies"},
          rc.GRANDFATHERED_PLANT_IDS)

    # dry_run carries the invariant (release-gate path) even for a synthetic corpus
    orig_ls, orig_lc = rc.load_scenarios, rc.load_corpus
    try:
        rc.load_scenarios = lambda: [dict(plant)]
        rc.load_corpus = lambda: []
        code = rc.dry_run([dict(plant)])
    finally:
        rc.load_scenarios, rc.load_corpus = orig_ls, orig_lc
    check("PLANTED unpaired plant fails dry-run (set-level, release-gate path)", code == 1,
          code)

    # the adversary brief demands pairs and documents the field
    import author_plants as ap
    prompt = ap.adversary_prompt(None)
    check("adversary brief demands plant+control pairs",
          "control_for" in prompt and "pair" in prompt.lower(), prompt[:400])
    check("CATEGORIES gained the script/runtime-safety class (script-adversary pairable)",
          "script" in ap.CATEGORIES, ap.CATEGORIES)


def _d2_fp_scoreboard_tests(d):
    """PLANTED (D2): a control the verifier wrongly flags must surface as FP, not vanish."""
    def run_ctrl(claude_bin, hist):
        return subprocess.run(
            [sys.executable, RUNNER, "--scenario", "good-fix-single-source",
             "--claude-bin", claude_bin, "--history", hist],
            capture_output=True, text=True, timeout=300)

    trigger_happy = make_stub(d, "Verdict: BAND-AID (1) -- this still isn't a per-tool "
                                 "attribute.\nRecommendation: refactor to attributes.")
    hp = os.path.join(d, "h-fp.md")
    p = run_ctrl(trigger_happy, hp)
    txt = open(hp).read()
    check("PLANTED trigger-happy verifier on a control -> FP 1/1, exit nonzero",
          p.returncode == 1 and "FP 1/1" in txt and "recall 0/0" in txt, (p.returncode, txt))

    quiet_right = make_stub(d, "The fix unifies audit.py to derive from tools -- a single "
                               "source of truth, root-fixed at the right seam.\n"
                               "Verdict: ARCHITECTURAL\nRecommendation: none.")
    hp = os.path.join(d, "h-fp0.md")
    p = run_ctrl(quiet_right, hp)
    txt = open(hp).read()
    check("correctly quiet on the control -> FP 0/1, exit 0",
          p.returncode == 0 and "FP 0/1" in txt, (p.returncode, txt))


def _d3_integrity_tests():
    """PLANTED (D3): the scoreboard's write path was forgeable by any session agent — edited
    rows, deleted corpus plants, loosened oracles. The reference checker must turn each forge
    into a nonzero exit against a git baseline: 0 clean · 2 integrity_red · 3 baseline
    unreadable (fail closed, never a silent pass)."""
    print("\n[D3 scoreboard integrity]")
    ck = os.path.join(HERE, "check_scoreboard_integrity.py")
    if not os.path.isfile(ck):
        check("check_scoreboard_integrity.py exists", False, "missing")
        return

    def scratch_repo(d):
        os.makedirs(os.path.join(d, "docs", "calibration"))
        os.makedirs(os.path.join(d, "calibration", "corpus", "approved"))
        with open(os.path.join(d, "docs", "calibration", "history.md"), "w") as fh:
            fh.write("# Calibration history\n\n| 2026-07-27 | haiku | s1 | a1 | PASS |\n")
        with open(os.path.join(d, "calibration", "scenarios.json"), "w") as fh:
            json.dump({"scenarios": [
                {"id": "s1", "agent": "a1", "plant": "p", "task": "t",
                 "must_match": ["REFUTED", "confirmed:?\\s*0"],
                 "must_not_match": ["confirmed:?\\s*[1-9]"]},
            ]}, fh)
        with open(os.path.join(d, "calibration", "corpus", "approved", "c1.json"), "w") as fh:
            json.dump({"id": "c1", "agent": "a1", "plant": "p", "task": "t",
                       "must_match": ["X"]}, fh)
        with open(os.path.join(d, "calibration", "oracle-changes.md"), "w") as fh:
            fh.write("# Oracle change journal (append-only)\n")

        def git(*a):
            subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, timeout=30)
        git("init", "-q")
        git("config", "user.email", "t@t")
        git("config", "user.name", "t")
        git("add", "-A")
        git("commit", "-qm", "baseline")
        return d

    def run_ck(repo, rev="HEAD"):
        return subprocess.run([sys.executable, ck, "--repo", repo, "--baseline-rev", rev],
                              capture_output=True, text=True, timeout=60)

    def path_in(d, *parts):
        return os.path.join(d, *parts)

    with tempfile.TemporaryDirectory() as d:
        scratch_repo(d)
        check("integrity: unchanged tree -> 0", run_ck(d).returncode == 0,
              (run_ck(d).returncode, run_ck(d).stdout, run_ck(d).stderr))

        # appended history rows are the normal case
        with open(path_in(d, "docs", "calibration", "history.md"), "a") as fh:
            fh.write("| 2026-08-10 | haiku | s1 | a1 | PASS |\n")
        check("integrity: appended history rows -> 0", run_ck(d).returncode == 0,
              run_ck(d).stdout)

        # PLANTED: an EDITED old row breaks the byte-prefix rule
        hp = path_in(d, "docs", "calibration", "history.md")
        body = open(hp).read().replace("| 2026-07-27 | haiku | s1 | a1 | PASS |",
                                       "| 2026-07-27 | haiku | s1 | a1 | **BLOCKING FAIL** |")
        with open(hp, "w") as fh:
            fh.write(body)
        p = run_ck(d)
        check("integrity: PLANTED edited old history row -> 2 (forged scoreboard)",
              p.returncode == 2, (p.returncode, p.stdout))

    with tempfile.TemporaryDirectory() as d:
        scratch_repo(d)
        # PLANTED: a deleted approved corpus plant (the corpus 'only grows')
        os.remove(path_in(d, "calibration", "corpus", "approved", "c1.json"))
        p = run_ck(d)
        check("integrity: PLANTED deleted corpus plant -> 2", p.returncode == 2,
              (p.returncode, p.stdout))

    with tempfile.TemporaryDirectory() as d:
        scratch_repo(d)
        # PLANTED: a MODIFIED approved corpus plant (append-only means immutable)
        cp = path_in(d, "calibration", "corpus", "approved", "c1.json")
        with open(cp) as fh:
            sc = json.load(fh)
        sc["must_match"] = ["X|.*"]
        with open(cp, "w") as fh:
            json.dump(sc, fh)
        p = run_ck(d)
        check("integrity: PLANTED modified corpus plant -> 2", p.returncode == 2,
              (p.returncode, p.stdout))
        # a NEW corpus plant is growth, not tampering
        with open(path_in(d, "calibration", "corpus", "approved", "c2.json"), "w") as fh:
            json.dump({"id": "c2", "agent": "a1", "plant": "p", "task": "t",
                       "must_match": ["Y"]}, fh)
        with open(cp, "w") as fh:
            json.dump({"id": "c1", "agent": "a1", "plant": "p", "task": "t",
                       "must_match": ["X"]}, fh)
        check("integrity: new corpus plant -> 0 (corpus grows)",
              run_ck(d).returncode == 0, run_ck(d).stdout)

    with tempfile.TemporaryDirectory() as d:
        scratch_repo(d)
        sp = path_in(d, "calibration", "scenarios.json")

        def write_scenarios(must_match, must_not_match, extra=None):
            scs = [{"id": "s1", "agent": "a1", "plant": "p", "task": "t",
                    "must_match": must_match, "must_not_match": must_not_match}]
            if extra:
                scs.append(extra)
            with open(sp, "w") as fh:
                json.dump({"scenarios": scs}, fh)

        # PLANTED: a REMOVED oracle regex without a journal entry is test-weakening one
        # level up
        write_scenarios(["REFUTED"], ["confirmed:?\\s*[1-9]"])
        p = run_ck(d)
        check("integrity: PLANTED oracle regex removed, no journal -> 2",
              p.returncode == 2, (p.returncode, p.stdout))

        # the same change WITH a journaled reason (appended since baseline) passes — and the
        # additions are PRINTED (hole 4 visibility: a self-journaled weakening must at least
        # be loud, since the journal mechanically authorizes whoever writes it)
        with open(path_in(d, "calibration", "oracle-changes.md"), "a") as fh:
            fh.write("- 2026-08-10 · s1 · dropped the count regex: false-fired on the "
                     "mandated summary line\n")
        p = run_ck(d)
        check("integrity: journaled oracle change -> 0", p.returncode == 0, p.stdout)
        check("integrity: journal additions since baseline printed loudly",
              "dropped the count regex" in p.stdout and "journal" in p.stdout.lower(),
              p.stdout)

        # PLANTED: a TRUNCATED journal cannot authorize anything (append-only applies to
        # the journal itself)
        with open(path_in(d, "calibration", "oracle-changes.md"), "w") as fh:
            fh.write("- 2026-08-10 · s1 · dropped the count regex\n")
        p = run_ck(d)
        check("integrity: PLANTED truncated journal -> 2", p.returncode == 2,
              (p.returncode, p.stdout))

    with tempfile.TemporaryDirectory() as d:
        scratch_repo(d)
        sp = path_in(d, "calibration", "scenarios.json")
        # pure additions pass: a new regex on an existing scenario + a new scenario
        with open(sp) as fh:
            data = json.load(fh)
        data["scenarios"][0]["must_match"].append("swept")
        data["scenarios"].append({"id": "s2", "agent": "a1", "plant": "p", "task": "t",
                                  "must_match": ["Z"]})
        with open(sp, "w") as fh:
            json.dump(data, fh)
        check("integrity: tightened oracle + new scenario -> 0 (directional rule)",
              run_ck(d).returncode == 0, run_ck(d).stdout)
        # PLANTED: a scenario REMOVED entirely without a journal entry
        with open(sp, "w") as fh:
            json.dump({"scenarios": [{"id": "s2", "agent": "a1", "plant": "p", "task": "t",
                                      "must_match": ["Z"]}]}, fh)
        p = run_ck(d)
        check("integrity: PLANTED scenario removed, no journal -> 2", p.returncode == 2,
              (p.returncode, p.stdout))

    with tempfile.TemporaryDirectory() as d:
        scratch_repo(d)
        p = run_ck(d, rev="no-such-rev")
        check("integrity: unreadable baseline -> 3 (fail closed, never a silent pass)",
              p.returncode == 3, (p.returncode, p.stdout, p.stderr))

    # G11 — the suite, which IS mechanically gated, carries the real-repo check: HEAD vs
    # the latest release tag must be integrity-clean (skip loudly if tags are absent)
    repo_root = os.path.dirname(HERE)
    tag = subprocess.run(["git", "-C", repo_root, "describe", "--tags", "--abbrev=0"],
                         capture_output=True, text=True, timeout=30)
    if tag.returncode == 0 and tag.stdout.strip():
        p = subprocess.run([sys.executable, ck, "--repo", repo_root,
                           "--baseline-rev", tag.stdout.strip()],
                          capture_output=True, text=True, timeout=120)
        check("integrity: THIS repo vs {} -> 0".format(tag.stdout.strip()),
              p.returncode == 0, (p.returncode, p.stdout, p.stderr))
    else:
        print("  note - no release tag resolvable here; real-repo integrity check skipped "
              "(runs on tagged clones)")


def _coverage_invariant_tests():
    """PLANTED (D1, lift/ratchet): the deletion-ratchet's R1 part 1 — every headless-
    calibratable agent needs >=1 PLANT (controls don't count: plants define coverage).
    Lands RED on integration-adversary (the behavioral gap: a softened brief keeps its
    verdict lines while losing its rules, and without a live plant nothing sees it)."""
    print("\n[coverage invariant (R1 part 1)]")
    import run_calibration as rc
    import author_plants as ap
    if not hasattr(rc, "agent_coverage_problems"):
        check("run_calibration.agent_coverage_problems exists", False, "missing")
        return

    plant = {"id": "cov-p", "agent": "claims-verifier", "plant": "p", "task": "t",
             "must_match": ["X"]}
    ctl = {"id": "cov-c", "agent": "script-adversary", "plant": "c", "task": "t",
           "must_match": ["Y"], "must_not_match": ["Z"], "control_for": "cov-p"}
    agents = {"claims-verifier", "script-adversary"}
    check("coverage: plant covers its agent",
          rc.agent_coverage_problems([plant], agents={"claims-verifier"}) == [])
    check("coverage: uncovered agent flagged",
          any("script-adversary" in p
              for p in rc.agent_coverage_problems([plant], agents=agents)))
    check("coverage: a CONTROL does not cover (plants define coverage)",
          any("script-adversary" in p
              for p in rc.agent_coverage_problems([plant, ctl], agents=agents)))

    # the real suite must be clean — RED until the island pair lands (introduction-RED)
    all_real = rc.load_scenarios() + rc.load_corpus()
    check("real suite: every calibratable agent has a plant (island pair closes this)",
          rc.agent_coverage_problems(all_real) == [],
          rc.agent_coverage_problems(all_real))

    # dry_run carries it on the FULL reloaded set (filter-defeat, like pairing)
    orig_ls, orig_lc = rc.load_scenarios, rc.load_corpus
    try:
        rc.load_scenarios = lambda: [dict(plant)]
        rc.load_corpus = lambda: []
        code = rc.dry_run([dict(plant)])
    finally:
        rc.load_scenarios, rc.load_corpus = orig_ls, orig_lc
    check("PLANTED uncovered roster fails dry-run (set-level, release-gate path)",
          code == 1, code)

    # the authoring loop is the invariant's consumer: uncovered agents are named as
    # priority targets in the adversary brief
    # isolation covers BOTH coverage sources: since v1.24 the proposed corpus can also
    # cover an agent (the first §6c authoring batch covers integration-adversary), so
    # filtering shipped scenarios alone no longer creates uncoveredness
    orig_ap_ls, orig_ap_cs = ap.load_scenarios, ap.corpus_scenarios
    try:
        ap.load_scenarios = lambda: [s for s in orig_ap_ls()
                                     if s["agent"] != "integration-adversary"]
        ap.corpus_scenarios = lambda states=("proposed", "approved"): [
            s for s in orig_ap_cs(states) if s["agent"] != "integration-adversary"]
        prompt = ap.adversary_prompt(None)
    finally:
        ap.load_scenarios, ap.corpus_scenarios = orig_ap_ls, orig_ap_cs
    check("adversary brief names uncovered agents as priority targets",
          "uncovered" in prompt.lower() and "integration-adversary" in
          prompt.split("uncovered", 1)[-1][:300], prompt[:200])


def _lift_ratchet_scenario_tests(d):
    """PLANTED (D1+D2): stub wrong/right verdicts for the four new plants + controls —
    oracles anchored on HOUSE contracts (Verdict: CONNECTED/ISLANDS, NOT VERIFIED,
    UNMEASURED), never task-invented formats."""
    print("\n[lift/ratchet scenario stubs]")

    def run_sc(scenario, claude_bin):
        return subprocess.run(
            [sys.executable, RUNNER, "--scenario", scenario,
             "--claude-bin", claude_bin, "--history", ""],
            capture_output=True, text=True, timeout=300)

    # island pair (integration-adversary)
    lazy = make_stub(d, "Everything in the plan connects fine.\nVerdict: CONNECTED\n"
                        "Recommendation: ship because the surface list looks complete.")
    p = run_sc("island-write-only-plan", lazy)
    check("island plant: CONNECTED on a write-only emitter -> BLOCKING FAIL",
          p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-300:]))
    sharp = make_stub(d, "The audit_events topic is emitted by the exporter and consumed by "
                         "NOTHING — a write-only island.\nVerdict: ISLANDS (1)\n"
                         "Recommendation: name the consumer for audit_events because the "
                         "exporter seam goes dark without it.")
    p = run_sc("island-write-only-plan", sharp)
    check("island plant: ISLANDS named -> PASS",
          p.returncode == 0 and "PASS" in p.stdout, (p.returncode, p.stdout[-300:]))
    fp = make_stub(d, "I distrust plans on principle.\nVerdict: ISLANDS (2)\n"
                      "Recommendation: block because something must be dark.")
    p = run_sc("control-connected-plan", fp)
    check("island control: ISLANDS invented on a connected plan -> BLOCKING FAIL (FP)",
          p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-300:]))
    ok = make_stub(d, "Emitter names its consumer, activation stated, reverse sweep clean.\n"
                      "Verdict: CONNECTED\nRecommendation: ship because every emitted "
                      "topic names a live consumer.")
    p = run_sc("control-connected-plan", ok)
    check("island control: CONNECTED on a connected plan -> PASS",
          p.returncode == 0 and "PASS" in p.stdout, (p.returncode, p.stdout[-300:]))

    # red-first symmetric break (fails BOTH sides proves nothing)
    fooled = make_stub(d, "The test fails without the fix — RED-FIRST: VERIFIED "
                          "(fails-without confirmed).\nRecommendation: trust it.")
    p = run_sc("red-first-symmetric-break", fooled)
    check("symmetric-break plant: VERIFIED on a fails-both-sides test -> BLOCKING FAIL",
          p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-300:]))
    right = make_stub(d, "The test fails on BOTH sides (NameError pre- and post-fix) — a "
                         "check that never sees green proves nothing about red-first.\n"
                         "NOT VERIFIED — the failure is a collection error, not the "
                         "claimed behavior.\nRecommendation: fix the test's import, then "
                         "re-verify.")
    p = run_sc("red-first-symmetric-break", right)
    check("symmetric-break plant: NOT VERIFIED for the right reason -> PASS",
          p.returncode == 0 and "PASS" in p.stdout, (p.returncode, p.stdout[-300:]))
    ctl_fp = make_stub(d, "Suspicious of everything.\nNOT VERIFIED.\nRecommendation: rewrite.")
    p = run_sc("control-assert-red-then-green", ctl_fp)
    check("symmetric-break control: NOT VERIFIED on a genuine red->green -> BLOCKING FAIL",
          p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-300:]))
    ctl_ok = make_stub(d, "Fails pre-fix with AssertionError on the real behavior, passes "
                          "post-fix.\nRED-FIRST: VERIFIED (fails-without / passes-with, "
                          "both quoted).\nRecommendation: trust it.")
    p = run_sc("control-assert-red-then-green", ctl_ok)
    check("symmetric-break control: VERIFIED -> PASS",
          p.returncode == 0 and "PASS" in p.stdout, (p.returncode, p.stdout[-300:]))

    # phantom mutation run (stale-bytecode signature)
    certifier = make_stub(d, "156 generated, all killed on both mutants — gate passes.")
    p = run_sc("mutation-phantom-run", certifier)
    check("phantom plant: certifying identical-results-no-cachebust -> BLOCKING FAIL",
          p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-300:]))
    refuser = make_stub(d, "Two DIFFERENT mutants produced byte-identical results with "
                           "same-second timestamps and no cache-busting — the stale-pyc "
                           "phantom signature: the mutants never ran. The scope is "
                           "UNMEASURED, not clean.\nRecommendation: delete __pycache__ per "
                           "mutant (or PYTHONDONTWRITEBYTECODE=1), then re-run.")
    p = run_sc("mutation-phantom-run", refuser)
    check("phantom plant: UNMEASURED refusal -> PASS",
          p.returncode == 0 and "PASS" in p.stdout, (p.returncode, p.stdout[-300:]))
    ctl2_fp = make_stub(d, "Same-second timestamps somewhere — UNMEASURED, refusing "
                           "everything.\nRecommendation: re-run forever.")
    p = run_sc("control-cachebusted-run", ctl2_fp)
    check("phantom control: refusing a cache-busted differing run -> BLOCKING FAIL (FP)",
          p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-300:]))
    ctl2_ok = make_stub(d, "Cache cleared per mutant, results differ across mutants, "
                           "killed + survived == generated — the run measured. Gate "
                           "passes.\nRecommendation: none.")
    p = run_sc("control-cachebusted-run", ctl2_ok)
    check("phantom control: certifying a genuine measured run -> PASS",
          p.returncode == 0 and "PASS" in p.stdout, (p.returncode, p.stdout[-300:]))



def _promotion_quarantine_tests():
    """CIVerd engine finding, 2026-08-05: the AMBER->BLOCKING promotion is MECHANICAL, so
    a scenario whose oracle is known-defective promotes a known-FALSE failure to BLOCKING
    on its second consecutive AMBER — hardening noise into policy while the real fix waits.
    Three such scenarios exist: v1.22.0-BASELINE plants whose oracles are proven wrong (one
    regex cannot match the word "survives") and which the integrity floor forbids editing,
    so superseding is the only sanctioned path and it is dated debt.

    The quarantine pauses PROMOTION ONLY. Matching, scoring, rep counts and the AMBER
    verdict itself are untouched, so the ten predictions in flight are measured against a
    byte-identical instrument. It is a dated exemption in the house shape: expired means
    it stops protecting AND is reported."""
    print("\n[promotion quarantine]")
    import run_calibration as rc
    live = datetime.date(2026, 8, 6)
    past = datetime.date(2026, 9, 16)
    q = rc.PROMOTION_QUARANTINE[0]["target"]

    check("quarantine: a known-defective scenario is NOT promoted on a second AMBER",
          rc.verdict_for(q, 1, 3, "AMBER", today=live) == "AMBER",
          rc.verdict_for(q, 1, 3, "AMBER", today=live))
    check("quarantine: an ordinary scenario IS still promoted on a second AMBER",
          rc.verdict_for("not-quarantined-scenario", 1, 3, "AMBER", today=live)
          == "**BLOCKING FAIL** (AMBER\u00d72)",
          rc.verdict_for("not-quarantined-scenario", 1, 3, "AMBER", today=live))
    check("quarantine: it never rescues a total miss (0/3 stays BLOCKING)",
          rc.verdict_for(q, 0, 3, "AMBER", today=live) == "**BLOCKING FAIL**")
    check("quarantine: it never manufactures a pass (3/3 is PASS, 1/3 first-time AMBER)",
          rc.verdict_for(q, 3, 3, "PASS", today=live) == "PASS"
          and rc.verdict_for(q, 1, 3, "PASS", today=live) == "AMBER")
    check("quarantine: EXPIRED stops protecting — promotion resumes",
          rc.verdict_for(q, 1, 3, "AMBER", today=past) == "**BLOCKING FAIL** (AMBER\u00d72)",
          rc.verdict_for(q, 1, 3, "AMBER", today=past))
    check("quarantine: EXPIRED is REPORTED, not silent",
          any(q in p for p in rc.quarantine_problems(past)),
          rc.quarantine_problems(past))
    check("quarantine: live quarantine reports no problem",
          rc.quarantine_problems(live) == [], rc.quarantine_problems(live))
    check("quarantine: every entry carries the house debt shape (what/target/owner/expires)",
          all(set(("what", "target", "owner", "expires")).issubset(e)
              for e in rc.PROMOTION_QUARANTINE), rc.PROMOTION_QUARANTINE)
    check("quarantine: covers ONLY the immutable baseline plants it names, not the "
          "scenarios with pending predictions",
          {e["target"] for e in rc.PROMOTION_QUARANTINE}
          == {"shadowed-import-vacuous-suite", "csv-escape-fixed-at-call-site",
              "special-case-bypasses-both-copies"},
          {e["target"] for e in rc.PROMOTION_QUARANTINE})


def _wilson_tests():
    """PLANTED (D4): `recall 9/9` implies certainty we don't have — at 3 reps, 3/3 is
    consistent with a true rate from ~0.44 to 1.0. wilson() is a pure statistic (the
    format module only RENDERS it); both the file header and the stdout summary carry it."""
    print("\n[wilson intervals]")
    import history_format as hfmt
    if not hasattr(hfmt, "wilson"):
        check("history_format.wilson exists", False, "missing")
        return
    lo, hi = hfmt.wilson(3, 3)
    check("wilson(3,3): wide at n=3 (certainty not implied)",
          0.40 < lo < 0.50 and hi == 1.0, (lo, hi))
    lo, hi = hfmt.wilson(0, 10)
    check("wilson(0,10): lower bound 0", lo == 0.0 and 0.20 < hi < 0.35, (lo, hi))
    check("wilson(0,0): undefined -> None (renders as [—])", hfmt.wilson(0, 0) is None)
    lo, hi = hfmt.wilson(13, 14)
    check("wilson(13,14) sane", 0.60 < lo < 0.75 and 0.95 < hi <= 1.0, (lo, hi))

    with tempfile.TemporaryDirectory() as d:
        hp = os.path.join(d, "history.md")
        hfmt.append_run_block(hp, {"date": "2026-08-10", "model": "haiku",
                                   "repo_sha": "abc1234", "selected": 1, "total": 30,
                                   "shipped": 26, "corpus": 4, "controls": 13,
                                   "recall": (3, 3), "fp": (0, 0)},
                              [{"date": "2026-08-10", "model_cell": "haiku",
                                "scenario": "s", "agent": "a", "runs": "3/3",
                                "mode": None, "verdict": "PASS"}])
        txt = open(hp).read()
        check("header renders recall interval", "recall 3/3 [" in txt, txt)
        check("zero-denominator FP renders [—]", "FP 0/0 [—]" in txt, txt)
        check("rows still parse (format compat)",
              len(hfmt.parse_rows(txt)) == 1 and hfmt.parse_rows(txt)[0]["kind"] == "PASS",
              txt)


def _quarterly_clock_tests():
    """PLANTED (D6): the quarterly bundle (catalog refresh · lift read · cross-tier row)
    gets a REAL clock — a dated record checked by the existing staleness gate — replacing
    the draft's print-string clause (a reminder inside a run David must remember to run is
    decoration, and refreshing the catalog would have silenced an unrelated reminder)."""
    print("\n[quarterly clock]")
    import run_calibration as rc
    cs = os.path.join(HERE, "check_staleness.py")
    q = os.path.join(os.path.dirname(HERE), "docs", "calibration", "quarterly.md")
    check("docs/calibration/quarterly.md exists and is dated",
          os.path.isfile(q) and __import__("history_format").latest_run_date(
              open(q).read()) is not None, q)

    def run_q(as_of):
        return subprocess.run([sys.executable, cs, "--history", q, "--as-of", as_of,
                               "--max-age-days", "100"],
                              capture_output=True, text=True, timeout=30).returncode
    check("quarterly: fresh within 100d -> 0", run_q("2026-08-30") == 0,
          run_q("2026-08-30"))
    check("quarterly: PLANTED stale past 100d -> 1", run_q("2026-11-15") == 1,
          run_q("2026-11-15"))

    # catalog_staleness gains an injectable today (G4: was real-clock-only, untestable)
    try:
        stale_at = rc.catalog_staleness(today=__import__("datetime").date(2026, 11, 15))
        fresh_at = rc.catalog_staleness(today=__import__("datetime").date(2026, 8, 1))
        check("catalog_staleness(today=...) injectable: fires past 100d, silent before",
              stale_at is not None and stale_at > 100
              and fresh_at is not None and fresh_at <= 100, (stale_at, fresh_at))
    except TypeError as e:
        check("catalog_staleness accepts today=", False, e)


def _weak_plant_flag_tests(d):
    """PLANTED (2026-07-28 sweep): a plant that has NEVER failed across recorded live runs
    teaches nothing — an adversary authoring easy plants inflates recall while the gate
    decays. The runner must flag the streak mechanically (risk-3 made a mechanism)."""
    print("\n[weak-plant streak flag]")
    import history_format as hfmt

    def run_hist(claude_bin, hist):
        return subprocess.run(
            [sys.executable, RUNNER, "--scenario", "false-negative-claim",
             "--claude-bin", claude_bin, "--history", hist],
            capture_output=True, text=True, timeout=300)

    def seed(hp, verdicts):
        for i, v in enumerate(verdicts):
            date = "2026-07-{:02d}".format(10 + i)
            hfmt.append_run_block(hp, {"date": date, "model": "haiku", "repo_sha": "0000000",
                                       "selected": 1, "total": 24, "shipped": 20,
                                       "corpus": 4, "controls": 10, "recall": (1, 1),
                                       "fp": (0, 0)},
                                  [{"date": date, "model_cell": "haiku",
                                    "scenario": "false-negative-claim",
                                    "agent": "claims-verifier",
                                    "runs": "3/3" if v == "PASS" else "0/3",
                                    "mode": None if v == "PASS" else "missed-entirely",
                                    "verdict": v}])

    stub, _ = make_sequence_stub(d, [OUT_RIGHT], "stub-weakflag")
    hp = os.path.join(d, "h-weakflag.md")
    seed(hp, ["PASS", "PASS"])
    p = run_hist(stub, hp)
    check("never-failed plant across >=3 runs -> WEAK-PLANT flag printed",
          p.returncode == 0 and "WEAK-PLANT" in p.stdout
          and "false-negative-claim" in p.stdout, (p.returncode, p.stdout[-500:]))

    stub, _ = make_sequence_stub(d, [OUT_RIGHT], "stub-noflag")
    hp = os.path.join(d, "h-noflag.md")
    seed(hp, ["PASS", "**BLOCKING FAIL**"])
    p = run_hist(stub, hp)
    check("plant with a recorded failure -> no weak-plant flag",
          p.returncode == 0 and "WEAK-PLANT" not in p.stdout, p.stdout[-300:])


def _rule_d_gate_surface_tests():
    """PLANTED (D3, lift/ratchet): gate removal must cost what addition costs — SKILL.md
    `## ` headings, agents/*.md, and commands/*.md removed vs baseline are RED unless named
    in gate-changes.md's added-since-baseline text. Additions stay FREE (R1's asymmetry:
    the draft's exact-set pin taxed new doctrine at the removal rate — wrong). Closes the
    live 7-of-11 hole: most command files were silently deletable."""
    print("\n[D3 gate-surface removal rule (d)]")
    ck = os.path.join(HERE, "check_scoreboard_integrity.py")

    def scratch(d):
        os.makedirs(os.path.join(d, "docs", "calibration"))
        os.makedirs(os.path.join(d, "calibration", "corpus", "approved"))
        os.makedirs(os.path.join(d, "plugins", "tdd-playbook", "skills", "tdd-playbook"))
        os.makedirs(os.path.join(d, "plugins", "tdd-playbook", "agents"))
        os.makedirs(os.path.join(d, "plugins", "tdd-playbook", "commands"))
        with open(os.path.join(d, "docs", "calibration", "history.md"), "w") as fh:
            fh.write("# Calibration history\n")
        with open(os.path.join(d, "calibration", "scenarios.json"), "w") as fh:
            json.dump({"scenarios": [{"id": "s1", "agent": "a1", "plant": "p", "task": "t",
                                      "must_match": ["X"]}]}, fh)
        with open(os.path.join(d, "calibration", "oracle-changes.md"), "w") as fh:
            fh.write("# Oracle change journal\n")
        with open(os.path.join(d, "calibration", "gate-changes.md"), "w") as fh:
            fh.write("# Gate change journal (append-only)\n")
        skill = os.path.join(d, "plugins", "tdd-playbook", "skills", "tdd-playbook",
                             "SKILL.md")
        with open(skill, "w") as fh:
            fh.write("# T\n## 1. Loop\nbody\n## 2. Edges\nbody\n## 13. Learning\nbody\n")
        for a in ("alpha-agent.md", "beta-agent.md"):
            with open(os.path.join(d, "plugins", "tdd-playbook", "agents", a), "w") as fh:
                fh.write("---\nname: x\n---\nbrief\n")
        for c in ("edge.md", "mutate.md"):
            with open(os.path.join(d, "plugins", "tdd-playbook", "commands", c), "w") as fh:
                fh.write("command\n")

        def git(*a):
            subprocess.run(["git", "-C", d, *a], capture_output=True, text=True, timeout=30)
        git("init", "-q")
        git("config", "user.email", "t@t")
        git("config", "user.name", "t")
        git("add", "-A")
        git("commit", "-qm", "baseline")
        return d

    def run_ck(repo):
        return subprocess.run([sys.executable, ck, "--repo", repo, "--baseline-rev", "HEAD"],
                              capture_output=True, text=True, timeout=60)

    with tempfile.TemporaryDirectory() as d:
        scratch(d)
        check("rule d: unchanged gate surfaces -> 0", run_ck(d).returncode == 0,
              (run_ck(d).returncode, run_ck(d).stdout, run_ck(d).stderr))

        skill = os.path.join(d, "plugins", "tdd-playbook", "skills", "tdd-playbook",
                             "SKILL.md")
        # additions are FREE — new doctrine must never pay the removal toll
        with open(skill, "a") as fh:
            fh.write("## 14. New doctrine\nbody\n")
        with open(os.path.join(d, "plugins", "tdd-playbook", "agents", "new-agent.md"),
                  "w") as fh:
            fh.write("---\nname: n\n---\nbrief\n")
        check("rule d: heading + agent ADDED -> 0 (asymmetry preserved)",
              run_ck(d).returncode == 0, run_ck(d).stdout)

        # PLANTED: SKILL heading removed, unjournaled -> RED
        body = open(skill).read().replace("## 2. Edges\nbody\n", "")
        with open(skill, "w") as fh:
            fh.write(body)
        p = run_ck(d)
        check("rule d: PLANTED heading removed unjournaled -> 2",
              p.returncode == 2 and "2. Edges" in p.stdout, (p.returncode, p.stdout))
        # journaled -> authorized
        with open(os.path.join(d, "calibration", "gate-changes.md"), "a") as fh:
            fh.write("- 2026-07-30 · SKILL section '## 2. Edges' folded into '## 1. Loop' "
                     "· dedupe\n")
        check("rule d: journaled heading removal -> 0", run_ck(d).returncode == 0,
              run_ck(d).stdout)

    with tempfile.TemporaryDirectory() as d:
        scratch(d)
        # PLANTED: agent brief deleted unjournaled -> RED
        os.remove(os.path.join(d, "plugins", "tdd-playbook", "agents", "beta-agent.md"))
        p = run_ck(d)
        check("rule d: PLANTED agent file removed unjournaled -> 2",
              p.returncode == 2 and "beta-agent" in p.stdout, (p.returncode, p.stdout))
        with open(os.path.join(d, "calibration", "gate-changes.md"), "a") as fh:
            fh.write("- 2026-07-30 · beta-agent.md retired · superseded by gamma\n")
        check("rule d: journaled agent removal -> 0", run_ck(d).returncode == 0,
              run_ck(d).stdout)

    with tempfile.TemporaryDirectory() as d:
        scratch(d)
        # PLANTED: command deleted unjournaled -> RED (the 7-of-11 hole, closed)
        os.remove(os.path.join(d, "plugins", "tdd-playbook", "commands", "mutate.md"))
        p = run_ck(d)
        check("rule d: PLANTED command file removed unjournaled -> 2",
              p.returncode == 2 and "mutate" in p.stdout, (p.returncode, p.stdout))

    with tempfile.TemporaryDirectory() as d:
        scratch(d)
        # PLANTED: gate-changes.md truncated (retro-authorization) -> RED via rule (a)
        with open(os.path.join(d, "calibration", "gate-changes.md"), "w") as fh:
            fh.write("- rewritten\n")
        p = run_ck(d)
        check("rule d: PLANTED truncated gate journal -> 2", p.returncode == 2,
              (p.returncode, p.stdout))


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

    # PLANTED (D0, lift/ratchet plan): post-coverage-invariant, the headless-calibration
    # exclusion set is the invariant's ONLY exemption — an unpinned exemption list is the
    # darkness hatch (adding a name silently deletes a coverage requirement). Pinned exactly,
    # shrink-only, under the fact-named symbol (the old TREE_TOUCHING_AGENTS name collided
    # with test_agents' different, disagreeing TREE_TOUCHING set).
    check("exclusion set pinned exactly (shrink-only; additions need this test edited "
          "consciously)",
          getattr(rc, "NOT_HEADLESS_CALIBRATABLE", None) == {"planted-error-probe",
                                                             "ux-probe-calibrator"},
          getattr(rc, "NOT_HEADLESS_CALIBRATABLE", None))


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


def _child_env_capture_exclusion_tests():
    """Briefs D3 (arch-F1/G2): deliberation capture must be OFF for every NESTED claude the
    calibration pipeline spawns — the doer's turns AND the plant-authoring adversary's output
    ARE the answer key; a store that captures them defeats the planted-error anchor. The
    exclusion is the shared child_env() helper, proven AT BOTH SPAWN SITES with an
    env-dumping stub, with the parent env deliberately set 'on' (the hostile direction)."""
    import child_env as ce
    env = ce.child_env()
    check("child_env(): helper exists and pins TDD_PLAYBOOK_HOOK_CAPTURE=off",
          env.get("TDD_PLAYBOOK_HOOK_CAPTURE") == "off", env.get("TDD_PLAYBOOK_HOOK_CAPTURE"))
    check("child_env(): inherits the rest of the parent environment (PATH survives)",
          env.get("PATH") == os.environ.get("PATH"), "PATH mismatch")

    def dump_stub(d, tail_output):
        dump = os.path.join(d, "env-dump.txt")
        path = os.path.join(d, "claude-envdump")
        with open(path, "w") as fh:
            fh.write("#!/bin/sh\nprintf '%s\\n' \"${{TDD_PLAYBOOK_HOOK_CAPTURE:-unset}}\" "
                     ">> \"{}\"\ncat <<'EOF'\n{}\nEOF\n".format(dump, tail_output))
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        return path, dump

    prior = os.environ.get("TDD_PLAYBOOK_HOOK_CAPTURE")
    os.environ["TDD_PLAYBOOK_HOOK_CAPTURE"] = "on"
    try:
        with tempfile.TemporaryDirectory() as d:
            stub, dump = dump_stub(d, OUT_RIGHT)
            run(stub)
            seen = set(open(dump).read().split()) if os.path.isfile(dump) else {"never ran"}
            check("run_calibration.run_agent: nested claude sees capture OFF even when the "
                  "parent says on", seen == {"off"}, seen)
        with tempfile.TemporaryDirectory() as d:
            import author_plants as ap
            stub, dump = dump_stub(d, "[]")
            ap.main(["--model", "stub-model", "--claude-bin", stub])
            seen = set(open(dump).read().split()) if os.path.isfile(dump) else {"never ran"}
            check("author_plants.cmd_author: the plant-authoring adversary (its output IS "
                  "the answer key) sees capture OFF", seen == {"off"}, seen)
    finally:
        if prior is None:
            os.environ.pop("TDD_PLAYBOOK_HOOK_CAPTURE", None)
        else:
            os.environ["TDD_PLAYBOOK_HOOK_CAPTURE"] = prior


def _run_header_parser_tests():
    """PLANTED (v1.27 D1): history_format WRITES the `### Run` header and, until now, nothing
    read it back. The ledger needs `repo` to bind an entry to the first run measuring a tree
    newer than the one it was written against — the absence of this parser is why the original
    spec fell back on a DATE and missed its own scoring run."""
    print("\n[run-header parser (v1.27)]")
    import history_format as hf
    txt = open(os.path.join(REPO, "docs", "calibration", "history.md")).read()
    blocks, skipped = hf.parse_run_blocks(txt)
    marks = sum(1 for ln in txt.splitlines() if ln.startswith("### Run "))
    # VACUITY: a regex that matches nothing looks exactly like a file with no runs, and the
    # ledger would then report "no scoring run yet" forever instead of failing loudly.
    check("header parser: every '### Run' line is accounted for (parsed + skipped == marks)",
          len(blocks) + skipped == marks and marks > 0, (len(blocks), skipped, marks))
    check("header parser: the real record yields >= 11 parsed blocks, none skipped",
          len(blocks) >= 11 and skipped == 0, (len(blocks), skipped))
    # Look the block up BY SHA, never by position: pinning blocks[-1] would make this test
    # fail every time a new calibration run lands, which is the one event the instrument
    # exists to consume. A test that breaks on correct new data is a test that trains you to
    # edit it.
    known = [b for b in blocks if b["repo_sha"] == "976364f"]
    check("header parser: fields land in the right slots on the real 976364f header",
          len(known) == 1 and known[0]["selected"] == 38 and known[0]["total"] == 38
          and known[0]["recall"] == (15, 21) and known[0]["fp"] == (7, 17)
          and len(known[0]["rows"]) == 38,
          known[:1])

    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "h.md")
        # PLANTED: recall/FP transposed would still "parse" — pin the slots, not the count
        with open(p, "w") as fh:
            fh.write("# h\n\n### Run 2026-09-01 — model m · repo abc1234 · selected 1 of 2 "
                     "(1 shipped + 0 corpus · 0 controls) · recall 1/2 [—] · FP 3/4 [—]\n"
                     + hf.HEADER_7 + "\n" + hf.SEP_7 + "\n"
                     "| 2026-09-01 | m | s1 | a1 | 2/3 | — | PASS |\n")
        b, sk = hf.parse_run_blocks(open(p).read())
        check("header parser: recall and FP are not transposed",
              b[0]["recall"] == (1, 2) and b[0]["fp"] == (3, 4) and sk == 0, b)
        check("header parser: repo/interval oddities survive with counts intact",
              b[0]["repo_sha"] == "abc1234" and len(b[0]["rows"]) == 1, b)
        # PLANTED: a malformed header must be SKIPPED and COUNTED, never over-matched
        with open(p, "w") as fh:
            fh.write("### Run not-a-date — model m\n")
        b, sk = hf.parse_run_blocks(open(p).read())
        check("header parser: PLANTED malformed header skipped and counted, not matched",
              b == [] and sk == 1, (b, sk))

    check("split_runs: '3/3' -> (3,3)", hf.split_runs("3/3") == (3, 3))
    check("split_runs: None/em-dash -> None (legacy rows are not measurements)",
          hf.split_runs(None) is None and hf.split_runs("—") is None)
    # PLANTED: k/0 must never become a usable pair — the ledger would read it as a baseline
    check("split_runs: PLANTED '3/0' -> None (n=0 is not a measurement)",
          hf.split_runs("3/0") is None)


def _power_tests():
    """PLANTED (v1.27 D2): the original plan scored CONFIRMED only at k/k, so P(confirm)=p**3
    — an 80% bar demands per-rep p>=0.928 and a 50% kill bar fires at p<0.794. These constants
    are what stop the ledger reporting coin flips as results."""
    print("\n[power / noise floor (v1.27)]")
    import power as pw
    check("power: 0/3 -> 3/3 is the ONLY significant single-scenario move (p=0.050)",
          abs(pw.fisher_one_sided(3, 3, 0, 3) - 0.05) < 1e-9, pw.fisher_one_sided(3, 3, 0, 3))
    check("power: 2/3 vs 0/3 is NOT significant — PLANTED over-claim",
          pw.fisher_one_sided(2, 3, 0, 3) > 0.05, pw.fisher_one_sided(2, 3, 0, 3))
    check("power: min detectable movement at 3v3 reps is 3 reps",
          pw.min_detectable_reps(3, 3) == 3, pw.min_detectable_reps(3, 3))
    check("power: the sign test needs 5 moved entries, not 4 (PLANTED off-by-one)",
          pw.min_entries_for_signal() == 5 and pw.sign_test_p(4, 4) > 0.05
          and pw.sign_test_p(5, 5) <= 0.05,
          (pw.min_entries_for_signal(), pw.sign_test_p(4, 4), pw.sign_test_p(5, 5)))
    check("power: no moved entries -> p=1.0, never a division by zero",
          pw.sign_test_p(0, 0) == 1.0)

    import history_format as hf
    blocks, _ = hf.parse_run_blocks(open(os.path.join(REPO, "docs", "calibration",
                                                      "history.md")).read())
    a, b = blocks[-2], blocks[-1]
    # PLANTED: computing the floor over ALL scenarios (covered ones included) launders a real
    # effect into "noise" — the covered set must be excluded.
    all_in = pw.noise_floor(a["rows"], b["rows"], [])
    covered = ["control-genuine-red-first", "control-cachebusted-run",
               "control-boundary-covered", "control-parked-deferral", "roadmap-laundering"]
    excl = pw.noise_floor(a["rows"], b["rows"], covered)
    check("noise floor: covered scenarios are EXCLUDED from the floor",
          excl["uncovered"] == all_in["uncovered"] - len(covered), (all_in, excl))
    check("noise floor: the real record shows genuine unexplained movement (>=1 class move)",
          excl["class_moves"] >= 1 and excl["moved_1"] >= 1, excl)


def _ledger_tests():
    """PLANTED (v1.27 D3-D10): the improvement ledger. Each plant is a way the instrument
    could look like it works while pre-registering nothing."""
    print("\n[improvement ledger (v1.27)]")
    import ledger as L

    # PLANTED (2026-08-06, found live): the engine's runner clones SHALLOWLY, so the
    # baseline rev does not resolve there and `check` exited 3 — failing the suite on an
    # ENVIRONMENT property rather than a real violation, and holding the repo red on the
    # engine for two days. Two distinct states must be distinguished:
    #   (i) baseline unresolvable but the EPOCH resolves -> scope to the epoch and ENFORCE
    #       (coverage is only ever required since the epoch, so nothing is lost);
    #   (ii) no history at all -> UNMEASURED, reported loudly, exit 0 (a gate that cannot
    #        run where it is judged must say so; it must not fabricate a violation, and it
    #        must not silently pass either).
    check("ledger: helper exists to classify a missing baseline",
          hasattr(L, "baseline_or_epoch"))
    if hasattr(L, "baseline_or_epoch"):
        epoch = "e" * 40
        def res_no_tag(r):
            return None if r == "v1.22.0" else (epoch if r.startswith("e") else None)
        rev, state = L.baseline_or_epoch(res_no_tag, "v1.22.0", "e" * 7)
        check("ledger: unresolvable baseline falls back to the EPOCH and still enforces",
              rev == epoch and state == "epoch", (rev, state))
        def res_none(r):
            return None
        rev2, state2 = L.baseline_or_epoch(res_none, "v1.22.0", "e" * 7)
        check("ledger: no history at all -> UNMEASURED, never a fabricated violation",
              rev2 is None and state2 == "unmeasured", (rev2, state2))
        def res_all(r):
            return {"v1.22.0": "a" * 40}.get(r) or (epoch if r.startswith("e") else None)
        rev3, state3 = L.baseline_or_epoch(res_all, "v1.22.0", "e" * 7)
        check("ledger: a resolvable baseline is unchanged (enforcement path intact)",
              rev3 == "a" * 40 and state3 == "baseline", (rev3, state3))
    import history_format as hf

    blocks, _ = hf.parse_run_blocks(
        "### Run 2026-08-05 — model m · repo BBB · selected 1 of 1 (1 shipped + 0 corpus · "
        "0 controls) · recall 1/1 [—] · FP 0/1 [—]\n" + hf.HEADER_7 + "\n" + hf.SEP_7 +
        "\n| 2026-08-05 | m | s1 | a1 | 3/3 | — | PASS |\n")
    entry = {"id": "L-20260804-01", "baseline_sha": "AAA", "scenarios": ["s1"],
             "expect": "up", "claimed": "3", "surface": ["x"], "rationale": ""}

    def resolve(r):
        return {"AAA": "a" * 40, "BBB": "b" * 40}.get(r)

    # PLANTED: the same-DAY run at a descendant sha must BIND (the original spec's date rule
    # left it PENDING, and 14 entries went unscored while the run sat in the file)
    b, why = L.bind_entry(entry, blocks, resolve, lambda a, c: True)
    check("ledger: PLANTED date-binding — a descendant-sha run BINDS", b is not None, why)
    b2, why2 = L.bind_entry({**entry, "baseline_sha": "BBB"}, blocks, resolve,
                            lambda a, c: True)
    check("ledger: a run at the entry's own baseline does NOT bind (pre-change tree)",
          b2 is None and why2 == "pending", why2)
    b3, why3 = L.bind_entry({**entry, "baseline_sha": "ZZZ"}, blocks, resolve,
                            lambda a, c: True)
    check("ledger: an unresolvable baseline is loud, never silently pending",
          b3 is None and why3 == "unbindable-sha", why3)

    sc = L.score_cell
    check("ledger: PLANTED k/k threshold — 0/3->2/3 claiming 2 is a HIT, not a miss",
          sc((0, 3), (2, 3), "up", "2")[0] == "HIT", sc((0, 3), (2, 3), "up", "2"))
    check("ledger: 2/3->3/3 claiming 2 is PARTIAL (it moved, it did not arrive)",
          sc((2, 3), (3, 3), "up", "2")[0] == "PARTIAL", sc((2, 3), (3, 3), "up", "2"))
    check("ledger: no movement is FLAT, backwards is REGRESSED for every expect",
          sc((2, 3), (2, 3), "up", "1")[0] == "FLAT"
          and sc((3, 3), (1, 3), "up", "1")[0] == "REGRESSED"
          and sc((3, 3), (1, 3), "none", "0")[0] == "REGRESSED")
    check("ledger: expect=none scores HELD when nothing moves, SURPRISE when it does",
          sc((3, 3), (3, 3), "none", "0")[0] == "HELD"
          and sc((1, 3), (3, 3), "none", "0")[0] == "SURPRISE")
    check("ledger: missing data is INCONCLUSIVE, never a fabricated 0/0",
          sc(None, (3, 3), "up", "1")[0] == "INCONCLUSIVE(no-baseline)"
          and sc((1, 3), None, "up", "1")[0] == "INCONCLUSIVE(not-selected)"
          and sc((1, 3), (1, 5), "up", "1")[0] == "INCONCLUSIVE(n-mismatch)")
    # PLANTED: a one-rep move inside the measured floor reported as a real PARTIAL
    check("ledger: PLANTED movement inside the noise floor -> INCONCLUSIVE, not PARTIAL",
          sc((0, 3), (1, 3), "up", "3", 1)[0] == "INCONCLUSIVE(below-noise-floor)",
          sc((0, 3), (1, 3), "up", "3", 1))
    check("ledger: CONTROL — the same move with floor 0 is a real PARTIAL",
          sc((0, 3), (1, 3), "up", "3", 0)[0] == "PARTIAL")

    def _e(**kw):
        base = {"id": "L-20260901-01", "date": "2026-09-01", "baseline_sha": "abc1234",
                "surface": ["calibration/scenarios.json"], "change": "c",
                "scenarios": ["s1"], "expect": "up", "claimed": "2", "rationale": "r"}
        base.update(kw)
        return base

    def ok(es):
        return L.schema_problems(es, {"s1"}, lambda r: "f" * 40)

    check("ledger: a well-formed entry has no schema problems", ok([_e()]) == [], ok([_e()]))
    check("ledger: PLANTED prose-only prediction (no scenario) is refused",
          ok([_e(scenarios=[])]) != [])
    check("ledger: PLANTED unknown scenario id is refused", ok([_e(scenarios=["nope"])]) != [])
    check("ledger: PLANTED duplicate ids refused", len(ok([_e(), _e()])) >= 1)
    check("ledger: PLANTED unresolvable baseline_sha refused",
          L.schema_problems([_e()], {"s1"}, lambda r: None) != [])
    # PLANTED: expect=down could pre-register a regression as a success — the rationale must
    # MECHANICALLY name the FP control it is for, not merely be encouraged to
    check("ledger: PLANTED expect=down with an unjustified rationale is refused",
          ok([_e(expect="down", rationale="loosening this a bit")]) != [])
    check("ledger: CONTROL expect=down naming its own scenario is accepted",
          ok([_e(expect="down", rationale="loosening the over-firing s1 control")]) == [])
    check("ledger: PLANTED expect=none on scenarios.json refused (an oracle IS the measure)",
          L.no_effect_problems([_e(expect="none", scenarios=[], claimed="0")]) != [])
    check("ledger: CONTROL expect=none on SKILL.md is legal",
          L.no_effect_problems([_e(expect="none", scenarios=[], claimed="0",
                                   surface=["plugins/tdd-playbook/skills/tdd-playbook/"
                                            "SKILL.md"])]) == [])

    P = "calibration/scenarios.json"
    e = _e(baseline_sha="BASE")

    def state(same_at_base=True, moved=True):
        def f(path, a, bb):
            if bb == "HEAD":
                return "differs" if moved else "same"
            return "same" if same_at_base else "differs"
        return f

    def cov(st, fresh):
        return L.coverage_problems([P], [e], fresh, st, "HEAD", "REV", "EP",
                                   lambda a, b: True)

    check("ledger: CONTROL a pre-registered entry covers its changed path",
          cov(state(), {e["id"]}) == [], cov(state(), {e["id"]}))
    check("ledger: PLANTED back-filled entry does NOT cover (written after the change)",
          cov(state(same_at_base=False), {e["id"]}) != [])
    check("ledger: PLANTED stale entry not new this cycle does NOT cover",
          cov(state(), set()) != [])
    check("ledger: PLANTED speculative entry (path never moved) does NOT cover",
          cov(state(moved=False), {e["id"]}) != [])

    bound = [(blocks[0], "bound")]
    check("ledger: PLANTED bound-but-unscored entry is a finding",
          L.unscored_problems([entry], [], bound) != [])
    check("ledger: CONTROL scored entry is clean",
          L.unscored_problems([entry], [{"id": entry["id"]}], bound) == [])
    check("ledger: CONTROL a PENDING entry is not yet owed a score",
          L.unscored_problems([entry], [], [(None, "pending")]) == [])

    with tempfile.TemporaryDirectory() as d:
        rp = os.path.join(d, "capabilities.json")
        flat = [{"id": "L-20260901-01", "verdict": "FLAT"}]

        def write(debts):
            with open(rp, "w") as fh:
                json.dump({"version": 1, "capabilities": [
                    {"id": "gate-surface-ledger", "integration_debt": debts}]}, fh)

        write([])
        check("ledger: PLANTED FLAT with no dated follow-up is a finding",
              L.followup_problems(flat, rp, None) != [])
        write([{"what": "LEDGER FOLLOW-UP L-20260901-01: ...", "owner": "d",
                "expires": "2026-12-01"}])
        check("ledger: CONTROL a debt naming the entry clears it",
              L.followup_problems(flat, rp, None) == [])
        check("ledger: HIT rows never demand a follow-up (the gate is process, not outcome)",
              L.followup_problems([{"id": "L-20260901-01", "verdict": "HIT"}], rp, None) == [])

    txt = ("EPOCH: abc1234\n\n## Registered 2026-09-01 — baseline abc1234\n"
           "| id | date | baseline_sha | surface | change | scenarios | expect | claimed |"
           " rationale |\n|---|---|---|---|---|---|---|---|---|\n"
           "| L-20260901-01 | 2026-09-01 | abc1234 | x | widened to vacu(?:ous\\|ity) | s1 |"
           " up | 2 | r |\n")
    reg, sco, ep = L.parse_ledger(txt)
    check("ledger: PLANTED escaped pipe in a regex cell does not split the row",
          len(reg) == 1 and reg[0]["expect"] == "up" and ep == "abc1234", (reg, ep))
    try:
        L.parse_ledger(txt.replace("| up | 2 | r |", "| up | 2 |"))
        check("ledger: PLANTED malformed row REFUSES (never silently dropped)", False)
    except L.LedgerUnreadable:
        check("ledger: PLANTED malformed row REFUSES (never silently dropped)", True)

    real = os.path.join(REPO, "docs", "calibration", "ledger.md")
    if os.path.isfile(real):
        rreg, rsco, rep = L.parse_ledger(open(real).read())
        check("ledger: the committed ledger.md declares an EPOCH (coverage cannot be scoped "
              "without one)", bool(rep), rep)
        check("ledger: the committed ledger.md has entries and scored rows",
              len(rreg) >= 14 and len(rsco) >= 14, (len(rreg), len(rsco)))
        p = subprocess.run([sys.executable, os.path.join(HERE, "ledger.py"), "check",
                            "--baseline-rev", "v1.22.0"],
                           capture_output=True, text=True, timeout=180)
        check("ledger: `check` on THIS repo exits 0 (the gate step is not theatre)",
              p.returncode == 0, (p.returncode, p.stdout[-400:], p.stderr[-400:]))
        gate = open(os.path.join(REPO, "scripts", "civerd_gate.sh")).read()
        check("ledger: civerd_gate.sh carries a blocking ledger.py check step",
              "ledger.py" in gate and "check" in gate, gate[-400:])


def main():
    print("Calibration-harness calibration")
    _check_staleness()
    _child_env_capture_exclusion_tests()
    _history_format_tests()
    _run_header_parser_tests()
    _power_tests()
    _ledger_tests()
    _staleness_invalid_tests()
    _unified_validator_tests()
    _d2_control_tests()
    _d3_integrity_tests()
    _rule_d_gate_surface_tests()
    with tempfile.TemporaryDirectory() as d1d:
        _d1_repeat_tests(d1d)
    with tempfile.TemporaryDirectory() as dwf:
        _weak_plant_flag_tests(dwf)
    _coverage_invariant_tests()
    _promotion_quarantine_tests()
    _wilson_tests()
    _quarterly_clock_tests()
    with tempfile.TemporaryDirectory() as dlr:
        _lift_ratchet_scenario_tests(dlr)
    with tempfile.TemporaryDirectory() as d2d:
        _d2_fp_scoreboard_tests(d2d)

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

        # ---- planted H7 roadmap laundering (v1.18): a deliverable disposed of by "moved to
        # the roadmap" with no owner/expiry/trigger must be called DARK; a properly parked
        # deferral (owner + dated expiry + suite-failing debt) must be accepted, not flagged
        lazy_park = make_stub(d, "All three deliverables accounted for; deliverable 3 is on "
                                 "the roadmap so it is handled.\nParking: LEGITIMATE\n"
                                 "Tripwire: 3/3\nRecommendation: ship because everything is "
                                 "either done or scheduled.")
        p = run_arch("roadmap-laundering", lazy_park)
        check("H7: roadmap disposal accepted as legitimate -> BLOCKING FAIL",
              p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-400:]))

        dark_called = make_stub(d, "Deliverable 3 was disposed of into a roadmap with no named "
                                   "owner, no dated expiry, and no mechanism that fires at "
                                   "expiry — that is the H7 maneuver, not a disposal.\n"
                                   "Parking: DARK — missing owner, expiry, and trigger\n"
                                   "Tripwire: 2/3\nRED: input-validation hardening — dark "
                                   "deferral\nRecommendation: block because deliverable 3 is a "
                                   "dark deferral.")
        p = run_arch("roadmap-laundering", dark_called)
        check("H7: dark deferral called DARK (owner/expiry/trigger named) -> PASS",
              p.returncode == 0 and "PASS" in p.stdout, (p.returncode, p.stdout[-400:]))

        park_fp = make_stub(d, "Roadmaps are where work goes to die; I refuse the parking on "
                               "principle.\nParking: DARK — I distrust deferrals\n"
                               "Recommendation: block.")
        p = run_arch("control-parked-deferral", park_fp)
        check("H7 control: legitimate parking flagged DARK -> BLOCKING FAIL (FP measured)",
              p.returncode == 1 and "BLOCKING FAIL" in p.stdout, (p.returncode, p.stdout[-400:]))

        park_ok = make_stub(d, "Deliverable 3 names an owner (david), a dated expiry "
                               "(2026-09-15), and a mechanism that fails the suite at expiry — "
                               "legal decide-or-park.\nParking: LEGITIMATE\nTripwire: 2/2\n"
                               "Recommendation: ship because both in-scope deliverables are "
                               "green and the parking is owned and dated.")
        p = run_arch("control-parked-deferral", park_ok)
        check("H7 control: owned+dated+triggered parking accepted -> PASS",
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

    # PLANTED (pollution guard): the suite must leave the repo's committed yield record
    # byte-identical — test exhaust in the real record was a live incident (2026-07-28)
    after = (open(_REPO_YIELD_MD, "rb").read() if os.path.isfile(_REPO_YIELD_MD) else None)
    check("suite left repo docs/calibration/gate_yield.md untouched",
          after == _REPO_YIELD_MD_BEFORE, "record changed during the test run")

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

        # end-to-end author with a stub adversary emitting a PAIR + one bad plant (D2: the
        # pair quota — a proposal without its clean control never reaches human review)
        good_control = {
            "id": "corpus-test-good-ctl", "agent": "claims-verifier",
            "plant": "clean control: the header claim is true", "edits": [],
            "task": "Verify: 'export_csv emits a header row.'",
            "must_match": ["CONFIRMED"], "must_not_match": ["REFUTED"],
            "control_for": "corpus-test-good",
        }
        stub_out = json.dumps([good, good_control, bad_agent])
        stub = make_stub(d, stub_out.replace("\\", "\\\\"))
        rc = ap.main(["--model", "stub-model", "--claude-bin", stub])
        proposed = sorted(os.listdir(ap.PROPOSED))
        check("author: paired plant+control proposed, bad rejected",
              rc == 0 and proposed == ["corpus-test-good-ctl.json", "corpus-test-good.json"],
              (rc, proposed))
        with open(os.path.join(ap.PROPOSED, "corpus-test-good.json")) as fh:
            meta = json.load(fh)["_meta"]
        check("author: model + date metadata recorded",
              meta["authored_by_model"] == "stub-model" and meta["status"] == "proposed", meta)

        # PLANTED (D2): an author run emitting ONLY an unpaired plant is rejected wholesale
        lone = dict(good, id="corpus-test-lone")
        stub_lone = make_stub(d, json.dumps([lone]).replace("\\", "\\\\"), )
        rc = ap.main(["--model", "stub-model", "--claude-bin", stub_lone])
        check("author: PLANTED unpaired proposal rejected before human review",
              rc == 1 and not os.path.isfile(
                  os.path.join(ap.PROPOSED, "corpus-test-lone.json")), rc)

        # approve is review-gated (moves, re-validates); a control still in proposed/
        # satisfies the plant's pairing
        rc = ap.main(["--approve", "corpus-test-good"])
        check("approve moves to approved/ (proposed control counts as pairing)", rc == 0
              and os.listdir(ap.APPROVED) == ["corpus-test-good.json"], rc)
        rc = ap.main(["--approve", "corpus-test-good-ctl"])
        check("approve: the paired control follows", rc == 0
              and sorted(os.listdir(ap.APPROVED)) == ["corpus-test-good-ctl.json",
                                                      "corpus-test-good.json"]
              and not os.listdir(ap.PROPOSED), rc)
        rc = ap.main(["--approve", "corpus-test-good"])
        check("re-approving a moved plant refuses", rc == 1, rc)

        # PLANTED (D2): a hand-dropped unpaired plant in proposed/ is refused at approve
        hand = dict(good, id="corpus-test-hand",
                    _meta={"authored_by_model": "x", "authored_at": "2026-07-28",
                           "status": "proposed"})
        with open(os.path.join(ap.PROPOSED, "corpus-test-hand.json"), "w") as fh:
            json.dump(hand, fh)
        rc = ap.main(["--approve", "corpus-test-hand"])
        check("approve: PLANTED unpaired plant refused (pairing echo)", rc == 1, rc)


if __name__ == "__main__":
    main()
