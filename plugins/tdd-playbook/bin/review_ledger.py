#!/usr/bin/env python3
"""Validate append-only adversarial-review records and their closure evidence."""
from __future__ import annotations

import ast
import glob
import hashlib
import json
import os
import re
import subprocess
import sys


VALID_STATUS = {"open", "incorporated", "rejected", "verified_closed"}
BLOCKERS = {"P0", "P1"}
SHA = re.compile(r"^[0-9a-f]{40}$")
HASH = re.compile(r"^[0-9a-f]{64}$")
INDEX_NAME = "index.json"
ALLOWED_REVIEW_TAIL = ("docs/reviews/", "docs/reference/current-state.md")


def file_hash(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def commit_exists(root: str, sha: str) -> bool:
    if not SHA.fullmatch(sha or ""):
        return False
    result = subprocess.run(["git", "cat-file", "-e", sha + "^{commit}"], cwd=root,
                            capture_output=True, timeout=15)
    return result.returncode == 0


def _strings(value) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(x, str) and x for x in value)


def validate_record(record: dict, source: str, exists, evidence_exists=lambda _target: True) -> list[str]:
    problems = []
    prefix = source + ": "
    if record.get("schema_version") != 1:
        problems.append(prefix + "schema_version must be 1")
    for field in ("id", "plan"):
        if not isinstance(record.get(field), str) or not record[field]:
            problems.append(prefix + field + " must be a non-empty string")
    if record.get("kind") not in {"plan", "implementation"}:
        problems.append(prefix + "kind must be plan or implementation")
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
        if (record.get("kind") == "implementation" and severity in BLOCKERS and
                status == "incorporated"):
            problems.append(label + " implementation blocker must be verified_closed or rejected")
        if status == "verified_closed":
            remediation = finding.get("remediation_commit")
            if not SHA.fullmatch(remediation or "") or not exists(remediation):
                problems.append(label + ".remediation_commit must name an existing full commit SHA")
            closure_review = finding.get("closure_review")
            if closure_review not in (record.get("reviewers") or []):
                problems.append(label + ".closure_review must name a registered reviewer")
            if not _strings(finding.get("closure_evidence")):
                problems.append(label + ".closure_evidence must be a non-empty string list")
            else:
                for target in finding["closure_evidence"]:
                    if not evidence_exists(target):
                        problems.append(label + ".closure_evidence target does not resolve: " + target)
    return problems


def topology_problems(records: list[dict], is_ancestor) -> list[str]:
    problems = []
    for record in records:
        review_range = record.get("review_range") or {}
        base, head = review_range.get("base", ""), review_range.get("head", "")
        if base and head and not is_ancestor(base, head):
            problems.append("review {} base is not an ancestor of head".format(record.get("id")))
    return problems


def coverage_problems(records: list[dict], candidate: str, is_ancestor,
                      tail_paths: list[str]) -> list[str]:
    implementations = [record for record in records if record.get("kind") == "implementation"]
    if not implementations:
        return ["candidate {} has no implementation review".format(candidate)]
    allowed_tail = all(path == "docs/reference/current-state.md" or
                       path.startswith("docs/reviews/") for path in tail_paths)
    for record in implementations:
        head = (record.get("review_range") or {}).get("head", "")
        if not is_ancestor(head, candidate) or not allowed_tail:
            continue
        blockers = [finding for finding in record.get("findings") or []
                    if finding.get("severity") in BLOCKERS and
                    finding.get("status") not in {"verified_closed", "rejected"}]
        if not blockers:
            return []
    return ["candidate {} is not covered by a closed implementation review with a metadata-only tail"
            .format(candidate)]


def validate_index(directory: str, index: dict, baseline_records: list[dict]) -> list[str]:
    problems = []
    if index.get("schema_version") != 1 or not isinstance(index.get("records"), list):
        return ["review index schema is invalid"]
    records = index["records"]
    if records[:len(baseline_records)] != baseline_records:
        problems.append("review index is not append-only relative to release baseline")
    indexed = set()
    for row in records:
        name = row.get("path")
        expected = row.get("sha256")
        if (not isinstance(name, str) or name == INDEX_NAME or os.path.basename(name) != name or
                not name.endswith(".json") or not HASH.fullmatch(expected or "")):
            problems.append("review index contains an invalid entry")
            continue
        indexed.add(name)
        path = os.path.join(directory, name)
        if not os.path.isfile(path):
            problems.append("missing indexed review " + name)
        elif file_hash(path) != expected:
            problems.append("indexed review hash mismatch " + name)
    actual = {os.path.basename(path) for path in glob.glob(os.path.join(directory, "*.json"))
              if os.path.basename(path) != INDEX_NAME}
    if actual - indexed:
        problems.append("unindexed review record(s): " + ", ".join(sorted(actual - indexed)))
    return problems


