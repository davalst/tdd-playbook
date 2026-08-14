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


# The ONE owner of the finding-status vocabulary (D-C, 2026-08-14): render_reference.py
# imports this — an ordered tuple, not a set, because the renderer's output order must be
# deterministic. A second literal copy is how a rename leaves one reader silently wrong.
VALID_STATUS = ("open", "incorporated", "rejected", "verified_closed")
BLOCKERS = {"P0", "P1"}
SHA = re.compile(r"^[0-9a-f]{40}$")
HASH = re.compile(r"^[0-9a-f]{64}$")
INDEX_NAME = "index.json"
ALLOWED_REVIEW_TAIL = ("docs/reviews/", "docs/reference/current-state.md")

# D-A (review-as-judgment-surface plan, 2026-08-14): every finding says what KIND of miss
# it was. `deterministic` = a mechanical check could have caught it; `judgment` = it needed
# a mind. The ONE machine owner of the vocabulary — the recurrence verb, the agent briefs'
# roster test, and any renderer import THIS tuple (a second copy is how a rename leaves one
# reader silently wrong — readable_surface.py:42 establishes the rule).
FINDING_CLASSES = ("deterministic", "judgment")
# Records dated on/after this REQUIRE class + recurrence_key per finding; the append-only
# history before it is untouched (optional, validated when present).
TAXONOMY_SHIP_DATE = "2026-08-15"
# Keys reach human-facing report lines: short-kebab only, so adversarial content
# (newlines, pipes, case games) is unrepresentable rather than escaped (§2).
RECURRENCE_KEY = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
CATALOG_ROW = re.compile(r"^H\d+$")
RECORD_ID_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


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


def validate_record(record: dict, source: str, exists, evidence_exists=lambda _target: True,
                    plan_exists=lambda _p: True) -> list[str]:
    problems = []
    prefix = source + ": "
    if record.get("schema_version") != 1:
        problems.append(prefix + "schema_version must be 1")
    for field in ("id", "plan"):
        if not isinstance(record.get(field), str) or not record[field]:
            problems.append(prefix + field + " must be a non-empty string")
    record_date = None
    if isinstance(record.get("id"), str) and record["id"]:
        date_match = RECORD_ID_DATE.match(record["id"])
        if date_match:
            record_date = date_match.group(1)
        else:
            problems.append(prefix + "id must begin YYYY-MM-DD (the taxonomy requirement "
                                     "is keyed on the record date)")
    taxonomy_required = record_date is not None and record_date >= TAXONOMY_SHIP_DATE
    # v1.32.0: the plan path must RESOLVE, not merely be a non-empty string. `plan_block.py
    # validate` was the only reader of docs/plans/gated/*.md and it was deleted with the CIVerd
    # engine, leaving the directory write-only. A review record citing a plan that does not
    # exist is the same class of claim this whole ledger exists to refuse.
    plan = record.get("plan")
    if isinstance(plan, str) and plan and not plan_exists(plan):
        problems.append(prefix + "plan does not resolve: " + plan)
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
        cls = finding.get("class")
        key = finding.get("recurrence_key")
        if taxonomy_required and cls is None:
            problems.append(label + ".class is required ({}) for records dated on/after {}"
                            .format("|".join(FINDING_CLASSES), TAXONOMY_SHIP_DATE))
        if cls is not None and cls not in FINDING_CLASSES:
            problems.append(label + ".class must be one of " + "|".join(FINDING_CLASSES))
        if taxonomy_required and key is None:
            problems.append(label + ".recurrence_key is required for records dated on/after "
                            + TAXONOMY_SHIP_DATE)
        if key is not None and (not isinstance(key, str) or not RECURRENCE_KEY.fullmatch(key)):
            problems.append(label + ".recurrence_key must be short-kebab "
                                    "([a-z0-9]+(-[a-z0-9]+)*) — keys reach report lines")
        catalog = finding.get("catalog_row")
        if catalog is not None and (not isinstance(catalog, str)
                                    or not CATALOG_ROW.fullmatch(catalog)):
            problems.append(label + ".catalog_row must be an H<number> row of the "
                                    "HACK_CATALOG Guard ↔ entry map")
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


def validate_directory(directory: str, exists, evidence_exists=lambda _target: True,
                       plan_exists=lambda _p: True) -> list[str]:
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
        problems.extend(validate_record(record, os.path.basename(path), exists,
                                        evidence_exists, plan_exists))
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
    if symbol not in functions:
        return False

    def dispatched(statements, wanted: str) -> bool:
        for statement in statements:
            if (isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Call) and
                    isinstance(statement.value.func, ast.Name) and
                    statement.value.func.id == wanted):
                return True
            if isinstance(statement, ast.Try) and dispatched(statement.body, wanted):
                return True
            if isinstance(statement, ast.If) and isinstance(statement.test, ast.Constant):
                branch = statement.body if statement.test.value else statement.orelse
                if dispatched(branch, wanted):
                    return True
            if (isinstance(statement, ast.For) and isinstance(statement.target, ast.Name) and
                    isinstance(statement.iter, (ast.Tuple, ast.List))):
                members = {item.id for item in statement.iter.elts if isinstance(item, ast.Name)}
                if wanted in members and dispatched(statement.body, statement.target.id):
                    return True
        return False

    if main is not None and dispatched(main.body, symbol):
        return True
    for statement in tree.body:
        if not isinstance(statement, ast.If):
            continue
        test = statement.test
        is_main_guard = (isinstance(test, ast.Compare) and isinstance(test.left, ast.Name) and
                         test.left.id == "__name__" and len(test.ops) == 1 and
                         isinstance(test.ops[0], ast.Eq) and len(test.comparators) == 1 and
                         isinstance(test.comparators[0], ast.Constant) and
                         test.comparators[0].value == "__main__")
        if is_main_guard and dispatched(statement.body, symbol):
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
                                  lambda target: closure_evidence_exists(root, target),
                                  lambda p: os.path.isfile(os.path.join(root, p)))
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


