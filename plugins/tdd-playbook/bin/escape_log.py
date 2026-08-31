#!/usr/bin/env python3
"""Escape ledger — WHO CAUGHT IT, the §13 discovery-path split, made mechanical.

§13 has said since v1.x to grade each caught defect by discovery path, calling a defect the
human caught in output already declared green "the loudest signal there is". An exhaustive
sweep on 2026-08-30 found the rule written in exactly one place (SKILL.md) and read by ZERO
code. This is that reader.

Why it is the metric that matters: gate_yield.py counts what the guards COST (blocks, warns,
overrides). Nothing counted what they SAVED, or what got past them. Cost without benefit
cannot answer "is this worth it" — it can only ever argue for less.

Not gameable in the direction that matters: `human` rows are minted in response to David
saying so. The agent cannot quietly omit one without the omission happening in front of him.

    escape_log.py record --what "..." --caught-by human --where <ref> [--declared-green]
    escape_log.py report [--since YYYY-MM-DD]

Paths: `oracle` (a mechanical check went red on the real defect — best), `accident` (a check
went red on CORRECT code and the defect was noticed while investigating — a weak check, not
diligence), `human` (David), `peer` (another session / cross-repo report).
"""
import argparse, collections, json, os, sys, datetime

PATHS = ("oracle", "accident", "human", "peer")


def store():
    root = os.environ.get("TDD_PLAYBOOK_YIELD_LOG")
    if root:
        return root
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        if os.path.isdir(os.path.join(here, ".git")):
            break
        here = os.path.dirname(here)
    return os.path.join(here, ".claude", "playbook-yield.jsonl")


def rows(since=None):
    p = store()
    if not os.path.isfile(p):
        return []
    out = []
    with open(p) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("event") != "escape":
                continue
            if since and str(d.get("ts", ""))[:10] < since:
                continue
            out.append(d)
    return out


def cmd_record(a):
    if a.caught_by not in PATHS:
        print("escape_log: --caught-by must be one of %s" % (PATHS,), file=sys.stderr)
        return 2
    row = {"event": "escape", "ts": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "what": a.what, "caught_by": a.caught_by, "where": a.where or "",
           "declared_green": bool(a.declared_green)}
    p = store()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "a") as fh:
        fh.write(json.dumps(row) + "\n")
    print("escape_log: recorded %s (%s)" % (a.caught_by, a.what[:60]))
    return 0


def cmd_report(a):
    rs = rows(a.since)
    if not rs:
        print("escape_log: no escapes recorded%s — that is an EMPTY DENOMINATOR, not a clean "
              "record" % (" since " + a.since if a.since else ""))
        return 0
    c = collections.Counter(r["caught_by"] for r in rs)
    green = sum(1 for r in rs if r.get("declared_green"))
    print("Escapes: %d total%s" % (len(rs), " since " + a.since if a.since else ""))
    for k in PATHS:
        print("  %-9s %d" % (k, c.get(k, 0)))
    caught_by_us = c.get("oracle", 0)
    caught_by_them = c.get("human", 0) + c.get("peer", 0)
    print("  ── self-caught %d : %d caught by a person" % (caught_by_us, caught_by_them))
    if caught_by_them >= caught_by_us:
        print("  VERDICT: the net is NOT catching — a person is finding as much as the "
              "machinery is.")
    else:
        print("  VERDICT: machinery ahead of the person, %.1fx" %
              (caught_by_us / max(caught_by_them, 1)))
    print("  %d of these were in work already DECLARED GREEN (the loudest signal, §13)" % green)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="escape_log.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("--what", required=True)
    r.add_argument("--caught-by", required=True, dest="caught_by")
    r.add_argument("--where", default="")
    r.add_argument("--declared-green", action="store_true", dest="declared_green")
    r.set_defaults(fn=cmd_record)
    q = sub.add_parser("report")
    q.add_argument("--since")
    q.set_defaults(fn=cmd_report)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
