#!/usr/bin/env python3
"""Structural calibration for the agent + command layer (the deterministic half of WS1).

The behavioral half (do the agents actually catch plants?) lives in calibration/ and needs a
live model. THIS file checks the invariants that hold without one:
  - every agent has parseable frontmatter (name, description, tools);
  - Edit is held ONLY by the sanctioned tree-touching agents;
  - the forced-verdict/Recommendation contracts are present (an agent that can end without a
    forced line can hedge — the exact failure mode the contracts exist to prevent);
  - the tree-touching agents carry the MECHANICAL revert-safety block (with_snapshot.py);
  - /edge /mutate /probe close their loops ("Loop closed:" contract present).
Per §13, the checker itself is calibrated: planted-bad fixtures must FAIL the checks.
Self-contained, no pytest. Run: python3 tests/test_agents.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AGENTS = os.path.join(ROOT, "agents")
COMMANDS = os.path.join(ROOT, "commands")

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


# ------------------------------------------------------------------ checker primitives
def frontmatter(text):
    """Parse simple `key: value` YAML frontmatter. Returns dict or None."""
    m = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not m:
        return None
    fm = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip()
    return fm


def tools_of(fm):
    return [t.strip() for t in fm.get("tools", "").split(",") if t.strip()]


def has_revert_safety(text):
    return "with_snapshot.py" in text and "begin" in text and "verify" in text


def has_forced_recommendation(text):
    return re.search(r"Recommendation:\s*<", text) is not None


# ------------------------------------------------------------------ expected contracts
# agent -> (may_hold_Edit, forced_line_regexes)
AGENT_CONTRACTS = {
    "red-first-verifier": (False, [r"RED-FIRST: VERIFIED", r"NOT VERIFIED"]),
    "tripwire-auditor": (False, [r"Recommendation:"]),
    "claims-verifier": (False, [r"Recommendation:"]),
    "edge-case-adversary": (False, [r"Recommendation:"]),
    "mutation-runner": (True, []),
    "planted-error-probe": (True, [r"SAFETY NET VERIFIED", r"BLOCKING GAP"]),
    "ux-probe-calibrator": (True, [r"PROBE VERIFIED", r"BLOCKING GAP", r"Recommendation:"]),
}
TREE_TOUCHING = {"red-first-verifier", "mutation-runner", "planted-error-probe",
                 "ux-probe-calibrator"}
LOOP_CLOSING_COMMANDS = {"edge", "mutate", "probe"}


def test_agents():
    found = {}
    for fn in sorted(os.listdir(AGENTS)):
        if not fn.endswith(".md"):
            continue
        name = fn[:-3]
        with open(os.path.join(AGENTS, fn)) as fh:
            found[name] = fh.read()

    check("all 7 contracted agents exist", set(AGENT_CONTRACTS) == set(found),
          sorted(set(AGENT_CONTRACTS) ^ set(found)))

    for name, text in sorted(found.items()):
        fm = frontmatter(text)
        check("{}: frontmatter parses with name+description+tools".format(name),
              fm is not None and fm.get("name") == name and fm.get("description")
              and fm.get("tools"), fm)
        if fm is None or name not in AGENT_CONTRACTS:
            continue
        may_edit, forced = AGENT_CONTRACTS[name]
        tools = tools_of(fm)
        if may_edit:
            check("{}: Edit sanctioned".format(name), "Edit" in tools, tools)
        else:
            check("{}: does NOT hold Edit".format(name), "Edit" not in tools, tools)
        for rx in forced:
            check("{}: forced line /{}/ present".format(name, rx),
                  re.search(rx, text) is not None)
        if name in TREE_TOUCHING:
            check("{}: mechanical revert-safety block present".format(name),
                  has_revert_safety(text))


def test_commands():
    for fn in sorted(os.listdir(COMMANDS)):
        if not fn.endswith(".md"):
            continue
        name = fn[:-3]
        with open(os.path.join(COMMANDS, fn)) as fh:
            text = fh.read()
        fm = frontmatter(text)
        check("/{}: frontmatter parses with description".format(name),
              fm is not None and fm.get("description"), fm)
        if name in LOOP_CLOSING_COMMANDS:
            check("/{}: closes its loop (Loop closed contract)".format(name),
                  "Loop closed:" in text)
    with open(os.path.join(COMMANDS, "claims.md")) as fh:
        check("/claims: cites the mechanical gate", "verify_citations.py" in fh.read())


def test_planted_fixtures():
    """The checker must be able to FAIL — planted-bad content must be flagged."""
    bad_no_reco = ("---\nname: edge-case-adversary\ndescription: x\n"
                   "tools: Read, Grep, Glob\n---\nbody with no forced line\n")
    check("planted: missing Recommendation is detected",
          not has_forced_recommendation(bad_no_reco))

    bad_edit = ("---\nname: claims-verifier\ndescription: x\n"
                "tools: Read, Grep, Glob, Edit\n---\nRecommendation: <action>\n")
    check("planted: illicit Edit tool is detected",
          "Edit" in tools_of(frontmatter(bad_edit)))

    bad_no_snapshot = ("---\nname: planted-error-probe\ndescription: x\n"
                       "tools: Bash, Read, Edit, Grep, Glob\n---\n"
                       "I promise to revert cleanly (git diff empty).\n")
    check("planted: prose-only revert promise is detected",
          not has_revert_safety(bad_no_snapshot))

    good = ("---\nname: planted-error-probe\ndescription: x\ntools: Bash, Edit\n---\n"
            "run with_snapshot.py begin first and with_snapshot.py verify last\n"
            "Recommendation: <action> because <finding>\n")
    check("planted: clean fixture passes all three checks",
          has_revert_safety(good) and has_forced_recommendation(good)
          and frontmatter(good) is not None)


def main():
    print("Agent/command structural calibration")
    for fn in (test_agents, test_commands, test_planted_fixtures):
        print("\n[{}]".format(fn.__name__))
        fn()
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
