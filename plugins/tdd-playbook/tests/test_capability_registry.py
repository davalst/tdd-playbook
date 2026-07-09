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


def main():
    print("capability_registry planted-input calibration")
    for fn in (test_validate, test_doctor, test_cli, test_own_registry):
        print("\n[{}]".format(fn.__name__))
        fn()
    print("\n{} passed, {} failed".format(_r["pass"], _r["fail"]))
    sys.exit(1 if _r["fail"] else 0)


if __name__ == "__main__":
    main()
