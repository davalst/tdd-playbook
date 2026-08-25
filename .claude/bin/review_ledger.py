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
# D3 (adversary-accountability plan, 2026-08-17): `reviewers` used to be checked only for
# SHAPE — a non-empty list of non-empty strings — so a typo, a renamed agent, or an
# invented name validated clean, and every participation count read off the field was only
# as good as its spelling. Entries are now canonical agent IDs (resolved through
# host_parity.agents_roster) or one of these NON-AGENT reviewer kinds. The ONE owner of
# the vocabulary: the authoring briefs' roster sweep imports THIS tuple, on the
# FINDING_CLASSES rule above — a second copy is how a rename leaves one reader wrong.
#
# A rename is the escape hatch, not a reason for an alias table: agent filenames are
# canonical IDs and are already frozen by test_agents.py:111 and :588. If one ever must
# change, the FORMER id joins this tuple as a historical alias, and immutable history
# stays valid.
NON_AGENT_REVIEWERS = ("self-review", "release-gate", "operator-field-report",
                       "live-dogfooding", "cheliped-field-report",
                       "calibration-live-replay", "d2d-live-probe", "codex-field-report")
# Records dated on/after this bind `reviewers`; earlier append-only history is untouched.
# Verified at authoring time: all 39 existing records use exactly 8 agent names + the 8
# tokens above, so the rollout binds today's records at zero cost.
REVIEWER_VOCAB_SHIP_DATE = "2026-08-17"
# D1 (recurrence-epoch plan, 2026-08-20): the recurrence list was RETIRED WHOLESALE here.
# It could not see a guard that had been BUILT — four of its items were guards misfiring and
# tag_guard was fixed in v1.42.0 by this repo, so it nagged forever; one of its keys held
# five unrelated findings; and `catalog_row`, the field linking a defect to its check, was
# present on 6 of 205 findings with two of the three load-bearing ones naming the wrong row.
# Reclassifying that history needs judgment nobody can supply honestly, so it is not
# attempted: findings dated before this are HISTORICAL — readable, reported as a count,
# never counted toward a verdict.
#
# The records are NOT deleted. They are the evidence that produced this diagnosis; they stop
# DRIVING the verdict, which is a different thing, and the historical line in
# recurrence_report exists to keep that difference visible (silence would read as "no
# history exists" — the H15 shape).
RECURRENCE_EPOCH = "2026-08-20"
# ...and the answer moves to AUTHORING time, where the author still knows it. The old design
# asked a READER to infer, months later, whether a defect had been guarded — which is how
# the blanks accumulated. `none` is a first-class answer; the BLANK was the problem.
# The ONE machine owner of the vocabulary, on the FINDING_CLASSES rule above.
GUARD_KINDS = ("hook", "test", "none")
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


