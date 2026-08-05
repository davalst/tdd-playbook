#!/usr/bin/env python3
"""Agent calibration harness — planted-defect runs for the Playbook's verifier agents.

§13 applied to ourselves: the hooks are calibrated deterministically (tests/test_hooks.py);
the AGENTS need a live model, so they are calibrated here on a schedule. Each scenario in
scenarios.json plants a defect in a copy of calibration/fixture/, drives the agent headlessly
(`claude -p`, cheap model, hard caps), and applies a DETERMINISTIC oracle: regexes the output
must / must not match. No LLM judge — the oracle split governs our own calibration too.

A plant surviving to a clean verdict is a BLOCKING failure (exit 1). Results append to
docs/calibration/history.md (override with --history; suppress with --history "").

Usage:
    python3 calibration/run_calibration.py                 # all scenarios, live model
    python3 calibration/run_calibration.py --agent NAME    # one agent's scenarios
    python3 calibration/run_calibration.py --dry-run       # validate without model calls
Environment: TDD_PLAYBOOK_CLAUDE_BIN (default "claude"), TDD_PLAYBOOK_CALIBRATION_MODEL
(default "haiku"), TDD_PLAYBOOK_CALIBRATION_ARGS (extra args, whitespace-split — e.g.
"--dangerously-skip-permissions" in a sandboxed CI container).
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import history_format  # noqa: E402  (the ONE owner of the scoreboard format — D0)
REPO = os.path.dirname(HERE)
FIXTURE = os.path.join(HERE, "fixture")
SCENARIOS = os.path.join(HERE, "scenarios.json")
AGENTS_DIR = os.path.join(REPO, "plugins", "tdd-playbook", "agents")
DEFAULT_HISTORY = os.path.join(REPO, "docs", "calibration", "history.md")
MAX_TURNS = "25"
TIMEOUT_S = 600
DEFAULT_REPEAT = 3  # §5a applied to ourselves: one roll of a probabilistic verifier is a
                    # coin flip, not a measurement (R1 — the 2026-07-27 lucky-roll rows)

# Agents that cannot run headless calibration (their scenarios need revert-safety
# discipline, so they stay hand-exercised via their commands). Named for the FACT it
# encodes — the old TREE_TOUCHING_AGENTS name collided with test_agents.py's different,
# disagreeing TREE_TOUCHING set (which means "carries the with_snapshot block"). Post-D1
# this set is the coverage invariant's ONLY exemption, so it is PINNED exactly in
# test_harness.py (shrink-only): adding a name here silently deletes a coverage
# requirement, and that edit must be conscious. Everything else in the agents/ roster is
# calibratable — the roster stays DERIVED, never a second hand-maintained list.
NOT_HEADLESS_CALIBRATABLE = {"planted-error-probe", "ux-probe-calibrator"}


def known_agents():
    try:
        names = {fn[:-3] for fn in os.listdir(AGENTS_DIR) if fn.endswith(".md")}
    except OSError:
        return set()
    return names - NOT_HEADLESS_CALIBRATABLE


# Pre-quota plants without a paired clean control (R2 grandfather, dated 2026-07-28).
# This list only SHRINKS: the suite's self-cleaning check fails if an entry gains a control
# or stops existing, so every backfilled pair forcibly retires its entry. Never add to it.
GRANDFATHERED_PLANT_IDS = {
    # corpus plants awaiting controls from the next author_plants cycles:
    "csv-escape-fixed-at-call-site", "dead-export-claim-cmd-indirection",
    "shadowed-import-vacuous-suite", "special-case-bypasses-both-copies",
}


def validate_scenario(sc, taken_ids, agents=None):
    """THE scenario validator (D0) — shipped scenarios, corpus plants, and adversary proposals
    all pass through here; there is deliberately no second copy. Returns problem strings."""
    problems = []
    for key in ("id", "agent", "plant", "task", "must_match"):
        if not sc.get(key):
            problems.append("missing/empty field: " + key)
    cf = sc.get("control_for")
    if cf is not None:
        if not isinstance(cf, str) or not cf:
            problems.append("control_for must be a non-empty plant id")
        elif cf == sc.get("id"):
            problems.append("control_for: self-reference")
        if not sc.get("must_not_match"):
            problems.append("control missing must_not_match (the alarm verdict a fooled "
                            "run would emit — without it the control cannot fail)")
    agents = known_agents() if agents is None else agents
    if sc.get("agent") not in agents:
        problems.append("unknown agent: {}".format(sc.get("agent")))
    if sc.get("id") in taken_ids:
        problems.append("duplicate id: {}".format(sc.get("id")))
    for rx in sc.get("must_match", []) + sc.get("must_not_match", []):
        try:
            re.compile(rx)
        except re.error as e:
            problems.append("bad regex /{}/: {}".format(rx, e))
    if not problems:
        root = tempfile.mkdtemp(prefix="scn-val-")
        try:
            shutil.copytree(FIXTURE, root, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            apply_edits(root, sc.get("edits", []))
        except Exception as e:
            problems.append("edits do not apply to fixture: {}".format(e))
        finally:
            shutil.rmtree(root, ignore_errors=True)
    return problems


def load_scenarios():
    with open(SCENARIOS) as fh:
        return json.load(fh)["scenarios"]


def load_corpus():
    """Approved adversary-authored plants (calibration/corpus/approved/). Only grows."""
    d = os.path.join(HERE, "corpus", "approved")
    out = []
    if os.path.isdir(d):
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                with open(os.path.join(d, fn)) as fh:
                    out.append(json.load(fh))
    return out


def catalog_staleness(today=None):
    """Days since the newest HACK_CATALOG refresh-log entry, or None if unparseable.
    The decay principle (§13): a stale catalog is itself a finding. `today` is injectable
    (D6/G4 — a clock nobody can test is a clock nobody trusts); the quarterly bundle's
    REAL trigger is docs/calibration/quarterly.md on check_staleness (see CLAUDE.md)."""
    path = os.path.join(REPO, "docs", "HACK_CATALOG.md")
    try:
        with open(path) as fh:
            dates = re.findall(r"\|\s*(\d{4})-(\d{2})\s*\|", fh.read())
    except OSError:
        return None
    if not dates:
        return None
    y, m = max((int(a), int(b)) for a, b in dates)
    newest = datetime.date(y, m, 1)
    return ((today or datetime.date.today()) - newest).days


def agent_body(agent):
    path = os.path.join(AGENTS_DIR, agent + ".md")
    with open(path) as fh:
        text = fh.read()
    # strip frontmatter — the body is the prompt
    m = re.match(r"^---\n.*?\n---\n", text, re.DOTALL)
    return text[m.end():] if m else text


def apply_edits(root, edits):
    """Apply a scenario's plant. Raises if an anchor string is missing (stale scenario)."""
    for e in edits:
        path = os.path.join(root, e["file"])
        with open(path) as fh:
            body = fh.read()
        if "append" in e:
            body += e["append"]
        else:
            if e["old"] not in body:
                raise RuntimeError("stale plant: anchor not found in {}: {!r}".format(
                    e["file"], e["old"][:60]))
            body = body.replace(e["old"], e["new"], 1)
        with open(path, "w") as fh:
            fh.write(body)


