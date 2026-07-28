#!/usr/bin/env python3
"""check_staleness — make the calibration cadence a MECHANISM, not a memory (audit finding F5).

CLAUDE.md's standing requirement says the calibration scoreboard must show a live cadence, and to
"raise it with David if history.md's last entry is stale >14 days." That was enforced only by a
human remembering. This makes it deterministic: read docs/calibration/history.md, find the most
recent dated run, and FAIL LOUDLY if it is missing or older than the threshold. A decaying gate
whose decay nobody is forced to notice has been asleep for an unknown duration (§13).

    check_staleness.py [--history PATH] [--max-age-days 14] [--as-of YYYY-MM-DD] [--warn-only]

Exit 0 = fresh (last run within the window). Exit 1 = STALE or never calibrated. Exit 2 = bad
invocation. --as-of injects "today" so tests are deterministic (never the real clock). --warn-only
prints the finding but exits 0 (advisory use inside a release gate that shouldn't hard-block).
"""
import argparse
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
sys.path.insert(0, HERE)
# The ONE owner of the scoreboard format (D0) — this gate previously carried its own date
# regex, and that private copy would have read a run of INVALID rows as "fresh". The shared
# parser skips INVALID: a run where nothing was calibrated never extends freshness.
from history_format import latest_run_date  # noqa: E402

DEFAULT_HISTORY = os.path.join(REPO, "docs", "calibration", "history.md")


def evaluate(history_path, as_of, max_age_days):
    """Return (fresh: bool, reason: str, age_days: int|None)."""
    if not os.path.isfile(history_path):
        return (False, "never_calibrated", None)
    with open(history_path, encoding="utf-8") as fh:
        latest = latest_run_date(fh.read())
    if latest is None:
        return (False, "never_calibrated", None)
    age = (as_of - latest).days
    if age < 0:
        # A future-dated last run can't extend freshness — treat as a broken scoreboard.
        return (False, "future_dated", age)
    if age > max_age_days:
        return (False, "stale", age)
    return (True, "fresh", age)


def _parse_as_of(s):
    y, m, d = (int(x) for x in s.split("-"))
    return date(y, m, d)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="check_staleness.py", description=__doc__.splitlines()[0])
    ap.add_argument("--history", default=DEFAULT_HISTORY)
    ap.add_argument("--max-age-days", type=int, default=14)
    ap.add_argument("--as-of", default=None, help="YYYY-MM-DD; defaults to today (real clock)")
    ap.add_argument("--warn-only", action="store_true")
    args = ap.parse_args(argv)

    try:
        as_of = _parse_as_of(args.as_of) if args.as_of else date.today()
    except (ValueError, AttributeError):
        print("check_staleness: bad --as-of (want YYYY-MM-DD)", file=sys.stderr)
        return 2

    fresh, reason, age = evaluate(args.history, as_of, args.max_age_days)
    if fresh:
        print("calibration FRESH — last run {} day(s) ago (<= {})".format(age, args.max_age_days))
        return 0

    detail = {
        "never_calibrated": "no dated run in {}".format(args.history),
        "future_dated": "last run is future-dated — scoreboard is broken",
        "stale": "last run {} day(s) ago (> {}); run python3 calibration/run_calibration.py".format(
            age, args.max_age_days),
    }[reason]
    print("calibration {} [{}] — {}".format(
        "STALE" if reason != "never_calibrated" else "NEVER CALIBRATED", reason, detail),
        file=sys.stderr)
    return 0 if args.warn_only else 1


if __name__ == "__main__":
    sys.exit(main())
