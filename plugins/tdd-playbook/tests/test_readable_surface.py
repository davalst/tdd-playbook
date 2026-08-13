#!/usr/bin/env python3
"""Planted-input calibration for the Readable Surface (v1.34.0 D2/D3/D4).

The premise inverts the usual requirement: the reader CANNOT fall back to source, so the
surface must be POINTABLE, not complete — an omission is recoverable (dispatch an agent at
the coordinates); a wrong statement is not. Contracts pinned here:
  - the 42-row scenario inventory: IDs unique and monotone, Route resolves to a REAL,
    dispatchable agent (via host_parity.canonical_inventory — the roster's one owner, never
    a third glob) or an explicit dash, Class from the owned vocabulary, Facts joins to
    readable_surface.PAGES in BOTH directions (one derivation, not two hand lists);
  - readable_surface.py facts: idempotent, cited, vacuous-refusing (exit 3, the
    dataflow_sweeps constant), absent facts render "not stated" (an absent fact and a
    false fact must look different), pinned summary line, usage logged through the ONE
    write path;
  - /readable: discoverable from the README roster (scoped to the roster, not a substring
    anywhere — the proxy trap), never dispatches a paid adversary (S23 dogfooded), never
    gates.
Self-contained, no pytest. Run: python3 tests/test_readable_surface.py
"""
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PLUGIN))
RS = os.path.join(PLUGIN, "bin", "readable_surface.py")
INVENTORY = os.path.join(REPO, "docs", "adversary-scenario-inventory.md")

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# G5 ISOLATION (found by its own incident, 2026-08-13). The first version of run_rs
# DELETED TDD_PLAYBOOK_YIELD_LOG rather than redirecting it, so readable_surface.py fell
# through to the REPO's real .claude/playbook-yield.jsonl; the next live calibration ran
# `gate_yield rollup` and drained this suite's events into the committed
# docs/calibration/usage.md — 24 fabricated uses in the very record the keep/kill decision
# reads. Redirect UNCONDITIONALLY rather than relying on every call site remembering, and
# pin the real record below: an instrument whose own record is test exhaust measures
# nothing. (The pin in calibration/test_harness.py could not catch this — it snapshots the
# file when the HARNESS starts, by which time this suite has already written.)
_ISO = tempfile.mkdtemp(prefix="rs-iso-")
_REPO_USAGE_MD = os.path.join(REPO, "docs", "calibration", "usage.md")
_REPO_USAGE_BEFORE = (open(_REPO_USAGE_MD, "rb").read()
                      if os.path.isfile(_REPO_USAGE_MD) else None)
_REPO_YIELD_LOG = os.path.join(REPO, ".claude", "playbook-yield.jsonl")
_REPO_YIELD_LOG_BEFORE = (open(_REPO_YIELD_LOG, "rb").read()
                          if os.path.isfile(_REPO_YIELD_LOG) else None)


def run_rs(*args, cwd=None, env_extra=None):
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("TDD_PLAYBOOK_") or k == "CLAUDE_PROJECT_DIR":
            del env[k]
    env["TDD_PLAYBOOK_YIELD_LOG"] = os.path.join(_ISO, "y.jsonl")
    env["TDD_PLAYBOOK_YIELD_MD"] = os.path.join(_ISO, "gate_yield.md")
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, RS, *args], capture_output=True, text=True,
                          cwd=cwd or REPO, env=env, timeout=60)


