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
    "schema: {schema}\n\n"
    "| date | sweep | checked | violations | exempted | unresolvable |\n"
    "|---|---|---|---|---|---|\n")

_SCHEMA_RX = re.compile(r"^schema:\s*(\d+)\s*$", re.MULTILINE)

# the summary-line contract is OWNED by the producer — import it, never re-type it
# (arch-adversary F3: four independent regex dialects was the drift surface)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dataflow_sweeps as _ds  # noqa: E402  (sibling, vendored alongside)

SUMMARY_LINE_RX = _ds.SUMMARY_LINE_RX

MD_HEADER = ("# Gate yield record (R4 — derived from telemetry, never self-report)\n\n"
             "One committed row per gate per calibration cycle. blocks/warns = frictions "
             "fired; overrides = ALL journaled unlocks; fp = the subset whose journaled "
             "reason-class is `gate-wrong` — the only kind that adjudicates a block as a "
             "false positive; suppressed = findings that fired while the gate was demoted "
             "to off (a muzzled gate, never a quiet one). Candidates need >=2 cycles and "
             "are computed from fp, never from overrides — see gate_yield.py.\n\n"
             "DATED CORRECTION (v1.27, pre-fix sha 119e2de): rows on or before 2026-08-05 "
             "have NO fp cell. Before that fix `overrides` was read as 'blocks adjudicated "
             "false-positive', so four cycles of the normal red-first lock/implement/unlock "
             "rhythm printed RETIREMENT CANDIDATE: testlock with zero real false positives. "
             "Those rows mix phase/feature-end/test-wrong/gate-wrong in unknown proportion "
             "and are UNMEASURED — they are left byte-identical and are never reinterpreted, "
             "because inferring a class into a durable record is the fabrication this fix "
             "exists to end.\n\n"
             "| date | gate | blocks | warns | overrides | suppressed | fp |\n"
             "|---|---|---|---|---|---|---|\n")


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
    """Committed rollup rows: (date, gate, blocks, warns, overrides, suppressed, fp).

    Widths 5/6/7 are all accepted — the record grew columns and older rows stay valid.
    `fp` is **None** when the row predates reason-class recording, never 0: a missing
    measurement is UNMEASURED, and coercing it to zero would fabricate the very number the
    v1.27 fix exists to stop inventing. Callers must branch on None explicitly.
    """
    out = []
    if not os.path.isfile(path):
        return out
    with open(path) as fh:
        for ln in fh:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if len(cells) not in (5, 6, 7) or not cells[0][:4].isdigit():
                continue
            try:
                out.append((cells[0], cells[1], int(cells[2]), int(cells[3]),
                            int(cells[4]), int(cells[5]) if len(cells) >= 6 else 0,
                            int(cells[6]) if len(cells) == 7 else None))
            except ValueError:
                continue
    return out


RESPONSE_SCHEMA = 1
RESPONSE_MD_HEADER = (
    "# Guard-response record (§12 v1.28 — was the block complied with, or routed around?)\n\n"
    "One committed row per gate per cycle. `blocks` is written by the HOOKS (mechanical, via\n"
    "_common.emit); `accounted` counts the agent's own three-clause responses recorded with\n"
    "`bin/guard_note.py`. Self-report can move `accounted`; it cannot touch `blocks` — so an\n"
    "agent that simply stays quiet produces a visible `unaccounted`, not a clean record.\n"
    "`elsewhere` counts responses admitting the blocked action was performed by another\n"
    "route: that column should be 0 forever, and any other value is a finding.\n\n"
    "schema: {schema}\n\n"
    "| date | gate | blocks | accounted | unaccounted | elsewhere |\n"
    "|---|---|---|---|---|---|\n")


# v1.34.0 D5 — the ROSTER/COUNTING split. cmd_rollup used to register the per_gate key
# BEFORE inspecting the event, so any non-gate producer on the one write path minted a
# phantom zero-yield gate row in the retirement instrument (proven by execution in the
# readable-surface plan re-review: three `usage` events -> `| readable-surface | 0 | 0 |
# 0 | 0 | 0 |`, and `candidates` counted a non-gate in its measured denominator). Only
# these events may mint a gate row; usage events route to their own table; anything else
# stays ignored-without-a-row (the deliberate old-vendored-copy tolerance).
GATE_EVENTS = ("block", "warn", "override", "suppressed", "response")
USAGE_EVENTS = ("usage", "usage-note")

