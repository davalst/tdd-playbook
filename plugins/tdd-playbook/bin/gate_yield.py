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
    gate_yield.py dataflow-rollup --date D --line "<sweep summary>" [--line ...]
                                      # v1.24 (§6c D13b): one committed row per dataflow
                                      # sweep per cycle, parsed from dataflow_sweeps.py's
                                      # pinned summary lines -> docs/calibration/
                                      # dataflow_yield.md (same instrument, new table)
    gate_yield.py dataflow-trend      # flags an excluded share that GREW --cycles
                                      # consecutive cycles — a growing exemption list under
                                      # a green sweep means the list is doing the tests'
                                      # work (§4's filter-audit rule, §6c governance)

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
import re
import sys

DATAFLOW_MD_HEADER = (
    "# Dataflow-sweep yield record (§6c D13b — committed rows, mechanical trend)\n\n"
    "One committed row per sweep per calibration cycle, parsed from dataflow_sweeps.py's "
    "pinned summary line. The excluded share (exempted/checked) is a TREND claim — "
    "undetectable from one run; `gate_yield.py dataflow-trend` is the comparator.\n\n"
    "| date | sweep | checked | violations | exempted | unresolvable |\n"
    "|---|---|---|---|---|---|\n")

SUMMARY_LINE_RX = re.compile(
    r"dataflow_sweeps ([a-z-]+): checked (\d+) · violations (\d+) · "
    r"exempted (\d+) · unresolvable (\d+)")

MD_HEADER = ("# Gate yield record (R4 — derived from telemetry, never self-report)\n\n"
             "One committed row per gate per calibration cycle. blocks/warns = frictions "
             "fired; overrides = journaled unlocks adjudicating a block as false-positive; "
             "suppressed = findings that fired while the gate was demoted to off (a muzzled "
             "gate, never a quiet one). Candidates need >=2 cycles — see gate_yield.py.\n\n"
             "| date | gate | blocks | warns | overrides | suppressed |\n"
             "|---|---|---|---|---|---|\n")


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
            if len(cells) not in (5, 6) or not cells[0][:4].isdigit():
                continue
            try:
                out.append((cells[0], cells[1], int(cells[2]), int(cells[3]),
                            int(cells[4]), int(cells[5]) if len(cells) == 6 else 0))
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
        counts = per_gate.setdefault(gate, {"block": 0, "warn": 0, "override": 0,
                                            "suppressed": 0})
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
            fh.write("| {} | {} | {} | {} | {} | {} |\n".format(
                args.date, gate, c["block"], c["warn"], c["override"], c["suppressed"]))
    os.remove(args.log)  # drained — the committed rollup is the durable record
    print("rollup: {} gate(s) recorded for {} in {} (raw log drained)".format(
        len(per_gate), args.date, args.md))
    return 0


def candidates(md_path, min_cycles):
    """(candidate_lines, measured_gate_count). Candidate = >=min_cycles cycles of friction
    with every block overridden."""
    rows = parse_md_rows(md_path)
    by_gate = {}
    for date, gate, blocks, warns, overrides, suppressed in rows:
        g = by_gate.setdefault(gate, {"cycles": set(), "blocks": 0, "overrides": 0,
                                      "suppressed": 0})
        g["cycles"].add(date)
        g["blocks"] += blocks
        g["overrides"] += overrides
        g["suppressed"] += suppressed
    lines = []
    for gate in sorted(by_gate):
        g = by_gate[gate]
        if g["suppressed"] > 0:
            lines.append(
                "SUPPRESSED FINDINGS: {} — {} finding(s) fired while the gate was demoted "
                "to off (a muzzled gate, not a quiet one). A demotion nobody journaled is "
                "the H-class kill switch; restore the gate or journal the demotion with an "
                "owner and expiry.".format(gate, g["suppressed"]))
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


def default_dataflow_md():
    explicit = os.environ.get("TDD_PLAYBOOK_DATAFLOW_MD")
    if explicit:
        return explicit
    # sibling of the yield record ON PURPOSE: every harness/test that isolates
    # TDD_PLAYBOOK_YIELD_MD isolates this record too — one instrument, one seam
    yield_md = os.environ.get("TDD_PLAYBOOK_YIELD_MD")
    if yield_md:
        return os.path.join(os.path.dirname(yield_md), "dataflow_yield.md")
    return os.path.join(project_root(), "docs", "calibration", "dataflow_yield.md")


