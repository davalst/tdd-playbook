#!/usr/bin/env python3
"""Capability registry — make darkness enumerable (Playbook §6a).

The meta-bug this tool exists for (origin: the Cheliped feature-wiring audit, 2026-07):
every health surface reported only on things that RAN, so a feature that was built but
never wired — or wired but gated off — read as "healthy, no runs recorded yet". Dead and
quiet were indistinguishable. The fix is structural: keep a small machine-readable registry
of what SHOULD run (`capabilities.json`), and enumerate FROM it, never from runtime traces.

Subcommands:
  validate  — schema + wiring rules; exit 1 on any violation. Rules:
                R-SCHEMA      required fields present and well-typed
                R-DUP         capability ids are unique
                R-DARK        activation.default=off REQUIRES a named user-reachable switch
                R-WRITE-ONLY  every emitted topic names >=1 consumer ("nobody yet" is debt,
                              not a design)
                R-DEBT        integration_debt entries carry what/owner/expires; an EXPIRED
                              entry FAILS (same teeth as §7 flaky quarantine — a loan, not
                              a landfill)
  doctor    — human report: dark features + their on-switch, write-only emitters, debt
              expiring/expired, capabilities with no liveness probe, topics consumed but
              never emitted. Exit 0 (report), or 1 with --strict if validate would fail.
  init      — write a starter capabilities.json (refuses to overwrite).

Registry rules of the road: the file only GROWS (removing an entry means the capability was
deliberately parked or deleted — say which in the commit); registering a new deliverable
here is part of its Tripwire WIRED proof (§6).

Stdlib-only. Default registry path: <base>/capabilities.json, falling back to
<base>/.claude/capabilities.json.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys

REQUIRED_FIELDS = ("id", "summary", "surfaces", "activation", "wired_by", "exercised_by")
DEBT_FIELDS = ("what", "owner", "expires")
DEBT_WARN_DAYS = 14

TEMPLATE = {
    "version": 1,
    "capabilities": [
        {
            "id": "example-subsystem",
            "summary": "One line: what the user gets from this capability.",
            "surfaces": ["cli"],
            "activation": {"default": "on"},
            "wired_by": ["src/app.py::build_app"],
            "exercised_by": ["tests/test_assembly.py::test_example_reachable"],
            "emits": [{"topic": "events.example_done", "consumers": ["example-consumer"]}],
            "consumes": [],
            "liveness": {"max_quiet_days": 30, "probe": "planted-event canary"},
            "integration_debt": [],
        }
    ],
}


def find_registry(base: str, explicit: str | None = None) -> str | None:
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    for rel in ("capabilities.json", os.path.join(".claude", "capabilities.json")):
        p = os.path.join(base, rel)
        if os.path.isfile(p):
            return p
    return None


def load_registry(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


def _parse_date(s):
    try:
        return _dt.date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def validate(reg: dict, today: _dt.date | None = None) -> list[str]:
    """Return a list of violations, each 'R-RULE <cap-id>: detail'. Empty = clean."""
    today = today or _dt.date.today()
    out: list[str] = []
    caps = reg.get("capabilities")
    if not isinstance(caps, list) or not caps:
        return ["R-SCHEMA <registry>: 'capabilities' must be a non-empty list"]

    seen: set[str] = set()
    for i, cap in enumerate(caps):
        if not isinstance(cap, dict):
            out.append("R-SCHEMA <#%d>: capability entries must be objects" % i)
            continue
        cid = cap.get("id") or "<#%d>" % i
        for f in REQUIRED_FIELDS:
            if not cap.get(f):
                out.append("R-SCHEMA %s: missing/empty required field '%s'" % (cid, f))
        if cap.get("id"):
            if cid in seen:
                out.append("R-DUP %s: duplicate capability id" % cid)
            seen.add(cid)

        act = cap.get("activation") or {}
        default = act.get("default")
        if default not in ("on", "off"):
            out.append("R-SCHEMA %s: activation.default must be 'on' or 'off'" % cid)
        elif default == "off" and not (act.get("switch") or "").strip():
            out.append("R-DARK %s: default=off with NO named on-switch — dark by "
                       "construction; name the user-reachable switch or ship it on" % cid)

        for j, em in enumerate(cap.get("emits") or []):
            topic = (em or {}).get("topic") or "<emit #%d>" % j
            if not (em or {}).get("consumers"):
                out.append("R-WRITE-ONLY %s: emits '%s' with no named consumer — a "
                           "write-only loop; name the reader or file integration debt"
                           % (cid, topic))

        for j, debt in enumerate(cap.get("integration_debt") or []):
            label = "%s debt #%d" % (cid, j)
            missing = [f for f in DEBT_FIELDS if not (debt or {}).get(f)]
            if missing:
                out.append("R-DEBT %s: missing %s" % (label, "/".join(missing)))
                continue
            exp = _parse_date(debt["expires"])
            if exp is None:
                out.append("R-DEBT %s: expires '%s' is not YYYY-MM-DD"
                           % (label, debt["expires"]))
            elif exp < today:
                out.append("R-DEBT %s: EXPIRED %s (owner: %s) — '%s'; pay it down, "
                           "re-date it with a reason, or park the capability loudly"
                           % (label, debt["expires"], debt["owner"], debt["what"]))
    return out


def doctor(reg: dict, today: _dt.date | None = None) -> str:
    """Human report. Enumerates from what SHOULD run; darkness is a first-class state."""
    today = today or _dt.date.today()
    caps = [c for c in reg.get("capabilities", []) if isinstance(c, dict)]
    lines: list[str] = ["capability doctor — %d registered capabilities" % len(caps)]

    dark = [c for c in caps if (c.get("activation") or {}).get("default") == "off"]
    lines.append("\n[dark by default: %d]" % len(dark))
    for c in dark:
        sw = (c.get("activation") or {}).get("switch") or "!! NO ON-SWITCH !!"
        lines.append("  %-28s on-switch: %s" % (c.get("id"), sw))

    write_only = [(c.get("id"), (em or {}).get("topic"))
                  for c in caps for em in (c.get("emits") or [])
                  if not (em or {}).get("consumers")]
    lines.append("\n[write-only emitters: %d]" % len(write_only))
    for cid, topic in write_only:
        lines.append("  %-28s emits '%s' → nobody reads it" % (cid, topic))

    lines.append("\n[integration debt]")
    any_debt = False
    for c in caps:
        for debt in (c.get("integration_debt") or []):
            exp = _parse_date((debt or {}).get("expires", ""))
            state = ("EXPIRED" if exp and exp < today
                     else "due soon" if exp and (exp - today).days <= DEBT_WARN_DAYS
                     else "open")
            lines.append("  %-28s [%s] %s (owner: %s, expires: %s)"
                         % (c.get("id"), state, (debt or {}).get("what"),
                            (debt or {}).get("owner"), (debt or {}).get("expires")))
            any_debt = True
    if not any_debt:
        lines.append("  none")

    no_liveness = [c.get("id") for c in caps if not c.get("liveness")]
    lines.append("\n[no liveness probe (staleness undetectable): %d]" % len(no_liveness))
    for cid in no_liveness:
        lines.append("  %s" % cid)

    emitted = {(em or {}).get("topic") for c in caps for em in (c.get("emits") or [])}
    orphans = [(c.get("id"), t) for c in caps for t in (c.get("consumes") or [])
               if t not in emitted]
    lines.append("\n[consumed but never emitted (check the seam): %d]" % len(orphans))
    for cid, topic in orphans:
        lines.append("  %-28s consumes '%s' — no registered emitter" % (cid, topic))
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("validate", "doctor", "init"))
    ap.add_argument("--base", default=".", help="repo root (default: cwd)")
    ap.add_argument("--registry", default=None, help="explicit path to capabilities.json")
    ap.add_argument("--strict", action="store_true",
                    help="doctor: exit 1 if validate would fail")
    args = ap.parse_args(argv)
    base = os.path.abspath(args.base)

    if args.command == "init":
        path = args.registry or os.path.join(base, "capabilities.json")
        if os.path.exists(path):
            sys.stderr.write("refusing to overwrite existing %s\n" % path)
            return 2
        with open(path, "w") as fh:
            json.dump(TEMPLATE, fh, indent=2)
            fh.write("\n")
        print("wrote starter registry: %s" % path)
        return 0

    path = find_registry(base, args.registry)
    if path is None:
        sys.stderr.write("no capabilities.json found under %s — run `init` to seed one; "
                         "a repo with no registry cannot enumerate its own darkness\n" % base)
        return 2
    try:
        reg = load_registry(path)
    except (json.JSONDecodeError, OSError) as e:
        sys.stderr.write("cannot read %s: %s\n" % (path, e))
        return 2

    violations = validate(reg)
    if args.command == "validate":
        for v in violations:
            print("VIOLATION " + v)
        print("capability_registry: %s (%d violation(s), %d capabilities)"
              % ("FAIL" if violations else "OK", len(violations),
                 len(reg.get("capabilities", []))))
        return 1 if violations else 0

    print(doctor(reg))
    if violations:
        print("\n[validate: %d violation(s) — run `validate` for details]" % len(violations))
    return 1 if (args.strict and violations) else 0


if __name__ == "__main__":
    sys.exit(main())