def validate_directory(directory: str, exists, evidence_exists=lambda _target: True) -> list[str]:
    paths = sorted(path for path in glob.glob(os.path.join(directory, "*.json"))
                   if os.path.basename(path) != INDEX_NAME)
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
        problems.extend(validate_record(record, os.path.basename(path), exists, evidence_exists))
        for finding in record.get("findings") or []:
            fid = finding.get("id")
            if fid in finding_ids:
                problems.append(path + ": duplicate finding id " + str(fid))
            finding_ids.add(fid)
    return problems


def _git(root: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=20)


def _records(directory: str) -> list[dict]:
    records = []
    for path in sorted(glob.glob(os.path.join(directory, "*.json"))):
        if os.path.basename(path) != INDEX_NAME:
            with open(path, encoding="utf-8") as fh:
                records.append(json.load(fh))
    return records


def closure_evidence_exists(root: str, target: str) -> bool:
    if not isinstance(target, str) or target.startswith("/") or ".." in target.split("/"):
        return False
    if "::" not in target:
        return False
    relative, symbol = target.split("::", 1)
    if not re.fullmatch(r"test_[A-Za-z0-9_]+", symbol):
        return False
    try:
        with open(os.path.join(root, "gate-manifest.json"), encoding="utf-8") as fh:
            manifest = json.load(fh)
        discovered = {os.path.relpath(path, root).replace(os.sep, "/") for path in
                      glob.glob(os.path.join(root, manifest["suite_glob"]))
                      if os.path.isfile(path)}
        if relative not in discovered:
            return False
        path = os.path.join(root, relative)
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read(), filename=path)
    except (OSError, ValueError, SyntaxError, KeyError):
        return False
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    main = functions.get("main")
    if symbol not in functions or main is None:
        return False
    if any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and
           node.func.id == symbol for node in ast.walk(main)):
        return True
    for node in ast.walk(main):
        if not isinstance(node, ast.For) or not isinstance(node.target, ast.Name):
            continue
        if not isinstance(node.iter, (ast.Tuple, ast.List)):
            continue
        members = {item.id for item in node.iter.elts if isinstance(item, ast.Name)}
        invokes_loop_item = any(
            isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and
            child.func.id == node.target.id for child in ast.walk(node))
        if symbol in members and invokes_loop_item:
            return True
    return False


def _baseline_index(root: str) -> list[dict]:
    tag = _git(root, "describe", "--tags", "--abbrev=0")
    if tag.returncode != 0:
        return []
    shown = _git(root, "show", "{}:docs/reviews/{}".format(tag.stdout.strip(), INDEX_NAME))
    if shown.returncode != 0:
        return []
    return (json.loads(shown.stdout).get("records") or [])


def validate_repository(root: str) -> list[str]:
    directory = os.path.join(root, "docs", "reviews")
    problems = validate_directory(directory, lambda sha: commit_exists(root, sha),
                                  lambda target: closure_evidence_exists(root, target))
    try:
        with open(os.path.join(directory, INDEX_NAME), encoding="utf-8") as fh:
            index = json.load(fh)
        problems.extend(validate_index(directory, index, _baseline_index(root)))
        records = _records(directory)
    except (OSError, ValueError) as exc:
        return problems + ["review index/records unreadable: " + str(exc)]
    problems.extend(topology_problems(
        records, lambda base, head: _git(root, "merge-base", "--is-ancestor", base, head).returncode == 0))
    candidate_result = _git(root, "rev-parse", "HEAD")
    if candidate_result.returncode != 0:
        return problems + ["candidate HEAD is unavailable"]
    candidate = candidate_result.stdout.strip()
    implementations = [row for row in records if row.get("kind") == "implementation"]
    covered = False
    for record in implementations:
        head = (record.get("review_range") or {}).get("head", "")
        ancestry = lambda base, tip: _git(root, "merge-base", "--is-ancestor", base, tip).returncode == 0
        diff = _git(root, "diff", "--name-only", head + ".." + candidate)
        tail = diff.stdout.splitlines() if diff.returncode == 0 else ["<unavailable>"]
        if not coverage_problems([record], candidate, ancestry, tail):
            covered = True
            break
    if not covered:
        problems.extend(coverage_problems(records, candidate,
                                          lambda base, tip: _git(root, "merge-base", "--is-ancestor", base, tip).returncode == 0,
                                          ["<non-metadata-or-unresolved-tail>"]))
    return problems


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv not in ([], ["validate"]):
        print("usage: review_ledger.py [validate]", file=sys.stderr)
        return 2
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    problems = validate_repository(root)
    if problems:
        for problem in problems:
            print("review ledger: REFUSED — " + problem, file=sys.stderr)
        return 1
    print("review ledger: PASS — all registered findings have valid consumed dispositions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