USAGE_SCHEMA = 1
USAGE_MD_HEADER = (
    "# Readable-surface usage record (v1.34.0 D5 — the R&D instrument)\n\n"
    "One committed row per scenario per cycle, drained from the same event log as the\n"
    "gate record. `uses` is MACHINE-written (the facts CLI logging its own invocation) —\n"
    "the denominator; `dispatched` / `changed_a_decision` count the agent's own\n"
    "usage-note events (source: agent), the same self-report split guard_response.md\n"
    "uses: a note can move its two columns and can never move `uses`. A note whose\n"
    "scenario saw no machine use this cycle is an ORPHAN — reported, never counted.\n"
    "Absent data is UNMEASURED, never zero. Usage measures whether the surface was\n"
    "ASKED, not whether it helped — the keep/kill criterion is rows nobody asks about.\n\n"
    "schema: {schema}\n\n"
    "| date | scenario | uses | dispatched | changed_a_decision |\n"
    "|---|---|---|---|---|\n")


def default_usage_md():
    explicit = os.environ.get("TDD_PLAYBOOK_USAGE_MD")
    if explicit:
        return explicit
    # sibling of the yield record ON PURPOSE (same rule as default_dataflow_md): every
    # harness/test that isolates TDD_PLAYBOOK_YIELD_MD isolates this record too — the
    # committed-record leak is a logged incident class (G5, 2026-08-06), not a hypothesis
    yield_md = os.environ.get("TDD_PLAYBOOK_YIELD_MD")
    if yield_md:
        return os.path.join(os.path.dirname(yield_md), "usage.md")
    return os.path.join(project_root(), "docs", "calibration", "usage.md")


def _write_usage_rows(path, date, per_scenario):
    """Append one row per scenario that saw MACHINE use this cycle; return print lines.
    Same drain pass as the yield rollup — a second pass over a drained log would record
    zeros. Orphan notes (a scenario with notes but no uses) are reported, never counted:
    self-report must not be able to create a denominator row."""
    lines, rows = [], []
    for scenario in sorted(per_scenario):
        c = per_scenario[scenario]
        if not c["uses"]:
            if c["dispatched"] or c["changed"] or c["noted"]:
                lines.append(
                    "ORPHAN NOTE: {} — {} note(s) with no machine-recorded use this "
                    "cycle. Not counted: the denominator is machine-written only."
                    .format(scenario, c["noted"]))
            continue
        rows.append((scenario, c["uses"], c["dispatched"], c["changed"]))
    if not rows:
        return lines
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    new = not os.path.isfile(path)
    with open(path, "a") as fh:
        if new:
            fh.write(USAGE_MD_HEADER.format(schema=USAGE_SCHEMA))
        for scenario, uses, dispatched, changed in rows:
            fh.write("| {} | {} | {} | {} | {} |\n".format(
                date, scenario, uses, dispatched, changed))
    lines.append("usage: {} scenario(s) recorded for {} in {}".format(
        len(rows), date, path))
    return lines


def default_response_md():
    explicit = os.environ.get("TDD_PLAYBOOK_RESPONSE_MD")
    if explicit:
        return explicit
    yield_md = os.environ.get("TDD_PLAYBOOK_YIELD_MD")
    if yield_md:
        return os.path.join(os.path.dirname(yield_md), "guard_response.md")
    return os.path.join(project_root(), "docs", "calibration", "guard_response.md")


def _write_response_rows(path, date, per_gate):
    """Append one row per gate that saw a block OR a response this cycle, and return the
    lines to print. Written from the SAME drain pass as the yield rollup — a second pass
    over a drained log would silently record zeros."""
    rows, lines = [], []
    for gate in sorted(per_gate):
        c = per_gate[gate]
        blocks, acc, elsewhere = c["block"], c["response"], c["elsewhere"]
        if not blocks and not acc:
            continue
        unaccounted = max(0, blocks - acc)
        rows.append((gate, blocks, acc, unaccounted, elsewhere))
        if elsewhere:
            lines.append(
                "PERFORMED ELSEWHERE: {} — {} response(s) admit the blocked action was "
                "carried out by another route. This is the move the guard exists to stop; "
                "read them before anything else.".format(gate, elsewhere))
        if unaccounted:
            lines.append(
                "UNACCOUNTED: {} — {} block(s) with no recorded response ({} of {} "
                "accounted). Silence is not compliance: record the three clauses with "
                "bin/guard_note.py, or the transcript is the only evidence there is."
                .format(gate, unaccounted, acc, blocks))
    if not rows:
        return lines
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    new = not os.path.isfile(path)
    with open(path, "a") as fh:
        if new:
            fh.write(RESPONSE_MD_HEADER.format(schema=RESPONSE_SCHEMA))
        for gate, blocks, acc, unaccounted, elsewhere in rows:
            fh.write("| {} | {} | {} | {} | {} | {} |\n".format(
                date, gate, blocks, acc, unaccounted, elsewhere))
    return lines