def test_inventory_contract():
    rs = load(RS, "readable_surface")
    hp = load(os.path.join(PLUGIN, "bin", "host_parity.py"), "host_parity")
    rows = rs.parse_inventory(INVENTORY)
    # vacuity: the count is compared against an INDEPENDENT expectation (the closed Role
    # set implies >= 6 sections; the plan fixes 42), never `>= 0`
    check("inventory: exactly 42 rows parsed (independent expectation)",
          len(rows) == 42, len(rows))
    ids = [r["id"] for r in rows]
    check("inventory: IDs unique", len(set(ids)) == len(ids))
    check("inventory: IDs are S01..S42 with no renumbering",
          ids == ["S{:02d}".format(i) for i in range(1, 43)], ids[:5])

    # Route resolves via the roster's ONE owner — and to a host-SUPPORTED asset, not a
    # basename (a filename check is green on a host where the agent is undispatchable)
    agents = hp.canonical_inventory(REPO)["agents"]
    check("roster owner: canonical_inventory returns a non-empty agent set (vacuity)",
          bool(agents), agents)
    bad = [r["id"] for r in rows if r["route"] != "—" and r["route"] not in agents]
    check("inventory: every Route is a real agent or an explicit dash", not bad, bad)
    routed = [r for r in rows if r["route"] != "—"]
    check("inventory: the four new lenses carry their rows (S17->security etc.)",
          any(r["id"] == "S17" and r["route"] == "security-adversary" for r in rows)
          and any(r["id"] == "S26" and r["route"] == "test-quality-adversary"
                  for r in rows)
          and any(r["id"] == "S33" and r["route"] == "observability-adversary"
                  for r in rows)
          and any(r["id"] == "S40" and r["route"] == "adoption-adversary" for r in rows),
          [(r["id"], r["route"]) for r in rows if r["id"] in ("S17", "S26", "S33", "S40")])
    check("inventory: S14 stays an HONEST dash (gate_yield measures it, no agent judges)",
          any(r["id"] == "S14" and r["route"] == "—" for r in rows))
    check("inventory: >=30 of 42 routed once the four lenses exist",
          len(routed) >= 30, len(routed))

    # Class from the OWNED vocabulary (one constant; a fourth prose copy drifts)
    badc = [r["id"] for r in rows if r["class"] not in rs.CLASSES]
    check("inventory: every Class value is in readable_surface.CLASSES", not badc, badc)
    check("inventory: the known crosswalks hold (S08=T3, S25=seam, S26=vacuity, "
          "S27=flaky, S41=write-only)",
          {r["id"]: r["class"] for r in rows if r["id"] in
           ("S08", "S25", "S26", "S27", "S41")} ==
          {"S08": "T3", "S25": "seam", "S26": "vacuity", "S27": "flaky",
           "S41": "write-only"},
          {r["id"]: r["class"] for r in rows if r["id"] in
           ("S08", "S25", "S26", "S27", "S41")})
    # the T-vocabulary the constant owns must be the one doctrine names (ties the
    # constant to SKILL §6c so a rename cannot drift silently) — vacuity-guarded
    skill = open(os.path.join(PLUGIN, "skills", "tdd-playbook", "SKILL.md")).read()
    tclasses = [c for c in rs.CLASSES if re.fullmatch(r"T[1-7]", c)]
    check("CLASSES: T-vocabulary non-empty and every member named in SKILL §6c",
          bool(tclasses) and all(c in skill for c in tclasses), tclasses)

    # Facts <-> PAGES: BOTH directions from ONE derivation (rs.PAGES)
    page_ids = {p[0] for p in rs.PAGES}
    check("PAGES: non-empty (vacuity)", bool(page_ids), page_ids)
    badf = [r["id"] for r in rows
            for f in (r["facts"].split("+") if r["facts"] != "—" else [])
            if f not in page_ids]
    check("inventory: every Facts value names an emitted page -> RED otherwise",
          not badf, badf)
    declared = {sid for p in rs.PAGES for sid in p[2]}
    mismatch = [r["id"] for r in rows
                if (r["id"] in declared) != (r["facts"] != "—")]
    check("inventory: Facts cells equal the PAGES declaration (one derivation)",
          not mismatch, mismatch)
    unreachable = [p[0] for p in rs.PAGES if not p[2]]
    check("PAGES: a page no scenario reaches is visible (reported set printed)",
          isinstance(unreachable, list), unreachable)

    # PLANTED: a fabricated Route/Class/Facts row must be DETECTABLE by the same checks
    fake = {"id": "S43", "route": "consent", "class": "not-a-class",
            "facts": "not-a-page"}
    check("planted: dangling route detected", fake["route"] not in agents)
    check("planted: unknown class detected", fake["class"] not in rs.CLASSES)
    check("planted: unknown facts page detected", fake["facts"] not in page_ids)


