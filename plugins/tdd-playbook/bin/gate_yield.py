#!/usr/bin/env python3
"""gate_yield — the retirement instrument (R4-lean, §13's second decay direction).

§13 instruments one decay direction: gates getting WEAKER than the threat (calibration).
This instruments the other: gates getting MORE EXPENSIVE than the risk. A playbook that only
accretes is itself a decaying asset — decaying in the direction the calibration suite cannot
see, because recall measured without cost looks like health.

Derived from EXHAUST, never self-report (§13): the single event log that _common.emit()
(every guard's one exit path) and tdd_lock's journaled unlocks already write. No new
telemetry pipeline.

    gate_yield.py rollup [--date D]   # aggregate the raw log -> ONE committed row per gate
                                      # per cycle in docs/calibration/gate_yield.md, then
                                      # drain the raw log (cycles stay disjoint)
    gate_yield.py candidates          # retirement candidates from >=2 COMMITTED cycles

Honesty rules, mechanical:
- The raw log is ephemeral (gitignored, resets on any fresh clone); candidates therefore
  derive ONLY from committed rollups across >= --min-cycles cycles — a 3-day-old clone must
  never make a healthy gate look like a zero-yield candidate.
- A gate absent from the record is UNMEASURED, never zero.
- A candidate needs friction (blocks fired) with EVERY block adjudicated as a false positive
  (journaled override). Unadjudicated friction is not evidence of zero yield — a block nobody
  overrode may have caught something real.
- Retirement itself stays a human decision with the R4.3 shape (dated demotion journal,
  expiry fails the release gate) — built when the first candidate actually appears.
Env: TDD_PLAYBOOK_YIELD_LOG (raw), TDD_PLAYBOOK_YIELD_MD (committed record). Stdlib-only.
"""
import argparse
import datetime
import json
import os
import sys

MD_HEADER = ("# Gate yield record (R4 — derived from telemetry, never self-report)\n\n"
             "One committed row per gate per calibration cycle. blocks/warns = frictions "
             "fired; overrides = journaled unlocks adjudicating a block as false-positive. "
             "Candidates need >=2 cycles — see gate_yield.py.\n\n"
             "| date | gate | blocks | warns | overrides |\n|---|---|---|---|---|\n")


def project_root():
    return os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def default_log():
    return os.environ.get("TDD_PLAYBOOK_YIELD_LOG") or os.path.join(
        project_root(), ".claude", "playbook-yield.jsonl")


def default_md():
    return os.environ.get("TDD_PLAYBOOK_YIELD_MD") or os.path.join(
        project_root(), "docs", "calibration", "gate_yield.md")


def read_raw(path):
    """(rows, skipped): parsed events + count of corrupt lines (skipped, never fatal)."""
    rows, skipped = [], 0
    if not os.path.isfile(path):
        return rows, skipped
    with open(path) as fh:
        for ln in fh:
            if not ln.strip():
                continue
            try:
                row = json.loads(ln)
                if not isinstance(row, dict):
                    raise ValueError("not an object")
                rows.append(row)
            except ValueError:
                skipped += 1
    return rows, skipped


def parse_md_rows(path):
    """Committed rollup rows: list of (date, gate, blocks, warns, overrides)."""
    out = []
    if not os.path.isfile(path):
        return out
    with open(path) as fh:
        for ln in fh:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) != 5 or not cells[0][:4].isdigit():
                continue
            try:
                out.append((cells[0], cells[1], int(cells[2]), int(cells[3]),
                            int(cells[4])))
            except ValueError:
                continue
    return out


def cmd_rollup(args):
    raw, skipped = read_raw(args.log)
    if skipped:
        print("rollup: {} corrupt line(s) skipped (telemetry, not a failure)".format(skipped))
    if not raw:
        print("yield: unmeasured this cycle (no event log at {})".format(args.log))
        return 0
    per_gate = {}
    for row in raw:
        gate = str(row.get("gate") or "unknown")
        counts = per_gate.setdefault(gate, {"block": 0, "warn": 0, "override": 0})
        ev = row.get("event")
        if ev in counts:
            counts[ev] += 1
    md_dir = os.path.dirname(args.md)
    if md_dir:
        os.makedirs(md_dir, exist_ok=True)
    new = not os.path.isfile(args.md)
    with open(args.md, "a") as fh:
        if new:
            fh.write(MD_HEADER)
        for gate in sorted(per_gate):
            c = per_gate[gate]
            fh.write("| {} | {} | {} | {} | {} |\n".format(
                args.date, gate, c["block"], c["warn"], c["override"]))
    os.remove(args.log)  # drained — the committed rollup is the durable record
    print("rollup: {} gate(s) recorded for {} in {} (raw log drained)".format(
        len(per_gate), args.date, args.md))
    return 0


def candidates(md_path, min_cycles):
    """(candidate_lines, measured_gate_count). Candidate = >=min_cycles cycles of friction
    with every block overridden."""
    rows = parse_md_rows(md_path)
    by_gate = {}
    for date, gate, blocks, warns, overrides in rows:
        g = by_gate.setdefault(gate, {"cycles": set(), "blocks": 0, "overrides": 0})
        g["cycles"].add(date)
        g["blocks"] += blocks
        g["overrides"] += overrides
    lines = []
    for gate in sorted(by_gate):
        g = by_gate[gate]
        if (len(g["cycles"]) >= min_cycles and g["blocks"] > 0
                and g["overrides"] >= g["blocks"]):
            lines.append(
                "RETIREMENT CANDIDATE: {} — {} cycles of friction ({} blocks) with every "
                "adjudicated block overridden (zero measured yield). Demotion is a human "
                "call with the R4.3 shape: TDD_PLAYBOOK_HOOK_{}=warn + a dated demotion "
                "journal entry whose expiry fails the release gate — never a silent "
                "deletion.".format(gate, len(g["cycles"]), g["blocks"], gate.upper()))
    return lines, len(by_gate)


def cmd_candidates(args):
    if not os.path.isfile(args.md):
        print("yield: unmeasured (no committed rollups yet at {})".format(args.md))
        return 0
    lines, measured = candidates(args.md, args.min_cycles)
    for ln in lines:
        print(ln)
    if not lines:
        print("yield: no retirement candidates.")
    print("yield: {} gate(s) measured across committed cycles; absent gates are "
          "UNMEASURED, not zero-yield".format(measured))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gate yield: the §13 second-direction "
                                             "instrument (cost decay).")
    ap.add_argument("command", choices=["rollup", "candidates"])
    ap.add_argument("--log", default=default_log())
    ap.add_argument("--md", default=default_md())
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--min-cycles", type=int, default=2)
    args = ap.parse_args(argv)
    return cmd_rollup(args) if args.command == "rollup" else cmd_candidates(args)


if __name__ == "__main__":
    sys.exit(main())