def _is_data_row(line):
    """One definition of "a row in this file", shared with parse_md_rows. The first
    migration used `startswith("| 2")`, which parse_md_rows does not — two disagreeing
    answers in one module, and the narrower one silently dropped both a 1999-dated row and
    the operator's own DEMOTION JOURNAL note (the note this tool TELLS them to write)."""
    return line.startswith("|") and not line.startswith("| date") \
        and not line.startswith("|---")


def migrate_header(path):
    """Replace a stale prose header in place, preserving every other line.

    Runs BEFORE the no-events early return. The first version sat after it, so on a quiet
    cycle — exactly how the header went stale in the first place — the repair never ran. It
    is also idempotent and a no-op when the header already matches, so a rollup is not a
    destructive rewrite of an evidence artifact on every invocation."""
    if not os.path.isfile(path):
        return False
    with open(path) as fh:
        text = fh.read()
    if text.startswith(MD_HEADER):
        return False
    # The header is everything ABOVE the table header line; everything from the table down
    # is data and is preserved verbatim. This is structural rather than a guess about which
    # prose is stale: an earlier predicate tried to classify line-by-line and could not tell
    # a superseded paragraph from an operator's own note, because nothing in the text says
    # which is which. Notes belong below the table, where they survive by construction.
    lines = text.splitlines(True)
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("| date"):
            start = i
            break
    if start is None:
        return False        # no table yet — nothing safe to preserve, leave it alone
    kept = [ln for ln in lines[start:] if not ln.startswith("| date")
            and not ln.startswith("|---")]
    tmp = path + ".migrating"
    with open(tmp, "w") as fh:
        fh.write(MD_HEADER)
        fh.writelines(kept)
    os.replace(tmp, path)   # atomic: a crash mid-write must not destroy the record
    return True


def cmd_rollup(args):
    raw, skipped = read_raw(args.log)
    if skipped:
        print("rollup: {} corrupt line(s) skipped (telemetry, not a failure)".format(skipped))
    if not raw:
        print("yield: unmeasured this cycle (no event log at {})".format(args.log))
        return 0
    per_gate, per_scenario = {}, {}
    for row in raw:
        ev = row.get("event")
        # ROSTER decision first (v1.34.0 D5): only the closed gate vocabulary may mint a
        # per_gate key — see GATE_EVENTS. Usage events go to their own table; anything
        # else is ignored without a row (the deliberate old-vendored-copy tolerance).
        if ev in USAGE_EVENTS:
            scenario = str(row.get("scenario") or "full")
            c = per_scenario.setdefault(scenario, {"uses": 0, "dispatched": 0,
                                                   "changed": 0, "noted": 0})
            if ev == "usage":
                c["uses"] += 1
            else:  # usage-note: source=agent self-report — moves its two columns only
                c["noted"] += 1
                if str(row.get("dispatched") or "").lower() == "yes":
                    c["dispatched"] += 1
                if str(row.get("changed_a_decision") or "").lower() == "yes":
                    c["changed"] += 1
            continue
        if ev not in GATE_EVENTS:
            continue
        gate = str(row.get("gate") or "unknown")
        counts = per_gate.setdefault(gate, {"block": 0, "warn": 0, "override": 0,
                                            "suppressed": 0, "fp": 0,
                                            "response": 0, "elsewhere": 0})
        if ev == "response":
            counts["response"] += 1
            if str(row.get("performed_elsewhere") or "").lower() == "yes":
                counts["elsewhere"] += 1
            continue          # `response` is a counts key, so the generic increment below
                              # would double it — the arithmetic IS the instrument here
        counts[ev] += 1
        # `overrides` keeps its exact old meaning (every unlock); `fp` is the adjudicating
        # subset. Kept as a sub-key rather than a new event NAME because unknown event
        # names are dropped above — an older vendored copy would eat the signal.
        if ev == "override" and str(row.get("reason_class") or "") == "gate-wrong":
            counts["fp"] += 1
    md_dir = os.path.dirname(args.md)
    if md_dir:
        os.makedirs(md_dir, exist_ok=True)
    if per_gate:
        migrate_header(args.md)
        new = not os.path.isfile(args.md)
        with open(args.md, "a") as fh:
            if new:
                fh.write(MD_HEADER)
            for gate in sorted(per_gate):
                c = per_gate[gate]
                fh.write("| {} | {} | {} | {} | {} | {} | {} |\n".format(
                    args.date, gate, c["block"], c["warn"], c["override"],
                    c["suppressed"], c["fp"]))
    response_lines = _write_response_rows(
        getattr(args, "response_md", None) or default_response_md(), args.date, per_gate)
    usage_lines = _write_usage_rows(
        getattr(args, "usage_md", None) or default_usage_md(), args.date, per_scenario)
    os.remove(args.log)  # drained — the committed rollup is the durable record
    print("rollup: {} gate(s) recorded for {} in {} (raw log drained)".format(
        len(per_gate), args.date, args.md))
    for ln in response_lines:
        print(ln)
    for ln in usage_lines:
        print(ln)
    return 0