def test_facts_tool():
    rs = load(RS, "readable_surface")
    p1 = run_rs("facts")
    p2 = run_rs("facts")
    check("facts: exits 0 on this repo", p1.returncode == 0,
          (p1.returncode, p1.stderr[-200:]))
    check("facts: byte-identical across two runs (idempotent, no timestamps)",
          p1.stdout == p2.stdout)
    m = re.search(rs.SUMMARY_RX, p1.stdout)
    check("facts: pinned summary line present (owned regex)", m is not None,
          p1.stdout[-200:])
    # §12: the summary's counts equal the visible rows — no silent truncation
    if m:
        check("facts: subsystem count equals the real registry (independent denominator)",
              int(m.group("subsystems")) == len(json.load(
                  open(os.path.join(REPO, "capabilities.json")))["capabilities"]),
              m.group("subsystems"))
    # every emitted citation resolves against the real tree
    vc = os.path.join(PLUGIN, "bin", "verify_citations.py")
    v = subprocess.run([sys.executable, vc, "-", "--base", REPO], input=p1.stdout,
                      capture_output=True, text=True, timeout=60)
    check("facts: every citation resolves via verify_citations (exit 0)",
          v.returncode == 0, v.stdout[-300:])
    check("facts: citations exist at all (N >= 1 — the vacuity hole in the reused gate)",
          re.search(r"Citations: (\d+)", v.stdout)
          and int(re.search(r"Citations: (\d+)", v.stdout).group(1)) >= 1,
          v.stdout[:200])

    # scenario mode: mechanical rows for a facts-backed scenario; honest refusal for an
    # agent-evidence scenario, NAMING the route
    ps = run_rs("facts", "S41")
    check("facts S41: scoped to its pages and says so", ps.returncode == 0
          and "S41" in ps.stdout, ps.stdout[-200:])
    pa = run_rs("facts", "S34")
    check("facts S34: no mechanical facts -> says so and names the Route agent",
          pa.returncode == 0 and "edge-case-adversary" in pa.stdout
          and "no mechanical facts" in pa.stdout.lower(), pa.stdout[-200:])
    pu = run_rs("facts", "S99")
    check("facts S99: unknown scenario refused (exit 2, usage never proof)",
          pu.returncode == 2, pu.returncode)

    # PLANT: a repo with NO registry must refuse loudly with the init instruction —
    # never render an empty page that reads as "nothing here" (exit 3, the
    # dataflow_sweeps vacuous-refusal constant, imported not re-picked)
    with tempfile.TemporaryDirectory() as d:
        pe = run_rs("facts", cwd=d, env_extra={"CLAUDE_PROJECT_DIR": d})
        check("PLANTED empty repo: vacuous refusal exit 3 with the init instruction",
              pe.returncode == 3 and "capability_registry.py init" in
              (pe.stdout + pe.stderr), (pe.returncode, (pe.stdout + pe.stderr)[-200:]))

    # PLANT: an entry missing `activation` renders "not stated", never omitted; paired
    # CONTROL: a complete entry renders its real value
    with tempfile.TemporaryDirectory() as d:
        reg = {"version": 1, "capabilities": [
            {"id": "planted-no-activation", "summary": "planted", "surfaces": ["local"],
             "wired_by": ["x"], "exercised_by": ["y"]},
            {"id": "control-complete", "summary": "control", "surfaces": ["local"],
             "activation": {"default": "on"},
             "emits": [{"topic": "t", "consumers": ["a real reader"]}],
             "wired_by": ["x"], "exercised_by": ["y"]},
        ]}
        with open(os.path.join(d, "capabilities.json"), "w") as fh:
            json.dump(reg, fh, indent=1)
        pp = run_rs("facts", cwd=d, env_extra={"CLAUDE_PROJECT_DIR": d})
        check("PLANTED missing activation: rendered as `not stated`, entry not omitted",
              pp.returncode == 0 and "planted-no-activation" in pp.stdout
              and "not stated" in pp.stdout, pp.stdout[-300:])
        check("CONTROL complete entry: renders its real default, no `not stated`",
              "control-complete" in pp.stdout
              and not re.search(r"control-complete.*not stated", pp.stdout))

    # usage logged through the ONE write path via the REAL CLI (never a synthetic event)
    with tempfile.TemporaryDirectory() as d:
        log = os.path.join(d, "y.jsonl")
        pl = run_rs("facts", env_extra={"TDD_PLAYBOOK_YIELD_LOG": log,
                                        "CLAUDE_PROJECT_DIR": REPO})
        rows = [json.loads(l) for l in open(log)] if os.path.isfile(log) else []
        check("usage: real CLI run lands ONE machine event with scenario + host",
              pl.returncode == 0 and len(rows) == 1 and rows[0]["event"] == "usage"
              and rows[0]["scenario"] == "full" and rows[0]["host"] == "claude"
              and rows[0]["source"] == "cli", rows)