def recurrence_report(records: list[dict]) -> list[str]:
    """The judgment surface speaking back: a recurrence_key appearing in >=2 DISTINCT
    records at class `deterministic` is an UNBUILT GUARD — a machine could have caught
    the same miss twice and none exists. Recurring judgment is listed, never labelled a
    missing guard. Output names the HACK_CATALOG Guard ↔ entry map row it feeds (via the
    optional per-finding catalog_row) rather than growing a parallel list.

    The denominator line prints keyed-of-total over ALL findings (A7): re-keying can game
    which guard a finding maps to, but it cannot shrink the unkeyed share."""
    rows = [(record.get("id") or "", finding)
            for record in records for finding in (record.get("findings") or [])]
    keyed = [(rid, finding) for rid, finding in rows if finding.get("recurrence_key")]
    percent = 100 * len(keyed) // len(rows) if rows else 0
    lines = ["recurrence: records {} · findings {} · keyed {} of {} ({}%)".format(
        len(records), len(rows), len(keyed), len(rows), percent)]
    groups: dict[str, list] = {}
    for rid, finding in keyed:
        groups.setdefault(finding["recurrence_key"], []).append((rid, finding))
    for key in sorted(groups):
        members = groups[key]
        deterministic = {rid for rid, f in members if f.get("class") == "deterministic"}
        everywhere = {rid for rid, _f in members}
        catalog = sorted({f.get("catalog_row") for _rid, f in members if f.get("catalog_row")})
        if len(deterministic) >= 2:
            target = (", ".join(catalog) if catalog else
                      "no matching row — propose one (docs/HACK_CATALOG.md Guard ↔ entry map)")
            lines.append("UNBUILT GUARD: {} ({} records) — HACK_CATALOG: {}".format(
                key, len(deterministic), target))
        elif len(everywhere) >= 2:
            lines.append("recurring judgment: {} ({} records) — not a missing guard".format(
                key, len(everywhere)))
    return lines


def resolve_root() -> str:
    """A12 fix (pre-existing shipped defect): the old four-dirname-hop derivation was
    correct at plugins/tdd-playbook/bin/ and named the HOST REPO'S PARENT from a vendored
    .claude/bin/. House pattern instead: CLAUDE_PROJECT_DIR when the host sets it, else
    walk up to the first directory that actually holds docs/reviews — the artifact this
    tool exists to read (proven from both layouts by the locked suite)."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return os.path.realpath(env)
    probe = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(probe, "docs", "reviews")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            break
        probe = parent
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))


def _log_usage(verb: str, extra: dict) -> None:
    """ONE machine usage event through the single write path (_common.log_yield_event —
    the readable_surface pattern). The usage denominator must move because the tool RAN,
    never because someone remembered to report. Telemetry failure never breaks the verb,
    but it is SAID, not swallowed."""
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "hooks", "scripts"))
    try:
        from _common import log_yield_event
    except Exception as exc:
        sys.stderr.write("review_ledger: usage NOT recorded (_common unreachable: "
                         "{})\n".format(exc))
        return
    log_yield_event("review-ledger", "usage", dict(extra, verb=verb), source="cli")


# The exit-code contract shared with dataflow_sweeps/readable_surface (0 clean · 2 usage ·
# 3 vacuous refusal). Imported from the owner when the sibling is present; the literal
# fallback keeps a partial vendored copy failing CLOSED with the same contract value.
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from dataflow_sweeps import EXIT_VACUOUS  # noqa: E402
except Exception:
    EXIT_VACUOUS = 3


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv not in ([], ["validate"], ["recurrence"]):
        print("usage: review_ledger.py [validate|recurrence]", file=sys.stderr)
        return 2
    root = resolve_root()
    if argv == ["recurrence"]:
        records = _records(os.path.join(root, "docs", "reviews"))
        if not records:
            print("review_ledger: VACUOUS REFUSAL — no records under docs/reviews/ "
                  "(zero scanned is not clean; §4a)", file=sys.stderr)
            return EXIT_VACUOUS
        lines = recurrence_report(records)
        for line in lines:
            print(line)
        _log_usage("recurrence", {
            "records": len(records),
            "unbuilt_guards": sum(1 for line in lines if line.startswith("UNBUILT GUARD")),
        })
        return 0
    problems = validate_repository(root)
    if problems:
        for problem in problems:
            print("review ledger: REFUSED — " + problem, file=sys.stderr)
        return 1
    print("review ledger: PASS — all registered findings have valid consumed dispositions")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
