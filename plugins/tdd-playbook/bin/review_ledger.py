#!/usr/bin/env python3
"""Validate append-only adversarial-review records and their closure evidence."""
from __future__ import annotations

import glob
import json
import os
import re
import subprocess
import sys


VALID_STATUS = {"open", "incorporated", "rejected", "verified_closed"}
BLOCKERS = {"P0", "P1"}
SHA = re.compile(r"^[0-9a-f]{40}$")


def commit_exists(root: str, sha: str) -> bool:
    if not SHA.fullmatch(sha or ""):
        return False
    result = subprocess.run(["git", "cat-file", "-e", sha + "^{commit}"], cwd=root,
                            capture_output=True, timeout=15)
    return result.returncode == 0


def _strings(value) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(x, str) and x for x in value)


def validate_record(record: dict, source: str, exists) -> list[str]:
    problems = []
    prefix = source + ": "
    if record.get("schema_version") != 1:
        problems.append(prefix + "schema_version must be 1")
    for field in ("id", "plan"):
        if not isinstance(record.get(field), str) or not record[field]:
            problems.append(prefix + field + " must be a non-empty string")
    if not _strings(record.get("reviewers")):
        problems.append(prefix + "reviewers must be a non-empty string list")
    review_range = record.get("review_range") or {}
    for endpoint in ("base", "head"):
        sha = review_range.get(endpoint)
        if not SHA.fullmatch(sha or "") or not exists(sha):
            problems.append(prefix + "review_range.{} must name an existing full commit SHA".format(endpoint))
    findings = record.get("findings")
    if not isinstance(findings, list) or not findings:
        return problems + [prefix + "findings must be a non-empty list"]
    local_ids = set()
    for index, finding in enumerate(findings):
        label = prefix + "finding[{}]".format(index)
        fid = finding.get("id")
        if not isinstance(fid, str) or not fid:
            problems.append(label + ".id must be non-empty")
        elif fid in local_ids:
            problems.append(label + " duplicate finding id " + fid)
        else:
            local_ids.add(fid)
        severity = finding.get("severity")
        if severity not in {"P0", "P1", "P2", "P3"}:
            problems.append(label + ".severity must be P0..P3")
        if not isinstance(finding.get("summary"), str) or not finding["summary"]:
            problems.append(label + ".summary must be non-empty")
        if not _strings(finding.get("evidence")):
            problems.append(label + ".evidence must be a non-empty string list")
        status = finding.get("status")
        if status not in VALID_STATUS:
            problems.append(label + ".status is invalid")
        if status == "open" and severity in BLOCKERS:
            problems.append(label + " unresolved blocker {} cannot pass the full gate".format(fid))
        if status == "incorporated" and not finding.get("disposition"):
            problems.append(label + ".disposition is required for incorporated findings")
        if status == "rejected" and not finding.get("rationale"):
            problems.append(label + ".rationale is required for rejected findings")
        if status == "verified_closed":
            remediation = finding.get("remediation_commit")
            if not SHA.fullmatch(remediation or "") or not exists(remediation):
                problems.append(label + ".remediation_commit must name an existing full commit SHA")
            if not finding.get("closure_review"):
                problems.append(label + ".closure_review is required")
            if not _strings(finding.get("closure_evidence")):
                problems.append(label + ".closure_evidence must be a non-empty string list")
    return problems


def validate_directory(directory: str, exists) -> list[str]:
    paths = sorted(glob.glob(os.path.join(directory, "*.json")))
    if not paths:
        return [directory + ": no review records found"]
    problems = []
    record_ids = set()
    finding_ids = set()
    for path in paths:
        try:
            with open(path, encoding="utf-8") as fh:
                record = json.load(fh)
        except (OSError, ValueError) as exc:
            problems.append(path + ": " + str(exc))
            continue
        rid = record.get("id")
        if rid in record_ids:
            problems.append(path + ": duplicate review record id " + str(rid))
        record_ids.add(rid)
        problems.extend(validate_record(record, os.path.basename(path), exists))
        for finding in record.get("findings") or []:
            fid = finding.get("id")
            if fid in finding_ids:
                problems.append(path + ": duplicate finding id " + str(fid))
            finding_ids.add(fid)
    return problems


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv not in ([], ["validate"]):
        print("usage: review_ledger.py [validate]", file=sys.stderr)
        return 2
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    problems = validate_directory(os.path.join(root, "docs", "reviews"),
                                  lambda sha: commit_exists(root, sha))
    if problems:
        for problem in problems:
            print("review ledger: REFUSED — " + problem, file=sys.stderr)
        return 1
    print("review ledger: PASS — all registered findings have valid consumed dispositions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
