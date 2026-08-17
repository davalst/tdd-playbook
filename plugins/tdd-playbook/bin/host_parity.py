#!/usr/bin/env python3
"""Resolve compact host policy into an exact, activation-bearing asset matrix."""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys


class ParityError(RuntimeError):
    pass


PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(PLUGIN))
POLICY = os.path.join(REPO, "docs", "architecture", "host-parity-policy.json")
OUTPUT = os.path.join(REPO, "docs", "architecture", "host-parity.json")
FAMILIES = ("commands", "agents", "guards")
HOSTS = ("claude", "codex")
SUPPORTED_FIELDS = ("producer", "installed_target", "binding",
                    "activation_prerequisite", "liveness_test")


def load_policy(path: str = POLICY) -> dict:
    with open(path, encoding="utf-8") as fh:
        policy = json.load(fh)
    if policy.get("schema_version") != 2:
        raise ParityError("host parity policy schema_version must be 2")
    return policy


def _markdown_names(directory: str) -> set[str]:
    return {name[:-3] for name in os.listdir(directory) if name.endswith(".md")}


def registered_scripts(hooks_json_path: str) -> set[str]:
    """Plugin-root-relative paths of every script a hooks.json registers — the ONE
    hooks.json command parser (arch F7, 2026-08-14): `_guard_names` and the Codex
    vendoring-parity test both consume this rather than forking a fourth traversal.
    Matches both hosts' root variables (`${CLAUDE_PLUGIN_ROOT}`, `${PLUGIN_ROOT}`)."""
    with open(hooks_json_path, encoding="utf-8") as fh:
        hooks = json.load(fh)["hooks"]
    found = set()
    for groups in hooks.values():
        for group in groups:
            for handler in group.get("hooks", []):
                match = re.search(r"\$\{(?:CLAUDE_)?PLUGIN_ROOT\}/([\w/.-]+\.py)",
                                  handler.get("command", ""))
                if match:
                    found.add(match.group(1))
    return found


def _guard_names(plugin: str) -> set[str]:
    return {os.path.basename(path)[:-3] for path in
            registered_scripts(os.path.join(plugin, "hooks", "hooks.json"))}


def canonical_inventory(root: str = REPO) -> dict[str, set[str]]:
    plugin = os.path.join(root, "plugins", "tdd-playbook")
    inventory = {
        "commands": _markdown_names(os.path.join(plugin, "commands")),
        "agents": _markdown_names(os.path.join(plugin, "agents")),
        "guards": _guard_names(plugin),
    }
    if not all(inventory.values()):
        raise ParityError("all canonical asset families must be non-vacuous")
    return inventory


AGENT_FAMILY_LAYOUTS = (os.path.join("plugins", "tdd-playbook", "agents"),
                        os.path.join(".claude", "agents"))


def agents_roster(root: str) -> set[str] | None:
    """CANONICAL REVIEWER IDS — the agent family across every layout the installer really
    produces — or None where the family is genuinely absent.

    Contract, stated rather than left to a caller's optimism (the model is
    review_ledger.catalog_rows, which returns None when docs/ is not vendored here):
      - source tree      -> <root>/plugins/tdd-playbook/agents
      - claude vendored  -> <root>/.claude/agents
      - codex vendored   -> None; CODEX_COPY_TREES carries adapters + bin only, so the
                            family does not exist there and cannot be invented
      - empty/absent     -> None, NEVER a vacuous set of zero names

    This returns IDs, not a description of the installed copy that happens to be running:
    the first layout yielding a NON-EMPTY family wins, source first, so a dev tree holding
    both is unambiguous — and an empty directory in one layout cannot mask a real family
    in the next.

    Deliberately NOT `canonical_inventory`. That function hardcodes the source layout
    (`os.path.join(root, "plugins", "tdd-playbook")`) and REFUSES a vacuous family, which
    is correct for parity duty and fatal for a downstream consumer: it raises
    FileNotFoundError in every vendored layout. It had no production bin/ caller, so
    nothing had exercised that path until review_ledger's reviewer binding became the
    first — which would have taken the ledger's default `validate` verb dark on exactly
    the hosts it serves. Weakening the parity refusal to fix that would have traded one
    correct invariant for another; a sibling with its own contract does not."""
    directory = agents_dir(root)
    return _markdown_names(directory) if directory else None


