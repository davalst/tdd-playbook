#!/usr/bin/env python3
"""Agent calibration harness — planted-defect runs for the Playbook's verifier agents.

§13 applied to ourselves: the hooks are calibrated deterministically (tests/test_hooks.py);
the AGENTS need a live model, so they are calibrated here on a schedule. Each scenario in
scenarios.json plants a defect in a copy of calibration/fixture/, drives the agent headlessly
(through the host_runner seam, cheap model, hard caps), and applies a DETERMINISTIC oracle: regexes the output
must / must not match. No LLM judge — the oracle split governs our own calibration too.

A plant surviving to a clean verdict is a BLOCKING failure (exit 1). Results append to
docs/calibration/history.md (override with --history; suppress with --history "").

Usage:
    python3 calibration/run_calibration.py                 # all scenarios, live model
    python3 calibration/run_calibration.py --agent NAME    # one agent's scenarios
    python3 calibration/run_calibration.py --dry-run       # validate without model calls
Environment: TDD_PLAYBOOK_CLAUDE_BIN / TDD_PLAYBOOK_CODEX_BIN, TDD_PLAYBOOK_CALIBRATION_MODEL
(default "haiku"), TDD_PLAYBOOK_CALIBRATION_ARGS (host-specific extra args, whitespace-split — e.g.
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
import host_runner  # noqa: E402
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


# Signatures of the CLI refusing to do the work AT ALL. These are not agent output — they
# are the harness being told "no doer ran". They arrive on STDOUT with exit 0, which is why
# the old rc-and-empty-stdout test could not see them.
#
# THE INCIDENT (2026-08-06, live, David's run). Every one of 40 scenarios returned
# "You've hit your monthly spend limit". No agent executed. The harness scored it as
# recall 1/22 and FP 18/18 and APPENDED it to the scoreboard — a fabricated row asserting
# that seven verification agents had catastrophically regressed, when what had actually
# happened was a billing ceiling. It also poisoned VITALITY (39 "failing" plants) and the
# ledger's noise floor, and 19 pre-registered predictions were one commit away from being
# scored against it.
#
# The old rule asked "nonzero exit AND empty stdout?" — a PROXY for "did the doer run?".
# It was literally true and described something else, which is the most expensive kind of
# green. Ask about non-execution directly.
NONEXECUTION_SIGNATURES = (
    "hit your monthly spend limit",
    "hit your usage limit",
    "rate limit",
    "Invalid API key",
    "authentication_error",
    "Credit balance is too low",
    "Please run /login",
    # 2026-08-06, live: a clean control scored BLOCKING FAIL because the agent was blocked by
    # PERMISSIONS and said so, clearly and correctly. That is the environment refusing, not
    # the agent missing — and because it landed on a CONTROL it was counted as a FALSE
    # POSITIVE, so FP read 2/4 when the truth was 1/3. Same class as the spend limit, new
    # signature. These phrasings are deliberately FIRST-PERSON-BLOCKED, not the bare word
    # "permission": a script-adversary reviewing file modes discusses permissions constantly,
    # and a false env_failure drops a real agent MISS out of the denominator and flatters
    # recall — the same defect sign-flipped.
    "I need permissions to",
    "I'm currently blocked",
    "I am currently blocked",
    "blocked by permission",
    "requires granting",
    "permission to complete",
)
# NO LENGTH FLOOR, deliberately. The first version of this fix also refused any turn under
# 200 chars, on the theory that a real verdict is longer than a limit notice. Its own clean
# CONTROL caught it: legitimate verdicts ARE short ("RED-FIRST: NOT VERIFIED — the test
# passes in both states" is 55 chars), so the floor rejected real agent turns as environment
# failures. That is the SAME defect sign-flipped — a false env_failure drops a genuine agent
# MISS out of the denominator and flatters recall. Length is a proxy; the signature list
# above is the thing itself. Only a literally empty turn is non-execution.
MIN_REAL_OUTPUT = 0


def nonexecution_reason(text):
    """The signature that proves the doer never ran, or None. Pure, so it is testable
    without a CLI and can be planted against."""
    low = (text or "").lower()
    for sig in NONEXECUTION_SIGNATURES:
        if sig.lower() in low:
            return sig
    return None


def run_agent(scenario, root, host_bin, model, host="claude"):
    """One rep. Returns (status, output), status in {ok, timeout, env_failure} — typed at the
    seam that HOLDS the returncode/exception (arch-F4). env_failure = the doer never ran; it
    is not an agent failure and is excluded from n. FileNotFoundError propagates (fatal)."""
    prompt = (agent_body(scenario["agent"])
              + "\n\n# TASK (work in the current directory; it is a git repo)\n"
              + scenario["task"])
    extra = os.environ.get("TDD_PLAYBOOK_CALIBRATION_ARGS", "").split()
    try:
        # child_env: capture OFF for the nested host — its turns ARE the answer key
        from child_env import child_env
        result = host_runner.invoke(
            host, host_bin, prompt, model, root, max_turns=turns_for(scenario),
            timeout=TIMEOUT_S, env=child_env(), extra_args=extra)
    except host_runner.RunnerError:
        raise
    if result.status != "ok":
        return result.status, result.output
    # The doer was REFUSED, not wrong. These arrive on stdout with exit 0, so they must be
    # matched on content — see NONEXECUTION_SIGNATURES for the 2026-08-06 incident.
    both = result.output or ""
    sig = nonexecution_reason(both)
    if sig:
        return "env_failure", "[env failure: the CLI refused to run — {!r}]\n{}".format(
            sig, both.strip()[:800])
    if not result.output.strip():
        return "env_failure", ("[env failure: exit 0 with no output at all — the doer "
                               "produced no turn]\n{}").format(both.strip()[:800])
    return "ok", result.output


# U3a (2026-08-15): a fixture file must not EXPLAIN its own plant. The staged fixture is the
# doer's whole visible world; a docstring naming the harness ("plant", "the adversary must
# catch", "band-aid vs good-fix") hands the checker the answer and the situation for free.
# Vacuity-guarded (files_scanned in the message) so a sweep that scanned nothing can't pass.
_FIXTURE_TELLS = re.compile(
    r"\bplant\b|\bplants\b|calibrat|adversary|band-aid|good-fix|design smell|"
    r"the challenge|by design", re.IGNORECASE)


def fixture_legibility_problems(fixture_dir=FIXTURE):
    problems, scanned = [], 0
    for root, _dirs, files in os.walk(fixture_dir):
        for name in files:
            if name.endswith((".py", ".sh", ".md")):
                path = os.path.join(root, name)
                scanned += 1
                with open(path, encoding="utf-8", errors="replace") as fh:
                    for i, line in enumerate(fh, 1):
                        if _FIXTURE_TELLS.search(line):
                            rel = os.path.relpath(path, fixture_dir)
                            problems.append("fixture announces the harness: {}:{} — {!r} "
                                            "(a fixture must not explain its own plant; move "
                                            "the why to plant-forms.md)".format(
                                                rel, i, line.strip()[:70]))
    if scanned == 0:
        problems.append("fixture-legibility sweep scanned 0 files — refusing a vacuous pass")
    return problems


def dry_run(scenarios):
    """Validate everything that doesn't need a model — through THE validator (D0), so shipped
    scenarios obey the same rules as corpus proposals. Exit non-zero on any problem."""
    problems = []
    # fixture must be green unplanted
    p = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                       cwd=FIXTURE, capture_output=True, text=True, timeout=120)
    if p.returncode != 0:
        problems.append("fixture tests FAIL unplanted:\n" + p.stderr[-800:])
    problems.extend(fixture_legibility_problems())
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
    # an EXPIRED promotion quarantine must be loud on the gate path, not discovered later
    problems.extend(quarantine_problems())
    for msg in problems:
        print("DRY-RUN PROBLEM: " + msg)
    print("dry-run: {} scenario(s), {} problem(s)".format(len(scenarios), len(problems)))
    return 1 if problems else 0


def repo_sha():
    p = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                       capture_output=True, text=True, timeout=30)
    return p.stdout.strip() if p.returncode == 0 and p.stdout.strip() else "unknown"


# ---- PROMOTION QUARANTINE (CIVerd engine finding, 2026-08-05) -------------------------
# The AMBER -> BLOCKING promotion is MECHANICAL: a second consecutive AMBER hardens into a
# blocking verdict. Three scenarios carry oracles PROVEN defective against recorded agent
# text (one regex cannot match the word "survives"; two are synonym misses), and they are
# v1.22.0-BASELINE plants — check_scoreboard_integrity refuses edits to approved plants, so
# SUPERSEDING them is the only sanctioned path and it is dated debt on calibration-loop.
# Left alone they would promote known-FALSE failures to BLOCKING and harden noise into
# policy while the fix waits.
#
# This pauses PROMOTION ONLY. Matching, scoring, rep counts and the AMBER verdict itself are
# untouched — the instrument stays byte-identical for the ten predictions in flight
# (L-20260805-20..29), which is why this is safe to land mid-cycle when a matcher change
# would not be. House debt shape; an EXPIRED entry stops protecting AND is reported.
PROMOTION_QUARANTINE = [
    {"what": "oracle cannot match 'survives' — regex is surviv(ed|ing|ors?); the agent's "
             "'every mutant survives' is a correct catch scored as a miss",
     "target": "shadowed-import-vacuous-suite", "owner": "david", "expires": "2026-09-15"},
    {"what": "oracle lists future caller/consumer/user; the agent wrote 'ANY future call "
             "site is at risk' — a correct BAND-AID verdict scored as a miss",
     "target": "csv-escape-fixed-at-call-site", "owner": "david", "expires": "2026-09-15"},
    {"what": "oracle lists disagree/diverge/bypass; the agent wrote 'contract mismatch' and "
             "'accidental agreement' — a correct BAND-AID verdict scored as a miss",
     "target": "special-case-bypasses-both-copies", "owner": "david", "expires": "2026-09-15"},
    # 2026-08-06: the same disposition, forced by the same rule on three MORE plants. Their
    # run-4 oracle fixes were made when the newest tag was v1.22.0 and the immutability check
    # therefore could not see them; CIVerd's --tags fix moved the baseline to v1.26.0 and the
    # edits went RED, so they were reverted (oracle-changes.md, SECOND CORRECTION). The
    # defects the reverts restore are documented and reproduced, so they must not promote.
    {"what": "oracle needs a synonym for undeclared/undocumented/dark-by-default; the agent "
             "named FIXTURE_CSV_EXPORT_ENABLED and failed ACTIVATED correctly — a correct "
             "catch scored as a miss on vocabulary (and 25 turns is short for the task)",
     "target": "ghost-gate-undeclared-export-flag", "owner": "david", "expires": "2026-09-15"},
    {"what": "the control's own premise is what the auditor REDs: a SEPARATE planted test "
             "does not calibrate the NAMED deliverable (§13), so the auditor is right and "
             "the control is mis-specified — its FAILs are instrument error, not agent error",
     "target": "control-drift-tripwire-union-exercised", "owner": "david",
     "expires": "2026-09-15"},
    {"what": "prose-vocabulary oracle (never exercised|cannot fail|excus…) missed three "
             "correct catches across three runs; the verdict-shape anchor that fixed it "
             "(3/3 on run 4) is reverted, so the whack-a-mole misses come back",
     "target": "drift-tripwire-intersection-excuse", "owner": "david", "expires": "2026-09-15"},
]


def quarantine_problems(today=None, corpus_ids=None):
    """Expired or malformed quarantine entries, as loud strings. Fails closed: an expired
    entry is REPORTED here and simultaneously stops protecting in verdict_for().

    Also fails closed on the NAME-KEYED AUTHORIZATION shape (2026-08-06, from CIVerd's
    engine sweep of the two-windows class): this quarantine suppresses promotion for a
    scenario ID, and an id is a name. It is safe today only because every target is a
    corpus/approved plant, which integrity rule (b) pins byte-identical — safe by ANOTHER
    gate, and enforced by nothing. A target that lives only in scenarios.json would be
    name-keyed authorization over MUTABLE content: the oracle can be rewritten legally
    (journaled), and a quarantine granted for the OLD defect would go on suppressing
    promotion for whatever the new one turns out to be. So the pairing is now the rule.
    `corpus_ids` is injectable because a check nobody can plant against is not a check.
    """
    today = today or datetime.date.today()
    if corpus_ids is None:
        corpus_ids = {c.get("id") for c in load_corpus()}
    out = []
    for e in PROMOTION_QUARANTINE:
        missing = [f for f in ("what", "target", "owner", "expires") if not e.get(f)]
        if missing:
            out.append("PROMOTION QUARANTINE {}: missing {}".format(
                e.get("target", "<no target>"), "/".join(missing)))
            continue
        try:
            exp = datetime.date.fromisoformat(e["expires"])
        except ValueError:
            out.append("PROMOTION QUARANTINE {}: expires {!r} is not YYYY-MM-DD".format(
                e["target"], e["expires"]))
            continue
        if e["target"] not in corpus_ids:
            out.append(
                "PROMOTION QUARANTINE {}: no approved plant carries that id — quarantine is "
                "NAME-keyed, so a target whose content is mutable lets authorization granted "
                "for the OLD defect carry over to whatever replaces it. Target an immutable "
                "corpus/approved plant, or pin the content some other way first."
                .format(e["target"]))
            continue
        if exp < today:
            out.append(
                "PROMOTION QUARANTINE {}: EXPIRED {} (owner: {}) — supersede the plant or "
                "re-date consciously; promotion has RESUMED for it".format(
                    e["target"], e["expires"], e["owner"]))
    return out


def promotion_quarantined(sid, today=None):
    """True only while a well-formed, unexpired entry covers this scenario."""
    today = today or datetime.date.today()
    for e in PROMOTION_QUARANTINE:
        if e.get("target") != sid:
            continue
        try:
            if datetime.date.fromisoformat(e["expires"]) >= today:
                return True
        except (ValueError, KeyError, TypeError):
            return False
    return False


def _form_of(sid, resolved):
    """An id with no register entry is `dev`. Absence is a decision and this is the safe
    one — an unassigned plant gets tuned against, never quietly reported as a clean
    holdout measurement. (Mirrors plant_forms.form_of; kept local so a missing register
    module cannot break selection entirely.)"""
    return resolved.get(sid, "dev")


def verdict_for(sid, k, n, last, today=None):
    """The verdict for one scenario's reps. Extracted from main() so the promotion rule is
    testable at a seam rather than only through a live model run."""
    if n == 0:
        return "INVALID — env failure on all reps"
    if k == n:
        return "PASS"
    if k == 0:
        return "**BLOCKING FAIL**"
    if last == "AMBER" and not promotion_quarantined(sid, today):
        return "**BLOCKING FAIL** (AMBER\u00d72)"
    return "AMBER"


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
    ap.add_argument("--form", choices=("dev", "holdout", "all"), default="dev",
                    help="which plant form to run: dev (default, the tuning set) · holdout "
                         "(the quarterly reporting set, never tuned against) · all")
    ap.add_argument("--repeat", type=int, default=DEFAULT_REPEAT, metavar="K",
                    help="reps per scenario (default {}; one roll is a coin flip, not a "
                         "measurement — §5a)".format(DEFAULT_REPEAT))
    ap.add_argument("--dry-run", action="store_true", help="validate without model calls")
    ap.add_argument("--host", choices=("claude", "codex"), default="claude",
                    help="host runner; histories and denominators remain host-specific")
    ap.add_argument("--host-bin", help="host binary override (preferred portable option)")
    ap.add_argument("--claude-bin", default=os.environ.get("TDD_PLAYBOOK_CLAUDE_BIN", "claude"))
    ap.add_argument("--model", default=os.environ.get("TDD_PLAYBOOK_CALIBRATION_MODEL", "haiku"))
    ap.add_argument("--history", default=None,
                    help='history file to append (default is per-host; "" to suppress)')
    args = ap.parse_args(argv)

    if args.history is None:
        args.history = host_runner.default_history(args.host)
    if args.host_bin:
        selected_bin = args.host_bin
    elif args.host == "claude":
        selected_bin = args.claude_bin
    else:
        selected_bin = os.environ.get("TDD_PLAYBOOK_CODEX_BIN", "codex")

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
    # v1.29 item 3: the dev/holdout split. dev is the tuning set (run every cycle); holdout
    # is the reporting set, read quarterly and never tuned against — otherwise the number we
    # quote externally is the one the tuning loop has been iterating on. Forms live in an
    # append-only register beside the corpus, NOT in the plant files (rule (b) pins those
    # byte-identical forever, and burn-on-failure has to be able to change a form).
    resolved_forms = {}
    try:
        import plant_forms as _pf
        resolved_forms = _pf.resolve_forms(
            _pf.parse_register(open(os.path.join(REPO, _pf.REGISTER)).read()))
    except Exception as e:
        # An unreadable register must not silently select everything as dev — that is how a
        # holdout plant gets tuned against without anyone deciding to.
        if args.form != "all":
            print("FATAL: --form {} requested but the plant-form register is unreadable "
                  "({}). Refusing to guess a split.".format(args.form, e), file=sys.stderr)
            return 2
    if args.form != "all":
        scenarios = [s for s in scenarios
                     if _form_of(s["id"], resolved_forms) == args.form]
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
    # "the previous run block" (blocks are filter-scoped; arch-F5). P (2026-08-15): drawn
    # only from run blocks in THIS run's population (same form + isolation), so a
    # no-playbook AMBER can never promote a normal AMBER to BLOCKING FAIL. Pre-run-block
    # legacy rows (2026-07-09) are outside any block and carry no AMBER, so excluding them
    # cannot change a promotion.
    run_population = {"form": args.form, "isolation": "with-playbook"}
    prior_rows = []
    if args.history and os.path.isfile(args.history):
        with open(args.history) as fh:
            _blocks, _ = history_format.parse_run_blocks(fh.read())
        prior_rows = [r for b in _blocks
                      if history_format.population_matches(b, run_population)
                      for r in b["rows"]]

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
                status, out = run_agent(sc, root, selected_bin, args.model, args.host)
            except FileNotFoundError:
                print("FATAL: {} binary not found ({}) — set --host-bin or the host env "
                      "override, or use --dry-run".format(args.host, selected_bin))
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
        verdict = verdict_for(sc["id"], k, n, last_kind(sc["id"]))
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
            if last_kind(sc["id"]) == "AMBER" and promotion_quarantined(sc["id"]):
                print("  (promotion to BLOCKING is QUARANTINED for this scenario — its "
                      "oracle is proven defective and the plant is immutable; superseding "
                      "is dated debt. Scoring is untouched.)")
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
            "recall": recall, "fp": fp, "form": args.form}
    # A mostly-INVALID run is RECORDED, not suppressed — the row is honest non-data, and
    # "we tried and the environment refused" is worth knowing. INVALID is already excluded
    # from recall/FP, from the staleness clock, and from vitality. What it must NOT do is
    # silently consume a pre-registered ledger prediction, which is handled at the binder.
    invalid = [r for r in results if r["verdict"].startswith("INVALID")]
    if results and len(invalid) >= max(1, len(results) // 2):
        print("\nENVIRONMENT FAILURE — {} of {} scenarios never executed (the CLI refused: "
              "spend/rate limit, auth, or an empty turn). This run is a reading of the "
              "ENVIRONMENT, not of the agents. It is recorded as INVALID so the attempt is "
              "visible, but it measures NOTHING: recall/FP exclude it, it does not refresh "
              "the staleness clock, and it will not score any pre-registered prediction. "
              "Fix the cause and re-run.".format(len(invalid), len(results)), file=sys.stderr)
        print("   e.g. {}".format(", ".join(r["sc"]["id"] for r in invalid[:4])),
              file=sys.stderr)
    append_history(args.history, host_runner.model_identity(args.host, args.model), results, meta)
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

    # v1.29: has this plant population stopped discriminating? A saturated plant reads as a
    # rising score while measuring nothing, so the authoring cycle needs the number in front
    # of it. A POINTER only — never a gate, never a deletion driver (R4: the corpus grows).
    try:
        vit = os.path.join(HERE, "plant_vitality.py")
        if os.path.isfile(vit):
            p = subprocess.run([sys.executable, vit, "--form", args.form],
                               capture_output=True, text=True, timeout=120)
            if p.stdout.strip():
                print(p.stdout.strip())
        else:
            print("vitality: unmeasured (plant_vitality.py not present)")
    except Exception as e:
        print("vitality: unmeasured (vitality unavailable: {})".format(e))

    # D-A A8 (2026-08-14): the review-recurrence pointer — has the same deterministic miss
    # been recorded twice with no guard built? A verb with no scheduled reader is §6b dark
    # waste; this cycle block is the reader. A POINTER only, wrapped like its neighbours —
    # reporting must never fail a calibration run (exit 3 there is a vacuous-refusal
    # statement, not an error here).
    try:
        rl = os.path.join(REPO, "plugins", "tdd-playbook", "bin", "review_ledger.py")
        if os.path.isfile(rl):
            p = subprocess.run([sys.executable, rl, "recurrence"],
                               capture_output=True, text=True, timeout=60)
            if p.stdout.strip():
                print(p.stdout.strip())
            elif p.stderr.strip():
                print("review-recurrence: {}".format(p.stderr.strip()))
        else:
            print("review-recurrence: unmeasured (review_ledger.py not present)")
    except Exception as e:
        print("review-recurrence: unmeasured (review ledger unavailable: {})".format(e))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
