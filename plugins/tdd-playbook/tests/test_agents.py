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
    # v1.22 (lift/ratchet D0): verdict lines are HOUSE contracts, never task-invented —
    # calibration oracles anchor on these, so a scenario-local format would be a second,
    # unpinned copy of "the agent's contract" (gate-by-proxy, arch-F5).
    "edge-case-adversary": (False, [r"Recommendation:", r"Coverage:\s*ADEQUATE",
                                    r"Coverage:\s*GAPS"]),
    "integration-adversary": (False, [r"Recommendation:", r"Verdict:\s*CONNECTED",
                                      r"Verdict:\s*ISLANDS"]),
    "architecture-adversary": (False, [r"Recommendation:"]),
    "script-adversary": (False, [r"Recommendation:"]),
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

    check("all contracted agents exist", set(AGENT_CONTRACTS) == set(found),
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
    names = []
    for fn in sorted(os.listdir(COMMANDS)):
        if not fn.endswith(".md"):
            continue
        name = fn[:-3]
        names.append(name)
        with open(os.path.join(COMMANDS, fn)) as fh:
            text = fh.read()
        fm = frontmatter(text)
        check("/{}: frontmatter parses with description".format(name),
              fm is not None and fm.get("description"), fm)
        if name in LOOP_CLOSING_COMMANDS:
            check("/{}: closes its loop (Loop closed contract)".format(name),
                  "Loop closed:" in text)
    # Family-parity vacuity guard (v1.26 G5 dogfood, §6c): this loop IS the repo's family
    # sweep over commands/ — before v1.26 an empty or mis-globbed listing passed green
    # having tested nothing. The count comes from an INDEPENDENT roster (the loop-closing
    # contract set), never `>= 0` / a literal this file could drift with.
    check("commands family sweep: enumeration non-vacuous (independent-roster count)",
          bool(names) and LOOP_CLOSING_COMMANDS <= set(names),
          sorted(LOOP_CLOSING_COMMANDS - set(names)))
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


def test_v181_doctrine():
    """v1.8.1 targeted-mutant revert-safety: a revert-based pass must preflight a clean tree.

    Origin (downstream telemetry): a hand-rolled targeted-mutant script git-checkout'd away
    uncommitted work mid-pass. detect-after (verify) is worse than refuse-before (preflight).
    These pins keep the precondition + the mechanical guard (with_snapshot.py preflight) present."""
    binp = os.path.join(ROOT, "bin", "with_snapshot.py")
    with open(binp) as fh:
        wsnap = fh.read()
    check("with_snapshot: preflight subcommand present",
          "cmd_preflight" in wsnap and '"preflight"' in wsnap)
    check("with_snapshot: preflight refuses + names the clobber risk",
          "REFUSING" in wsnap and "clobber" in wsnap.lower())

    skill = os.path.join(ROOT, "skills", "tdd-playbook", "SKILL.md")
    with open(skill) as fh:
        text = fh.read()
    check("SKILL §4: targeted-mutant clean-tree precondition (preflight)", "preflight" in text)
    check("SKILL §4: revert clobbers uncommitted work named", "clobber uncommitted" in text)

    with open(os.path.join(AGENTS, "mutation-runner.md")) as fh:
        check("mutation-runner: revert-based pass gates on preflight", "preflight" in fh.read())
    with open(os.path.join(COMMANDS, "mutate.md")) as fh:
        check("/mutate: revert-based script preflight precondition", "preflight" in fh.read())


def test_v181_planted_fixtures():
    """The v1.8.1 pin must be able to FAIL — guidance stripped of the preflight precondition."""
    stripped = "Run the mutation pass and git checkout to revert when done.\n"
    check("planted: missing preflight precondition detected", "preflight" not in stripped)
    intact = ("Gate a revert-based pass on with_snapshot.py preflight — it refuses to clobber "
              "uncommitted work.\n")
    check("planted: intact preflight precondition passes",
          "preflight" in intact and "clobber" in intact)


def test_v19_doctrine():
    """v1.9 mutation-discipline + test-honesty amendments (from a 52.5%->91.2% downstream session).

    Three grounded lessons the abstract doctrine didn't prevent: (1) 'tests that cannot fail' — a
    fixture picks values where correct and mutated code agree (§1); (2) phase-boundary gating + the
    per-module discovery loop (§4); (3) three further false-green modes — killed+survived<generated
    is UNMEASURED, a too-permissive equivalence filter is a GATE DEFECT (SQLite values are
    case-SENSITIVE), and a roster entry with no gate invocation is a comment (§4). Pins keep the
    concrete rules (which is what made them land) from being paraphrased back to the abstractions."""
    skill = os.path.join(ROOT, "skills", "tdd-playbook", "SKILL.md")
    with open(skill) as fh:
        text = fh.read()
    for label, needle in [
        # Amendment 2 — §1 tests that cannot fail
        ("SKILL §1: 'tests that cannot fail' subsection", "Tests that cannot fail"),
        ("SKILL §1: the fixture-value check question",
         "what value would make this pass with the bug present"),
        ("SKILL §1: 'a mystery in a test is usually the test'",
         "mystery in a test is usually the test"),
        # Amendment 1 — §4 phase gating + per-module loop
        ("SKILL §4: each phase is a feature for gating", "EACH PHASE is a feature for gating"),
        ("SKILL §4: per-module discovery loop", "per-module discovery loop"),
        # Amendment 3a/b/c — §4 three false-green modes
        ("SKILL §4: killed+survived<generated = UNMEASURED", "killed + survived < generated"),
        ("SKILL §4: SQLite values are case-SENSITIVE (filter correctness)",
         "case-SENSITIVE for VALUES"),
        ("SKILL §4: too-permissive filter is a GATE DEFECT", "GATE DEFECT"),
        ("SKILL §4: audit the excluded SHARE over time", "excluded SHARE"),
        ("SKILL §4: roster entry with no gate invocation is a comment",
         "roster entry with no gate invocation is a comment"),
    ]:
        check(label, needle in text, "needle {!r} missing".format(needle))

    with open(os.path.join(AGENTS, "mutation-runner.md")) as fh:
        agent = fh.read()
    check("mutation-runner: accounts for every mutant (unmeasured refusal)",
          "killed + survived < generated" in agent and "UNMEASURED" in agent)
    check("mutation-runner: SQLite values case-SENSITIVE filter correction",
          "case-SENSITIVE for VALUES" in agent)
    check("mutation-runner: resolves named scope first, never substitutes (vacuity fix)",
          "RESOLVE the named scope" in agent and "NEVER silently substitute" in agent)
    # 2026-07-27 corpus live-fails (fix the agent, never the plant):
    check("mutation-runner: verifies test BINDING (shadowed-import live fail)",
          "VERIFY THE BINDING" in agent and "SHADOWS" in agent)
    with open(os.path.join(AGENTS, "architecture-adversary.md")) as fh:
        arch = fh.read()
    check("architecture-adversary: caller count irrelevant to seam (csv-escape live fail)",
          "caller count today is irrelevant" in arch)

    with open(os.path.join(COMMANDS, "mutate.md")) as fh:
        cmd = fh.read()
    check("/mutate: mutant-accounting + per-module discovery", "UNMEASURED" in cmd and "per-module" in cmd)

    scen = os.path.join(os.path.dirname(os.path.dirname(ROOT)), "calibration", "scenarios.json")
    if os.path.isfile(scen):
        with open(scen) as fh:
            ids = [s["id"] for s in json.load(fh)["scenarios"]]
        check("calibration: unmeasured-not-certified scenario present",
              "unmeasured-not-certified" in ids, ids)


def test_v19_planted_fixtures():
    """The v1.9 pins must be able to FAIL — doctrine stripped of an amendment is flagged."""
    stripped = "Run mutation, count survivors, gate on the score.\n"
    check("planted: missing 'tests that cannot fail' detected", "Tests that cannot fail" not in stripped)
    check("planted: missing accounting rule detected", "killed + survived < generated" not in stripped)
    intact = ("Tests that cannot fail pick agreeing values; killed + survived < generated is "
              "UNMEASURED; the per-module discovery loop reads survivor lines.\n")
    check("planted: intact v1.9 doctrine passes the same needles",
          all(n in intact for n in ("Tests that cannot fail", "killed + survived < generated",
                                    "per-module discovery loop".replace(" discovery loop", ""))))


def test_verifier_model_pins():
    """F3: the judgment/adversary verifiers pin a strong model floor so live dispatch never
    silently floats to a cheap session model (a verifier on the doer's tier is the same mind it
    checks). Mechanical test-runners stay inherit — they run suites, not judgment."""
    PINNED = {"claims-verifier", "tripwire-auditor", "architecture-adversary",
              "integration-adversary", "edge-case-adversary", "mutation-runner",
              "script-adversary"}
    INHERIT = {"red-first-verifier", "planted-error-probe", "ux-probe-calibrator"}
    for name in sorted(PINNED):
        with open(os.path.join(AGENTS, name + ".md")) as fh:
            fm = frontmatter(fh.read())
        check("{}: pins a model floor (F3)".format(name),
              fm is not None and fm.get("model") == "opus", fm and fm.get("model"))
    for name in sorted(INHERIT):
        with open(os.path.join(AGENTS, name + ".md")) as fh:
            fm = frontmatter(fh.read())
        check("{}: mechanical runner stays inherit (no pin)".format(name),
              fm is not None and "model" not in fm, fm and fm.get("model"))
    with open(os.path.join(ROOT, "skills", "tdd-playbook", "SKILL.md")) as fh:
        text = fh.read()
    check("SKILL §13: mechanical verifier-model floor documented",
          "pin `model: opus`" in text and "audit finding F3" in text)


def test_verifier_pin_planted():
    """The pin check must be able to FAIL — an unpinned judgment verifier is detectable."""
    unpinned = "---\nname: claims-verifier\ndescription: x\ntools: Read\n---\nbody\n"
    check("planted: unpinned judgment verifier detected", "model" not in frontmatter(unpinned))
    pinned = "---\nname: claims-verifier\ndescription: x\ntools: Read\nmodel: opus\n---\nbody\n"
    check("planted: pinned verifier detected", frontmatter(pinned).get("model") == "opus")


def test_v114_doctrine():
    """v1.14 remote-runtime discipline (audit finding: CIVerd capability-gaps report). The
    Playbook's mechanical oracles were scoped to code-in-this-repo; a deliverable that RUNS
    ELSEWHERE (VPS, daemon, vendored copy) had no oracle, so verification fell back to reading
    output — where over-confidence lives. These pins keep the counter-rules present:
      §6  a fifth RUNNING Tripwire leg for remote deliverables (deployed version == intended).
      §6a version-echo convention + deploy_surface/running_version_probe registry field.
      §1  assert the outcome not the proxy — reaches every CHECK, not just tests.
      §12 "done" about a remote runtime is a claim needing a probe, never a commit sha.
      §13 grade WHO CAUGHT IT (self/accidental/human/peer) — the over-confidence signal."""
    skill = os.path.join(ROOT, "skills", "tdd-playbook", "SKILL.md")
    with open(skill) as fh:
        text = fh.read()
    for label, needle in [
        ("SKILL §6: RUNNING is a fifth leg", "a FIFTH leg"),
        ("SKILL §6: 97-minutes/six-commits origin", "97 minutes / six commits"),
        ("SKILL §6: remote deliverable needs a running_version_probe", "running_version_probe"),
        ("SKILL §6: Tripwire report includes RUNNING M/M", "RUNNING M/M"),
        ("SKILL §6a: version-echo convention", "Version-echo"),
        ("SKILL §6a: deploy drift named", "DEPLOY DRIFT"),
        ("SKILL §6a: running == intended invariant", "running == intended"),
        ("SKILL §6a: R-DEPLOY registry rule", "R-DEPLOY"),
        ("SKILL §1: assert the outcome not the proxy reaches CHECKS", "reaches every CHECK"),
        ("SKILL §1: RuntimeMaxSec Type=oneshot origin", "Type=oneshot"),
        ("SKILL §12: remote 'done' needs a probe not a sha", "never a commit sha"),
        ("SKILL §13: grade who caught it", "Grade WHO CAUGHT IT"),
        ("SKILL §13: over-confidence signal named", "over-confidence"),
    ]:
        check(label, needle in text, "needle {!r} missing".format(needle))

    # the description now names the fifth leg and stays within budget
    fm = frontmatter(text) or {}
    desc = fm.get("description", "")
    check("SKILL description names the RUNNING leg", "+ RUNNING" in desc)
    check("SKILL description within 1024-char budget", len(desc) <= 1024, len(desc))


def test_v114_planted_fixtures():
    """The v1.14 pins must be able to FAIL — doctrine stripped of a remote-runtime counter-rule
    must be detected (§13 calibrate-the-checker)."""
    stripped = "SKILL with four Tripwire legs and no remote-runtime discipline at all.\n"
    check("planted: missing RUNNING-leg needle detected", "a FIFTH leg" not in stripped)
    check("planted: missing version-echo needle detected", "Version-echo" not in stripped)
    check("planted: missing who-caught-it needle detected", "Grade WHO CAUGHT IT" not in stripped)
    intact = ("a FIFTH leg RUNNING; Version-echo asserts running == intended; Grade WHO CAUGHT IT.\n")
    check("planted: intact remote-runtime doctrine passes the same needles",
          all(n in intact for n in ("a FIFTH leg", "Version-echo", "Grade WHO CAUGHT IT")))


def test_v116_doctrine():
    """v1.15/1.16 operational discipline (CIVerd capability-gaps report B + C):
      §0  a deploy-surface plan block (Runs where / Gets there how / Verified how / Divergence) +
          deploy-path-is-deliverable-#1, and the script-adversary dispatched on operator scripts.
      C   the script-adversary agent brief carries the load-bearing probe rule + four failure modes."""
    skill = os.path.join(ROOT, "skills", "tdd-playbook", "SKILL.md")
    with open(skill) as fh:
        text = fh.read()
    for label, needle in [
        ("SKILL §0: deploy-surface plan block", "Deploy surface"),
        ("SKILL §0: names the actual host/process", "Runs where"),
        ("SKILL §0: 'I'll paste files' is a finding", "I'll paste files"),
        ("SKILL §0: deploy path is deliverable #1", "deploy path is deliverable #1"),
        ("SKILL §0: dispatches script-adversary on operator scripts", "script-adversary"),
        ("SKILL §13: script-adversary in the model-floor list",
         "`mutation-runner`, `script-adversary`"),
    ]:
        check(label, needle in text, "needle {!r} missing".format(needle))

    with open(os.path.join(AGENTS, "script-adversary.md")) as fh:
        sa = fh.read()
    for label, needle in [
        ("script-adversary: load-bearing probe rule", "TAKE ITS TARGET AS AN ARGUMENT"),
        ("script-adversary: blocks-on-stdin mode", "BLOCKS ON STDIN"),
        ("script-adversary: destructive-probe mode", "DESTRUCTIVE PROBE"),
        ("script-adversary: passes-for-wrong-reason mode", "PASSES FOR THE WRONG REASON"),
        ("script-adversary: guessed-diagnostics mode", "GUESSED DIAGNOSTICS"),
        ("script-adversary: SCRIPT-SAFE verdict grammar", "Verdict: SCRIPT-SAFE"),
    ]:
        check(label, needle in sa, "needle {!r} missing".format(needle))
    fm = frontmatter(sa)
    check("script-adversary: pins model floor (F3)", fm and fm.get("model") == "opus")


def test_v116_planted_fixtures():
    """The v1.15/1.16 pins must be able to FAIL — stripped doctrine is detected (§13)."""
    stripped = "a plan with an integration surface but no deploy discipline and no script review.\n"
    check("planted: missing deploy-surface needle detected", "Deploy surface" not in stripped)
    check("planted: missing probe-rule needle detected",
          "TAKE ITS TARGET AS AN ARGUMENT" not in stripped)
    intact = "Deploy surface: Runs where; script-adversary; TAKE ITS TARGET AS AN ARGUMENT.\n"
    check("planted: intact doctrine passes the same needles",
          all(n in intact for n in ("Deploy surface", "script-adversary", "TAKE ITS TARGET AS AN ARGUMENT")))


def test_v124_doctrine():
    """v1.24 Dataflow Liveness (§6c — the Cheliped excavation, 2026-08-03). The node-level
    wiring net was perfect on its home turf while all 12 post-safeguard escapes were EDGE
    failures — flows produced with no live consumer, values accepted with no reader, fixes
    verified at the supply end. These pins keep the edge counter-rules present:
      §6c the new section: doctrine line, decidability tiers, migration consumer-parity DoD,
          the T1–T7 escape taxonomy, silent-default boundaries.
      §0  the scale-gated flow table (flow · producer · consumer · liveness test).
      §6  FLOWS join the Tripwire accounting (and /tripwire carries the same line).
      §6a evidence tiers; monitors record SUCCESS; reachability through the REAL dispatch
          order (last-write-wins banned).
      §12 a "now wired" claim is proven at the OUTPUT end or it is not proven.
      §13 escapes reported BY CLASS — a repeating class means its mechanism isn't real."""
    skill = os.path.join(ROOT, "skills", "tdd-playbook", "SKILL.md")
    with open(skill) as fh:
        text = fh.read()
    for label, needle in [
        ("SKILL §6c: section exists", "## 6c. Dataflow Liveness"),
        ("SKILL §6c: doctrine line", "nodes are necessary; edges are the truth"),
        ("SKILL §6c: every flow names a live consumer", "every flow names a live consumer"),
        ("SKILL §6c: two decidability tiers", "two decidability tiers"),
        ("SKILL §6c: silent-default boundaries", "silent-default boundaries"),
        ("SKILL §6c: migration consumer-parity DoD", "consumer-parity"),
        ("SKILL §6c: T1–T7 escape taxonomy named", "T1–T7"),
        ("SKILL §0: flow-table columns", "flow · producer · consumer · liveness test"),
        ("SKILL §6: FLOWS in the Tripwire report", "+ FLOWS M/M"),
        ("SKILL §6a: evidence-tier ladder",
         "config-read < import < runtime-probe < composition-root"),
        ("SKILL §6a: import-existence never renders OK",
         "import-existence alone can never render OK"),
        ("SKILL §6a: monitors record SUCCESS", "record SUCCESS as well as failure"),
        ("SKILL §6a: reachability through the real dispatch order", "real dispatch order"),
        ("SKILL §6a: last-write-wins banned", "last-write-wins is banned"),
        ("SKILL §12: wired claims proven at the output end", "proven at the OUTPUT end"),
        ("SKILL §12: supply-side evidence necessary-not-sufficient",
         "necessary-not-sufficient"),
        ("SKILL §13: escapes reported by class", "escapes BY CLASS"),
    ]:
        check(label, needle in text, "needle {!r} missing".format(needle))

    fm = frontmatter(text) or {}
    desc = fm.get("description", "")
    check("SKILL description names dataflow liveness", "dataflow liveness" in desc)
    check("SKILL description within 1024-char budget", len(desc) <= 1024, len(desc))

    with open(os.path.join(COMMANDS, "tripwire.md")) as fh:
        check("/tripwire: carries the FLOWS accounting line", "+ FLOWS M/M" in fh.read())


def test_v124_planted_fixtures():
    """The v1.24 pins must be able to FAIL — doctrine stripped of the edge discipline must
    be detected (§13 calibrate-the-checker)."""
    stripped = ("SKILL with a perfect node-level wiring net and no flow discipline: "
                "Tripwire reports N/N, migrations verified at the supply end.\n")
    check("planted: missing §6c heading detected", "## 6c. Dataflow Liveness" not in stripped)
    check("planted: missing doctrine-line needle detected",
          "nodes are necessary; edges are the truth" not in stripped)
    check("planted: missing FLOWS-report needle detected", "+ FLOWS M/M" not in stripped)
    check("planted: missing output-end needle detected",
          "proven at the OUTPUT end" not in stripped)
    intact = ("## 6c. Dataflow Liveness — nodes are necessary; edges are the truth; "
              "report Tripwire: N/N (+ FLOWS M/M); a wired claim is proven at the "
              "OUTPUT end.\n")
    check("planted: intact edge doctrine passes the same needles",
          all(n in intact for n in ("## 6c. Dataflow Liveness",
                                    "nodes are necessary; edges are the truth",
                                    "+ FLOWS M/M", "proven at the OUTPUT end")))


def test_v124_gate_surfaces():
    """v1.24 Phase 2 (D7–D9): the commands/agents ADOPT §6c — the reverse sweep the plan
    owed. /integration-audit gains the FIFTH darkness class (with a partition boundary so
    D6's repeat-class metric stays uncorrupted); integration-adversary hunts a SIXTH island
    pattern (dangling flows) with its forced verdict lines UNTOUCHED; /tdd-plan renders the
    scale-gated flow table + the migration old-seam enumeration."""
    with open(os.path.join(COMMANDS, "integration-audit.md")) as fh:
        audit = fh.read()
    fm = frontmatter(audit) or {}
    for label, needle, text in [
        ("/integration-audit: fifth class named", "Dangling dataflow", audit),
        ("/integration-audit: description names five classes", "dangling dataflow",
         fm.get("description", "")),
        ("/integration-audit: T1–T7 hunt list", "T1–T7", audit),
        ("/integration-audit: partition boundary stated", "stays class 4", audit),
        ("/integration-audit: ghost gates in the hunt list", "ghost gates", audit),
        ("/integration-audit: absence-blind monitors in the hunt list", "absence-blind",
         audit),
    ]:
        check(label, needle in text, "needle {!r} missing".format(needle))

    with open(os.path.join(AGENTS, "integration-adversary.md")) as fh:
        adversary = fh.read()
    for label, needle in [
        ("integration-adversary: six island patterns", "Hunt the six island patterns"),
        ("integration-adversary: dangling-flows pattern named", "Dangling flows"),
        ("integration-adversary: template-key refute prompt",
         "a template key with no placeholder"),
        ("integration-adversary: old-seam refute prompt", "old seam"),
    ]:
        check(label, needle in adversary, "needle {!r} missing".format(needle))
    # the forced-line contract is FROZEN (calibration oracles anchor on it) — assert the
    # v1.22 wording survived the v1.24 edit verbatim, not just that some verdict exists
    check("integration-adversary: forced-line contract untouched",
          "never improvise a different format" in adversary
          and "`Verdict: CONNECTED` — every emitted surface names a live consumer" in adversary)

    with open(os.path.join(COMMANDS, "tdd-plan.md")) as fh:
        plan = fh.read()
    for label, needle in [
        ("/tdd-plan: flow-table columns", "flow · producer · consumer · liveness test"),
        ("/tdd-plan: migration old-seam enumeration", "replaced seam"),
    ]:
        check(label, needle in plan, "needle {!r} missing".format(needle))


def test_v124_gate_surfaces_planted():
    """The Phase 2 pins must be able to FAIL (§13 calibrate-the-checker)."""
    stripped = ("an audit command with four darkness classes and an adversary that hunts "
                "five island patterns; plans answer Emits in prose.\n")
    check("planted: missing fifth-class needle detected", "Dangling dataflow" not in stripped)
    check("planted: missing sixth-pattern needle detected",
          "Hunt the six island patterns" not in stripped)
    check("planted: missing flow-table needle detected",
          "flow · producer · consumer · liveness test" not in stripped)
    intact = ("**Dangling dataflow** joins; Hunt the six island patterns; "
              "flow · producer · consumer · liveness test.\n")
    check("planted: intact gate-surface doctrine passes the same needles",
          all(n in intact for n in ("Dangling dataflow", "Hunt the six island patterns",
                                    "flow · producer · consumer · liveness test")))


def test_v125_doctrine():
    """v1.25 Guard Calibration (the Cheliped proposal, 2026-08-04 — a guard that excused
    the very bug shape it was built to catch: red-first in ritual, never failed for the
    right reason). Pins:
      §13 the guard-calibration rule: REPLAY the motivating artifact (git show pre-fix),
          cite the sha in the frozen fixture's docstring; cross-refs from §6 and §6c so
          tripwire/sweep authors actually reach it.
      §1  the generalized trigger question (single home); state-not-action clause;
          silent-failure corollary; the seam-fabrication rule (+ create_autospec check).
      §12 the trigger question governs claims evidence (cross-ref, not a copy).
      Briefs: red-first-verifier / tripwire-auditor / planted-error-probe adopt the rule
      (agents receive briefs, not SKILL — the v1.7 house precedent)."""
    skill = os.path.join(ROOT, "skills", "tdd-playbook", "SKILL.md")
    with open(skill) as fh:
        text = fh.read()
    for label, needle in [
        ("SKILL §13: replay the motivating artifact",
         "REPLAYED against the motivating artifact"),
        ("SKILL §13: sha cited in the frozen fixture", "cite the pre-fix"),
        ("SKILL §13: cheapest plant is the bug in git history",
         "cheapest plant is the bug already in git history"),
        ("SKILL §6: tripwire guards reach the rule",
         "itself subject to §13's guard-calibration"),
        ("SKILL §6c: sweep governance reaches the rule",
         "obeys §13's guard-calibration"),
        ("SKILL §1: generalized trigger question",
         "what would still be true if this were broken?"),
        ("SKILL §1: state-not-action clause",
         "Assert the resulting STATE, not the action"),
        ("SKILL §1: silent-failure corollary",
         "never wrap the line that establishes the guarantee"),
        ("SKILL §1: seam-fabrication rule",
         "never supply an attribute, method, or seam"),
        ("SKILL §1: mechanical seam check named", "create_autospec"),
        ("SKILL §12: trigger question governs evidence",
         "trigger question governs evidence"),
    ]:
        check(label, needle in text, "needle {!r} missing".format(needle))

    for fname, label, needle in [
        ("red-first-verifier.md", "right-reason includes the pre-fix artifact",
         "PRE-FIX artifact"),
        ("tripwire-auditor.md", "EXERCISED asks for the motivating defect shape",
         "motivating defect shape"),
        ("planted-error-probe.md", "prefer real historical defects",
         "historical defect from git history"),
    ]:
        with open(os.path.join(AGENTS, fname)) as fh:
            check("{}: {}".format(fname[:-3], label), needle in fh.read(),
                  "needle {!r} missing".format(needle))


def test_v125_downstream_pins():
    """tripwire-fold (G6a/G6c REDs): the ADOPT bullet and the HACK_CATALOG H9/H10 rows
    are downstream adoption surfaces OUTSIDE rule (d)'s protected set — without needles
    their silent removal is undetectable."""
    repo_root = os.path.dirname(os.path.dirname(ROOT))
    with open(os.path.join(repo_root, "CLAUDE.md")) as fh:
        claude_md = fh.read()
    check("CLAUDE.md ADOPT: guard-calibration bullet present",
          "§13 guard calibration (v1.25)" in claude_md)
    check("CLAUDE.md ADOPT: seam-fabrication line present",
          "never\n     supply an attribute/method/seam" in claude_md
          or "never supply an attribute/method/seam" in claude_md)
    with open(os.path.join(repo_root, "docs", "HACK_CATALOG.md")) as fh:
        catalog = fh.read()
    for label, needle in [
        ("HACK_CATALOG: H9 entry", "### H9 — Seam fabrication"),
        ("HACK_CATALOG: H10 entry",
         "### H10 — The guard that excuses its own motivating bug"),
        ("HACK_CATALOG: H9 map row", "| H9 | overmock_guard fabricated-seam pattern"),
        ("HACK_CATALOG: H10 map row", "| H10 | —"),
    ]:
        check(label, needle in catalog, "needle {!r} missing".format(needle))
    # planted-stripped pair (§13): a catalog without the rows must be detectable
    stripped = "| H8 | doctor GUARDS-DARK |\n"
    check("planted: catalog stripped of H9/H10 detected",
          "### H9 — Seam fabrication" not in stripped
          and "| H10 | —" not in stripped)


def test_v126_seam_contract_pins():
    """v1.26 (seam-contract): the new doctrine's load-bearing phrases across EVERY surface
    that carries them — SKILL body, the score-delivering brief/command (G1/F1: agents
    receive briefs, not SKILL), the plan/audit commands, and the downstream ADOPT surfaces
    outside rule (d)'s protected set. Without needles a later edit can silently drop the
    correction from the one surface a reader actually sees."""
    repo_root = os.path.dirname(os.path.dirname(ROOT))
    skill = open(os.path.join(
        ROOT, "skills", "tdd-playbook", "SKILL.md")).read()
    for label, needle in [
        ("SKILL §1: seam rule present", "Test at the seam you don't own"),
        ("SKILL §1: self-consistency tell present", "SELF-CONSISTENCY test"),
        ("SKILL §1: deleted-other-side corollary present",
         "other side of the seam DELETED"),
        ("SKILL §4: limitation note present", "What mutation score does NOT cover"),
        ("SKILL §0: field granularity present", "at FIELD granularity"),
        ("SKILL §6c: family parity sweep is the Tier-1 bullet, tiered not orphaned",
         "family\n  parity sweep"),
        ("SKILL §6c: vacuity guard mandatory on the enumerator",
         "vacuity guard on the enumerator count MANDATORY"),
    ]:
        check(label, needle in skill, "needle {!r} missing".format(needle))
    for fname, base, label, needle in [
        ("mutation-runner.md", AGENTS,
         "score-delivering brief carries the limitation",
         "What mutation score does not cover"),
        ("mutate.md", COMMANDS, "score-delivering command carries the limitation",
         "What mutation score does not cover"),
        ("tdd-plan.md", COMMANDS, "plan command asks for the family parity sweep",
         "FAMILY PARITY SWEEP"),
        ("tdd-plan.md", COMMANDS, "plan command emits at field granularity",
         "at FIELD granularity"),
        ("integration-audit.md", COMMANDS,
         "audit command enumerates the family parity sweep as a standing mechanism",
         "FAMILY PARITY SWEEP"),
        ("integration-adversary.md", AGENTS,
         "brief judges emitters at field granularity",
         "a consumer is named by the LINE that reads the specific field"),
        ("integration-adversary.md", AGENTS,
         "dangling-flows demand includes received-but-never-read fields",
         "RECEIVES but never reads"),
    ]:
        with open(os.path.join(base, fname)) as fh:
            check("{}: {}".format(fname[:-3], label), needle in fh.read(),
                  "needle {!r} missing".format(needle))
    with open(os.path.join(repo_root, "CLAUDE.md")) as fh:
        check("CLAUDE.md ADOPT: v1.26 seam bullet present",
              "§1 seam rule + §6c family parity sweep (v1.26)" in fh.read())
    with open(os.path.join(repo_root, "README.md")) as fh:
        readme = fh.read()
    check("README: mutation-score claim carries its scope",
          "test at the seam you don't own" in readme)
    check("README verify-list: vendored SKILL check names the seam rule + parity sweep",
          "§1 seam rule, the §6c family parity sweep" in readme)
    with open(os.path.join(repo_root, "docs", "HACK_CATALOG.md")) as fh:
        catalog = fh.read()
    for label, needle in [
        ("HACK_CATALOG: H11 entry", "### H11 — The self-consistency test"),
        ("HACK_CATALOG: H11 partitioned from H9 (existence vs direction)",
         "H9 is EXISTENCE"),
        ("HACK_CATALOG: H11 map row", "| H11 | family parity sweeps"),
        ("HACK_CATALOG: 2026.08 refresh-log row", "| 2026-08 | 2026.08 |"),
    ]:
        check(label, needle in catalog, "needle {!r} missing".format(needle))
    # planted-stripped twin (§13): the pins can fail — a surface missing the needles
    # must be detectable, not vacuously green
    stripped = "You run the Playbook §4 mutation pass. Report a clean result.\n"
    check("planted: brief stripped of the limitation detected",
          "What mutation score does not cover" not in stripped)


def test_v125_planted_fixtures():
    """The v1.25 pins must be able to FAIL (§13 calibrate-the-checker)."""
    stripped = ("SKILL where a guard is trusted after ordinary red-first and a double "
                "may patch in whatever production lacks.\n")
    check("planted: missing replay needle detected",
          "REPLAYED against the motivating artifact" not in stripped)
    check("planted: missing trigger-question needle detected",
          "what would still be true if this were broken?" not in stripped)
    check("planted: missing seam-rule needle detected",
          "never supply an attribute, method, or seam" not in stripped)
    intact = ("a guard is REPLAYED against the motivating artifact; ask what would "
              "still be true if this were broken?; a double may never supply an "
              "attribute, method, or seam production lacks.\n")
    check("planted: intact guard-calibration doctrine passes the same needles",
          all(n in intact for n in ("REPLAYED against the motivating artifact",
                                    "what would still be true if this were broken?",
                                    "never supply an attribute, method, or seam")))


def main():
    print("Agent/command structural calibration")
    for fn in (test_agents, test_commands, test_planted_fixtures, test_v16_doctrine,
               test_v17_doctrine, test_v17_planted_fixtures,
               test_v171_doctrine, test_v171_planted_fixtures,
               test_v18_doctrine, test_v18_planted_fixtures,
               test_v181_doctrine, test_v181_planted_fixtures,
               test_v19_doctrine, test_v19_planted_fixtures,
               test_verifier_model_pins, test_verifier_pin_planted,
               test_v114_doctrine, test_v114_planted_fixtures,
               test_v116_doctrine, test_v116_planted_fixtures,
               test_v124_doctrine, test_v124_planted_fixtures,
               test_v124_gate_surfaces, test_v124_gate_surfaces_planted,
               test_v125_doctrine, test_v125_downstream_pins,
               test_v125_planted_fixtures, test_v126_seam_contract_pins):
        print("\n[{}]".format(fn.__name__))
        fn()
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
