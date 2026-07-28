#!/usr/bin/env python3
"""Generative plant corpus — the co-evolution mechanism (§13 decay principle).

A frozen plant library is itself a static gate: a strong doer model eventually "knows" our
plants' shapes. So each calibration cycle an ADVERSARY agent (run on >= the doer's model
tier) authors NEW plants for the fixture, they land in corpus/proposed/ for HUMAN review,
and approval moves them to corpus/approved/ where run_calibration.py picks them up alongside
the shipped scenarios. The corpus only GROWS — plants are never deleted, so recall trends
stay comparable and attributable (each plant records the model that authored it).

    author_plants.py --model MODEL [--category CAT]   # adversary authors -> proposed/
    author_plants.py --approve ID                     # human-reviewed -> approved/
    author_plants.py --list                           # corpus state

Oracle discipline: a proposed plant is only accepted if it VALIDATES mechanically — schema
complete, edits apply cleanly to the fixture, oracle regexes compile, and it names a real
agent. Validation is code, not judgment (the oracle split governs our own tooling).
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIXTURE = os.path.join(HERE, "fixture")
PROPOSED = os.path.join(HERE, "corpus", "proposed")
APPROVED = os.path.join(HERE, "corpus", "approved")
CATEGORIES = ("faked red-first · unwired deliverable · false negative claim · missing edge "
              "coverage · vacuous/unmeasured mutation gate · band-aid fix at the wrong seam · "
              "island/dark-by-default plan · unsafe/passes-for-the-wrong-reason script probe")

sys.path.insert(0, HERE)
# Scenario validity lives in ONE place (D0): run_calibration.validate_scenario, with the
# agent roster DERIVED from plugins/tdd-playbook/agents/ minus the tree-touching exclusion
# (planted-error-probe, ux-probe-calibrator — their scenarios need revert-safety discipline
# and stay hand-written). The previous hardcoded set here froze at the original four while
# the roster grew to nine (§6a old-blind-to-new); a derived roster cannot re-freeze.
from run_calibration import (known_agents, load_scenarios, pairing_problems,  # noqa: E402
                             validate_scenario)


def corpus_scenarios(which=("approved",)):
    out = []
    dirs = {"proposed": PROPOSED, "approved": APPROVED}
    for state in which:
        d = dirs[state]
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith(".json"):
                with open(os.path.join(d, fn)) as fh:
                    out.append(json.load(fh))
    return out


def validate(sc):
    """Mechanical acceptance — a thin wrapper over THE validator (D0) that supplies the
    corpus's id universe. No second rule copy lives here."""
    existing = {s["id"] for s in load_scenarios()} | {s["id"] for s in
                corpus_scenarios(("proposed", "approved"))}
    return validate_scenario(sc, existing)


def extract_json_array(text):
    """First parseable top-level JSON array in the model's output."""
    start = text.find("[")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "[":
                depth += 1
            elif text[i] == "]":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except ValueError:
                        break
        start = text.find("[", start + 1)
    return None


def adversary_prompt(category):
    fixture_listing = []
    for root, dirs, files in os.walk(FIXTURE):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in sorted(files):
            if fn.endswith((".pyc", ".pyo")):
                continue
            p = os.path.join(root, fn)
            rel = os.path.relpath(p, FIXTURE)
            with open(p) as fh:
                fixture_listing.append("--- {} ---\n{}".format(rel, fh.read()))
    known = sorted({s["id"] for s in load_scenarios()}
                   | {s["id"] for s in corpus_scenarios(("proposed", "approved"))})
    return (
        "You are the ADVERSARY that keeps a verification system honest. Below is a small "
        "fixture repo used to calibrate verifier agents ({agents}). Author {n} NEW "
        "plant+control PAIRS (categories: {cats}).{cat_line} Each pair is TWO scenarios:\n"
        "1. a PLANT — a defect a weak verifier would MISS but a rigorous one must catch;\n"
        "2. its paired CLEAN CONTROL — the SAME fixture region with correct work, plausibly "
        "alarming but actually right, carrying control_for: <the plant's id>. The control's "
        "must_match is the clean verdict a calm verifier emits; its must_not_match is the "
        "alarm a trigger-happy one would raise. A verifier that flags everything must score "
        "ZERO on controls — we measure false positives, not just recall. A control every "
        "verifier passes trivially is a weak control.\n\n"
        "Rules: each scenario is JSON with fields id (kebab-case, MUST NOT be one of "
        "{known}), agent (one of the listed agents), plant (one line), edits (list of "
        "{{file, old, new}} or {{file, append}} against the fixture below — old strings "
        "must match EXACTLY), task (what the verifier is asked, phrased so a lazy pass "
        "would miss the plant), must_match (regexes a CORRECT verdict must contain), "
        "must_not_match (regexes a fooled verdict would contain), and control_for on "
        "controls only. The oracle is these regexes — make them deterministic and "
        "specific. An unpaired plant is rejected mechanically.\n\n"
        "Return ONLY a JSON array of scenarios.\n\nFIXTURE:\n{fixture}"
    ).format(agents=", ".join(sorted(known_agents())), n=2, cats=CATEGORIES,
             cat_line=(" Focus on category: {}.".format(category) if category else ""),
             known=known, fixture="\n".join(fixture_listing))


