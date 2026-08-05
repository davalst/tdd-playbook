#!/usr/bin/env python3
"""Planted-input calibration for bin/capability_registry.py (Playbook §6a).

Per the release discipline: every mechanical check ships with planted violations that must
FAIL it. Planted here — each maps to a darkness class from the full-platform feature-wiring
audit that motivated the tool:
  - default=off with no on-switch (dark by construction)          -> R-DARK
  - an emitter with no named consumer (write-only growth loop)    -> R-WRITE-ONLY
  - expired integration debt (the never-actioned review doc)      -> R-DEBT
  - duplicate id / missing exercised_by (schema drift)            -> R-DUP / R-SCHEMA
A clean registry must pass, and `doctor` must ENUMERATE darkness rather than hide it.
Self-contained, no pytest. Run: python3 tests/test_capability_registry.py
"""
import copy
import datetime
import importlib.util
import json
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOL = os.path.join(ROOT, "bin", "capability_registry.py")

_r = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _r["pass"] += 1
        print("  ok   - " + name)
    else:
        _r["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def load_tool():
    spec = importlib.util.spec_from_file_location("capability_registry", TOOL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


TODAY = datetime.date(2026, 7, 9)

CLEAN = {
    "version": 1,
    "capabilities": [
        {
            "id": "orchestrator",
            "summary": "Reflexes engine: reacts to system events.",
            "surfaces": ["internal"],
            "activation": {"default": "on"},
            "wired_by": ["src/daemon.py::build_daemon"],
            "exercised_by": ["tests/test_assembly.py::test_orchestrator_receives_events"],
            "emits": [{"topic": "events.intent", "consumers": ["delivery-gateway"]}],
            "consumes": ["events.task_done"],
            "liveness": {"max_quiet_days": 30, "probe": "planted-event canary"},
            "integration_debt": [],
        },
        {
            "id": "delivery-gateway",
            "summary": "Single outbound delivery gate.",
            "surfaces": ["telegram"],
            "activation": {"default": "off", "switch": "/delivery on (wizard step 3)"},
            "wired_by": ["src/daemon.py::build_daemon"],
            "exercised_by": ["tests/test_assembly.py::test_delivery_gateway_reachable"],
            "emits": [{"topic": "events.task_done", "consumers": ["orchestrator"]}],
            "integration_debt": [
                {"what": "route heartbeat escalations through the delivery gateway",
                 "owner": "david", "expires": "2026-09-01"}
            ],
        },
    ],
}


def rules_of(violations):
    return {v.split()[0] for v in violations}


def test_validate():
    mod = load_tool()

    check("clean registry passes", mod.validate(CLEAN, today=TODAY) == [],
          mod.validate(CLEAN, today=TODAY))

    # PLANTED: dark by construction — off with no switch
    bad = copy.deepcopy(CLEAN)
    bad["capabilities"][1]["activation"] = {"default": "off"}
    v = mod.validate(bad, today=TODAY)
    check("planted dark-no-switch trips R-DARK", "R-DARK" in rules_of(v), v)

    # PLANTED: write-only emitter — nobody reads the growth loop
    bad = copy.deepcopy(CLEAN)
    bad["capabilities"][0]["emits"] = [{"topic": "events.lesson", "consumers": []}]
    v = mod.validate(bad, today=TODAY)
    check("planted write-only emitter trips R-WRITE-ONLY", "R-WRITE-ONLY" in rules_of(v), v)

    # PLANTED: expired integration debt — the never-actioned review doc
    bad = copy.deepcopy(CLEAN)
    bad["capabilities"][1]["integration_debt"][0]["expires"] = "2026-01-01"
    v = mod.validate(bad, today=TODAY)
    check("planted expired debt trips R-DEBT", "R-DEBT" in rules_of(v), v)

    # PLANTED: debt without an owner rots anonymously
    bad = copy.deepcopy(CLEAN)
    del bad["capabilities"][1]["integration_debt"][0]["owner"]
    v = mod.validate(bad, today=TODAY)
    check("planted ownerless debt trips R-DEBT", "R-DEBT" in rules_of(v), v)

    # PLANTED: duplicate id
    bad = copy.deepcopy(CLEAN)
    bad["capabilities"][1]["id"] = "orchestrator"
    v = mod.validate(bad, today=TODAY)
    check("planted duplicate id trips R-DUP", "R-DUP" in rules_of(v), v)

    # PLANTED: no exercised_by — built but provably untested at assembly level
    bad = copy.deepcopy(CLEAN)
    bad["capabilities"][0]["exercised_by"] = []
    v = mod.validate(bad, today=TODAY)
    check("planted missing exercised_by trips R-SCHEMA", "R-SCHEMA" in rules_of(v), v)

    # a well-formed remote deploy_surface is clean
    good_remote = copy.deepcopy(CLEAN)
    good_remote["capabilities"][0]["deploy_surface"] = {
        "runs_on": "vps-1", "gets_there_by": "update.sh",
        "running_version_probe": "heartbeat echoes sha; assert == HEAD",
        "divergence": "no heartbeat -> RED; owner: david"}
    check("well-formed deploy_surface passes", mod.validate(good_remote, today=TODAY) == [],
          mod.validate(good_remote, today=TODAY))

    # PLANTED: a remote surface with NO running_version_probe — drift is undetectable
    bad = copy.deepcopy(good_remote)
    del bad["capabilities"][0]["deploy_surface"]["running_version_probe"]
    v = mod.validate(bad, today=TODAY)
    check("planted remote surface w/o version probe trips R-DEPLOY", "R-DEPLOY" in rules_of(v), v)

    # PLANTED: a remote surface missing runs_where/gets-there-how also trips R-DEPLOY
    bad = copy.deepcopy(good_remote)
    del bad["capabilities"][0]["deploy_surface"]["gets_there_by"]
    v = mod.validate(bad, today=TODAY)
    check("planted deploy_surface missing gets_there_by trips R-DEPLOY", "R-DEPLOY" in rules_of(v), v)

    # a capability with NO deploy_surface (local-only) is unaffected
    check("local-only capability needs no deploy_surface",
          "R-DEPLOY" not in rules_of(mod.validate(CLEAN, today=TODAY)))

    # future-dated debt with owner is a legitimate loan, not a violation
    check("future-dated owned debt is NOT a violation",
          mod.validate(CLEAN, today=TODAY) == [])


def test_doctor():
    mod = load_tool()
    report = mod.doctor(CLEAN, today=TODAY)
    check("doctor enumerates the dark feature with its switch",
          "delivery-gateway" in report and "/delivery on" in report, report)
    check("doctor lists open debt with owner",
          "route heartbeat escalations" in report and "david" in report, report)

    # PLANTED: a switchless dark feature must be loudly flagged, not omitted
    bad = copy.deepcopy(CLEAN)
    bad["capabilities"][1]["activation"] = {"default": "off"}
    check("doctor flags missing on-switch loudly",
          "NO ON-SWITCH" in mod.doctor(bad, today=TODAY))

    # consumed-but-never-emitted seam check
    bad = copy.deepcopy(CLEAN)
    bad["capabilities"][0]["consumes"] = ["events.ghost_topic"]
    check("doctor surfaces consumed-but-never-emitted topics",
          "events.ghost_topic" in mod.doctor(bad, today=TODAY))

    # doctor enumerates a remote deploy surface and loudly flags a missing version probe
    remote = copy.deepcopy(CLEAN)
    remote["capabilities"][0]["deploy_surface"] = {
        "runs_on": "vps-1", "gets_there_by": "update.sh", "running_version_probe": "",
        "divergence": "no heartbeat -> RED"}
    rep = mod.doctor(remote, today=TODAY)
    check("doctor lists remote deploy surfaces", "remote deploy surfaces" in rep, rep)
    check("doctor flags missing version probe loudly", "NO VERSION PROBE" in rep, rep)


def test_cli():
    mod = load_tool()
    with tempfile.TemporaryDirectory() as base:
        # no registry -> exit 2 (missing registry is itself a reportable state)
        check("validate with no registry exits 2", mod.main(["validate", "--base", base]) == 2)

        check("init seeds a starter registry", mod.main(["init", "--base", base]) == 0)
        path = os.path.join(base, "capabilities.json")
        check("init refuses to overwrite", mod.main(["init", "--base", base]) == 2)

        with open(path, "w") as fh:
            json.dump(CLEAN, fh)
        check("validate exits 0 on clean registry",
              mod.main(["validate", "--base", base]) == 0)
        check("doctor exits 0 on clean registry",
              mod.main(["doctor", "--base", base]) == 0)

        bad = copy.deepcopy(CLEAN)
        bad["capabilities"][1]["activation"] = {"default": "off"}
        with open(path, "w") as fh:
            json.dump(bad, fh)
        check("validate exits 1 on planted violation",
              mod.main(["validate", "--base", base]) == 1)
        check("doctor --strict exits 1 on planted violation",
              mod.main(["doctor", "--base", base, "--strict"]) == 1)
        check("doctor without --strict still reports (exit 0)",
              mod.main(["doctor", "--base", base]) == 0)

        # registry in .claude/ fallback location is found
        os.remove(path)
        os.makedirs(os.path.join(base, ".claude"))
        with open(os.path.join(base, ".claude", "capabilities.json"), "w") as fh:
            json.dump(CLEAN, fh)
        check("registry found at .claude/ fallback",
              mod.main(["validate", "--base", base]) == 0)


def test_own_registry():
    """Dogfood: THIS repo's own capabilities.json must validate — mechanically, on every
    suite run, with the REAL current date. A checklist entry saying "run validate before
    release" is the honor-system seam §10 warns about; this check is the wire. Teeth are
    intentional: when an integration_debt entry here expires (e.g. the owed first live
    calibration run), this suite FAILS until the debt is paid, re-dated with a reason, or
    the capability is parked loudly — same rule as an expired flaky quarantine (§7)."""
    mod = load_tool()
    repo_root = os.path.dirname(os.path.dirname(ROOT))
    path = mod.find_registry(repo_root)
    check("this repo carries its own capabilities.json", path is not None, repo_root)
    if path is None:
        return
    violations = mod.validate(mod.load_registry(path))  # real today() — expiry has teeth
    check("own registry validates (expired debt fails this suite BY DESIGN)",
          violations == [], violations)

    # PLANTED (2026-07-28): --as-of makes the expiry trigger PROVABLE, deterministically —
    # the H7 doctrine tells people to prove a deferral's trigger with
    # `validate --as-of <expiry+1>`; without the flag that command exits 2 as an ARGPARSE
    # error, i.e. nonzero for the wrong reason (the exact wrong-reason-green the
    # script-adversary hunts — caught live when this repo's own trigger 'proof' turned out
    # to be a usage error). The flag must exist, and its nonzero must mean EXPIRED.
    rc = mod.main(["validate", "--base", repo_root, "--as-of", "2099-01-01"])
    check("own registry: --as-of far-future -> exit 1 (every dated debt expired)", rc == 1)
    rc = mod.main(["validate", "--base", repo_root, "--as-of", "2026-08-01"])
    check("own registry: --as-of before all expiries -> exit 0", rc == 0)
    rc = mod.main(["validate", "--base", repo_root, "--as-of", "not-a-date"])
    check("--as-of garbage -> exit 2 (usage), distinct from expiry's exit 1", rc == 2)

    # PLANTED (lift/ratchet D7, G2): the quarterly trigger proof must name ITS debt in the
    # violation STRING — a bare exit-code assert at 2026-11-02 is vacuous (earlier debts
    # already expire by then; nonzero-for-the-wrong-reason is the class this repo was
    # burned by, twice). Boundary: expires 2026-11-01 -> violating strictly AFTER.
    import datetime as _dt
    reg = mod.load_registry(mod.find_registry(repo_root))
    v_after = mod.validate(reg, _dt.date(2026, 11, 2))
    v_on = mod.validate(reg, _dt.date(2026, 11, 1))
    check("quarterly debt: violation string present at 2026-11-02",
          any("quarterly" in v for v in v_after),
          [v for v in v_after][:3])
    check("quarterly debt: NOT expired on its own expiry day (strictly-after rule)",
          not any("quarterly" in v for v in v_on), [v for v in v_on][:3])

    # STRING-PINNED boundary proofs for the v1.23 briefs debts (David's ships-on-or-
    # triggered rule, 2026-07-30: anything shipped OFF must carry an ARMED trigger).
    # Violation STRINGS, never bare exit codes — by each of these dates OTHER debts have
    # already expired, so an exit code alone passes for the wrong reason (same class).
    def _fires(day, needle):
        return [v for v in mod.validate(reg, _dt.date.fromisoformat(day))
                if "EXPIRED" in v and needle in v]

    check("enrollment-sweep debt (2026-08-31): silent on its expiry day, fires 09-01 "
          "naming deliberation-capture",
          not _fires("2026-08-31", "ENROLLMENT SWEEP")
          and any("deliberation-capture" in v for v in _fires("2026-09-01", "ENROLLMENT SWEEP")),
          _fires("2026-09-01", "ENROLLMENT SWEEP")[:2])
    check("engine-arming debt (2026-09-15): silent on its expiry day, fires 09-16 "
          "naming plan-authoring",
          not _fires("2026-09-15", "ENGINE-SIDE ARMING")
          and any("plan-authoring" in v for v in _fires("2026-09-16", "ENGINE-SIDE ARMING")),
          _fires("2026-09-16", "ENGINE-SIDE ARMING")[:2])
    check("consumer debt (2026-10-31): silent on its expiry day, fires 11-01 — a recorder "
          "nobody reads does not run forever",
          not _fires("2026-10-31", "CONSUMER: the store")
          and any("deliberation-capture" in v for v in _fires("2026-11-01", "CONSUMER: the store")),
          _fires("2026-11-01", "CONSUMER: the store")[:2])

    # v1.24 (§6c) dated triggers — same string-pinned boundary discipline (H7: every
    # deferral gets a mechanical trigger PROVEN in the landing commit, never prose):
    check("create-capability debt (2026-09-15): silent on its expiry day, fires 09-16 "
          "naming calibration-loop — writer-with-no-reader plants need new fixture files",
          not _fires("2026-09-15", "APPLY_EDITS CREATE")
          and any("calibration-loop" in v for v in _fires("2026-09-16", "APPLY_EDITS CREATE")),
          _fires("2026-09-16", "APPLY_EDITS CREATE")[:2])
    check("Cheliped Tier-2 pilot debt (2026-09-15): silent on its expiry day, fires 09-16 "
          "naming dataflow-sweeps — the pilot must not silently become the permanent state",
          not _fires("2026-09-15", "CHELIPED TIER-2 PILOT")
          and any("dataflow-sweeps" in v for v in _fires("2026-09-16", "CHELIPED TIER-2 PILOT")),
          _fires("2026-09-16", "CHELIPED TIER-2 PILOT")[:2])
    check("CIVerd proposal-forwarding debt (2026-09-15): silent on its expiry day, fires "
          "09-16 naming dataflow-sweeps — a review doc nobody actioned is the documented rot",
          not _fires("2026-09-15", "CIVERD UPGRADE PROPOSAL")
          and any("dataflow-sweeps" in v for v in _fires("2026-09-16", "CIVERD UPGRADE PROPOSAL")),
          _fires("2026-09-16", "CIVERD UPGRADE PROPOSAL")[:2])
    # tripwire-auditor (v1.24 fold): two deferrals were parked in PROSE ONLY — the exact
    # H7 class the plan's §B rule bans. Now dated + string-pinned like every other loan:
    check("v1.24 corpus-batch debt (2026-08-17): silent on its expiry day, fires 08-18 "
          "naming calibration-loop — proposed plants nobody approves are a dark queue",
          not _fires("2026-08-17", "V1.24 CORPUS BATCH")
          and any("calibration-loop" in v for v in _fires("2026-08-18", "V1.24 CORPUS BATCH")),
          _fires("2026-08-18", "V1.24 CORPUS BATCH")[:2])
    check("v1.24 gate-surface calibration debt (2026-08-17): silent on its expiry day, "
          "fires 08-18 — D7–D9 text is untrusted until its history.md rows land",
          not _fires("2026-08-17", "V1.24 GATE-SURFACE CALIBRATION")
          and any("calibration-loop" in v
                  for v in _fires("2026-08-18", "V1.24 GATE-SURFACE CALIBRATION")),
          _fires("2026-08-18", "V1.24 GATE-SURFACE CALIBRATION")[:2])
    check("v1.25 gate-surface calibration debt (2026-08-17): silent on its expiry day, "
          "fires 08-18 — G1/G1b/G2 doctrine+brief text untrusted until history.md rows",
          not _fires("2026-08-17", "V1.25 GATE-SURFACE CALIBRATION")
          and any("calibration-loop" in v
                  for v in _fires("2026-08-18", "V1.25 GATE-SURFACE CALIBRATION")),
          _fires("2026-08-18", "V1.25 GATE-SURFACE CALIBRATION")[:2])
    check("v1.25 corpus-queue debt (2026-08-17): silent on its expiry day, fires 08-18 "
          "— the H10 proposals must not go dark in proposed/",
          not _fires("2026-08-17", "V1.25 CORPUS QUEUE")
          and any("calibration-loop" in v for v in _fires("2026-08-18", "V1.25 CORPUS QUEUE")),
          _fires("2026-08-18", "V1.25 CORPUS QUEUE")[:2])
    check("testlock override-semantics debt (2026-09-15): silent on its expiry day, "
          "fires 09-16 naming gate-yield — phase-boundary unlocks are not adjudicated "
          "false positives, and 4 cycles of spurious retirement flags prove it",
          not _fires("2026-09-15", "TESTLOCK OVERRIDE SEMANTICS")
          and any("gate-yield" in v
                  for v in _fires("2026-09-16", "TESTLOCK OVERRIDE SEMANTICS")),
          _fires("2026-09-16", "TESTLOCK OVERRIDE SEMANTICS")[:2])
    check("layer_10 sha report-back debt (2026-09-15): silent on its expiry day, fires "
          "09-16 naming dataflow-sweeps — the sha-citation rule's own slot must not sit "
          "empty forever in the release that invented the rule",
          not _fires("2026-09-15", "LAYER_10 PRE-FIX SHA")
          and any("dataflow-sweeps" in v
                  for v in _fires("2026-09-16", "LAYER_10 PRE-FIX SHA")),
          _fires("2026-09-16", "LAYER_10 PRE-FIX SHA")[:2])
    # (The TDD-PLAYBOOK INTEGRITY_GLOBS arming pin lived here 2026-08-03 only: the debt
    # was PAID the same day it was registered — David armed the engine-side floor/globs
    # on srv1621832; the corrected record is the `notes` field on civerd-release-gate.
    # A paid loan's trigger is retired WITH this dated comment, never silently.)
    check("integrity_globs arming: paid — the entry is GONE, its record survives in notes",
          not _fires("2026-09-16", "TDD-PLAYBOOK INTEGRITY_GLOBS")
          and any("PAID 2026-08-03" in (c.get("notes") or "")
                  for c in reg.get("capabilities", [])
                  if c.get("id") == "civerd-release-gate"))

    # v1.26 (seam-contract) dated triggers — same string-pinned boundary discipline:
    check("v1.26 gate-surface calibration debt (2026-08-17): silent on its expiry day, "
          "fires 08-18 — seam-contract doctrine+brief text untrusted until history.md rows",
          not _fires("2026-08-17", "V1.26 GATE-SURFACE CALIBRATION")
          and any("calibration-loop" in v
                  for v in _fires("2026-08-18", "V1.26 GATE-SURFACE CALIBRATION")),
          _fires("2026-08-18", "V1.26 GATE-SURFACE CALIBRATION")[:2])
    check("v1.26 corpus-queue debt (2026-08-17): silent on its expiry day, fires 08-18 "
          "— the H11 seam pair must not go dark in proposed/",
          not _fires("2026-08-17", "V1.26 CORPUS QUEUE")
          and any("calibration-loop" in v for v in _fires("2026-08-18", "V1.26 CORPUS QUEUE")),
          _fires("2026-08-18", "V1.26 CORPUS QUEUE")[:2])
    check("field-pairing sweep debt (2026-09-15): silent on its expiry day, fires 09-16 "
          "naming dataflow-sweeps — the deferred mechanical form of field granularity "
          "must not become a silent prose-only rule",
          not _fires("2026-09-15", "TIER-2 FIELD-PAIRING SWEEP")
          and any("dataflow-sweeps" in v
                  for v in _fires("2026-09-16", "TIER-2 FIELD-PAIRING SWEEP")),
          _fires("2026-09-16", "TIER-2 FIELD-PAIRING SWEEP")[:2])
    check("seam-contract forwarding debt (2026-09-15): silent on its expiry day, fires "
          "09-16 naming civerd-release-gate — a recommendation doc nobody actioned is "
          "the documented rot case this repo already paid for once",
          not _fires("2026-09-15", "SEAM-CONTRACT RECOMMENDATION FORWARDED")
          and any("civerd-release-gate" in v
                  for v in _fires("2026-09-16", "SEAM-CONTRACT RECOMMENDATION FORWARDED")),
          _fires("2026-09-16", "SEAM-CONTRACT RECOMMENDATION FORWARDED")[:2])
    check("seam-contract report-back debt (2026-09-15): silent on its expiry day, fires "
          "09-16 naming civerd-release-gate — the answers slot must not sit empty forever",
          not _fires("2026-09-15", "SEAM-CONTRACT REPORT-BACK")
          and any("civerd-release-gate" in v
                  for v in _fires("2026-09-16", "SEAM-CONTRACT REPORT-BACK")),
          _fires("2026-09-16", "SEAM-CONTRACT REPORT-BACK")[:2])


def test_probe_survivor_gaps():
    """CIVerd's engine-owned planted-error probe, FIRST live firing (2026-07-28), planted
    flip_compare and constant_return mutants into capability_registry.py and this suite
    stayed GREEN — the probe named this suite partly theater, with evidence. A local sweep
    reproduced the survivors: doctor's debt-state classification, doctor's _consume_topic,
    validate's schema branch, and find_registry's explicit path were all unasserted. These
    tests kill those classes; each was verified to FAIL under its mutant before shipping
    (mutation red-first — the probe, not the author, chose these targets)."""
    import datetime as dt
    mod = load_tool()
    today = dt.date(2026, 7, 28)

    def cap(cid, **kw):
        base = {"id": cid, "summary": "s", "surfaces": ["local"],
                "activation": {"default": "on"},
                "wired_by": ["w.py"], "exercised_by": ["t.py"]}
        base.update(kw)
        return base

    # doctor debt states: EXPIRED strictly-before today, "due soon" within DEBT_WARN_DAYS,
    # "open" beyond — a flipped comparison misclassifies at least one of these
    reg = {"version": 1, "capabilities": [
        cap("exp-cap", integration_debt=[
            {"what": "w", "owner": "o", "expires": "2026-07-20"}]),
        cap("soon-cap", integration_debt=[
            {"what": "w", "owner": "o", "expires": "2026-08-05"}]),
        cap("open-cap", integration_debt=[
            {"what": "w", "owner": "o", "expires": "2027-06-01"}]),
    ]}
    out = mod.doctor(reg, today=today)

    def state_of(cid):
        for ln in out.splitlines():
            if cid in ln and "[" in ln:
                return ln.split("[", 1)[1].split("]", 1)[0]
        return None
    check("doctor: past-expiry debt classified EXPIRED", state_of("exp-cap") == "EXPIRED",
          state_of("exp-cap"))
    check("doctor: within-warn-window debt classified 'due soon'",
          state_of("soon-cap") == "due soon", state_of("soon-cap"))
    check("doctor: far-future debt classified 'open'", state_of("open-cap") == "open",
          state_of("open-cap"))
    # boundary: expires exactly today is NOT expired (strictly-before), but IS due soon
    reg_edge = {"version": 1, "capabilities": [cap("today-cap", integration_debt=[
        {"what": "w", "owner": "o", "expires": "2026-07-28"}])]}
    out = mod.doctor(reg_edge, today=today)
    check("doctor: expires-today is 'due soon', not EXPIRED",
          "due soon" in out and "EXPIRED" not in out, out)

    # doctor consumed-orphans: both consume shapes (bare string + emits-style dict) must be
    # resolved — a gutted _consume_topic drops the dict form and undercounts
    reg = {"version": 1, "capabilities": [
        cap("consumer-cap", consumes=["ghost.topic", {"topic": "dict.topic"}]),
    ]}
    out = mod.doctor(reg, today=today)
    check("doctor: consumed-but-never-emitted counts BOTH consume shapes",
          "consumed but never emitted (check the seam): 2" in out
          and "ghost.topic" in out and "dict.topic" in out, out)

    # validate schema branch: a registry with no capability list must return the R-SCHEMA
    # violation LIST (a constant/None return silently passes garbage registries)
    for bad in ({"capabilities": []}, {"capabilities": "not-a-list"}, {}):
        out = mod.validate(bad, today)
        check("validate: schema violation is a real R-SCHEMA list for %r" % (bad,),
              isinstance(out, list) and len(out) == 1 and "R-SCHEMA" in out[0]
              and "non-empty list" in out[0], out)

    # find_registry explicit path: honored when present, None when missing (an explicit
    # --registry that is missing must NOT silently fall back to the base registry)
    with tempfile.TemporaryDirectory() as d:
        explicit = os.path.join(d, "somewhere", "caps.json")
        os.makedirs(os.path.dirname(explicit))
        with open(explicit, "w") as fh:
            json.dump({"version": 1, "capabilities": []}, fh)
        with open(os.path.join(d, "capabilities.json"), "w") as fh:
            json.dump({"version": 1, "capabilities": []}, fh)
        check("find_registry: explicit existing path returned",
              mod.find_registry(d, explicit) == explicit)
        check("find_registry: explicit MISSING path -> None (no silent fallback to base)",
              mod.find_registry(d, os.path.join(d, "nope.json")) is None)
        check("find_registry: no explicit -> base fallback still works",
              mod.find_registry(d) == os.path.join(d, "capabilities.json"))


def test_user_facing():
    """v1.24 (D12b): the optional capability-level `user_facing` audience attribute — the
    ground truth §6c's companion rule keys on (`surfaces` is deployment hosts, NOT an
    audience fact). Schema rule: if present it must be a BOOL; anything else is R-SCHEMA
    (a string "yes" silently truthy would let the companion rule fire on garbage)."""
    mod = load_tool()

    # CONTROL: bool values (either way) are clean
    good = copy.deepcopy(CLEAN)
    good["capabilities"][0]["user_facing"] = True
    good["capabilities"][1]["user_facing"] = False
    check("user_facing: bool annotation is clean", mod.validate(good, today=TODAY) == [],
          mod.validate(good, today=TODAY))

    # PLANTED: non-bool user_facing must trip R-SCHEMA, never validate as truthy
    bad = copy.deepcopy(CLEAN)
    bad["capabilities"][0]["user_facing"] = "yes"
    v = mod.validate(bad, today=TODAY)
    check("planted non-bool user_facing trips R-SCHEMA",
          any(s.startswith("R-SCHEMA") and "user_facing" in s for s in v), v)

    # the repo's OWN registry annotates every entry explicitly (the audience fact is
    # stated, never implied — same rule as activation)
    repo_root = os.path.dirname(os.path.dirname(ROOT))
    reg = mod.load_registry(os.path.join(repo_root, "capabilities.json"))
    unannotated = [c.get("id") for c in reg.get("capabilities", [])
                   if not isinstance(c.get("user_facing"), bool)]
    check("own registry: every capability carries an explicit bool user_facing",
          unannotated == [], unannotated)


def main():
    print("capability_registry planted-input calibration")
    for fn in (test_validate, test_doctor, test_cli, test_own_registry,
               test_probe_survivor_gaps, test_user_facing):
        print("\n[{}]".format(fn.__name__))
        fn()
    print("\n{} passed, {} failed".format(_r["pass"], _r["fail"]))
    sys.exit(1 if _r["fail"] else 0)


if __name__ == "__main__":
    main()
