#!/usr/bin/env python3
"""Family-parity sweep: every canonical host asset has an explicit host disposition."""
import json
import importlib.util
import os
import re
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(PLUGIN))
PARITY = os.path.join(REPO, "docs", "architecture", "host-parity.json")
POLICY = os.path.join(REPO, "docs", "architecture", "host-parity-policy.json")
BIN = os.path.join(PLUGIN, "bin", "host_parity.py")
INSTALLER = os.path.join(REPO, "scripts", "install_into_repo.py")

_results = {"pass": 0, "fail": 0}


def check(name, condition, detail=""):
    if condition:
        _results["pass"] += 1
        print("  ok   - " + name)
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def _names(directory):
    return {name[:-3] for name in os.listdir(directory) if name.endswith(".md")}


def _guards():
    with open(os.path.join(PLUGIN, "hooks", "hooks.json")) as fh:
        hooks = json.load(fh)["hooks"]
    found = set()
    for groups in hooks.values():
        for group in groups:
            for handler in group.get("hooks", []):
                match = re.search(r"/([^/]+\.py)", handler.get("command", ""))
                if match:
                    found.add(match.group(1)[:-3])
    return found


def _load_resolver():
    spec = importlib.util.spec_from_file_location("host_parity", BIN)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_host_parity_inventory():
    hp = _load_resolver()
    policy = hp.load_policy(POLICY)
    manifest = hp.materialize(REPO, policy)
    canonical = hp.canonical_inventory(REPO)
    check("parity: all three canonical families are non-vacuous",
          all(canonical.values()), canonical)
    for family, names in canonical.items():
        entries = manifest.get("assets", {}).get(family, {})
        check("parity: {} inventory is exact".format(family), set(entries) == names,
              sorted(set(entries) ^ names))
        for name in sorted(names):
            hosts = entries[name]
            check("parity: {}:{} names both hosts".format(family, name),
                  set(hosts) == {"claude", "codex"}, hosts)
            for host, disposition in hosts.items():
                status = disposition.get("status")
                owned = (status == "supported" or
                         (status in {"unavailable", "debt"}
                          and disposition.get("owner")
                          and re.match(r"^\d{4}-\d{2}-\d{2}$",
                                       disposition.get("expires", ""))))
                check("parity: {}:{}:{} is supported or dated debt".format(
                    family, name, host), owned, disposition)
    with open(PARITY) as fh:
        committed = json.load(fh)
    check("parity: committed expanded output equals resolver materialization",
          committed == manifest, PARITY)


def test_parity_digest_and_exception_plants():
    hp = _load_resolver()
    policy = hp.load_policy(POLICY)
    inventory = hp.canonical_inventory(REPO)
    planted = {family: set(names) for family, names in inventory.items()}
    planted["commands"].add("new-command-plant")
    try:
        hp.materialize(REPO, policy, inventory=planted)
    except hp.ParityError as exc:
        digest_refused = "inventory digest" in str(exc).lower()
    else:
        digest_refused = False
    check("parity: PLANTED new canonical asset needs human digest acknowledgement",
          digest_refused)

    bad = json.loads(json.dumps(policy))
    bad.setdefault("overrides", {}).setdefault("codex", {}).setdefault(
        "commands", {})["ghost-command"] = {"status": "supported"}
    try:
        hp.materialize(REPO, bad)
    except hp.ParityError as exc:
        stale_refused = "unknown asset" in str(exc).lower()
    else:
        stale_refused = False
    check("parity: PLANTED stale exception cannot mask inventory drift", stale_refused)


def _flat_commands(path):
    with open(path) as fh:
        config = json.load(fh)
    return [handler.get("command", "")
            for groups in config.get("hooks", {}).values()
            for group in groups for handler in group.get("hooks", [])]


def test_installed_host_activation():
    hp = _load_resolver()
    matrix = hp.materialize(REPO, hp.load_policy(POLICY))
    required = {"producer", "installed_target", "binding",
                "activation_prerequisite", "liveness_test"}
    supported = []
    for family, assets in matrix["assets"].items():
        for asset, hosts in assets.items():
            for host, row in hosts.items():
                if row["status"] == "supported":
                    supported.append((family, asset, host, row))
                    check("activation metadata: {}:{}:{} complete".format(
                        family, asset, host), required.issubset(row), row)

    with tempfile.TemporaryDirectory() as target:
        install = subprocess.run([sys.executable, INSTALLER, "--host", "all", target],
                                 cwd=REPO, capture_output=True, text=True, timeout=60)
        check("activation: dual-host scratch install succeeds", install.returncode == 0,
              (install.stdout, install.stderr))
        claude_commands = _flat_commands(os.path.join(target, ".claude", "settings.json"))
        codex_commands = _flat_commands(os.path.join(target, ".codex", "hooks.json"))
        problems = []
        for family, asset, host, row in supported:
            installed = os.path.join(target, row["installed_target"])
            if not os.path.isfile(installed):
                problems.append("missing {}:{}:{} -> {}".format(family, asset, host, installed))
            binding = row["binding"]
            commands = claude_commands if host == "claude" else codex_commands
            if binding.startswith("hook:") and not any(
                    binding.split(":", 1)[1] in command for command in commands):
                problems.append("unbound {}:{}:{} -> {}".format(
                    family, asset, host, binding))
        check("activation: every supported materialized row reaches installed composition",
              not problems, problems)

        unavailable_present = []
        for family, assets in matrix["assets"].items():
            for asset, hosts in assets.items():
                for host, row in hosts.items():
                    if row["status"] != "supported" and row.get("installed_target"):
                        if os.path.exists(os.path.join(target, row["installed_target"])):
                            unavailable_present.append("{}:{}:{}".format(family, asset, host))
        check("activation: unavailable runtime assets are absent",
              not unavailable_present, unavailable_present)


def test_compact_parity_output():
    proc = subprocess.run([sys.executable, BIN, "check"], cwd=REPO,
                          capture_output=True, text=True, timeout=30)
    check("parity output: success is compact and denominator-bearing",
          proc.returncode == 0 and len(proc.stdout.splitlines()) <= 2
          and "32 assets" in proc.stdout and "64 dispositions" in proc.stdout,
          (proc.returncode, proc.stdout, proc.stderr))


def main():
    print("host asset parity calibration")
    for fn in (test_host_parity_inventory, test_parity_digest_and_exception_plants,
               test_installed_host_activation, test_compact_parity_output):
        try:
            fn()
        except Exception as exc:
            check(fn.__name__ + " executes", False, repr(exc))
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    assert not _results["fail"], "host parity calibration failed"


if __name__ == "__main__":
    main()
