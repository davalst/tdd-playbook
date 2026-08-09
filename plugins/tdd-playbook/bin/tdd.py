#!/usr/bin/env python3
"""Portable TDD Playbook CLI.

`doctor` reports what a host adapter declares separately from what a recent local probe
actually observed.  Its journal is forgeable local evidence: useful for liveness and decay,
never release-authorizing.  Since v1.32.0 the release authority is DAVID creating the tag
on a gate-green commit; no verdict, and no script, can stand in for that.
"""
import argparse
import datetime
import json
import os
import subprocess
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
    other_worktree_routes = set()
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
        scope = "current" if row.get("worktree_id") == identity["worktree_id"] else "other"
        grouped.setdefault((scope, route, row.get("run_id")), []).append(row)
    for (scope, route, _run_id), rows in grouped.items():
        outcomes = {(row.get("details") or {}).get("outcome") for row in rows}
        if {"blocked", "allowed"} <= outcomes:
            if scope == "other":
                other_worktree_routes.add(route)
                continue
            newest = max(rows, key=lambda row: row["ts"])
            prior = complete_by_route.get(route)
            if prior is None or newest["ts"] > prior["ts"]:
                complete_by_route[route] = newest
    complete = set(complete_by_route) == set(routes)
    if not complete:
        return {"assurance": "unmeasured", "trust": "local_unverified",
                "stale": saw_stale, "required_routes": routes,
                "observed_routes": sorted(complete_by_route),
                "other_worktree_routes": sorted(other_worktree_routes)}
    return {"assurance": declared, "trust": "local_unverified", "stale": False,
            "required_routes": routes, "observed_routes": sorted(complete_by_route),
            "other_worktree_routes": sorted(other_worktree_routes),
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
            "release_authority": "David creating the v* tag on a gate-green commit "
                                 "(no in-repo script or session may tag)",

            "findings": _run_checks(root, getattr(args, "only", None)),
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
        for f in report["findings"]:
            print("{:<5} {} — {}".format(f["severity"].upper(), f["id"], f["message"]))
            print("      fix: " + f["fix"])
        if report["findings"]:
            print("\n{} finding(s), {} repairable — re-run with --fix".format(
                len(report["findings"]),
                sum(1 for f in report["findings"] if f["repairable"])))
    if getattr(args, "fix", False):
        if args.json:
            sys.stderr.write("tdd doctor: --fix is refused with --json — machine output "
                             "must not mutate the repo as a side effect\n")
            return 2
        for f in report["findings"]:
            if not f["repairable"]:
                continue
            print("running: " + f["fix"])
            # report the RESULT: discarding the return code makes a failed fix
            # indistinguishable from a successful one, and the exit code below would still
            # reflect pre-fix findings.
            r = subprocess.run(f["fix"].split(), cwd=root, timeout=300,
                               capture_output=True, text=True)
            print("  -> exit {}{}".format(r.returncode,
                                          "" if r.returncode == 0
                                          else ": " + (r.stderr or "").strip()[:160]))
        report["findings"] = _run_checks(root, getattr(args, "only", None))
        print("after --fix: {} finding(s) remain".format(len(report["findings"])))
    return 1 if any(f["severity"] == "fail" for f in report["findings"]) else 0


def _root(args):
    return os.path.realpath(getattr(args, "target", None)
                            or os.environ.get("TDD_PLAYBOOK_PROJECT_ROOT")
                            or os.environ.get("CLAUDE_PROJECT_DIR")
                            or os.getcwd())


def clone_findings(root):
    """Is this clone deep enough for the gate to MEASURE rather than skip?

    The default new-user and default CI experience: a shallow clone makes the ledger stage
    return UNMEASURED, `calibration/test_harness.py`'s substring assertion then fails, and the
    gate reports `FAIL calibration` — with the real cause buried in a stage log. Nothing told
    you to run `git fetch --unshallow`.

    Two tiers on purpose: the trigger is "the ledger EPOCH is unreachable", NOT "the clone is
    shallow". A `--depth 400` clone is shallow and perfectly green, and scolding it would be a
    check that fires when nothing is wrong."""
    import re
    out = []
    epoch = None
    led = os.path.join(root, "docs", "calibration", "ledger.md")
    if os.path.isfile(led):
        with open(led) as fh:
            m = re.search(r"^EPOCH:\s*([0-9a-f]{7,40})", fh.read(), re.M)
            epoch = m.group(1) if m else None
    shallow = _git_text(root, "rev-parse", "--is-shallow-repository").strip() == "true"
    if epoch and not _git_ok(root, "rev-parse", "--verify", epoch + "^{commit}"):
        out.append({
            "id": "shallow-epoch", "family": "clone", "severity": "fail",
            "message": ("this clone cannot reach the ledger EPOCH {} — the ledger stage "
                        "returns UNMEASURED and the gate reports `FAIL calibration` with the "
                        "real cause only inside a stage log".format(epoch)),
            "fix": "git fetch --unshallow --tags" if shallow else "git fetch --deepen=500",
            "repairable": True})
    if not _git_text(root, "tag", "-l").strip():
        out.append({
            "id": "no-tags", "family": "clone", "severity": "warn",
            "message": ("no tags: the real-repo scoreboard-integrity check is SKIPPED and the "
                        "gate's ledger baseline falls back to the EPOCH"),
            "fix": "git fetch --tags", "repairable": True})
    return out


def _git_text(root, *args):
    try:
        p = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True,
                           timeout=60)
        return p.stdout if p.returncode == 0 else ""
    except Exception:
        return ""