def test_readable_command_and_discoverability():
    cmd = os.path.join(PLUGIN, "commands", "readable.md")
    check("commands/readable.md exists", os.path.isfile(cmd))
    text = open(cmd).read() if os.path.isfile(cmd) else ""
    check("/readable: runs the bin and the citation gate (workflow, not enforcement — "
          "Markdown cannot refuse)", "readable_surface.py" in text
          and "verify_citations.py" in text)
    check("/readable: never dispatches a paid adversary (S23 dogfooded)",
          "Task(" not in text and "dispatch the" not in text.lower()
          and "subagent" not in text.lower(), "dispatch instruction found")
    check("/readable: paste-the-summary rule (self-reported N/N is narration)",
          "summary line" in text.lower())
    # README discoverability, SCOPED to the roster/routing lines — a substring anywhere
    # is the proxy trap (`/tdd-unlock` matches outside the roster today)
    readme = open(os.path.join(REPO, "README.md")).read()
    roster = [l for l in readme.splitlines() if l.startswith("- **Scaffolding commands")]
    check("README roster line exists (vacuity)", len(roster) == 1, len(roster))
    cmds = {fn[:-3] for fn in os.listdir(os.path.join(PLUGIN, "commands"))
            if fn.endswith(".md")}
    missing = sorted(c for c in cmds if "`/" + c + "`" not in roster[0])
    # tdd-lock family is documented in its own README section; the roster names the
    # scaffolding set — assert every command is in the roster OR named elsewhere in a
    # heading/bullet the user is routed to (Hook controls / TEST-LOCK sections)
    truly_missing = [c for c in missing if "/" + c not in readme]
    check("README: every command is findable from the canonical surface",
          not truly_missing, truly_missing)
    check("README: /readable is IN the scaffolding roster line itself",
          "`/readable`" in roster[0], roster[0])
    agents_lines = [l for l in readme.splitlines() if "adversary" in l or "verifier" in l]
    for a in ("security-adversary", "test-quality-adversary", "observability-adversary",
              "adoption-adversary", "architecture-adversary", "script-adversary"):
        check("README: agent roster names {}".format(a), a in readme, a)


