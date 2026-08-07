#!/usr/bin/env python3
"""Portable TDD Playbook CLI.

`doctor` reports what a host adapter declares separately from what a recent local probe
actually observed.  Its journal is forgeable local evidence: useful for liveness and decay,
never release-authorizing.  CIVerd's fresh signed exact-SHA verdict remains the authority.
"""
import argparse
import datetime
import json
import os
import sys

from host_contract import (ASSURANCE_LEVELS, ContractError, read_events, read_lock,
                           lock_binding, resolve_repository)

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADAPTERS = os.path.join(PLUGIN, "adapters")


def _date(value):
    try:
        return datetime.date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ContractError("--as-of needs YYYY-MM-DD")


def _timestamp(value):
    try:
        return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def _manifests():
    found = []
    if not os.path.isdir(ADAPTERS):
        raise ContractError("adapter manifest directory is missing: {}".format(ADAPTERS))
    for host in sorted(os.listdir(ADAPTERS)):
        path = os.path.join(ADAPTERS, host, "adapter.json")
        if not os.path.isfile(path):
            continue
        try:
            with open(path) as fh:
                manifest = json.load(fh)
        except (OSError, ValueError) as exc:
            raise ContractError("invalid adapter manifest {}: {}".format(path, exc))
        if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
            raise ContractError("unsupported adapter manifest: {}".format(path))
        if manifest.get("host") != host or not isinstance(manifest.get("capabilities"), dict):
            raise ContractError("adapter manifest host/capabilities mismatch: {}".format(path))
        if not isinstance(manifest.get("adapter_version"), str):
            raise ContractError("adapter manifest lacks adapter_version: {}".format(path))
        found.append(manifest)
    if not found:
        raise ContractError("no adapter manifests found")
    return found


def _capability(manifest, capability, spec, events, identity, as_of):
    routes = spec.get("required_routes")
    if not isinstance(routes, list) or not routes or not all(isinstance(v, str) for v in routes):
        raise ContractError("{}:{} has invalid required_routes".format(
            manifest["host"], capability))
    max_age = manifest.get("max_probe_age_days", 14)
    if not isinstance(max_age, int) or max_age < 1:
        raise ContractError("{} has invalid max_probe_age_days".format(manifest["host"]))
    declared = spec.get("declared_assurance")
    if declared not in ASSURANCE_LEVELS[:4]:
        raise ContractError("{}:{} has invalid declared_assurance".format(
            manifest["host"], capability))
    candidates = [row for row in events
                  if isinstance(row, dict)
                  and row.get("event") == "capability_probe"
                  and row.get("host") == manifest["host"]
                  and row.get("adapter_version") == manifest["adapter_version"]
                  and row.get("repo_id") == identity["repo_id"]
                  and row.get("sha") == identity["head"]
                  and (row.get("details") or {}).get("capability") == capability]
    complete_by_route = {}
    saw_stale = False
    grouped = {}
    for row in candidates:
        route = (row.get("details") or {}).get("route")
        stamp = _timestamp(row.get("ts"))
        if route not in routes or stamp is None:
            continue
        age = (as_of - stamp.date()).days
        if age < 0 or age > max_age:
            saw_stale = True
            continue
        grouped.setdefault((route, row.get("run_id")), []).append(row)
    for (route, _run_id), rows in grouped.items():
        outcomes = {(row.get("details") or {}).get("outcome") for row in rows}
        if {"blocked", "allowed"} <= outcomes:
            newest = max(rows, key=lambda row: row["ts"])
            prior = complete_by_route.get(route)
            if prior is None or newest["ts"] > prior["ts"]:
                complete_by_route[route] = newest
    complete = set(complete_by_route) == set(routes)
    if not complete:
        return {"assurance": "unmeasured", "trust": "local_unverified",
                "stale": saw_stale, "required_routes": routes,
                "observed_routes": sorted(complete_by_route)}
    return {"assurance": declared, "trust": "local_unverified", "stale": False,
            "required_routes": routes, "observed_routes": sorted(complete_by_route),
            "latest_probe": max(row["ts"] for row in complete_by_route.values())}


def doctor(args):
    try:
        as_of = _date(args.as_of) if args.as_of else datetime.datetime.now(
            datetime.timezone.utc).date()
        root = (os.environ.get("TDD_PLAYBOOK_PROJECT_ROOT")
                or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        identity = resolve_repository(root)
        lock = read_lock(identity)  # validation is itself a doctor check; malformed is RED
        events = read_events(identity)
        hosts = {}
        for manifest in _manifests():
            capabilities = {}
            for name, spec in sorted(manifest["capabilities"].items()):
                capabilities[name] = _capability(
                    manifest, name, spec, events, identity, as_of)
            hosts[manifest["host"]] = {
                "adapter_version": manifest["adapter_version"],
                "declared": sorted(manifest["capabilities"]),
                "capabilities": capabilities,
            }
        report = {
            "schema_version": 1,
            "as_of": as_of.isoformat(),
            "repo_id": identity["repo_id"],
            "worktree_id": identity["worktree_id"],
            "sha": identity["head"],
            "active_lock": None if lock is None else {
                "files": len(lock["files"]), "source_worktree_id": lock["source_worktree_id"],
                "head": lock["head"], "locked_at": lock["locked_at"],
                "binding": lock_binding(identity, lock)},
            "hosts": hosts,
            "release_authority": "CIVerd signed exact-SHA verdict only",
        }
    except ContractError as exc:
        sys.stderr.write("tdd doctor: {}\n".format(exc))
        return 1
    if args.json:
        print(json.dumps(report, sort_keys=True))
    else:
        print("tdd doctor — {} @ {}".format(report["sha"] or "unborn", report["as_of"]))
        for host, host_report in sorted(report["hosts"].items()):
            print("{} adapter {}:".format(host, host_report["adapter_version"]))
            for name, value in sorted(host_report["capabilities"].items()):
                suffix = " (STALE)" if value["stale"] else ""
                print("  {}: {}{} [{}]".format(
                    name, value["assurance"], suffix, value["trust"]))
        print("release authority: " + report["release_authority"])
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tdd")
    sub = parser.add_subparsers(dest="command", required=True)
    p_doctor = sub.add_parser("doctor")
    p_doctor.add_argument("--json", action="store_true")
    p_doctor.add_argument("--as-of")
    p_doctor.set_defaults(func=doctor)
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
