#!/usr/bin/env python3
"""deliberation — David's verbs over the capture store (briefs D3).

The store is EVENT-SOURCED: `close` APPENDS a closure record, it never rewrites a line —
effective status derives from the presence of closure records (missing = open). This verb
is deliberately the ONLY emitter of the closure shape; hooks/scripts/capture.py has no code
path that can produce one (pinned by test_capture). Closing is David's word — conveyed is
never ratified.

    deliberation.py close --session <id> [--note TEXT]
    deliberation.py close --day YYYY-MM-DD [--note TEXT]
    deliberation.py stats

Store resolution, schema, and the append primitive are OWNED by capture.py (imported via
the hooks/scripts sys.path shim — same layout in the plugin and in vendored .claude/
copies). Stdlib-only by repo invariant.
"""
import argparse
import datetime
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "hooks", "scripts"))
import capture  # noqa: E402


def cmd_close(args):
    if bool(args.session) == bool(args.day):
        sys.stderr.write("deliberation: close needs exactly one of --session / --day\n")
        return 1
    scope = {"session_id": args.session} if args.session else {"day": args.day}
    rec = {"ts": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
           "schema": capture.SCHEMA, "closure": scope, "note": args.note or ""}
    capture.append_record(capture.store_dir(), rec)
    print("deliberation: closure appended for {}".format(scope))
    return 0


def cmd_stats(args):
    store = capture.store_dir()
    days = sorted(glob.glob(os.path.join(store, "????-??-??.jsonl")))
    if not days:
        print("deliberation stats: 0 records, 0 bytes (store: {})".format(store))
        return 0
    t_rec = t_bytes = t_red = t_close = 0
    for path in days:
        n = red = closes = 0
        for ln in open(path):
            if not ln.strip():
                continue
            n += 1
            rec = json.loads(ln)
            red += rec.get("redactions") or 0
            closes += 1 if "closure" in rec else 0
        b = os.path.getsize(path)
        print("{}: {} records, {} bytes, {} redactions, {} closures".format(
            os.path.basename(path)[:-6], n, b, red, closes))
        t_rec += n
        t_bytes += b
        t_red += red
        t_close += closes
    print("total: {} records, {} bytes, {} redactions, {} closures (store: {})".format(
        t_rec, t_bytes, t_red, t_close, store))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    cl = sub.add_parser("close", help="append a closure record (David's word; event-sourced)")
    cl.add_argument("--session", help="session_id to close")
    cl.add_argument("--day", help="YYYY-MM-DD to close")
    cl.add_argument("--note", help="why / what was reviewed")
    sub.add_parser("stats", help="records/bytes/redactions per day — the measured volume")
    args = ap.parse_args(argv)
    return cmd_close(args) if args.cmd == "close" else cmd_stats(args)


if __name__ == "__main__":
    sys.exit(main())