def candidates(md_path, min_cycles):
    """(candidate_lines, measured_gate_count). Candidate = >=min_cycles cycles of friction
    where every CLASSIFIED block was adjudicated a false positive (`fp`, i.e. an unlock
    journaled `--class gate-wrong`).

    v1.27: `overrides` left this predicate entirely. It counts EVERY unlock, so the normal
    red-first lock/implement/unlock rhythm satisfied `overrides >= blocks` and flagged
    testlock for retirement across four cycles with zero real false positives.

    Both sides of the ratio are classified-only. Counting legacy `blocks` against post-fix
    `fp` would inflate the denominator and permanently suppress a REAL candidate — the same
    bug with the sign flipped. Rows predating the fix (fp is None) contribute to neither
    numerator nor denominator and are reported as UNCLASSIFIED HISTORY instead.
    """
    rows = parse_md_rows(md_path)
    by_gate = {}
    for date, gate, blocks, warns, overrides, suppressed, fp in rows:
        g = by_gate.setdefault(gate, {"cycles": set(), "blocks_classified": 0, "fp": 0,
                                      "suppressed": 0, "unknown_cycles": set()})
        g["cycles"].add(date)
        g["suppressed"] += suppressed
        if fp is None:
            g["unknown_cycles"].add(date)
        else:
            g["blocks_classified"] += blocks
            g["fp"] += fp
    lines = []
    for gate in sorted(by_gate):
        g = by_gate[gate]
        if g["suppressed"] > 0:
            lines.append(
                "SUPPRESSED FINDINGS: {} — {} finding(s) fired while the gate was demoted "
                "to off (a muzzled gate, not a quiet one). A demotion nobody journaled is "
                "the H-class kill switch; restore the gate or journal the demotion with an "
                "owner and expiry.".format(gate, g["suppressed"]))
        if g["unknown_cycles"]:
            lines.append(
                "UNCLASSIFIED HISTORY: {} — {} committed cycle(s) predate reason-class "
                "recording (pre-119e2de); their overrides are UNMEASURED and are never "
                "counted as adjudicated false positives. Any retirement verdict for this "
                "gate rests only on the {} classified cycle(s)."
                .format(gate, len(g["unknown_cycles"]),
                        len(g["cycles"]) - len(g["unknown_cycles"])))
        classified_cycles = len(g["cycles"]) - len(g["unknown_cycles"])
        if (classified_cycles >= min_cycles and g["blocks_classified"] > 0
                and g["fp"] >= g["blocks_classified"]):
            lines.append(
                "RETIREMENT CANDIDATE: {} — {} classified cycles of friction ({} blocks) "
                "with every block adjudicated a false positive (unlock --class gate-wrong; "
                "zero measured yield). Demotion is a human call with the R4.3 shape: "
                "TDD_PLAYBOOK_HOOK_{}=warn + a dated demotion journal entry whose expiry "
                "fails the release gate — never a silent deletion."
                .format(gate, classified_cycles, g["blocks_classified"], gate.upper()))
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
    if not new:
        # v1.25 arch-F4: the series is versioned AT THE CONTRACT. The producer stamps
        # its counting semantics (dataflow_sweeps.SUMMARY_SCHEMA); a record whose stamp
        # differs (or predates stamping) REFUSES — a semantics change is a conscious,
        # committed migration of the record, never a prose note the comparator ignores.
        m = _SCHEMA_RX.search(open(args.md).read())
        have = int(m.group(1)) if m else None
        if have != _ds.SUMMARY_SCHEMA:
            print("dataflow-rollup: REFUSED — record schema {} != producer schema {}; "
                  "the counting semantics changed. Migrate the committed record "
                  "consciously (retire pre-change rows, stamp 'schema: {}') before "
                  "appending — comparing across the change corrupts the trend.".format(
                      have, _ds.SUMMARY_SCHEMA, _ds.SUMMARY_SCHEMA))
            return 1
    with open(args.md, "a") as fh:
        if new:
            fh.write(DATAFLOW_MD_HEADER.format(schema=_ds.SUMMARY_SCHEMA))
        for sweep, checked, violations, exempted, unresolvable in parsed:
            fh.write("| {} | {} | {} | {} | {} | {} |\n".format(
                args.date, sweep, checked, violations, exempted, unresolvable))
    print("dataflow-rollup: {} sweep row(s) recorded for {} in {}".format(
        len(parsed), args.date, args.md))
    return 0