def cmd_dataflow_rollup(args):
    # validate EVERY line before writing anything — a fabricated row is worse than a
    # refused rollup (the record is the trend check's ground truth)
    parsed = []
    for line in args.line or []:
        m = SUMMARY_LINE_RX.search(line)
        if not m:
            print("dataflow-rollup: REFUSED — not a dataflow_sweeps summary line: "
                  "{!r}".format(line))
            return 1
        parsed.append(m.groups())
    if not parsed:
        print("dataflow yield: unmeasured this cycle (no --line summaries supplied)")
        return 0
    md_dir = os.path.dirname(args.md)
    if md_dir:
        os.makedirs(md_dir, exist_ok=True)
    new = not os.path.isfile(args.md)
    with open(args.md, "a") as fh:
        if new:
            fh.write(DATAFLOW_MD_HEADER)
        for sweep, checked, violations, exempted, unresolvable in parsed:
            fh.write("| {} | {} | {} | {} | {} | {} |\n".format(
                args.date, sweep, checked, violations, exempted, unresolvable))
    print("dataflow-rollup: {} sweep row(s) recorded for {} in {}".format(
        len(parsed), args.date, args.md))
    return 0


def dataflow_trend(md_path, cycles):
    """Trend lines for sweeps whose excluded share (exempted/checked) grew strictly
    across the last `cycles` committed rows. Returns a list of flag lines."""
    rows = sorted(parse_md_rows(md_path))  # (date, sweep, checked, violations, exempted, unres)
    by_sweep = {}
    for date, sweep, checked, violations, exempted, unresolvable in rows:
        by_sweep.setdefault(sweep, []).append(exempted / max(checked, 1))
    flags = []
    for sweep in sorted(by_sweep):
        shares = by_sweep[sweep][-cycles:]
        if len(shares) >= cycles and all(a < b for a, b in zip(shares, shares[1:])):
            flags.append(
                "DATAFLOW TREND: {} — excluded share grew {} consecutive cycles "
                "({}). A growing exemption list under a green sweep means the list is "
                "doing the tests' work (§6c governance / §4 filter-audit rule): burn the "
                "exemptions down or justify each with a re-dated entry.".format(
                    sweep, cycles,
                    " -> ".join("{:.1%}".format(s) for s in shares)))
    return flags


def cmd_dataflow_trend(args):
    if not os.path.isfile(args.md):
        print("dataflow yield: unmeasured (no committed sweep rows yet at {})".format(
            args.md))
        return 0
    flags = dataflow_trend(args.md, args.min_cycles)
    for ln in flags:
        print(ln)
    if not flags:
        print("dataflow yield: excluded share held or shrank — no trend flag.")
    return 1 if flags else 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gate yield: the §13 second-direction "
                                             "instrument (cost decay).")
    ap.add_argument("command", choices=["rollup", "candidates",
                                        "dataflow-rollup", "dataflow-trend"])
    ap.add_argument("--log", default=default_log())
    ap.add_argument("--md", default=None,
                    help="committed record (defaults per command: gate_yield.md / "
                         "dataflow_yield.md)")
    ap.add_argument("--date", default=datetime.date.today().isoformat())
    ap.add_argument("--min-cycles", type=int, default=None,
                    help="candidates: min committed cycles (default 2); dataflow-trend: "
                         "consecutive growth cycles to flag (default 3)")
    ap.add_argument("--line", action="append", default=[],
                    help="dataflow-rollup: one dataflow_sweeps summary line (repeatable)")
    args = ap.parse_args(argv)
    if args.command in ("dataflow-rollup", "dataflow-trend"):
        args.md = args.md or default_dataflow_md()
        args.min_cycles = args.min_cycles if args.min_cycles is not None else 3
        return (cmd_dataflow_rollup(args) if args.command == "dataflow-rollup"
                else cmd_dataflow_trend(args))
    args.md = args.md or default_md()
    args.min_cycles = args.min_cycles if args.min_cycles is not None else 2
    return cmd_rollup(args) if args.command == "rollup" else cmd_candidates(args)


if __name__ == "__main__":
    sys.exit(main())
