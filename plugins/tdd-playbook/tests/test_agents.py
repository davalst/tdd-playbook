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
import json
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
    "integration-adversary": (False, [r"Recommendation:"]),
    "architecture-adversary": (False, [r"Recommendation:"]),
    "mutation-runner": (True, []),
    "planted-error-probe": (True, [r"SAFETY NET VERIFIED", r"BLOCKING GAP"]),
    "ux-probe-calibrator": (True, [r"PROBE VERIFIED", r"BLOCKING GAP", r"Recommendation:"]),
}
TREE_TOUCHING = {"red-first-verifier", "mutation-runner", "planted-error-probe",
                 "ux-probe-calibrator"}
LOOP_CLOSING_COMMANDS = {"edge", "mutate", "probe", "tdd-plan", "integration-audit"}


def test_agents():
    found = {}
    for fn in sorted(os.listdir(AGENTS)):
        if not fn.endswith(".md"):
            continue
        name = fn[:-3]
        with open(os.path.join(AGENTS, fn)) as fh:
            found[name] = fh.read()

    check("all 9 contracted agents exist", set(AGENT_CONTRACTS) == set(found),
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
    with open(os.path.join(COMMANDS, "tripwire.md")) as fh:
        text = fh.read()
        check("/tripwire: carries the ACTIVATED leg", "ACTIVATED" in text)
        check("/tripwire: cites the registry gate", "capability_registry.py" in text)
        check("/tripwire: demands the production composition root",
              "composition root" in text)
    with open(os.path.join(COMMANDS, "tdd-plan.md")) as fh:
        text = fh.read()
        check("/tdd-plan: carries the Integration surface", "Integration surface" in text)
        check("/tdd-plan: dispatches the integration-adversary",
              "integration-adversary" in text)
    with open(os.path.join(COMMANDS, "integration-audit.md")) as fh:
        text = fh.read()
        check("/integration-audit: cites the mechanical citation gate",
              "verify_citations.py" in text)
        check("/integration-audit: dispatches the claims-verifier",
              "claims-verifier" in text)
        check("/integration-audit: findings carry owner + expiry",
              "OWNER" in text and "EXPIRY" in text)


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


def test_v16_doctrine():
    """v1.6 anti-tax + gate-quality doctrine must stay present (SKILL, agent, command).

    Origin: downstream ROI telemetry (cheliped) — roster creep to 44 modules, prose-pinning
    forced by zero-survivor gates, duplicate hook firing. These pins keep the counter-rules
    from silently regressing out of the doctrine."""
    skill = os.path.join(ROOT, "skills", "tdd-playbook", "SKILL.md")
    with open(skill) as fh:
        text = fh.read()
    for label, needle in [
        ("SKILL §4: roster admission rule (survivor-cost line)", "a survivor here costs"),
        ("SKILL §4: rendering/presentation excluded from roster", "explicitly OUT"),
        ("SKILL §4: string mutants classed by role", "classed by ROLE"),
        ("SKILL §4: prose-pinning named as anti-pattern", "pinning the prose"),
        ("SKILL §4: informational class is string-internal only", "f-string"),
        ("SKILL §4: function-scoped two-tier gating", "function-scoped"),
        ("SKILL §4: vacuity guard on scoped gates", "vacuous pass"),
        ("SKILL §4: audited equivalence ledger", "equivalence ledger"),
        ("SKILL §4: killing-suite visibility check", "killing suite"),
        ("SKILL §0: numeric ceremony thresholds", "path-criticality"),
        ("SKILL §11: checkpoint transient exclusions", "transient"),
        ("SKILL §11: subagent/session-aware checkpoints", "holds the tree"),
        ("SKILL §11: mutation runs isolated from the tree", "isolated worktree"),
        ("SKILL §10: SHA-pinned actions + pinned container", "SHA-pin"),
        ("SKILL §10: determinism from pinning, not the vendor", "not the vendor"),
        ("SKILL §10: workflow edits are risky paths", "disable a blocking gate"),
    ]:
        check(label, needle in text, "needle {!r} missing".format(needle))

    with open(os.path.join(AGENTS, "mutation-runner.md")) as fh:
        agent = fh.read()
    check("mutation-runner: refuses vacuous scoped pass", "vacuous" in agent)
    check("mutation-runner: audited equivalence ledger path", "equivalence ledger" in agent)
    check("mutation-runner: exact-substitution ledger matching",
          "exact-substitution" in agent)
    check("mutation-runner: batched survivor extraction", "batch" in agent.lower())
    check("mutation-runner: f-string expressions stay code", "f-string" in agent)

    # David's standing budget (2026-07-10): the skill description is system-prompt tax on
    # EVERY session/surface — keep it <=1024 chars. If a future doctrine change genuinely
    # cannot fit, do NOT silently exceed or gut trigger vocabulary: WARN DAVID and let him
    # decide (the 1.6.3 dedupe trim is the precedent for finding chars first).
    m = re.search(r"^description: (.*)$", text, re.M)
    check("SKILL description within David's 1024-char budget",
          m is not None and len(m.group(1)) <= 1024,
          "len={} — over budget: warn David, don't silently exceed".format(
              len(m.group(1)) if m else -1))

    with open(os.path.join(COMMANDS, "mutate.md")) as fh:
        cmd = fh.read()
    check("/mutate: vacuity guard demanded", "vacuous" in cmd)
    check("/mutate: ledger with written proof", "ledger" in cmd)
    check("/mutate: roster admission enforced", "a survivor here costs" in cmd)
    check("/mutate: string-role classes carried", "prose" in cmd)
    check("/mutate: f-string expressions stay code", "f-string" in cmd)


def test_v17_doctrine():
    """v1.7 reachability doctrine must stay present (SKILL + both agent briefs + commands).

    Origin: a downstream consumer shipped six user-facing toggles that were built + wired +
    tested + registered yet UNREACHABLE — hidden from both /features and the doctor by one
    coverage-test exemption entry, with the (optional) integration-adversary skipped. These
    pins keep the four counter-rules from silently regressing out of the doctrine:
      1. Tripwire ACTIVATED/WIRED is a two-surface reachability test for toggle-gated features.
      2. An exemption/ignore/allow-list entry is for internals, never a user-facing darkness hatch.
      3. The integration-adversary is MANDATORY for config-gate / user-facing deliverables.
      4. §6b Onboard-don't-hide: default-OFF needs an online-measurable onboarding contract."""
    skill = os.path.join(ROOT, "skills", "tdd-playbook", "SKILL.md")
    with open(skill) as fh:
        text = fh.read()
    for label, needle in [
        # (1) two-surface Tripwire reachability
        ("SKILL §6: toggle wiring is a two-surface test", "TWO-surface test"),
        ("SKILL §6: route-exists trap named", "route-exists trap"),
        ("SKILL §6: canonical feature-control surface", "canonical feature-control surface"),
        ("SKILL §6: dark-to-the-operator (health surface)", "dark-to-the-OPERATOR"),
        # (2) exemption-as-darkness-vector
        ("SKILL §6a: exemption is for internals", "Exemption is for internals"),
        ("SKILL §6a: darkness hatch named", "darkness hatch"),
        ("SKILL §6a: companion test — user-facing gates never exempted", "never exempted"),
        # (3) mandatory integration-adversary
        ("SKILL §0: adversary MANDATORY for gate/user-facing deliverables",
         "MANDATORY, not optional"),
        # (4) §6b onboard, don't hide
        ("SKILL §6b: onboarding contract for default-OFF", "onboarding contract"),
        ("SKILL §6b: unscheduled switch aphorism", "will never be thrown"),
        ("SKILL §6b: named ONLINE metric, not offline eval", "named ONLINE metric"),
        ("SKILL §6b: can't-measure-online forcing rule", "it ships ON"),
    ]:
        check(label, needle in text, "needle {!r} missing".format(needle))

    with open(os.path.join(AGENTS, "integration-adversary.md")) as fh:
        adv = fh.read()
    check("integration-adversary: dispatch is MANDATORY", "MANDATORY, not optional" in adv)
    check("integration-adversary: two-surface dark-shipping question",
          "route-exists trap" in adv and "health/status surface" in adv)
    check("integration-adversary: flags the exemption hatch", "darkness HATCH" in adv)

    with open(os.path.join(AGENTS, "tripwire-auditor.md")) as fh:
        aud = fh.read()
    check("tripwire-auditor: WIRED is a two-surface test", "TWO-surface test" in aud)
    check("tripwire-auditor: exemption is evidence of darkness", "EVIDENCE OF darkness" in aud)

    with open(os.path.join(COMMANDS, "tripwire.md")) as fh:
        tw = fh.read()
    check("/tripwire: ACTIVATED carries the two-surface test", "TWO-surface" in tw)

    with open(os.path.join(COMMANDS, "integration-audit.md")) as fh:
        ia = fh.read()
    check("/integration-audit: hunts the exemption darkness hatch", "darkness HATCH" in ia)


def test_v17_planted_fixtures():
    """The v1.7 pins must be able to FAIL — a doctrine file stripped of a counter-rule needle
    must be flagged, or the pin is theater (§13 calibrate-the-checker rule)."""
    stripped = "SKILL with no reachability doctrine at all — just prose about tests.\n"
    check("planted: missing two-surface needle is detected",
          "TWO-surface test" not in stripped)
    check("planted: missing exemption-hatch needle is detected",
          "darkness hatch" not in stripped)
    check("planted: missing onboarding-contract needle is detected",
          "onboarding contract" not in stripped)
    intact = ("A toggle is a TWO-surface test; Exemption is for internals, never a darkness "
              "hatch; ships with an onboarding contract or it ships ON.\n")
    check("planted: intact doctrine passes the same needles",
          all(n in intact for n in ("TWO-surface test", "darkness hatch", "onboarding contract")))


def test_v171_doctrine():
    """v1.7.1 mutation-gate-integrity doctrine must stay present (SKILL §4 + mutation-runner + mutate).

    Origin: a downstream scoped mutation gate false-greened intermittently since before 2026-07 —
    a RED/drifted baseline made mutmut GENERATE mutants but EXECUTE zero, and the gate discarded the
    tool's exit code, so `generated>0 / 0 survivors / exit 0` read as a clean green. The single-axis
    vacuity guard (generated-count only) was necessary but not sufficient. These pins keep the
    two-axis guard — and its two load-bearing aphorisms — from being paraphrased back out."""
    skill = os.path.join(ROOT, "skills", "tdd-playbook", "SKILL.md")
    with open(skill) as fh:
        text = fh.read()
    for label, needle in [
        ("SKILL §4: vacuity guard has TWO axes", "TWO axes"),
        ("SKILL §4: baseline-green precondition", "GREEN baseline"),
        ("SKILL §4: 'generated > 0 ≠ measured' aphorism verbatim", "generated > 0 ≠ measured"),
        ("SKILL §4: 'discarded exit code is a discarded truth' verbatim",
         "discarded exit code is a discarded truth"),
        ("SKILL §4: false-green signature named", "generated>0 / 0 survivors / exit 0"),
        ("SKILL §4: generated-count guard necessary-but-not-sufficient",
         "necessary but NOT sufficient"),
    ]:
        check(label, needle in text, "needle {!r} missing".format(needle))

    with open(os.path.join(AGENTS, "mutation-runner.md")) as fh:
        agent = fh.read()
    check("mutation-runner: two-axis guard (cannot measure on aborted run)",
          "cannot measure" in agent)
    check("mutation-runner: captures the tool exit code (discarded-exit aphorism)",
          "discarded exit code is a discarded truth" in agent)
    check("mutation-runner: false-green signature named",
          "generated>0 / 0 survivors / exit 0" in agent)

    with open(os.path.join(COMMANDS, "mutate.md")) as fh:
        cmd = fh.read()
    check("/mutate: two-axis vacuity guard (cannot measure)", "cannot measure" in cmd)
    check("/mutate: 'generated > 0 ≠ measured' aphorism", "generated > 0 ≠ measured" in cmd)
    check("/mutate: captures exit/stats before reading survivors",
          "CAPTURE the tool's exit" in cmd)

    # the live calibration anchor must exist and target mutation-runner
    scen = os.path.join(os.path.dirname(os.path.dirname(ROOT)),
                        "calibration", "scenarios.json")
    if os.path.isfile(scen):
        with open(scen) as fh:
            ids = [s["id"] for s in json.load(fh)["scenarios"]]
        check("calibration: red-baseline-false-green scenario present",
              "red-baseline-false-green" in ids, ids)


def test_v171_planted_fixtures():
    """The v1.7.1 pins must be able to FAIL — doctrine stripped of an aphorism must be flagged."""
    stripped = "A scoped gate refuses zero generated mutants. Nothing about baselines here.\n"
    check("planted: missing 'generated > 0 ≠ measured' is detected",
          "generated > 0 ≠ measured" not in stripped)
    check("planted: missing 'discarded exit code' aphorism is detected",
          "discarded exit code is a discarded truth" not in stripped)
    intact = ("TWO axes; needs a GREEN baseline; 0 survivors ≠ pass, and generated > 0 ≠ measured; "
              "a discarded exit code is a discarded truth.\n")
    check("planted: intact two-axis doctrine passes the same needles",
          all(n in intact for n in ("TWO axes", "GREEN baseline", "generated > 0 ≠ measured",
                                    "discarded exit code is a discarded truth")))


def test_v18_doctrine():
    """v1.8 architecture-adversary (design-quality band-aid reviewer) must be present + wired.

    Origin: on a real multi-surface agent codebase, a false-positive was 'fixed' by adding a tool
    name to ONE of THREE disagreeing read-only lists instead of unifying them — every other gate
    (wiring, claims, tests) passed it because none evaluates DESIGN quality. This agent makes that
    check mechanical; these pins keep it, its seven patterns, and its dispatch points from
    regressing out."""
    with open(os.path.join(AGENTS, "architecture-adversary.md")) as fh:
        agent = fh.read()
    for label, needle in [
        ("architecture-adversary: refute-framed band-aid stance", "band-aid"),
        ("architecture-adversary: pattern WRONG SEAM", "WRONG SEAM"),
        ("architecture-adversary: pattern DUPLICATION", "DUPLICATION"),
        ("architecture-adversary: pattern SPECIAL-CASE CREEP", "SPECIAL-CASE CREEP"),
        ("architecture-adversary: pattern REUSE MISS", "REUSE MISS"),
        ("architecture-adversary: pattern LAYERING VIOLATION", "LAYERING VIOLATION"),
        ("architecture-adversary: pattern GATE-BY-PROXY", "GATE-BY-PROXY"),
        ("architecture-adversary: pattern CONFIG/KNOB SPRAWL", "CONFIG/KNOB SPRAWL"),
        ("architecture-adversary: earliest-seam refute question", "EARLIEST seam"),
        ("architecture-adversary: forced Verdict contract", "Verdict: ARCHITECTURAL"),
        ("architecture-adversary: origin incident (read-only lists)", "read-only"),
        ("architecture-adversary: worked example present", "Worked example"),
        ("architecture-adversary: must not invent debt", "invent debt"),
    ]:
        check(label, needle in agent, "needle {!r} missing".format(needle))

    skill = os.path.join(ROOT, "skills", "tdd-playbook", "SKILL.md")
    with open(skill) as fh:
        text = fh.read()
    check("SKILL §0/§6: dispatches architecture-adversary", "architecture-adversary" in text)
    check("SKILL: names the band-aid/spaghetti design failure",
          "band-aid" in text or "spaghetti" in text)

    with open(os.path.join(COMMANDS, "tdd-plan.md")) as fh:
        check("/tdd-plan: dispatches architecture-adversary",
              "architecture-adversary" in fh.read())

    scen = os.path.join(os.path.dirname(os.path.dirname(ROOT)),
                        "calibration", "scenarios.json")
    if os.path.isfile(scen):
        with open(scen) as fh:
            ids = [s["id"] for s in json.load(fh)["scenarios"]]
        check("calibration: band-aid plant scenario present", "band-aid-parallel-list" in ids, ids)
        check("calibration: good-fix (no-false-positive) scenario present",
              "good-fix-single-source" in ids, ids)


def test_v18_planted_fixtures():
    """The v1.8 pins must be able to FAIL — a design reviewer stripped of its contract is flagged."""
    stripped = "A design reviewer that only praises clean code and never names a seam.\n"
    check("planted: missing band-aid stance detected", "band-aid" not in stripped)
    check("planted: missing Verdict contract detected", "Verdict: ARCHITECTURAL" not in stripped)
    intact = ("Assume it's a band-aid; hunt WRONG SEAM / DUPLICATION / GATE-BY-PROXY; "
              "end with Verdict: ARCHITECTURAL or BAND-AID.\n")
    check("planted: intact architecture-adversary doctrine passes the same needles",
          all(n in intact for n in ("band-aid", "WRONG SEAM", "GATE-BY-PROXY",
                                    "Verdict: ARCHITECTURAL")))


def main():
    print("Agent/command structural calibration")
    for fn in (test_agents, test_commands, test_planted_fixtures, test_v16_doctrine,
               test_v17_doctrine, test_v17_planted_fixtures,
               test_v171_doctrine, test_v171_planted_fixtures,
               test_v18_doctrine, test_v18_planted_fixtures):
        print("\n[{}]".format(fn.__name__))
        fn()
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
