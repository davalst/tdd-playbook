#!/usr/bin/env python3
"""Capability registry — make darkness enumerable (Playbook §6a).

The meta-bug this tool exists for (origin: a full-platform feature-wiring audit of a
production multi-surface agent system, 2026-07):
every health surface reported only on things that RAN, so a feature that was built but
never wired — or wired but gated off — read as "healthy, no runs recorded yet". Dead and
quiet were indistinguishable. The fix is structural: keep a small machine-readable registry
of what SHOULD run (`capabilities.json`), and enumerate FROM it, never from runtime traces.

Subcommands:
  validate  — schema + wiring rules; exit 1 on any violation. Rules:
                R-SCHEMA      required fields present and well-typed; the optional
                              capability-level `user_facing` AUDIENCE fact (v1.24 —
                              §6c's companion rule keys on it; `surfaces` is deployment
                              hosts, not an audience) must be a bool when present
                R-DUP         capability ids are unique
                R-DARK        activation.default=off REQUIRES a named user-reachable switch
                R-WRITE-ONLY  every emitted topic names >=1 consumer ("nobody yet" is debt,
                              not a design)
                R-DEBT        integration_debt entries carry what/owner/expires; an EXPIRED
                              entry FAILS (same teeth as §7 flaky quarantine — a loan, not
                              a landfill)
                R-DEPLOY      a capability with a deploy_surface (runs elsewhere: VPS, daemon,
                              vendored copy) MUST name a running_version_probe — else the
                              deployed version can drift from HEAD undetected (§6 RUNNING leg)
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _debt  # noqa: E402  (the ONE house debt-date implementation, vendored alongside)

REQUIRED_FIELDS = ("id", "summary", "surfaces", "activation", "wired_by", "exercised_by")
DEBT_FIELDS = _debt.DEBT_FIELDS
# A capability whose execution host is NOT this repo/process (a VPS, a daemon, a vendored copy in
# another repo) declares a deploy_surface. running_version_probe is load-bearing: without a way to
# assert the deployed version == the intended one, the deliverable can drift (the "97-minutes-behind"
# class) while every other Tripwire leg passes about the laptop. See SKILL.md §6 RUNNING leg.
DEPLOY_FIELDS = ("runs_on", "gets_there_by", "running_version_probe", "divergence")
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


_parse_date = _debt.parse_date  # one debt shape, one date logic (v1.24 D10 extraction)


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

        ds = cap.get("deploy_surface")
        if ds is not None:
            if not isinstance(ds, dict):
                out.append("R-DEPLOY %s: deploy_surface must be an object" % cid)
            else:
                if not (ds.get("running_version_probe") or "").strip():
                    out.append("R-DEPLOY %s: remote deploy_surface with NO "
                               "running_version_probe — the deployed version can drift from the "
                               "intended one undetected (§6 RUNNING); name the probe" % cid)
                other = [f for f in DEPLOY_FIELDS
                         if f != "running_version_probe" and not (ds.get(f) or "").strip()]
                if other:
                    out.append("R-DEPLOY %s: deploy_surface missing %s (runs where / gets there "
                               "how / who notices divergence)" % (cid, "/".join(other)))

        for j, debt in enumerate(cap.get("integration_debt") or []):
            label = "%s debt #%d" % (cid, j)
            out.extend("R-DEBT %s" % p for p in _debt.debt_problems(debt, today, label))

        # v1.24 (D12b): optional capability-level AUDIENCE fact. §6c's companion rule keys
        # on this ("an exemption naming a user-facing flow FAILS") — `surfaces` is
        # deployment hosts, not an audience fact, so it can never carry that rule. If
        # present it must be a real bool: a truthy string would make the companion rule
        # fire on garbage.
        if "user_facing" in cap and not isinstance(cap["user_facing"], bool):
            out.append("R-SCHEMA %s: user_facing must be a bool (audience fact), got %r"
                       % (cid, cap["user_facing"]))
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
            state = ("EXPIRED" if _debt.is_expired((debt or {}).get("expires", ""), today)
                     else "due soon" if exp and (exp - today).days <= DEBT_WARN_DAYS
                     else "open")
            lines.append("  %-28s [%s] %s (owner: %s, expires: %s)"
                         % (c.get("id"), state, (debt or {}).get("what"),
                            (debt or {}).get("owner"), (debt or {}).get("expires")))
            any_debt = True
    if not any_debt:
        lines.append("  none")

    remote = [c for c in caps if c.get("deploy_surface")]
    lines.append("\n[remote deploy surfaces (running != intended is a drift risk): %d]"
                 % len(remote))
    for c in remote:
        ds = c.get("deploy_surface") or {}
        probe = (ds.get("running_version_probe") or "").strip() or "!! NO VERSION PROBE — drift undetectable !!"
        lines.append("  %-28s runs_on: %s | probe: %s"
                     % (c.get("id"), ds.get("runs_on") or "?", probe))

    # The header says "no liveness PROBE"; this used to test only that a `liveness` OBJECT
    # existed, so a capability declaring {"max_quiet_days": 30} and nothing else was reported
    # as probe-covered. A check literally true while describing something other than what you
    # need (§1). Found 2026-08-09 when `independent-gate-rerun` — whose own debt says "it has
    # never executed on GitHub" — was certified as having a probe.
    no_liveness = [c.get("id") for c in caps
                   if not (c.get("liveness") or {}).get("probe")
                   and not (c.get("deploy_surface") or {}).get("running_version_probe")]
    lines.append("\n[no liveness probe (staleness undetectable): %d]" % len(no_liveness))
    for cid in no_liveness:
        lines.append("  %s" % cid)

    emitted = {(em or {}).get("topic") for c in caps for em in (c.get("emits") or [])}

    def _consume_topic(entry):
        # `consumes` entries are either a bare topic string or the same dict
        # shape `emits` uses ({"topic": ..., "producer": ...}).
        return (entry or {}).get("topic") if isinstance(entry, dict) else entry

    orphans = [(c.get("id"), topic) for c in caps for t in (c.get("consumes") or [])
               if (topic := _consume_topic(t)) and topic not in emitted]
    lines.append("\n[consumed but never emitted (check the seam): %d]" % len(orphans))
    for cid, topic in orphans:
        lines.append("  %-28s consumes '%s' — no registered emitter" % (cid, topic))

    # Deliberation capture (briefs D3): informational, NON-demoting — capture is not a
    # finding-bearing guard, so an off state is a fact to surface, never a muzzled-gate
    # event. This line exists so "is it recording?" is always answerable on any machine.
    lines.append("\n[deliberation capture]")
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                        "..", "hooks", "scripts"))
        import capture as _capture
        on, store, n = _capture.status()
        if on:
            lines.append("  capture: ON (store: %s, %d records today)" % (store, n))
        else:
            lines.append("  capture: OFF (opt-in: touch %s)"
                         % os.path.join(store, "ENABLED"))
    except Exception:
        lines.append("  capture: UNKNOWN (capture.py not vendored alongside this registry)")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=("validate", "doctor", "init"))
    ap.add_argument("--base", default=".", help="repo root (default: cwd)")
    ap.add_argument("--registry", default=None, help="explicit path to capabilities.json")
    ap.add_argument("--strict", action="store_true",
                    help="doctor: exit 1 if validate would fail")
    ap.add_argument("--as-of", default=None, metavar="YYYY-MM-DD",
                    help="evaluate debt expiries as of this date instead of today — the "
                         "deterministic way to PROVE a deferral's trigger fires "
                         "(`validate --as-of <expiry+1>` must exit 1, meaning EXPIRED; "
                         "exit 2 is usage, never proof)")
    args = ap.parse_args(argv)
    base = os.path.abspath(args.base)
    as_of = None
    if args.as_of is not None:
        as_of = _parse_date(args.as_of)
        if as_of is None:
            sys.stderr.write("capability_registry: bad --as-of (want YYYY-MM-DD)\n")
            return 2

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

    violations = validate(reg, today=as_of)
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
