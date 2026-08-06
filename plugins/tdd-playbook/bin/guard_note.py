#!/usr/bin/env python3
"""guard_note — record what happened AFTER a guard blocked you (Playbook §12, v1.28).

WHY THIS EXISTS. A guard block leaves a mechanical trace (every hook exits through
`_common.emit`, which logs it). What the block *led to* leaves none — and the two possible
outcomes are behaviourally identical from outside:

    the guard blocked a compound command -> I dropped the offending part and re-ran the rest
    the guard blocked a compound command -> I split it up until something got through

The first is compliance. The second is the H-class "write around the guard" move the lock
exists to stop. In the 2026-08-05/06 session David asked which one he had just watched, and
answering took a hand-audit of the unlock journal, the lock state, git history and four
transcript moments. That is not a control; it is archaeology. This tool makes the answer a
record.

THE THREE CLAUSES, at every guard block:
    --objected            what the guard actually objected to;
    --performed-elsewhere whether that action was performed by ANY other route (yes|no);
    --dropped             what was dropped or changed instead.
If `--performed-elsewhere yes` is ever true, that is a FINDING, not a footnote — the rollup
alarms on it by name.

WHY A SELF-REPORT IS WORTH ANYTHING HERE. It is paired with a count nobody self-reports: the
HOOK writes the blocks, the agent writes only the responses, and `gate_yield rollup` prints
`blocks N · accounted M · UNACCOUNTED N-M` per gate per cycle. An agent that stays silent
does not produce a clean record — it produces a visible unaccounted count. Self-report can
move the numerator; it cannot touch the denominator.

Rows ride the ONE existing write path (`hooks/scripts/_common.log_yield_event`) so this can
never become a second, drifting telemetry pipeline — and they are stamped `source: "agent"`
so a reader can always tell a self-report from a mechanical observation.

Stdlib-only. Exit 0 recorded · 2 usage.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "hooks", "scripts"))
try:
    from _common import log_yield_event
except ImportError:  # vendored trees keep the same layout; fail loudly, never silently
    log_yield_event = None


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="guard_note",
        description="Record the three-clause response to a guard block (Playbook §12).")
    sub = ap.add_subparsers(dest="command", required=True)
    rec = sub.add_parser("record", help="record one guard-block response")
    rec.add_argument("--gate", required=True,
                     help="the guard that fired, as it names itself (testlock, overmock, ...)")
    rec.add_argument("--objected", required=True,
                     help="what the guard actually objected to")
    rec.add_argument("--performed-elsewhere", required=True,
                     help="yes|no — was that action performed by ANY other route? "
                          "'yes' is a finding, and the rollup alarms on it")
    rec.add_argument("--dropped", required=True,
                     help="what was dropped or changed instead")
    args = ap.parse_args(argv)

    elsewhere = str(args.performed_elsewhere).strip().lower()
    if elsewhere not in ("yes", "no"):
        print("guard_note: --performed-elsewhere must be exactly 'yes' or 'no' (got {!r}) — "
              "the whole point is a two-valued answer nobody can hedge; exit 2 is usage, "
              "never proof".format(args.performed_elsewhere), file=sys.stderr)
        return 2
    for field in ("objected", "dropped"):
        if not str(getattr(args, field)).strip():
            print("guard_note: --{} must not be empty — an unexplained block is the thing "
                  "this record exists to prevent".format(field), file=sys.stderr)
            return 2
    if log_yield_event is None:
        print("guard_note: cannot reach hooks/scripts/_common.py — the response was NOT "
              "recorded (failing loudly rather than pretending it was)", file=sys.stderr)
        return 2

    log_yield_event(args.gate, "response", {
        "objected": args.objected,
        "performed_elsewhere": elsewhere,
        "dropped": args.dropped,
    }, source="agent")
    note = "" if elsewhere == "no" else "  ** performed elsewhere: this is a FINDING **"
    print("guard_note: recorded a response for '{}' (performed_elsewhere={}){}".format(
        args.gate, elsewhere, note))
    return 0


if __name__ == "__main__":
    sys.exit(main())
