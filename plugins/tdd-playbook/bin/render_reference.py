#!/usr/bin/env python3
"""Render output-only current-state documentation from existing machine authorities."""
from __future__ import annotations

import glob
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from review_ledger import (VALID_STATUS as VALID_REVIEW_STATUS,  # noqa: E402  (sibling; the one status-vocabulary owner)
                           participation_report, record_authoring_briefs,
                           recurrence_report)
from host_parity import agents_roster  # noqa: E402  (sibling; vendored together)


class ReferenceError(RuntimeError):
    pass


PROVENANCE_INPUTS = (
    "gate-manifest.json",
    "plugins/tdd-playbook/bin/gate_plan.py",
    "docs/architecture/host-parity-policy.json",
    "docs/architecture/host-parity.json",
    "plugins/tdd-playbook/bin/host_parity.py",
    "capabilities.json",
    # D3 (recurrence-epoch plan, 2026-08-20): the guard-state inventory below is derived
    # from the catalog rows and from each hook's SHIPPED default mode, so both are named
    # here. A rendered fact whose source is unlisted is a fact with no provenance.
    "docs/HACK_CATALOG.md",
    "plugins/tdd-playbook/hooks/scripts/_common.py",
)
OUTPUT = "docs/reference/current-state.md"


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


def _debt_key(cap_id: str, debt: dict) -> str:
    """`cap/id` when the optional id exists (a cross-file join key), bare `cap` when not."""
    return "{}/{}".format(cap_id, debt["id"]) if debt.get("id") else cap_id


def _first_clause(text: str, limit: int = 120) -> str:
    """First clause of a debt's `what`, shortening VISIBLY (§12 — never silent)."""
    cuts = [i for sep in (". ", ": ", "; ") for i in (text.find(sep),) if 0 < i < limit]
    if cuts:
        clause = text[:min(cuts)]
        return clause + ("…" if clause != text else "")
    if len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text


def _load(root: str, relative: str):
    with open(os.path.join(root, relative), encoding="utf-8") as fh:
        return json.load(fh)


def review_section(reviews: list[dict], root: str | None = None) -> list[str]:
    """The adversarial-review lines. When no finding has ever been rejected, that fact is
    a SENTENCE, not a `0` a reader's eye slides past (the /readable business-owner test).
    Printed, not interpreted: whether the zero is a rubber-stamp signal or a schema fact
    (rejections may live in advisory dispositions, not these records) stays an open
    question this generator does not answer."""
    findings = [finding for review in reviews for finding in review.get("findings", [])]
    lines = [
        "",
        "## Adversarial review records",
        "",
        "- Review records: {}. Findings: {}.".format(len(reviews), len(findings)),
    ]
    for status in sorted(VALID_REVIEW_STATUS):
        count = sum(1 for finding in findings if finding.get("status") == status)
        lines.append("- `{}`: {}".format(status, count))
    if findings and not any(finding.get("status") == "rejected" for finding in findings):
        lines.append("- No finding has ever been rejected.")
    # D4 (adversary-accountability, 2026-08-17): recorded participation lands HERE, not
    # only in `review_ledger.py recurrence`. That verb's reader is run_calibration, which
    # is opt-in and triggered by "a verifier misbehaves" — and an agent named in no record
    # cannot misbehave, so the report would have been dark in exactly the case it exists
    # to show. This file is regenerated at every release, so the inventory is READ.
    if root is not None:
        lines.append("")
        for line in participation_report(reviews, agents_roster(root),
                                         record_authoring_briefs(root)):
            lines.append("- " + line.strip() if line.startswith("  ") else line)
    # D3 (recurrence-epoch plan, 2026-08-20): the guard-state inventory lands here for the
    # SAME reason participation does — `recurrence`'s only code consumer is run_calibration,
    # which CLAUDE.md declares unscheduled and opt-in, so a report fixed there would still
    # be dark. This file regenerates at every release, so the inventory is READ.
    #
    # Safe to render because every state is a pure function of the tree: the epoch is a
    # constant, and hook liveness is the SHIPPED default, never resolve_mode() — which reads
    # env vars and break-glass state and would make this committed file machine-dependent.
    lines.append("")
    lines.extend(recurrence_report(reviews))
    return lines


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
    # H1 (v1.33.1): the label comes from the REQUIRED `what` (_debt.py DEBT_FIELDS), never
    # from the optional `id` — keying on `id` fabricated `unnamed` for 51 of 55 entries.
    # When an `id` exists the `cap/id` join key is KEPT: host-parity-policy.json cites
    # three of those keys by value, so fixing the label must not discard the reference.
    debts = [(_debt_key(cap["id"], debt), _first_clause(debt["what"]),
              debt["owner"], debt["expires"])
             for cap in capabilities for debt in (cap.get("integration_debt") or [])]
    reviews = [_load(root, path) for path in provenance_inputs(root)
               if path.startswith("docs/reviews/") and not path.endswith("/index.json")]

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
        "- Acknowledged execution-manifest digest: `{}`".format(gate["acknowledged_plan_sha256"]),
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
    lines.extend("- `{}` — {} (owner `{}`, expires `{}`)".format(*row) for row in debts)
    lines.extend(review_section(reviews, root))
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