def hook_default_modes() -> dict | None:
    """The SHIPPED default mode of every hook, or None where the hook tree is not vendored
    (Codex carries adapters + bin only) — the caller then degrades to shape-only, stated
    here rather than silently.

    Deliberately the SHIPPED default and never `_common.resolve_mode()`. resolve_mode reads
    the per-hook env var, the global env var and break-glass state; this table is rendered
    into a COMMITTED file whose test asserts committed == rendered, so keying on it would
    make the same tree render differently on two machines and fail the gate for whoever
    happened to have a var set. A generated artifact is a pure function of the tree.

    AST-parsed rather than imported: reading a literal cannot execute anything, and it is
    the same idiom test_hooks uses to read each guard's NAME constant."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "hooks", "scripts", "_common.py")
    if not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            tree = ast.parse(fh.read())
    except (OSError, SyntaxError):
        return None
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_DEFAULT_MODES":
                try:
                    value = ast.literal_eval(node.value)
                except ValueError:
                    return None
                return value if isinstance(value, dict) else None
    return None


def guard_problems(guard, label: str, evidence_exists) -> list[str]:
    """Validate one finding's `guard` answer — shape AND resolution.

    A check that only confirmed the field was non-empty is precisely the weakness this
    replaces: the capability registry's own `wired_by`/`exercised_by` are unresolved strings
    to this day, so a capability naming a test that does not exist validates clean."""
    if not isinstance(guard, dict):
        return [label + ".guard must be an object {kind, ref, why}"]
    problems = []
    kind = guard.get("kind")
    if kind not in GUARD_KINDS:
        return [label + ".guard.kind must be one of " + "|".join(GUARD_KINDS)]
    ref = guard.get("ref")
    if kind == "none":
        # An unexplained "nothing guards this" is the BLANK the epoch just retired, wearing
        # a label. The reason is the entire difference between the two.
        if not (isinstance(guard.get("why"), str) and guard["why"].strip()):
            problems.append(label + ".guard.why is required when kind is none — an "
                                    "unexplained 'nothing guards this' is the blank the "
                                    "recurrence epoch retired")
        if ref:
            problems.append(label + ".guard.ref must be absent when kind is none")
        return problems
    if not (isinstance(ref, str) and ref.strip()):
        return [label + ".guard.ref is required when kind is " + kind]
    if kind == "hook":
        modes = hook_default_modes()
        if modes is not None and ref not in modes:
            problems.append(label + ".guard.ref '" + ref + "' names no registered hook — "
                            "expected one of: " + ", ".join(sorted(modes)))
    elif kind == "test" and not evidence_exists(ref):
        problems.append(label + ".guard.ref '" + ref + "' does not resolve to a defined "
                        "test — a guard nobody can run is not a guard")
    return problems


def guard_state(answers: list[dict]) -> tuple[str, str]:
    """(state, detail) for one recurrence key, computed from the answers its findings gave.

    A key is GUARDED when ANY finding names a live mechanism — something guards it now, even
    if an earlier sighting predated that guard. GUARD DARK only when the only mechanisms
    named are hooks that SHIP off; UNBUILT when nothing was named at all."""
    modes = hook_default_modes()
    dark = []
    for answer in answers:
        kind, ref = answer.get("kind"), answer.get("ref")
        if kind == "test":
            return "GUARDED", ref
        if kind == "hook":
            if modes is None:
                return "GUARDED", ref + " (shipped mode unverifiable in this layout)"
            mode = modes.get(ref)
            if mode and mode != "off":
                return "GUARDED", "{} ships {}".format(ref, mode)
            dark.append(ref)
    if dark:
        return "GUARD DARK", ("{} ships off — doctrine, not a live mechanism"
                              .format(", ".join(sorted(set(dark)))))
    return "UNBUILT GUARD", "no finding named a mechanism"


def validate_record(record: dict, source: str, exists, evidence_exists=lambda _target: True,
                    plan_exists=lambda _p: True,
                    catalog_exists=lambda _row: True,
                    reviewer_known=lambda _name: True) -> list[str]:
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
    guard_required = record_date is not None and record_date >= RECURRENCE_EPOCH
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
    elif record_date is not None and record_date >= REVIEWER_VOCAB_SHIP_DATE:
        # The refusal ENUMERATES the accepted vocabulary: an error that names the problem
        # and not the next step is the adoption failure this ledger's own briefs hunt.
        unknown = [name for name in record["reviewers"] if not reviewer_known(name)]
        if unknown:
            problems.append(
                prefix + "reviewers not recognised: {} — each must be a canonical agent id "
                "(a basename in agents/) or one of: {}".format(
                    ", ".join(sorted(unknown)), ", ".join(NON_AGENT_REVIEWERS)))
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
        # D1 (2026-08-20): what would have caught this? Asked of the AUTHOR, while they
        # still know — never of a reader months later, which is how the blanks accumulated.
        guard = finding.get("guard")
        if guard_required and guard is None:
            problems.append(label + ".guard is required for records dated on/after "
                            + RECURRENCE_EPOCH + " — answer what would have caught this: "
                            '{"kind": "hook|test|none", "ref": ..., "why": ...}')
        if guard is not None:
            problems.extend(guard_problems(guard, label, evidence_exists))
        catalog = finding.get("catalog_row")
        if catalog is not None and (not isinstance(catalog, str)
                                    or not CATALOG_ROW.fullmatch(catalog)):
            problems.append(label + ".catalog_row must be an H<number> row of the "
                                    "HACK_CATALOG Guard ↔ entry map")
        elif catalog is not None and not catalog_exists(catalog):
            # arch-adversary F9: shape alone would let H99 print as though it names a
            # real row. Membership when the catalog is present; the repository caller
            # degrades to shape-only (stated in its docstring) where the file is not
            # vendored.
            problems.append(label + ".catalog_row " + catalog +
                            " is not a row of the HACK_CATALOG Guard ↔ entry map")
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
                       plan_exists=lambda _p: True,
                       catalog_exists=lambda _row: True,
                       reviewer_known=lambda _name: True) -> list[str]:
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
                                        evidence_exists, plan_exists, catalog_exists,
                                        reviewer_known))
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


# Evidence artifacts removed by a deliberate LATER policy change. Closed history that cited
# them stays valid: the evidence was true when written, and retiring a policy retires its test.
# Narrow by construction — each entry names what was removed, when, and why, and anything not
# named here must still resolve. This is not a tolerance for missing evidence; it is the
# producer-and-consumer-retire-together rule applied to an append-only record that cannot be
# edited to follow the code.
RETIRED_EVIDENCE = {
    "plugins/tdd-playbook/tests/test_review_ledger.py::"
    "test_preimplementation_review_cannot_cover_candidate":
        "removed 2026-08-18 with the per-commit review-coverage rule it tested. The two "
        "findings citing it (STREAM-POST-ARCH-3, REL-META-2) were defects IN that rule, so "
        "the evidence and the policy retire together.",
}


def closure_evidence_exists(root: str, target: str) -> bool:
    if target in RETIRED_EVIDENCE:
        return True
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


def catalog_rows(root: str) -> set[str] | None:
    """The H-rows of docs/HACK_CATALOG.md's Guard ↔ entry map, or None when the catalog
    is not vendored here (downstream copies don't carry docs/) — the caller then degrades
    to shape-only validation, stated here rather than silently."""
    path = os.path.join(root, "docs", "HACK_CATALOG.md")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return set(re.findall(r"^\|\s*(H\d+)\s*\|", fh.read(), re.MULTILINE))


def validate_repository(root: str) -> list[str]:
    directory = os.path.join(root, "docs", "reviews")
    rows = catalog_rows(root)
    # D3: agents_roster returns None where the family is not vendored (codex carries
    # adapters + bin only), and the binding degrades to shape-only there — the same
    # contract catalog_rows already declares one function above. Stated, not incidental.
    roster = agents_roster(root)
    problems = validate_directory(directory, lambda sha: commit_exists(root, sha),
                                  lambda target: closure_evidence_exists(root, target),
                                  lambda p: os.path.isfile(os.path.join(root, p)),
                                  (lambda row: row in rows) if rows is not None
                                  else lambda _row: True,
                                  (lambda name: name in roster or name in NON_AGENT_REVIEWERS)
                                  if roster is not None else lambda _name: True)
    try:
        with open(os.path.join(directory, INDEX_NAME), encoding="utf-8") as fh:
            index = json.load(fh)
        problems.extend(validate_index(directory, index, _baseline_index(root)))
        records = _records(directory)
    except (OSError, ValueError) as exc:
        return problems + ["review index/records unreadable: " + str(exc)]
    problems.extend(topology_problems(
        records, lambda base, head: _git(root, "merge-base", "--is-ancestor", base, head).returncode == 0))
    # Records are OPT-IN evidence as of 2026-08-18. The per-commit coverage rule that used to
    # live here (`coverage_problems`) demanded every non-metadata commit be covered by a closed
    # implementation review with a metadata-only tail. It was the one obligation that fired on
    # EVERY commit, and its output was unconsumed — 205 findings, 57% keyed, 12 UNBUILT-GUARD
    # keys, zero guards built from any of them. What remains below it is unchanged: a record
    # that IS written still gets the full schema teeth. Optional never means unchecked.
    return problems


def record_authoring_briefs(root: str) -> set[str]:
    """The agents whose brief carries the review-record output contract — DERIVED by
    reading the briefs, never a hand list (run_calibration.py:55-59 states the rule: "the
    roster stays DERIVED, never a second hand-maintained list"). `recurrence_key` is the
    marker because only a brief instructed to AUTHOR a record needs to name it; the same
    membership is asserted independently at test_agents.py:1038."""
    directory = agents_dir(root)
    if directory is None:
        return set()
    found = set()
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".md"):
            continue
        with open(os.path.join(directory, name), encoding="utf-8") as fh:
            if "recurrence_key" in fh.read():
                found.add(name[:-3])
    return found


def participation_report(records: list[dict], roster: set[str] | None,
                         producers: set[str]) -> list[str]:
    """RECORDED REVIEW PARTICIPATION — for each agent in the roster, how many indexed
    records NAME it.

    What this is not, stated in the output itself because the distinction is the whole
    point: `reviewers` is hand-authored, so a count is evidence a name was RECORDED and
    never evidence an agent ran. An earlier draft called this usage/dispatch and proposed
    the finding key `adversary-built-registered-never-dispatched`; both were dropped —
    the machine cannot establish "never dispatched," and a GATE on a hand-typed field
    would reward name-stuffing rather than review.

    Every roster member is printed and NOTHING is flagged. Earlier drafts partitioned the
    roster judgment-vs-mechanical so a zero could be called a defect; that partition was
    an Nth copy of a classification the repo already derives, and an unpinned exemption
    set is the documented darkness hatch (test_harness.py:1116). Printing the whole
    roster deletes the problem instead of relocating it: with nothing flagged, nothing
    can be false-flagged, and a reader who sees a zero beside `authors records` has the
    two facts needed to judge it. Same category as capability_registry doctor's
    dark-feature inventory."""
    if roster is None:
        return ["participation: unmeasured — no agent roster resolves from this tree "
                "(a vendored copy carrying bin/ without agents/), so no id can be checked"]
    if not roster:
        return ["participation: unmeasured — the agent roster enumerated VACUOUSLY (zero "
                "ids); an empty enumeration is refused, never reported as clean"]
    if not records:
        return ["participation: unmeasured — no indexed review records"]
    counts: dict[str, int] = {}
    for record in records:
        for name in set(record.get("reviewers") or []):
            if name in roster:
                counts[name] = counts.get(name, 0) + 1
    lines = ["participation: what the {} indexed records RECORDED — `reviewers` is written "
             "by hand, so this shows which names were written down, never who ran".format(
                 len(records))]
    for name in sorted(roster):
        mark = " · authors records" if name in producers else ""
        count = counts.get(name, 0)
        lines.append("  {}{} — {}".format(
            name, mark, count if count else "not named in any indexed review"))
    return lines


# ---------------------------------------------------------------- small-change lane
# Measured 2026-08-18: narrowing one regex cost five sequential ledger refusals, two
# ledger-entry attempts, three doc regenerations and six full gate runs. One refusal caught
# something real; four were schema friction. The recording cost is FIXED while its benefit
# scales with change size, so the apparatus that earns its keep on a feature is tax on a fix.
#
# What the lane changes: the WEIGHT OF THE RECORD, and nothing else. Same gate, same suites,
# same red-first, same no-weakening rules, same guards. That asymmetry is the defense — a lie
# that got you in would save a paragraph and leave every verification standing, so there is
# nothing worth cheating for. There is deliberately NO override: an escape hatch is the first
# thing a motivated agent reaches for, so it does not exist.
#
# And the lane REQUIRES TDD rather than merely not removing it: a source change with no test
# beside it is refused outright. Reduced paperwork must never become a road for untested code.

# Surfaces a human must read in full, whatever the diff size — doctrine, the things that
# judge (agents/commands/guards), the things that ship (installer), the things that measure
# (calibration, oracles, the registry), and the standing instructions themselves.
_FULL_LANE_PREFIXES = (
    "plugins/tdd-playbook/skills/", "plugins/tdd-playbook/agents/",
    "plugins/tdd-playbook/commands/", "plugins/tdd-playbook/hooks/",
    "plugins/tdd-playbook/adapters/", "calibration/", "docs/plans/gated/",
    ".github/workflows/", "scripts/",
)
_FULL_LANE_EXACT = ("capabilities.json", "CLAUDE.md", "AGENTS.md", "README.md",
                    "gate-manifest.json", "dataflow-sweeps.json")
_SMALL_MAX_LINES = 150
_SMALL_MAX_FILES = 8
_CODE_SUFFIXES = (".py", ".sh", ".js", ".ts", ".go", ".rs", ".rb", ".java")


def _is_test_path(path: str) -> bool:
    base = path.rsplit("/", 1)[-1]
    return ("/tests/" in path or "/test/" in path
            or base.startswith("test_") or base.endswith("_test.py"))


def small_change_eligible(changed_paths, insertions, deletions):
    """(eligible, reason) computed from the DIFF — never from a caller's opinion.

    The signature takes only facts about the change. It cannot be told that something is
    small; it works it out. A mixed diff is judged by its most dangerous path, never averaged.
    """
    paths = [p.replace("\\", "/").lstrip("./") for p in (changed_paths or []) if p]
    if not paths:
        return False, "no changed paths — nothing to classify"
    for path in paths:
        if path in _FULL_LANE_EXACT or path.startswith(_FULL_LANE_PREFIXES):
            return False, ("full lane: `{}` is a surface a reader must see in full "
                           "(doctrine, a judge, a shipped artifact, or a measurement)"
                           .format(path))
    if len(paths) > _SMALL_MAX_FILES:
        return False, ("full lane: {} files changed (> {}) — breadth is its own risk"
                       .format(len(paths), _SMALL_MAX_FILES))
    total = int(insertions or 0) + int(deletions or 0)
    if total > _SMALL_MAX_LINES:
        return False, ("full lane: {} lines changed (> {})".format(total, _SMALL_MAX_LINES))
    code = [p for p in paths if p.endswith(_CODE_SUFFIXES) and not _is_test_path(p)]
    if code and not any(_is_test_path(p) for p in paths):
        return False, ("full lane: {} changed with NO test alongside it — the lane reduces "
                       "paperwork, never the test. Write the test, or take the full lane"
                       .format(code[0]))
    return True, ""


# Which judgment the DIFF calls for — derived, never remembered. Blanket adversary dispatch
# is the bureaucracy this lane exists to remove; zero dispatch is how a security fix ships
# unread. Deriving it puts the cost on the changes that earn it: most small fixes summon
# nothing, an auth or egress fix summons exactly one. Keys are path/name signals, matched
# against the agent briefs' own stated triggers (see agents/*.md `description`).
_ADVERSARY_SIGNALS = (
    ("security-adversary",
     ("auth", "session", "token", "secret", "credential", "egress", "network",
      "permission", "authz", "login", "oauth", "jwt", "crypto", "sanitiz")),
    ("observability-adversary",
     ("retry", "except", "logger", "logging", "monitor", "health", "daemon",
      "scheduler", "worker", "background", "alert")),
    ("script-adversary",
     ("verify_", "healthcheck", "health_check", "deploy", "probe", "install", "bootstrap")),
)


def suggested_adversaries(changed_paths):
    """The lenses this diff earns, from its paths. Empty is the common and correct answer."""
    paths = [p.replace("\\", "/").lower() for p in (changed_paths or []) if p]
    out = []
    for agent, signals in _ADVERSARY_SIGNALS:
        if any(sig in path for path in paths for sig in signals):
            out.append(agent)
    # TEST-ONLY diffs earn the test-quality lens — and only those. The first draft asked for
    # it whenever a test changed, which, because the lane REQUIRES a test beside the source,
    # meant every eligible diff summoned an adversary: blanket ceremony, the exact thing this
    # lane exists to remove. The risk that actually needs a second pair of eyes is a test
    # changed with no source behind it, which is where a weakening is cheapest to hide (the
    # blatant form is already blocked by weakening_guard; the subtle form is judgment).
    code = [p for p in paths if p.endswith(_CODE_SUFFIXES)]
    if code and all(_is_test_path(p) for p in code):
        out.append("test-quality-adversary")
    return sorted(set(out))


def small_lane_preconditions(changed_paths, insertions, deletions,
                             gate_green, accounted):
    """(ok, reason) — the lane's POSITIVE requirements, all of them facts.

    Eligibility alone is not entry. The lane trades paperwork, never verification: the gate
    must be green on the tree being recorded, and every adversary the diff earns must be
    ACCOUNTED for — ran, or consciously skipped and named. Neither is satisfiable by
    assertion; both are things that either happened or did not."""
    ok, why = small_change_eligible(changed_paths, insertions, deletions)
    if not ok:
        return False, why
    if not gate_green:
        return False, ("full lane: the gate is not green on this tree — the lane reduces "
                       "paperwork, never verification. Get it green, then record")
    missing = [a for a in suggested_adversaries(changed_paths) if a not in (accounted or [])]
    if missing:
        return False, ("full lane: this diff earns {} and none is accounted for — dispatch "
                       "it, or record why it was skipped. Derived from the paths changed, "
                       "so it is the diff asking, not a checklist"
                       .format(", ".join(missing)))
    return True, ""


RECORD_OUTPUT_MARKER = "## Review record output (when these findings land in `docs/reviews/`)"


def record_output_block() -> str:
    """The record-authoring contract, DERIVED from the constants that define it.

    It lived as six byte-identical hand-maintained copies in the authoring briefs, so a
    vocabulary change had to land six times and would silently rot five of them —
    `constant-second-home` / `unpinned-prose-constant`, two shapes this repo's own ledger
    carries records of. Deriving it from FINDING_CLASSES / GUARD_KINDS / RECURRENCE_EPOCH
    means a brief can never describe a state that no longer exists; a tidier copy-paste
    would not have fixed that.

    Rendered between sentinels by render_agents.py; committed == render() is pinned by
    test_agents.py, enumerated from the real directory and vacuity-guarded."""
    return """{marker}

When this review's findings are recorded in the adversarial-review ledger, each finding
carries `class: {classes}` — `deterministic` means a mechanical check could have caught
it, `judgment` means it needed a mind — plus a short-kebab `recurrence_key`, REUSED when
the same defect shape recurs (`python3 plugins/tdd-playbook/bin/review_ledger.py
recurrence` lists the keys already seen), and an optional `catalog_row` (`H<n>`) naming the
`docs/HACK_CATALOG.md` Guard ↔ entry map row the recurrence feeds. Records dated on/after
{taxonomy} are REFUSED by `validate` without the class and key; earlier history is
untouched.

**Answer what would have caught it.** Records dated on/after {epoch} carry, per finding,
`guard: {{"kind": "{kinds}", "ref": ..., "why": ...}}` — the hook or test that would have
caught this, or an explicit `none` WITH a reason. `validate` REFUSES the finding otherwise,
and the ref is RESOLVED, not merely non-empty: a hook must name a registered hook, a test
must name a defined test. `none` is a first-class answer; the BLANK was the problem. This
is asked of YOU, now, while you still know — the previous design asked a reader to infer it
months later, and the recurrence list it produced had to be retired wholesale at {epoch}
because nobody could honestly reconstruct the answers.

The record's `reviewers` list is BOUND, not free text: every entry is a
**canonical agent id** — a basename in `agents/`, which are stable ids and are not
renamed — or one of the non-agent reviewer kinds: {reviewers}. Records dated on/after {vocab} are REFUSED by
`validate` with an unrecognised name, so write the id exactly; a plausible-looking variant
is a refusal, not a silent miss. Name every reviewer that actually contributed — the
ledger's participation report reads this field, and it can only ever show what was
RECORDED, never who ran.""".format(
        marker=RECORD_OUTPUT_MARKER,
        classes="|".join(FINDING_CLASSES),
        kinds="|".join(GUARD_KINDS),
        taxonomy=TAXONOMY_SHIP_DATE,
        epoch=RECURRENCE_EPOCH,
        vocab=REVIEWER_VOCAB_SHIP_DATE,
        reviewers=", ".join(NON_AGENT_REVIEWERS))


def _record_date(record_id: str) -> str:
    """The YYYY-MM-DD prefix of a record id, or "" — which sorts BEFORE any real date, so
    an unparseable id lands in history rather than silently claiming a current verdict."""
    match = RECORD_ID_DATE.match(record_id or "")
    return match.group(1) if match else ""


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
    # The EPOCH split. Pre-epoch findings are historical: never counted toward a verdict,
    # never classified — but REPORTED, because silence would read as "no history exists",
    # which is the H15 narrowed-scope-reported-as-the-whole shape. The keyed-of-total
    # denominator above deliberately still spans ALL findings (A7): the epoch retires the
    # verdict, not the coverage ratio, and re-keying must never shrink that denominator.
    historical = [(rid, f) for rid, f in keyed if _record_date(rid) < RECURRENCE_EPOCH]
    current = [(rid, f) for rid, f in keyed if _record_date(rid) >= RECURRENCE_EPOCH]
    if historical:
        lines.append("historical: {} keyed findings in {} records before {} — not counted "
                     "(they remain readable in docs/reviews/)".format(
                         len(historical), len({rid for rid, _f in historical}),
                         RECURRENCE_EPOCH))
    groups: dict[str, list] = {}
    for rid, finding in current:
        groups.setdefault(finding["recurrence_key"], []).append((rid, finding))
    for key in sorted(groups):
        members = groups[key]
        deterministic = {rid for rid, f in members if f.get("class") == "deterministic"}
        everywhere = {rid for rid, _f in members}
        catalog = sorted({f.get("catalog_row") for _rid, f in members if f.get("catalog_row")})
        if len(deterministic) >= 2:
            state, detail = guard_state([f.get("guard") or {} for _rid, f in members])
            # catalog_row is HUMAN CONTEXT and never decides state: H13's cell names both a
            # live mechanism and the default-off exitcode_guard, so no row-level rule can
            # classify it. The mechanism the findings NAMED is the fact.
            if catalog:
                row = " — HACK_CATALOG: " + ", ".join(catalog)
            elif state == "UNBUILT GUARD":
                # An UNBUILT line that names the problem and not the NEXT STEP is the
                # adoption failure this repo's own briefs hunt (S40). Only UNBUILT needs it:
                # a GUARDED key has nothing to propose.
                row = (" — no matching row: propose one (docs/HACK_CATALOG.md "
                       "Guard ↔ entry map)")
            else:
                row = ""
            lines.append("{}: {} ({} records) — {}{}".format(
                state, key, len(deterministic), detail, row))
        elif len(everywhere) >= 2:
            lines.append("recurring judgment: {} ({} records) — not a missing guard".format(
                key, len(everywhere)))
    return lines


def resolve_root() -> str | None:
    """A12 fix (pre-existing shipped defect): the old four-dirname-hop derivation was
    correct at plugins/tdd-playbook/bin/ and named the HOST REPO'S PARENT from a vendored
    .claude/bin/. Resolution order (arch-adversary F1/F2, 2026-08-14):
    TDD_PLAYBOOK_PROJECT_ROOT first — the adapter contract the Codex host declares
    (tdd_lock.py, _common.runtime_host) — then CLAUDE_PROJECT_DIR, then walk up to the
    first directory that actually holds docs/reviews (the artifact this tool exists to
    read; works in non-git trees where a git-derived root cannot). Exhausted walk-up
    returns None and the caller REFUSES with the real problem named — the old four-hop
    fallback reproduced the very defect this function replaces, as a live untested
    branch, and is deleted."""
    for var in ("TDD_PLAYBOOK_PROJECT_ROOT", "CLAUDE_PROJECT_DIR"):
        env = os.environ.get(var)
        if env:
            return os.path.realpath(env)
    probe = os.path.dirname(os.path.abspath(__file__))
    while True:
        if os.path.isdir(os.path.join(probe, "docs", "reviews")):
            return probe
        parent = os.path.dirname(probe)
        if parent == probe:
            return None
        probe = parent


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


# The exit-code contract (0 clean · 2 usage · 3 vacuous refusal): imported from its one
# owner, never re-typed (arch-adversary F3 — the installer only copies bin/ as a whole
# tree, so a partial copy missing the sibling cannot ship; a fallback literal was an
# unreachable, untestable second home for the constant).
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dataflow_sweeps import EXIT_VACUOUS  # noqa: E402  (sibling; vendored together)
from host_parity import agents_dir, agents_roster  # noqa: E402  (siblings; vendored together)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv not in ([], ["validate"], ["recurrence"]):
        print("usage: review_ledger.py [validate|recurrence]", file=sys.stderr)
        return 2
    root = resolve_root()
    if root is None:
        print("review_ledger: cannot locate a repository root holding docs/reviews — "
              "set CLAUDE_PROJECT_DIR (or TDD_PLAYBOOK_PROJECT_ROOT on Codex)",
              file=sys.stderr)
        return 2
    if argv == ["recurrence"]:
        records = _records(os.path.join(root, "docs", "reviews"))
        if not records:
            print("review_ledger: VACUOUS REFUSAL — no records under docs/reviews/ "
                  "(zero scanned is not clean; §4a)", file=sys.stderr)
            return EXIT_VACUOUS
        lines = recurrence_report(records)
        lines += participation_report(records, agents_roster(root),
                                      record_authoring_briefs(root))
        for line in lines:
            print(line)
        # D1 (2026-08-20): `unbuilt_guards` KEEPS its name and its meaning — the count of
        # keys nothing guards — but the epoch changes what it is counted over, so its series
        # STEP-CHANGES here rather than drifting. The sibling counters are added beside it
        # instead of quietly redefining the old one: a metric that silently changes what it
        # measures is worse than a metric that stops.
        _log_usage("recurrence", {
            "records": len(records),
            "unbuilt_guards": sum(1 for line in lines if line.startswith("UNBUILT GUARD")),
            "guarded": sum(1 for line in lines if line.startswith("GUARDED:")),
            "guard_dark": sum(1 for line in lines if line.startswith("GUARD DARK:")),
            "historical": sum(1 for line in lines if line.startswith("historical:")),
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
