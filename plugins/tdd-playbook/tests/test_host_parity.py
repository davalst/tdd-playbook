#!/usr/bin/env python3
"""Family-parity sweep: every canonical host asset has an explicit host disposition."""
import json
import os
import re

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(PLUGIN))
PARITY = os.path.join(REPO, "docs", "architecture", "host-parity.json")

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


def test_host_parity_inventory():
    with open(PARITY) as fh:
        manifest = json.load(fh)
    canonical = {
        "commands": _names(os.path.join(PLUGIN, "commands")),
        "agents": _names(os.path.join(PLUGIN, "agents")),
        "guards": _guards(),
    }
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


def main():
    print("host asset parity calibration")
    try:
        test_host_parity_inventory()
    except Exception as exc:
        check("test_host_parity_inventory executes", False, repr(exc))
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    assert not _results["fail"], "host parity calibration failed"


if __name__ == "__main__":
    main()