def _git_ok(root, *args):
    try:
        return subprocess.run(["git", "-C", root, *args], capture_output=True,
                              timeout=60).returncode == 0
    except Exception:
        return False


CHECKS = [{"family": "clone", "run": clone_findings}]


def _run_checks(root, only=None):
    """Drive the doctor from CHECKS and honour --only.

    The first version called clone_findings directly and parsed --only without ever reading
    it, so `--only registry` was an advertised choice that routed to nothing — an accepted
    flag that does nothing is worse than an absent one, because it reports a scoping the
    operator never got. Families not yet implemented say so rather than passing silently."""
    want = set(only or [])
    out = []
    known = {c["family"] for c in CHECKS}
    for fam in sorted(want - known):
        out.append({"id": "family-unimplemented", "family": fam, "severity": "warn",
                    "message": "the '{}' family is not implemented in `tdd doctor` yet — run "
                               "its own tool".format(fam),
                    "fix": {"install": "python3 scripts/install_into_repo.py --doctor .",
                            "registry": "python3 <plugin>/bin/capability_registry.py doctor",
                            "assurance": "python3 <plugin>/bin/tdd.py doctor"}.get(fam, ""),
                    "repairable": False})
    for c in CHECKS:
        if want and c["family"] not in want:
            continue
        out += c["run"](root)
    return out


