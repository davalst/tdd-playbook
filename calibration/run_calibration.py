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
REPO = os.path.dirname(HERE)
FIXTURE = os.path.join(HERE, "fixture")
SCENARIOS = os.path.join(HERE, "scenarios.json")
AGENTS_DIR = os.path.join(REPO, "plugins", "tdd-playbook", "agents")
DEFAULT_HISTORY = os.path.join(REPO, "docs", "calibration", "history.md")
MAX_TURNS = "25"
TIMEOUT_S = 600


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


def catalog_staleness():
    """Days since the newest HACK_CATALOG refresh-log entry, or None if unparseable.
    The decay principle (§13): a stale catalog is itself a finding."""
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
    return (datetime.date.today() - newest).days


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
    """Deterministic verdict: (passed, problems)."""
    problems = []
    for rx in scenario.get("must_match", []):
        if not re.search(rx, output, re.IGNORECASE):
            problems.append("expected /{}/ — NOT found (plant survived?)".format(rx))
    for rx in scenario.get("must_not_match", []):
        if re.search(rx, output, re.IGNORECASE):
            problems.append("forbidden /{}/ — FOUND".format(rx))
    return (not problems), problems


def run_agent(scenario, root, claude_bin, model):
    prompt = (agent_body(scenario["agent"])
              + "\n\n# TASK (work in the current directory; it is a git repo)\n"
              + scenario["task"])
    cmd = [claude_bin, "-p", prompt, "--model", model, "--max-turns", MAX_TURNS]
    extra = os.environ.get("TDD_PLAYBOOK_CALIBRATION_ARGS", "").split()
    cmd.extend(extra)
    p = subprocess.run(cmd, cwd=root, capture_output=True, text=True, timeout=TIMEOUT_S)
    return p.stdout + ("\n[stderr]\n" + p.stderr if p.returncode != 0 else "")


def dry_run(scenarios):
    """Validate everything that doesn't need a model. Exit non-zero on any problem."""
    problems = []
    # fixture must be green unplanted
    p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                       cwd=FIXTURE, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        problems.append("fixture tests FAIL unplanted:\n" + p.stderr[-800:])
    for sc in scenarios:
        if not os.path.isfile(os.path.join(AGENTS_DIR, sc["agent"] + ".md")):
            problems.append("{}: unknown agent {}".format(sc["id"], sc["agent"]))
        for rx in sc.get("must_match", []) + sc.get("must_not_match", []):
            try:
                re.compile(rx)
            except re.error as e:
                problems.append("{}: bad regex /{}/: {}".format(sc["id"], rx, e))
        try:
            root = stage(sc)
            shutil.rmtree(root, ignore_errors=True)
        except Exception as e:
            problems.append("{}: plant does not apply: {}".format(sc["id"], e))
        if not sc.get("must_match"):
            problems.append("{}: no must_match oracle — scenario cannot fail".format(sc["id"]))
    for msg in problems:
        print("DRY-RUN PROBLEM: " + msg)
    print("dry-run: {} scenario(s), {} problem(s)".format(len(scenarios), len(problems)))
    return 1 if problems else 0


def append_history(history_path, model, results):
    if not history_path:
        return
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    new = not os.path.isfile(history_path)
    with open(history_path, "a") as fh:
        if new:
            fh.write("# Calibration history\n\n"
                     "| date | model | scenario | agent | verdict |\n"
                     "|---|---|---|---|---|\n")
        today = datetime.date.today().isoformat()
        for sc, passed, _problems in results:
            fh.write("| {} | {} | {} | {} | {} |\n".format(
                today, model, sc["id"], sc["agent"],
                "PASS" if passed else "**BLOCKING FAIL**"))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Run planted-defect calibration of the agents.")
    ap.add_argument("--agent", help="only scenarios for this agent")
    ap.add_argument("--scenario", help="only this scenario id")
    ap.add_argument("--dry-run", action="store_true", help="validate without model calls")
    ap.add_argument("--claude-bin", default=os.environ.get("TDD_PLAYBOOK_CLAUDE_BIN", "claude"))
    ap.add_argument("--model", default=os.environ.get("TDD_PLAYBOOK_CALIBRATION_MODEL", "haiku"))
    ap.add_argument("--history", default=DEFAULT_HISTORY,
                    help='history file to append ("" to suppress)')
    args = ap.parse_args(argv)

    corpus = load_corpus()
    scenarios = load_scenarios() + corpus
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

    results, failed = [], 0
    for sc in scenarios:
        print("\n=== {} [{}] — plant: {}".format(sc["id"], sc["agent"], sc["plant"]))
        root = stage(sc)
        try:
            out = run_agent(sc, root, args.claude_bin, args.model)
        except FileNotFoundError:
            print("FATAL: claude binary not found ({}) — set TDD_PLAYBOOK_CLAUDE_BIN "
                  "or use --dry-run".format(args.claude_bin))
            return 2
        except subprocess.TimeoutExpired:
            out = "[TIMEOUT after {}s]".format(TIMEOUT_S)
        finally:
            shutil.rmtree(root, ignore_errors=True)
        passed, problems = oracle(sc, out)
        results.append((sc, passed, problems))
        if passed:
            print("PASS — the agent caught the plant")
        else:
            failed += 1
            print("BLOCKING FAIL — the plant survived:")
            for pr in problems:
                print("  - " + pr)
            print("--- agent output (tail) ---\n" + out[-1500:])
    append_history(args.history, args.model, results)
    print("\nCalibration: {}/{} caught · corpus size {} (only grows)".format(
        len(results) - failed, len(results), len(corpus)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
