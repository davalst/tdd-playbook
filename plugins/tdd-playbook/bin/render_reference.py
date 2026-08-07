#!/usr/bin/env python3
"""Render output-only current-state documentation from existing machine authorities."""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys


class ReferenceError(RuntimeError):
    pass


PROVENANCE_INPUTS = (
    "gate-manifest.json",
    "plugins/tdd-playbook/bin/gate_plan.py",
    "docs/architecture/host-parity-policy.json",
    "docs/architecture/host-parity.json",
    "plugins/tdd-playbook/bin/host_parity.py",
    "capabilities.json",
)
OUTPUT = "docs/reference/current-state.md"
VALID_REVIEW_STATUS = ("incorporated", "open", "rejected", "verified_closed")


def file_hash(root: str, relative: str) -> str:
    digest = hashlib.sha256()
    with open(os.path.join(root, relative), "rb") as fh:
        for block in iter(lambda: fh.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def provenance_inputs(root: str) -> tuple[str, ...]:
    reviews = sorted(os.path.relpath(path, root).replace(os.sep, "/") for path in
                     glob.glob(os.path.join(root, "docs", "reviews", "*.json")))
    return PROVENANCE_INPUTS + tuple(reviews)


def _load(root: str, relative: str):
    with open(os.path.join(root, relative), encoding="utf-8") as fh:
        return json.load(fh)


def render(root: str) -> str:
    gate = _load(root, "gate-manifest.json")
    parity = _load(root, "docs/architecture/host-parity.json")
    registry = _load(root, "capabilities.json")
    suites = sorted(os.path.basename(path)[:-3] for path in
                    glob.glob(os.path.join(root, gate["suite_glob"]))
                    if os.path.isfile(path))
    fixed = [row["id"] for row in gate["fixed_stages"]]
    assets = parity.get("assets") or {}
    asset_count = sum(len(rows) for rows in assets.values())
    dispositions = {host: {"supported": 0, "unavailable": 0, "debt": 0}
                    for host in ("claude", "codex")}
    for rows in assets.values():
        for hosts in rows.values():
            for host, row in hosts.items():
                dispositions[host][row["status"]] += 1
    capabilities = registry.get("capabilities") or []
    debts = [(cap["id"], debt.get("id", "unnamed"), debt["owner"], debt["expires"])
             for cap in capabilities for debt in (cap.get("integration_debt") or [])]
    reviews = [_load(root, path) for path in provenance_inputs(root)
               if path.startswith("docs/reviews/")]
    review_findings = [finding for review in reviews for finding in review.get("findings", [])]

    lines = [
        "# Generated current state",
        "",
        "> DO NOT EDIT. This output contains machine-owned facts only; rationale and history stay in authored documents.",
        "",
        "## Provenance",
        "",
    ]
    lines.extend("- `{}` — `{}`".format(path, file_hash(root, path))
                 for path in provenance_inputs(root))
    lines.extend([
        "",
        "## Gate surface",
        "",
        "- `sh scripts/civerd_gate.sh` — **AUTHORIZING** complete local gate and CIVerd suite command.",
        "- `sh scripts/civerd_gate.sh affected --base <revision>` — **NON-AUTHORIZING** diagnostic subset; ambiguous scope falls back to full.",
        "- Discovered suites: {}. Fixed stages: {}. Total stages: {}.".format(
            len(suites), len(fixed), len(suites) + len(fixed)),
        "- Suite IDs: {}".format(", ".join("`{}`".format(item) for item in suites) or "none"),
        "- Fixed IDs: {}".format(", ".join("`{}`".format(item) for item in fixed)),
        "- Acknowledged roster digest: `{}`".format(gate["acknowledged_roster_sha256"]),
        "",
        "## Host parity",
        "",
        "- Canonical assets: {}. Exact host dispositions: {}.".format(asset_count, asset_count * 2),
        "- Claude: {} supported, {} unavailable, {} debt.".format(
            dispositions["claude"]["supported"], dispositions["claude"]["unavailable"],
            dispositions["claude"]["debt"]),
        "- Codex: {} supported, {} unavailable, {} debt.".format(
            dispositions["codex"]["supported"], dispositions["codex"]["unavailable"],
            dispositions["codex"]["debt"]),
        "- Acknowledged inventory digest: `{}`".format(parity["inventory_sha256"]),
        "",
        "## Capability registry",
        "",
        "- Registered capabilities: {}. Owned dated integration-debt entries: {}.".format(
            len(capabilities), len(debts)),
    ])
    lines.extend("- `{}/{}` — owner `{}`, expires `{}`".format(*row) for row in debts)
    lines.extend([
        "",
        "## Adversarial review records",
        "",
        "- Review records: {}. Findings: {}.".format(len(reviews), len(review_findings)),
    ])
    for status in sorted(VALID_REVIEW_STATUS):
        count = sum(1 for finding in review_findings if finding.get("status") == status)
        lines.append("- `{}`: {}".format(status, count))
    return "\n".join(lines) + "\n"


def check(root: str) -> list[str]:
    target = os.path.join(root, OUTPUT)
    try:
        expected = render(root)
        with open(target, encoding="utf-8") as fh:
            actual = fh.read()
    except (OSError, ValueError, KeyError) as exc:
        return [str(exc)]
    return [] if actual == expected else ["generated reference is stale; run render_reference.py render"]


def _write(root: str) -> None:
    target = os.path.join(root, OUTPUT)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    temp = target + ".tmp"
    with open(temp, "w", encoding="utf-8") as fh:
        fh.write(render(root))
    os.replace(temp, target)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    command = argv[0] if argv else "check"
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    try:
        if command == "render" and len(argv) == 1:
            _write(root)
        elif command == "check" and len(argv) == 1:
            problems = check(root)
            if problems:
                raise ReferenceError("; ".join(problems))
        else:
            raise ReferenceError("usage: render_reference.py [check|render]")
    except (OSError, ValueError, KeyError, ReferenceError) as exc:
        print("reference docs: REFUSED — {}".format(exc), file=sys.stderr)
        return 1
    print("reference docs: PASS — provenance and generated current state agree")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