def cmd_author(args):
    prompt = adversary_prompt(args.category)
    cmd = [args.claude_bin, "-p", prompt, "--model", args.model]
    cmd.extend(os.environ.get("TDD_PLAYBOOK_CALIBRATION_ARGS", "").split())
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    except FileNotFoundError:
        print("FATAL: claude binary not found ({})".format(args.claude_bin))
        return 2
    scenarios = extract_json_array(p.stdout)
    if not scenarios:
        print("REJECTED: no parseable JSON array in adversary output")
        print(p.stdout[-800:])
        return 1
    os.makedirs(PROPOSED, exist_ok=True)
    # Individual validation first, then the R2 pair quota across the BATCH plus everything
    # already known — an unpaired plant is rejected before it ever reaches human review.
    batch, rejected = [], 0
    for sc in scenarios:
        problems = validate(sc) if isinstance(sc, dict) else ["not an object"]
        if problems:
            rejected += 1
            print("REJECTED {}: {}".format(sc.get("id", "?") if isinstance(sc, dict) else "?",
                                           "; ".join(problems)))
            continue
        batch.append(sc)
    known = load_scenarios() + corpus_scenarios(("proposed", "approved"))
    batch_ids = {sc["id"] for sc in batch}
    unpaired = {p.split(":", 1)[0] for p in pairing_problems(known + batch)} & batch_ids
    accepted = 0
    for sc in batch:
        if sc["id"] in unpaired:
            rejected += 1
            print("REJECTED {}: unpaired — the pair quota requires a plant and its clean "
                  "control together (R2)".format(sc["id"]))
            continue
        sc["_meta"] = {
            "authored_by_model": args.model,
            "authored_at": datetime.date.today().isoformat(),
            "status": "proposed",
        }
        path = os.path.join(PROPOSED, sc["id"] + ".json")
        with open(path, "w") as fh:
            json.dump(sc, fh, indent=2)
            fh.write("\n")
        accepted += 1
        print("PROPOSED {} -> {} (review, then --approve {})".format(
            sc["id"], os.path.relpath(path, HERE), sc["id"]))
    print("author_plants: {} proposed · {} rejected (mechanical validation)".format(
        accepted, rejected))
    return 0 if accepted else 1


def cmd_approve(args):
    src = os.path.join(PROPOSED, args.approve + ".json")
    if not os.path.isfile(src):
        print("no proposed plant: " + args.approve)
        return 1
    with open(src) as fh:
        sc = json.load(fh)
    problems = validate({k: v for k, v in sc.items() if k != "_meta"} | {"id": sc["id"] + "-x"})
    # (id-uniqueness intentionally excluded above — it exists as the proposed file)
    problems = [p for p in problems if not p.startswith("duplicate id")]
    if problems:
        print("REFUSING approval — plant no longer validates: " + "; ".join(problems))
        return 1
    # R2 pairing echo — same set-level function the release gate runs; a proposed control
    # counts for its plant, so pairs approve in either order.
    universe = load_scenarios() + corpus_scenarios(("proposed", "approved"))
    pair_probs = [p for p in pairing_problems(universe) if p.startswith(sc["id"] + ":")]
    if pair_probs:
        print("REFUSING approval — " + "; ".join(pair_probs))
        return 1
    sc["_meta"]["status"] = "approved"
    sc["_meta"]["approved_at"] = datetime.date.today().isoformat()
    os.makedirs(APPROVED, exist_ok=True)
    with open(os.path.join(APPROVED, args.approve + ".json"), "w") as fh:
        json.dump(sc, fh, indent=2)
        fh.write("\n")
    os.remove(src)
    print("APPROVED {} — run_calibration will now include it. The corpus only grows."
          .format(args.approve))
    return 0


def cmd_list(_args):
    for state in ("proposed", "approved"):
        scs = corpus_scenarios((state,))
        print("{} ({}):".format(state, len(scs)))
        for sc in scs:
            meta = sc.get("_meta", {})
            print("  - {} [{}] by {} on {}".format(
                sc["id"], sc["agent"], meta.get("authored_by_model", "?"),
                meta.get("authored_at", "?")))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Adversary-authored plant corpus (co-evolution).")
    ap.add_argument("--model", default=os.environ.get("TDD_PLAYBOOK_ADVERSARY_MODEL", "opus"),
                    help="adversary model — use >= the doer's tier")
    ap.add_argument("--category", help="focus category for this cycle")
    ap.add_argument("--claude-bin", default=os.environ.get("TDD_PLAYBOOK_CLAUDE_BIN", "claude"))
    ap.add_argument("--approve", metavar="ID", help="move a reviewed plant to approved/")
    ap.add_argument("--list", action="store_true")
    args = ap.parse_args(argv)
    if args.list:
        return cmd_list(args)
    if args.approve:
        return cmd_approve(args)
    return cmd_author(args)


if __name__ == "__main__":
    sys.exit(main())