def agents_dir(root: str) -> str | None:
    """The directory backing `agents_roster` — the first layout holding a NON-EMPTY agent
    family, or None. Separate so a caller needing the BRIEFS (not just their ids) reads
    the same resolution instead of re-deriving the layout list."""
    for relative in AGENT_FAMILY_LAYOUTS:
        directory = os.path.join(root, relative)
        if os.path.isdir(directory) and _markdown_names(directory):
            return directory
    return None


def inventory_digest(inventory: dict[str, set[str]]) -> str:
    body = json.dumps({family: sorted(inventory[family]) for family in FAMILIES},
                      sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _debt_index(root: str) -> dict[str, dict]:
    with open(os.path.join(root, "capabilities.json"), encoding="utf-8") as fh:
        registry = json.load(fh)
    index = {}
    for capability in registry.get("capabilities", []):
        cid = capability.get("id")
        for debt in capability.get("integration_debt") or []:
            did = debt.get("id")
            if did:
                key = "{}/{}".format(cid, did)
                if key in index:
                    raise ParityError("duplicate capability debt reference {}".format(key))
                index[key] = debt
    return index


def _expand(value, asset: str):
    if isinstance(value, str):
        return value.replace("{asset}", asset)
    if isinstance(value, dict):
        return {key: _expand(item, asset) for key, item in value.items()}
    return value


def materialize(root: str, policy: dict, inventory=None) -> dict:
    inventory = inventory or canonical_inventory(root)
    actual_digest = inventory_digest(inventory)
    if policy.get("acknowledged_inventory_sha256") != actual_digest:
        raise ParityError("inventory digest mismatch: review the canonical roster and acknowledge {}"
                          .format(actual_digest))
    defaults = policy.get("defaults") or {}
    overrides = policy.get("overrides") or {}
    for host, families in overrides.items():
        if host not in HOSTS:
            raise ParityError("unknown host override {}".format(host))
        for family, assets in families.items():
            if family not in FAMILIES:
                raise ParityError("unknown family override {}".format(family))
            unknown = set(assets) - set(inventory[family])
            if unknown:
                raise ParityError("override names unknown asset(s): {}".format(
                    ", ".join(sorted(unknown))))
    debts = _debt_index(root)
    expanded = {family: {} for family in FAMILIES}
    for family in FAMILIES:
        for asset in sorted(inventory[family]):
            expanded[family][asset] = {}
            for host in HOSTS:
                try:
                    row = dict(defaults[host][family])
                except (KeyError, TypeError):
                    raise ParityError("missing default for {}:{}".format(host, family))
                row.update((overrides.get(host, {}).get(family, {}).get(asset) or {}))
                row = _expand(row, asset)
                status = row.get("status")
                if status == "supported":
                    missing = [field for field in SUPPORTED_FIELDS if not row.get(field)]
                    if missing:
                        raise ParityError("supported {}:{}:{} missing {}".format(
                            family, asset, host, ", ".join(missing)))
                elif status in ("unavailable", "debt"):
                    ref = row.get("debt_ref")
                    if ref not in debts:
                        raise ParityError("{}:{}:{} has unknown debt_ref {!r}".format(
                            family, asset, host, ref))
                    debt = debts[ref]
                    row["owner"] = debt["owner"]
                    row["expires"] = debt["expires"]
                else:
                    raise ParityError("{}:{}:{} has invalid status {!r}".format(
                        family, asset, host, status))
                expanded[family][asset][host] = row
    return {"schema_version": 2, "generated": True,
            "inventory_sha256": actual_digest, "assets": expanded}


def _rendered() -> dict:
    return materialize(REPO, load_policy(POLICY))


def _write(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv[0] if argv else "check"
    try:
        current = _rendered()
        if command == "render" and len(argv) == 1:
            _write(OUTPUT, current)
        elif command == "check" and len(argv) == 1:
            with open(OUTPUT, encoding="utf-8") as fh:
                committed = json.load(fh)
            if committed != current:
                raise ParityError("generated host-parity.json is stale; run host_parity.py render")
        else:
            raise ParityError("usage: host_parity.py [check|render]")
    except (OSError, ValueError, KeyError, ParityError) as exc:
        print("host parity: REFUSED — {}".format(exc), file=sys.stderr)
        return 1
    assets = sum(len(rows) for rows in current["assets"].values())
    dispositions = sum(len(hosts) for rows in current["assets"].values()
                       for hosts in rows.values())
    print("host parity: PASS — {} assets · {} dispositions · inventory {}".format(
        assets, dispositions, current["inventory_sha256"][:12]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
