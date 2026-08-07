#!/usr/bin/env python3
"""Planted contracts for stable, consumed adversarial-review findings."""
from __future__ import annotations

import importlib.util
import json
import os
import tempfile

HERE = os.path.dirname(os.path.realpath(__file__))
PLUGIN = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PLUGIN))
SCRIPT = os.path.join(PLUGIN, "bin", "review_ledger.py")
TOTAL = PASSED = 0


def check(label, condition, detail=""):
    global TOTAL, PASSED
    TOTAL += 1
    if condition:
        PASSED += 1
        print("PASS", label)
    else:
        print("FAIL", label, detail)


def load_module():
    spec = importlib.util.spec_from_file_location("review_ledger", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def finding(status="incorporated", severity="P1"):
    row = {
        "id": "ARCH-1",
        "severity": severity,
        "summary": "one resolver must own full and affected plans",
        "evidence": ["scripts/civerd_gate.sh:19-72"],
        "status": status,
    }
    if status == "incorporated":
        row["disposition"] = "D1 uses one shared resolver"
    if status == "rejected":
        row["rationale"] = "Evidence disproved by composition-root trace"
    if status == "verified_closed":
        row.update(remediation_commit="a" * 40,
                   closure_review="architecture-adversary",
                   closure_evidence=["test_gate_runner.py::test_full_plan_discovers_live_roster"])
    return row


def record(findings=None):
    return {
        "schema_version": 1,
        "id": "2026-08-07-streamlining-plan-review",
        "kind": "plan",
        "plan": "docs/plans/gated/2026-08-07-assurance-pipeline-streamlining.md",
        "review_range": {"base": "b" * 40, "head": "c" * 40},
        "reviewers": ["architecture-adversary", "integration-adversary"],
        "findings": findings or [finding()],
    }


def test_unresolved_blocker_refused():
    rl = load_module()
    problems = rl.validate_record(record([finding("open", "P1")]), "plant.json",
                                  lambda _sha: True)
    check("PLANTED unresolved P1 is refused", any("unresolved blocker" in p for p in problems), problems)
    control = rl.validate_record(record(), "control.json", lambda _sha: True)
    check("clean incorporated control passes", control == [], control)


def test_false_closure_and_scope_refused():
    rl = load_module()
    closed = finding("verified_closed")
    closed.pop("closure_evidence")
    problems = rl.validate_record(record([closed]), "plant.json", lambda _sha: True)
    check("PLANTED evidence-free closure is refused", any("closure_evidence" in p for p in problems), problems)
    bad = record()
    bad["review_range"]["head"] = "not-a-sha"
    problems = rl.validate_record(bad, "plant.json", lambda _sha: False)
    check("PLANTED invalid review SHA is refused", any("review_range.head" in p for p in problems), problems)


def test_terminal_closure_evidence_and_range_are_executable():
    rl = load_module()
    closed = record([finding("verified_closed")])
    closed["kind"] = "implementation"
    closed["findings"][0]["closure_review"] = "not-a-registered-reviewer"
    closed["findings"][0]["closure_evidence"] = ["not-a-test-or-citation"]
    problems = rl.validate_record(closed, "plant.json", lambda _sha: True,
                                  lambda _target: False)
    check("PLANTED unregistered closure reviewer is refused",
          any("registered reviewer" in p for p in problems), problems)
    check("PLANTED nonexistent closure evidence is refused",
          any("closure_evidence target" in p for p in problems), problems)
    check("PLANTED existing documentation line is not executable closure evidence",
          not rl.closure_evidence_exists(REPO, "README.md:1"))
    check("PLANTED existing but non-dispatched helper is not closure evidence",
          not rl.closure_evidence_exists(
              REPO, "plugins/tdd-playbook/tests/test_review_ledger.py::finding"))
    check("real tuple-dispatched blessed test is executable closure evidence",
          rl.closure_evidence_exists(
              REPO,
              "plugins/tdd-playbook/tests/test_gate_runner.py::test_full_plan_discovers_live_roster"))
    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(os.path.join(tmp, "tests"))
        with open(os.path.join(tmp, "gate-manifest.json"), "w") as fh:
            json.dump({"suite_glob": "tests/test_*.py"}, fh)
        with open(os.path.join(tmp, "tests", "test_hidden.py"), "w") as fh:
            fh.write("def test_hidden():\n    pass\n\n"
                     "def main():\n    if False:\n        test_hidden()\n")
        check("PLANTED blessed test behind if False is not executable evidence",
              not rl.closure_evidence_exists(tmp, "tests/test_hidden.py::test_hidden"))
    topology = rl.topology_problems([closed], lambda _base, _head: False)
    check("PLANTED non-ancestral review range is refused",
          any("base is not an ancestor" in p for p in topology), topology)


def test_directory_consumes_records_and_rejects_duplicate_ids():
    rl = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        with open(os.path.join(tmp, "one.json"), "w") as fh:
            json.dump(record(), fh)
        second = record()
        second["id"] = "another-review"
        with open(os.path.join(tmp, "two.json"), "w") as fh:
            json.dump(second, fh)
        problems = rl.validate_directory(tmp, lambda _sha: True)
        check("PLANTED duplicate finding ID across packets is refused",
              any("duplicate finding id" in p for p in problems), problems)


def test_preimplementation_review_cannot_cover_candidate():
    rl = load_module()
    plan_only = record()
    problems = rl.coverage_problems([plan_only], "d" * 40,
                                    lambda _base, _head: True, [])
    check("PLANTED old plan-only review does not cover implementation candidate",
          any("implementation review" in p for p in problems), problems)
    implementation = record([finding("verified_closed")])
    implementation["id"] = "implementation-review"
    implementation["kind"] = "implementation"
    implementation["review_range"] = {"base": "b" * 40, "head": "c" * 40}
    control = rl.coverage_problems([implementation], "d" * 40,
                                   lambda _base, _head: True,
                                   ["docs/reviews/implementation.json",
                                    "docs/reference/current-state.md"])
    check("verified implementation review plus metadata-only tail covers candidate",
          control == [], control)


def test_append_only_index_refuses_deleted_record():
    rl = load_module()
    with tempfile.TemporaryDirectory() as tmp:
        paths = []
        for name in ("one.json", "two.json"):
            path = os.path.join(tmp, name)
            with open(path, "w") as fh:
                json.dump(record(), fh)
            paths.append(path)
        index = {"schema_version": 1, "records": [
            {"path": os.path.basename(path), "sha256": rl.file_hash(path)} for path in paths
        ]}
        check("append-only index clean control passes",
              rl.validate_index(tmp, index, []) == [])
        os.unlink(paths[0])
        problems = rl.validate_index(tmp, index, [])
        check("PLANTED deletion of one valid review record is refused",
              any("missing indexed review" in p for p in problems), problems)


def test_repository_review_records_are_valid():
    rl = load_module()
    problems = rl.validate_repository(REPO)
    check("repository review records are consumed and valid", problems == [], problems)


if __name__ == "__main__":
    test_unresolved_blocker_refused()
    test_false_closure_and_scope_refused()
    test_terminal_closure_evidence_and_range_are_executable()
    test_directory_consumes_records_and_rejects_duplicate_ids()
    test_preimplementation_review_cannot_cover_candidate()
    test_append_only_index_refuses_deleted_record()
    test_repository_review_records_are_valid()
    print("\nResult: {}/{} passed".format(PASSED, TOTAL))
    raise SystemExit(0 if PASSED == TOTAL else 1)