def stage(scenario):
    """Copy the fixture, apply the plant, git-init it. Returns the temp root."""
    root = tempfile.mkdtemp(prefix="tdd-cal-")
    shutil.copytree(FIXTURE, root, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    apply_edits(root, scenario.get("edits", []))
    def git(*a):
        subprocess.run(["git", *a], cwd=root, capture_output=True, text=True, timeout=30)
    git("init", "-q")
    git("config", "user.email", "cal@tdd-playbook")
    git("config", "user.name", "calibration")
    git("add", "-A")
    git("commit", "-qm", "fixture (plant applied)")
    return root


def oracle(scenario, output):
    """Deterministic verdict: (passed, problems, mode). PURE — knows nothing about the runner
    (timeouts/env failures are classified at the run_agent seam from the returncode it holds,
    never re-derived here by string-sniffing). Mode is the closed R1.3 vocabulary's oracle
    slice: wrong-verdict-line > found-but-hedged > missed-entirely."""
    problems, matched_some = [], False
    for rx in scenario.get("must_match", []):
        if re.search(rx, output, re.IGNORECASE):
            matched_some = True
        else:
            problems.append("expected /{}/ — NOT found (plant survived?)".format(rx))
    wrong_line = False
    for rx in scenario.get("must_not_match", []):
        if re.search(rx, output, re.IGNORECASE):
            wrong_line = True
            problems.append("forbidden /{}/ — FOUND".format(rx))
    if not problems:
        return True, [], None
    if wrong_line:
        mode = "wrong-verdict-line"
    elif matched_some:
        mode = "found-but-hedged"
    else:
        mode = "missed-entirely"
    return False, problems, mode


def pairing_problems(scenarios):
    """Set-level R2 invariant over shipped ∪ corpus: every non-grandfathered plant has a
    clean control referencing it, and every control references a real plant. Runs on the
    dry-run/release-gate path — a plant hand-dropped into scenarios.json or corpus/approved/
    is caught HERE, not only at --approve (a one-time authoring gate)."""
    ids = {s.get("id") for s in scenarios}
    controlled = set()
    problems = []
    for s in scenarios:
        cf = s.get("control_for")
        if cf:
            controlled.add(cf)
            if cf not in ids:
                problems.append("{}: control_for references unknown plant: {}".format(
                    s.get("id"), cf))
    for s in scenarios:
        sid = s.get("id")
        if s.get("control_for") or sid in GRANDFATHERED_PLANT_IDS:
            continue
        if sid not in controlled:
            problems.append("{}: unpaired plant — no clean control references it "
                            "(R2 pair quota; a recall-only corpus grows one-directional)"
                            .format(sid))
    return problems


def agent_coverage_problems(scenarios, agents=None):
    """Set-level R1-part-1 invariant (lift/ratchet plan): every headless-calibratable agent
    has >=1 PLANT. Controls don't count — plants define coverage; a control proves
    restraint, not that the agent's rules are exercised. This is the behavioral half of
    gate-removal protection: the test_agents roster pin catches DELETING an agent, this
    catches the agent nobody can see decay — a softened brief keeps its verdict lines
    while losing its rules, and without a live plant nothing notices between calibrations."""
    agents = known_agents() if agents is None else agents
    covered = {s.get("agent") for s in scenarios if not s.get("control_for")}
    return ["{}: no plant covers this agent — a softened brief goes unseen between "
            "calibrations (R1 coverage invariant; author a plant+control pair)".format(a)
            for a in sorted(agents - covered)]


def turns_for(scenario):
    """Per-scenario turn budget: `max_turns` (int) overrides the default hard cap.
    Investigation-heavy plants (e.g. static analysis under a ceremony-heavy brief on a
    cheap model) legitimately need more room than count-reasoning ones; the default stays
    the cost floor, never lower."""
    try:
        return str(max(int(scenario.get("max_turns", MAX_TURNS)), int(MAX_TURNS)))
    except (TypeError, ValueError):
        return MAX_TURNS


def run_agent(scenario, root, claude_bin, model):
    """One rep. Returns (status, output), status in {ok, timeout, env_failure} — typed at the
    seam that HOLDS the returncode/exception (arch-F4). env_failure = nonzero exit with empty
    stdout: the doer never ran (the 2026-07-09 root-permission case); it is not an agent
    failure and is excluded from n. FileNotFoundError propagates (fatal, short-circuits)."""
    prompt = (agent_body(scenario["agent"])
              + "\n\n# TASK (work in the current directory; it is a git repo)\n"
              + scenario["task"])
    cmd = [claude_bin, "-p", prompt, "--model", model, "--max-turns", turns_for(scenario)]
    extra = os.environ.get("TDD_PLAYBOOK_CALIBRATION_ARGS", "").split()
    cmd.extend(extra)
    try:
        # child_env: capture OFF for the nested claude — its turns ARE the answer key
        from child_env import child_env
        p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=TIMEOUT_S,
                           env=child_env())
    except subprocess.TimeoutExpired:
        return "timeout", "[TIMEOUT after {}s]".format(TIMEOUT_S)
    if p.returncode != 0 and not p.stdout.strip():
        return "env_failure", "[env failure rc={}]\n{}".format(p.returncode, p.stderr[-800:])
    return "ok", p.stdout + ("\n[stderr]\n" + p.stderr if p.returncode != 0 else "")