def dataflow_trend(md_path, cycles):
    """Trend lines for sweeps whose excluded share (exempted/checked) grew strictly
    across the last `cycles` committed rows. Returns a list of flag lines."""
    # (date, sweep, checked, violations, exempted, unres, _fp) — parse_md_rows is shared with
    # the gate record, so it yields the v1.27 7th cell here too; it is always None for sweep
    # rows and is ignored. Sort on (date, sweep) ONLY: a full-tuple sort would compare None
    # against None-or-int whenever two rows tie on the first six cells, a latent TypeError.
    rows = sorted(parse_md_rows(md_path), key=lambda r: r[:2])
    by_sweep = {}
    for date, sweep, checked, violations, exempted, unresolvable, _fp in rows:
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


def cmd_usage_note(args):
    """One line of self-report per use of the readable surface, riding the ONE write path
    as an EVENT (the guard_note.py pattern) — never an edit to the committed record.
    Joined to machine `usage` events at the next rollup; a note whose scenario saw no
    machine use is an orphan (reported, never counted), so a forged note cannot create a
    denominator row BY CONSTRUCTION. Exit 0 recorded · 2 usage."""
    for name, val in (("--dispatched", args.dispatched),
                      ("--changed-a-decision", args.changed_a_decision)):
        if val not in ("yes", "no"):
            sys.stderr.write("usage-note: {} must be exactly yes|no (got {!r}) — a vague "
                             "answer is not a record\n".format(name, val))
            return 2
    if not (args.scenario or "").strip():
        sys.stderr.write("usage-note: --scenario is required (an S-row id, or `full`)\n")
        return 2
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "..", "hooks", "scripts"))
    try:
        from _common import log_yield_event
    except Exception as exc:
        sys.stderr.write("usage-note: cannot reach hooks/scripts/_common.py — the note "
                         "was NOT recorded ({})\n".format(exc))
        return 2
    log_yield_event("readable-surface", "usage-note",
                    {"scenario": args.scenario.strip(),
                     "dispatched": args.dispatched,
                     "changed_a_decision": args.changed_a_decision},
                    source="agent")
    print("usage-note: recorded for '{}' (dispatched={}, changed_a_decision={})".format(
        args.scenario.strip(), args.dispatched, args.changed_a_decision))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="Gate yield: the §13 second-direction "
                                             "instrument (cost decay).")
    ap.add_argument("command", choices=["rollup", "candidates",
                                        "dataflow-rollup", "dataflow-trend",
                                        "usage-note"])
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
    ap.add_argument("--response-md", default=None,
                    help="rollup: committed guard-response record (default: beside the "
                         "yield record)")
    ap.add_argument("--usage-md", default=None,
                    help="rollup: committed readable-surface usage record (default: "
                         "beside the yield record)")
    ap.add_argument("--scenario", default=None,
                    help="usage-note: the S-row asked about, or `full`")
    ap.add_argument("--dispatched", default=None,
                    help="usage-note: did you dispatch an adversary from it (yes|no)")
    ap.add_argument("--changed-a-decision", default=None,
                    help="usage-note: did the answer change what you did (yes|no)")
    args = ap.parse_args(argv)
    if args.command == "usage-note":
        return cmd_usage_note(args)
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
