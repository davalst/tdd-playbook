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


def test_repository_review_records_are_valid():
    rl = load_module()
    problems = rl.validate_directory(os.path.join(REPO, "docs", "reviews"),
                                     lambda sha: rl.commit_exists(REPO, sha))
    check("repository review records are consumed and valid", problems == [], problems)


if __name__ == "__main__":
    test_unresolved_blocker_refused()
    test_false_closure_and_scope_refused()
    test_directory_consumes_records_and_rejects_duplicate_ids()
    test_repository_review_records_are_valid()
    print("\nResult: {}/{} passed".format(PASSED, TOTAL))
    raise SystemExit(0 if PASSED == TOTAL else 1)