def dry_run(scenarios):
    """Validate everything that doesn't need a model — through THE validator (D0), so shipped
    scenarios obey the same rules as corpus proposals. Exit non-zero on any problem."""
    problems = []
    # fixture must be green unplanted
    p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                       cwd=FIXTURE, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        problems.append("fixture tests FAIL unplanted:\n" + p.stderr[-800:])
    seen = set()
    for sc in scenarios:
        for msg in validate_scenario(sc, seen):
            problems.append("{}: {}".format(sc.get("id"), msg))
        seen.add(sc.get("id"))
    # R2 pairing and R1 coverage are corpus-level invariants — evaluated over the FULL
    # suite even when dry_run was invoked on a filtered selection (a --scenario run must
    # not false-flag its plant's control as missing, nor mask a real gap).
    full = load_scenarios() + load_corpus()
    problems.extend(pairing_problems(full))
    problems.extend(agent_coverage_problems(full))
    for msg in problems:
        print("DRY-RUN PROBLEM: " + msg)
    print("dry-run: {} scenario(s), {} problem(s)".format(len(scenarios), len(problems)))
    return 1 if problems else 0


def repo_sha():
    p = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                       capture_output=True, text=True, timeout=30)
    return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else "unknown"


def append_history(history_path, model, results, meta):
    """Append one run block via history_format. results: dicts {sc, runs, mode, verdict};
    meta: selected/total/shipped/corpus/controls/recall/fp (date/model/repo_sha filled here).
    The run header carries the repo SHA (R1.4 fix-traceability) and the DERIVED composition —
    counts are computed, never hand-written (the CLAUDE.md '13 scenarios' drift class)."""
    if not history_path:
        return
    today = datetime.date.today().isoformat()
    rows = []
    for r in results:
        sc = r["sc"]
        # F3 — surface the verifier-vs-adversary tier: `<verifier> vs <plant-author>` for
        # corpus plants so a verifier weaker than the model that authored the plant is
        # VISIBLE on the scoreboard (the §13 ratio, not just prose).
        author = (sc.get("_meta") or {}).get("authored_by_model")
        model_cell = "{} vs {}".format(model, author) if author else model
        rows.append({"date": today, "model_cell": model_cell, "scenario": sc["id"],
                     "agent": sc["agent"], "runs": r["runs"], "mode": r["mode"],
                     "verdict": r["verdict"]})
    hf_meta = dict(meta)
    hf_meta.setdefault("date", today)
    hf_meta.setdefault("model", model)
    hf_meta.setdefault("repo_sha", repo_sha())
    history_format.append_run_block(history_path, hf_meta, rows)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run planted-defect calibration of the agents.")
    ap.add_argument("--agent", help="only scenarios for this agent")
    ap.add_argument("--scenario", help="only this scenario id")
    ap.add_argument("--repeat", type=int, default=DEFAULT_REPEAT, metavar="K",
                    help="reps per scenario (default {}; one roll is a coin flip, not a "
                         "measurement — §5a)".format(DEFAULT_REPEAT))
    ap.add_argument("--dry-run", action="store_true", help="validate without model calls")
    ap.add_argument("--claude-bin", default=os.environ.get("TDD_PLAYBOOK_CLAUDE_BIN", "claude"))
    ap.add_argument("--model", default=os.environ.get("TDD_PLAYBOOK_CALIBRATION_MODEL", "haiku"))
    ap.add_argument("--history", default=DEFAULT_HISTORY,
                    help='history file to append ("" to suppress)')
    args = ap.parse_args(argv)

    if args.repeat < 1:
        print("--repeat must be >= 1")
        return 2

    # H8 — guards-liveness check on the surface David actually runs: work committed after
    # the last guard heartbeat means the hook layer was DARK (plugin disabled user-wide is
    # one mis-click away — live incident 2026-07-28). Warning, never a run-blocker.
    try:
        sys.path.insert(0, os.path.join(REPO, "plugins", "tdd-playbook", "hooks", "scripts"))
        from _common import guards_dark
        status, detail = guards_dark(REPO)
        if status == "dark":
            print("GUARDS-DARK WARNING: {} — check `claude /plugin` enablement "
                  "(user-scope!) before trusting any session-enforced discipline.".format(
                      detail))
    except Exception:
        pass

    corpus = load_corpus()
    shipped = load_scenarios()
    # Composition is computed PRE-filter (arch-F8): a --scenario rerun records
    # "selected 1 of N", never itself as the whole suite.
    all_scenarios = shipped + corpus
    controls_total = sum(1 for s in all_scenarios if s.get("control_for"))
    scenarios = all_scenarios
    stale = catalog_staleness()
    if stale is not None and stale > 100:
        print("DECAY WARNING: docs/HACK_CATALOG.md last refreshed ~{} days ago — the "
              "quarterly ritual is due (a stale catalog is a decaying gate, §13).".format(stale))
    if args.agent:
        scenarios = [s for s in scenarios if s["agent"] == args.agent]
    if args.scenario:
        scenarios = [s for s in scenarios if s["id"] == args.scenario]
    if not scenarios:
        print("no scenarios selected")
        return 2
    if args.dry_run:
        return dry_run(scenarios)

    # Prior verdicts for the mechanical AMBER×2 promotion — matched per SCENARIO ID, never
    # "the previous run block" (blocks are filter-scoped; arch-F5).
    prior_rows = []
    if args.history and os.path.isfile(args.history):
        with open(args.history) as fh:
            prior_rows = history_format.parse_rows(fh.read())

    def last_kind(sid):
        for r in reversed(prior_rows):
            if r["scenario"] == sid:
                return r["kind"]
        return None

    mode_precedence = ("timeout", "env-failure", "wrong-verdict-line",
                       "found-but-hedged", "missed-entirely")
    results, failed = [], 0
    for sc in scenarios:
        print("\n=== {} [{}] — plant: {}".format(sc["id"], sc["agent"], sc["plant"]))
        reps = []
        for _rep in range(args.repeat):
            root = stage(sc)
            try:
                status, out = run_agent(sc, root, args.claude_bin, args.model)
            except FileNotFoundError:
                print("FATAL: claude binary not found ({}) — set TDD_PLAYBOOK_CLAUDE_BIN "
                      "or use --dry-run".format(args.claude_bin))
                return 2
            finally:
                shutil.rmtree(root, ignore_errors=True)
            if status == "ok":
                passed, problems, mode = oracle(sc, out)
                reps.append({"passed": passed, "mode": mode, "problems": problems,
                             "out": out, "env": False})
            else:
                mode = "timeout" if status == "timeout" else "env-failure"
                reps.append({"passed": False, "mode": mode, "problems": ["[{}]".format(mode)],
                             "out": out, "env": status == "env_failure"})
        counted = [r for r in reps if not r["env"]]  # env failures never poison n
        k = sum(1 for r in counted if r["passed"])
        n = len(counted)
        fail_modes = [r["mode"] for r in reps if r["mode"]]
        mode = next((m for m in mode_precedence if m in fail_modes), None)
        if n == 0:
            verdict = "INVALID — env failure on all reps"
        elif k == n:
            verdict = "PASS"
        elif k == 0:
            verdict = "**BLOCKING FAIL**"
        elif last_kind(sc["id"]) == "AMBER":
            verdict = "**BLOCKING FAIL** (AMBER×2)"
        else:
            verdict = "AMBER"
        results.append({"sc": sc, "runs": "{}/{}".format(k, n), "mode": mode,
                        "verdict": verdict})
        if verdict == "PASS":
            print("PASS — the agent caught the plant ({}/{})".format(k, n))
            continue
        failed += 1
        if verdict.startswith("INVALID"):
            print("INVALID — environment failure on every rep; nothing was measured")
        elif verdict.endswith("(AMBER×2)"):
            print("BLOCKING FAIL — AMBER on consecutive runs, promoted mechanically "
                  "(caught {}/{}, mode: {})".format(k, n, mode))
        elif verdict == "AMBER":
            print("AMBER — caught only {}/{} (mode: {}); a terminal pass no longer closes "
                  "a failure".format(k, n, mode))
        else:
            print("BLOCKING FAIL — the plant survived ({}/{}, mode: {}):".format(k, n, mode))
        worst = next((r for r in reps if not r["passed"]), reps[-1])
        for pr in worst["problems"]:
            print("  - " + pr)
        print("--- agent output (tail) ---\n" + worst["out"][-1500:])

    plants = [r for r in results if not r["sc"].get("control_for")]
    controls = [r for r in results if r["sc"].get("control_for")]

    def measured(rs):
        return [r for r in rs if not r["verdict"].startswith("INVALID")]

    recall = (sum(1 for r in measured(plants) if r["verdict"] == "PASS"),
              len(measured(plants)))
    fp = (sum(1 for r in measured(controls) if r["verdict"] != "PASS"),
          len(measured(controls)))
    meta = {"selected": len(scenarios), "total": len(all_scenarios),
            "shipped": len(shipped), "corpus": len(corpus), "controls": controls_total,
            "recall": recall, "fp": fp}
    append_history(args.history, args.model, results, meta)
    # Weak-plant streak (2026-07-28 sweep): a plant no verifier has EVER missed teaches
    # nothing — an adversary authoring easy plants inflates recall while the gate decays.
    # Mechanical from the same prior rows the promotion check parsed; plants only (a
    # control that never fails means the verifier never false-positives — that's health).
    for r in results:
        sc = r["sc"]
        if r["verdict"] != "PASS" or sc.get("control_for"):
            continue
        prior = [row["kind"] for row in prior_rows if row["scenario"] == sc["id"]]
        if len(prior) >= 2 and all(k == "PASS" for k in prior):
            print("WEAK-PLANT? {} has never failed across {} recorded runs — a plant every "
                  "verifier always catches teaches nothing; harden or supersede it next "
                  "authoring cycle (the corpus grows, it never dilutes).".format(
                      sc["id"], len(prior) + 1))
    print("\nCalibration: {}/{} caught · selected {} of {} ({} shipped + {} corpus · {} "
          "controls) · recall {}/{} {} · FP {}/{} {} · corpus size {} (only grows)".format(
              len(results) - failed, len(results), len(scenarios), len(all_scenarios),
              len(shipped), len(corpus), controls_total,
              recall[0], recall[1], history_format.interval_cell(*recall),
              fp[0], fp[1], history_format.interval_cell(*fp), len(corpus)))
    # R4 — the retirement-candidate mirror of the DECAY WARNING (§13's second decay
    # direction: more expensive than the risk). This run IS the cycle: roll the raw yield
    # exhaust into the committed record, then report. NEVER fails the calibration run.
    try:
        gy = os.path.join(REPO, "plugins", "tdd-playbook", "bin", "gate_yield.py")
        if os.path.isfile(gy):
            for cmd in ("rollup", "candidates"):
                p = subprocess.run([sys.executable, gy, cmd], capture_output=True,
                                   text=True, timeout=60)
                if p.stdout.strip():
                    print(p.stdout.strip())
        else:
            print("yield: unmeasured (gate_yield.py not present)")
    except Exception as e:
        print("yield: unmeasured (gate_yield unavailable: {})".format(e))
    # v1.24 (§6c D13b) — the dataflow half of the same instrument: run the configured
    # sweeps, commit one row per sweep this cycle, then run the excluded-share trend
    # check. The TREND flag is the consumer the CLAUDE.md checklist points at. NEVER
    # fails the calibration run.
    try:
        ds = os.path.join(REPO, "plugins", "tdd-playbook", "bin", "dataflow_sweeps.py")
        gy = os.path.join(REPO, "plugins", "tdd-playbook", "bin", "gate_yield.py")
        ds_cfg = os.path.join(REPO, "dataflow-sweeps.json")
        if os.path.isfile(ds) and os.path.isfile(ds_cfg) and os.path.isfile(gy):
            # `all` derives the armed sweeps from the config — no hardcoded list here
            # (arch-F2); the strict line validation lives in dataflow-rollup, which
            # imports the producer's own regex
            p = subprocess.run([sys.executable, ds, "all", "--config", ds_cfg],
                               capture_output=True, text=True, timeout=120)
            lines = [ln for ln in p.stdout.splitlines()
                     if ln.startswith("dataflow_sweeps ") and "checked" in ln]
            if lines:
                cmd = [sys.executable, gy, "dataflow-rollup",
                       "--date", datetime.date.today().isoformat()]
                for ln in lines:
                    cmd += ["--line", ln]
                p = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                if p.stdout.strip():
                    print(p.stdout.strip())
                p = subprocess.run([sys.executable, gy, "dataflow-trend"],
                                   capture_output=True, text=True, timeout=60)
                if p.stdout.strip():
                    print(p.stdout.strip())
            else:
                print("dataflow yield: unmeasured (no sweep summary produced)")
        else:
            print("dataflow yield: unmeasured (sweeps/config not present)")
    except Exception as e:
        print("dataflow yield: unmeasured (dataflow sweeps unavailable: {})".format(e))

    # v1.27 (§13 RSI): the ledger's pointer line — did the changes since the last run do what
    # they were pre-registered to do, and could this cycle have shown it either way? A POINTER,
    # not the check (that is `ledger.py check` in civerd_gate.sh). Wrapped like the yield and
    # dataflow blocks above: reporting must never fail a calibration run.
    try:
        led = os.path.join(HERE, "ledger.py")
        if os.path.isfile(led):
            p = subprocess.run([sys.executable, led, "report"],
                               capture_output=True, text=True, timeout=120)
            if p.stdout.strip():
                print(p.stdout.strip())
        else:
            print("ledger: unmeasured (ledger.py not present)")
    except Exception as e:
        print("ledger: unmeasured (ledger unavailable: {})".format(e))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
