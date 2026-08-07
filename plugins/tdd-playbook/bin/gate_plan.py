#!/usr/bin/env python3
"""One fail-closed plan for the full CIVerd gate and its diagnostic safe subset."""
from __future__ import annotations

import fnmatch
import glob
import hashlib
import json
import os
import subprocess
from typing import Iterable, NamedTuple


class PlanError(RuntimeError):
    pass


class Stage(NamedTuple):
    id: str
    argv: tuple[str, ...]
    kind: str


class Scope(NamedTuple):
    paths: tuple[str, ...]
    sources: tuple[str, ...]


class Plan(NamedTuple):
    mode: str
    authorizing: bool
    stages: tuple[Stage, ...]
    total_stages: int
    reasons: tuple[str, ...] = ()
    changed_paths: tuple[str, ...] = ()


def load_manifest(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if data.get("schema_version") != 1:
        raise PlanError("gate manifest schema_version must be 1")
    for field in ("suite_glob", "acknowledged_roster_sha256", "fixed_stages",
                  "force_full", "safe_rules"):
        if field not in data:
            raise PlanError("gate manifest missing '{}'".format(field))
    ids = [row.get("id") for row in data["fixed_stages"]]
    if not ids or len(ids) != len(set(ids)) or any(not value for value in ids):
        raise PlanError("fixed stage ids must be non-empty and unique")
    return data


def roster_digest(suite_ids: Iterable[str], fixed_ids: Iterable[str]) -> str:
    material = json.dumps({"suites": sorted(suite_ids), "fixed": list(fixed_ids)},
                          sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _suite_stages(root: str, manifest: dict) -> list[Stage]:
    paths = sorted(glob.glob(os.path.join(root, manifest["suite_glob"])))
    stages = []
    for path in paths:
        if not os.path.isfile(path):
            continue
        sid = os.path.basename(path)[:-3]
        stages.append(Stage(sid, ("python3", os.path.relpath(path, root)), "suite"))
    if not stages:
        raise PlanError("the plugin suite glob matched nothing")
    return stages


def _fixed_stages(manifest: dict) -> list[Stage]:
    out = []
    for row in manifest["fixed_stages"]:
        argv = row.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
            raise PlanError("fixed stage '{}' needs a non-empty argv list".format(row.get("id")))
        out.append(Stage(row["id"], tuple(argv), "fixed"))
    return out


def full_plan(root: str, manifest: dict) -> Plan:
    suites = _suite_stages(root, manifest)
    fixed = _fixed_stages(manifest)
    actual = roster_digest([s.id for s in suites], [s.id for s in fixed])
    expected = manifest["acknowledged_roster_sha256"]
    if actual != expected:
        raise PlanError("gate roster digest mismatch: discovered {} suite(s) + {} fixed stage(s); "
                        "review the new/deleted stage and acknowledge {} (manifest has {})".format(
                            len(suites), len(fixed), actual, expected))
    stages = tuple(suites + fixed)
    return Plan("full", True, stages, len(stages), ("no-argument complete gate",), ())


def _git(root: str, args: list[str]) -> bytes:
    proc = subprocess.run(["git", *args], cwd=root, capture_output=True, timeout=30)
    if proc.returncode != 0:
        raise PlanError("git {} failed: {}".format(" ".join(args),
                                                   os.fsdecode(proc.stderr).strip()))
    return proc.stdout


def _name_status_paths(payload: bytes) -> set[str]:
    parts = payload.split(b"\0")
    if parts and parts[-1] == b"":
        parts.pop()
    paths: set[str] = set()
    i = 0
    while i < len(parts):
        status = os.fsdecode(parts[i])
        i += 1
        count = 2 if status[:1] in ("R", "C") else 1
        if i + count > len(parts):
            raise PlanError("malformed NUL-delimited git name-status output")
        for raw in parts[i:i + count]:
            paths.add(os.fsdecode(raw))
        i += count
    return paths


def _safe_path(path: str) -> str:
    path = path.replace(os.sep, "/")
    if not path or path.startswith("/") or "\x00" in path or ".." in path.split("/"):
        raise PlanError("unsafe changed path {!r}".format(path))
    return path


def collect_changed_paths(root: str, base: str) -> Scope:
    _git(root, ["rev-parse", "--verify", "{}^{{commit}}".format(base)])
    found: set[str] = set()
    sources = []
    for label, args in (
        ("committed", ["diff", "--name-status", "-z", "{}..HEAD".format(base)]),
        ("staged", ["diff", "--cached", "--name-status", "-z"]),
        ("unstaged", ["diff", "--name-status", "-z"]),
    ):
        payload = _git(root, args)
        paths = _name_status_paths(payload)
        if paths:
            sources.append(label)
            found.update(paths)
    untracked = _git(root, ["ls-files", "--others", "--exclude-standard", "-z"])
    extra = {os.fsdecode(raw) for raw in untracked.split(b"\0") if raw}
    if extra:
        sources.append("untracked")
        found.update(extra)
    return Scope(tuple(sorted(_safe_path(path) for path in found)), tuple(sources))


def _matches(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def affected_plan(root: str, manifest: dict, base: str) -> Plan:
    complete = full_plan(root, manifest)
    try:
        scope = collect_changed_paths(root, base)
    except PlanError as exc:
        return complete._replace(authorizing=False,
                                 reasons=("affected request fell back to full: {}".format(exc),))

    if not scope.paths:
        sentinel = next((s for s in complete.stages
                         if s.id == "test_aaa_suites_via_main"), complete.stages[0])
        return Plan("affected", False, (sentinel,), len(complete.stages),
                    ("no changed paths; ran one gate-liveness sentinel",), ())

    forced = [path for path in scope.paths if _matches(path, manifest["force_full"])]
    if forced:
        return complete._replace(
            authorizing=False, changed_paths=scope.paths,
            reasons=("affected request fell back to full: gate surface changed: {}".format(
                ", ".join(forced)),))

    selected: set[str] = set()
    unmapped: list[str] = []
    suite_by_id = {s.id: s for s in complete.stages if s.kind == "suite"}
    suite_dir = os.path.dirname(manifest["suite_glob"]).rstrip("/") + "/"
    for path in scope.paths:
        matched = False
        if path.startswith(suite_dir) and path.endswith(".py"):
            sid = os.path.basename(path)[:-3]
            if sid in suite_by_id:
                selected.add(sid)
                if "test_aaa_suites_via_main" in suite_by_id:
                    selected.add("test_aaa_suites_via_main")
                matched = True
        for rule in manifest["safe_rules"]:
            if _matches(path, rule.get("patterns") or []):
                selected.update(rule.get("suites") or [])
                matched = True
        if not matched:
            unmapped.append(path)
    invalid = sorted(selected - set(suite_by_id))
    if invalid:
        raise PlanError("safe rule names unknown suite(s): {}".format(", ".join(invalid)))
    if unmapped:
        return complete._replace(
            authorizing=False, changed_paths=scope.paths,
            reasons=("affected request fell back to full: unmapped path(s): {}".format(
                ", ".join(unmapped)),))
    if not selected:
        return complete._replace(authorizing=False, changed_paths=scope.paths,
                                 reasons=("affected request fell back to full: empty selection",))
    stages = tuple(s for s in complete.stages if s.id in selected)
    reason = "safe subset from {} path(s) ({})".format(
        len(scope.paths), ", ".join(scope.sources) or "committed")
    return Plan("affected", False, stages, len(complete.stages), (reason,), scope.paths)


def suite_directory_plan(directory: str) -> Plan:
    paths = sorted(glob.glob(os.path.join(directory, "test_*.py")))
    stages = tuple(Stage(os.path.basename(path)[:-3], ("python3", path), "suite")
                   for path in paths if os.path.isfile(path))
    if not stages:
        raise PlanError("suite directory matched no test_*.py files")
    return Plan("focused", False, stages, len(stages),
                ("explicit planted suite-directory seam",), ())