def cmd_reset(args):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import reset_plan
    root = _root(args)
    scopes = [s for s in ("repo", "shared", "machine", "plugin") if getattr(args, s)]
    if args.all:
        scopes = ["repo", "shared", "machine", "plugin"]
    if args.burn_evidence:
        # --reason makes the scope LEGAL (so you can preview it); --yes makes the run REAL.
        # Coupling them meant the only accepted invocation was the irreversible one: an
        # operator asking "show me what this would remove" got exit 2, and their next,
        # natural command deleted the evidence.
        if not args.reason:
            sys.stderr.write(
                "tdd reset: REFUSED — --burn-evidence needs --reason (add --yes to apply; "
                "--reason alone gives you a dry run).\n"
                "  docs/calibration/ and calibration/corpus/ are append-only and immutable "
                "under check_scoreboard_integrity; deleting them does not merely lose data, "
                "it makes this repo permanently RED against every baseline.\n")
            return 2
        scopes.append("burn-evidence")
    if not scopes:
        sys.stderr.write("tdd reset: pick a scope — --repo --shared --machine --plugin "
                         "--all (or --burn-evidence, which is never implied by --all)\n")
        return 2
    rows = reset_plan.plan(root, scopes=scopes, force=args.force)
    dry = not args.yes
    if dry:
        print("tdd reset — DRY RUN. Nothing has been changed. Re-run with --yes to apply.\n")
    # NEVER truncate the path: a 58-char slice printed two DIFFERENT rmtree targets as the
    # same string, so the human-readable dry run stopped being the set that gets deleted.
    for r in rows:
        print("{:<8} {:<7} {}".format(r["scope"], r["kind"], r["path"]))
        print("{:>17}{}".format("", r["why"]))
    roots = [root, os.path.expanduser("~/.claude")]
    ident = None
    try:
        import host_contract
        ident = host_contract.resolve_repository(root)
        roots.append(ident["common_git_dir"])
    except Exception:
        pass
    if not dry:
        _journal_reset(root, scopes, args.reason, rows)
    removed = reset_plan.apply(rows, dry_run=dry, roots=roots)
    n = sum(1 for r in rows if r["kind"] in ("file", "dir"))
    print("\n{} path(s) planned · {} refused · {} removed".format(
        n, sum(1 for r in rows if r["kind"] in ("wtree", "refused")), len(removed)))
    return 0


def _journal_reset(root, scopes, reason, rows):
    """Record the burn BEFORE it happens, somewhere reset does not remove.

    --reason was checked for truthiness and then discarded, so `--reason x` satisfied the
    gate and left nothing to review. For --shared the record cannot live in events.jsonl,
    because that is the file being deleted."""
    import datetime
    store = os.environ.get("TDD_PLAYBOOK_DELIBERATION_DIR") or \
        os.path.join(os.path.expanduser("~"), ".claude", "deliberation")
    try:
        os.makedirs(store, exist_ok=True)
        with open(os.path.join(store, ".reset-journal.jsonl"), "a") as fh:
            fh.write(json.dumps({
                "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "root": root, "scopes": sorted(scopes), "reason": reason,
                "paths": [r["path"] for r in rows if r["kind"] in ("file", "dir")],
            }) + "\n")
    except OSError:
        pass


def cmd_uninstall(args):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import vendoring
    rows = vendoring.uninstall(_root(args), host=args.host, apply=args.apply)
    if not args.apply:
        print("tdd uninstall — DRY RUN. Nothing has been changed. Re-run with --apply.\n")
    for r in rows:
        print("  {:<5} {:<52} {}".format(r["kind"], r["path"], r["why"]))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(prog="tdd")
    sub = parser.add_subparsers(dest="command", required=True)
    p_doctor = sub.add_parser("doctor")
    p_doctor.add_argument("--json", action="store_true")
    p_doctor.add_argument("--as-of")
    p_doctor.add_argument("--only", action="append",
                          choices=("clone", "install", "assurance", "registry"))
    p_doctor.add_argument("--fix", action="store_true",
                          help="run each finding's fix command (never implied)")
    p_doctor.set_defaults(func=doctor)

    p_reset = sub.add_parser("reset", help="remove Playbook machine state (dry run by default)")
    for flag in ("repo", "shared", "machine", "plugin"):
        p_reset.add_argument("--" + flag, action="store_true")
    p_reset.add_argument("--all", action="store_true")
    p_reset.add_argument("--burn-evidence", action="store_true")
    p_reset.add_argument("--yes", action="store_true", help="actually apply")
    p_reset.add_argument("--force", action="store_true")
    p_reset.add_argument("--reason")
    p_reset.add_argument("target", nargs="?")
    p_reset.set_defaults(func=cmd_reset)

    p_un = sub.add_parser("uninstall", help="the inverse of install_into_repo.py")
    p_un.add_argument("--host", choices=("claude", "codex", "all"), default="claude")
    p_un.add_argument("--apply", action="store_true")
    p_un.add_argument("target", nargs="?")
    p_un.set_defaults(func=cmd_uninstall)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