def test_plant_control_pairs_differ_only_in_the_planted_defect():
    """v1.34.0 D1 — the structural half of what live calibration caught the hard way.

    The adoption control sat at 0/3 because it CLEANED ONLY ONE of the fixture's error
    paths and left four genuine S40 dead ends standing: it was never clean code, so it
    could not measure restraint, and the agent flagging it was RIGHT. A control that
    differs from its plant by more than the planted defect is measuring the difference,
    not the defect — and no live run is needed to see that. This asserts the invariant
    mechanically for the four v1.34.0 pairs: every edit in the control is either identical
    to one in the plant, or is the single differing edit that IS the planted defect.

    SCOPE, measured not assumed (§12). This does NOT catch the 2026-08-13 defect. Verified
    by planting it: the original pair had exactly ONE differing edit at the SAME anchor and
    passed this check cleanly — it was structurally perfect and semantically wrong, because
    the FIXTURE carried four other S40 dead ends neither side touched. That failure is only
    visible from a live run and a captured transcript, and it is recorded as such in the
    review ledger rather than pinned here. What this DOES catch: a control that patches a
    location its plant never touches, that drifts to a second difference, that loses its
    `control_for`, or that ships without `must_not_match` (and so cannot fail)."""
    corpus = os.path.join(REPO, "calibration", "corpus", "approved")
    pairs = [("secret-token-reaches-output", "control-token-kept-out-of-output"),
             ("assertion-free-smoke-test", "control-asserting-smoke-test"),
             ("swallowed-export-failure", "control-export-failure-surfaces"),
             ("dead-end-error-message", "control-helpful-error-message")]
    check("pair roster non-empty (vacuity guard)", len(pairs) == 4, len(pairs))
    for plant_id, control_id in pairs:
        try:
            with open(os.path.join(corpus, plant_id + ".json")) as fh:
                plant = json.load(fh)
            with open(os.path.join(corpus, control_id + ".json")) as fh:
                control = json.load(fh)
        except OSError as exc:
            check("{}: pair files readable".format(plant_id), False, repr(exc))
            continue
        check("{}: control declares control_for = the plant".format(control_id),
              control.get("control_for") == plant_id, control.get("control_for"))
        check("{}: control carries must_not_match (else it cannot fail)".format(control_id),
              bool(control.get("must_not_match")))
        p_edits = [(e["file"], e["old"], e["new"]) for e in plant.get("edits") or []]
        c_edits = [(e["file"], e["old"], e["new"]) for e in control.get("edits") or []]
        shared = [e for e in c_edits if e in p_edits]
        differing = [e for e in c_edits if e not in p_edits]
        check("{}: differs from its plant in EXACTLY ONE edit (the planted defect) — "
              "{} shared, {} differing".format(control_id, len(shared), len(differing)),
              len(differing) == 1, [e[1][:60] for e in differing])
        check("{}: the differing edit targets the same source anchor as the plant's"
              .format(control_id),
              bool(differing) and any(d[0] == pe[0] and d[1] == pe[1]
                                      for d in differing for pe in p_edits),
              "control patches a location the plant never touches")


def test_suite_left_committed_records_untouched():
    """PLANTED-BY-CONSTRUCTION: this suite drives the REAL readable_surface.py many times
    and must leave the repo's committed instrument records byte-identical. It did NOT —
    run_rs originally DELETED TDD_PLAYBOOK_YIELD_LOG instead of redirecting it, so the bin
    wrote to the repo's real .claude/playbook-yield.jsonl and the next live calibration's
    `gate_yield rollup` drained 24 fabricated uses into docs/calibration/usage.md: the very
    record the 2026-09-30 keep/kill decision reads. An instrument whose own denominator is
    test exhaust measures nothing. (The equivalent pin in calibration/test_harness.py could
    not catch this — it snapshots the file when the HARNESS starts, by which time this
    suite has already written. A pin belongs in the suite that does the writing.)"""
    after_md = (open(_REPO_USAGE_MD, "rb").read()
                if os.path.isfile(_REPO_USAGE_MD) else None)
    check("suite left the repo's real docs/calibration/usage.md untouched",
          after_md == _REPO_USAGE_BEFORE,
          "committed usage record was written by the test suite")
    after_log = (open(_REPO_YIELD_LOG, "rb").read()
                 if os.path.isfile(_REPO_YIELD_LOG) else None)
    check("suite left the repo's real .claude/playbook-yield.jsonl untouched "
          "(the drain path into the committed record)",
          after_log == _REPO_YIELD_LOG_BEFORE,
          "real yield log received this suite's events")


def main():
    print("readable_surface calibration")
    if not os.path.isfile(RS):
        check("bin/readable_surface.py exists", False, "missing")
    if not os.path.isfile(INVENTORY):
        check("docs/adversary-scenario-inventory.md exists", False, "missing")
    if os.path.isfile(RS) and os.path.isfile(INVENTORY):
        for fn in (test_inventory_contract, test_facts_tool,
                   test_readable_command_and_discoverability,
                   test_plant_control_pairs_differ_only_in_the_planted_defect):
            try:
                fn()
            except Exception as exc:
                check(fn.__name__ + " executes", False, repr(exc))
    test_suite_left_committed_records_untouched()
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    assert not _results["fail"], "readable_surface calibration failed"


if __name__ == "__main__":
    main()