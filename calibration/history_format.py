#!/usr/bin/env python3
"""history_format — the ONE owner of the calibration scoreboard's on-disk format (D0).

docs/calibration/history.md is APPEND-ONLY: legacy 5-column rows (pre-v1.17) and run-block
7-column rows coexist in the file forever, so the parser accepts both, permanently. Writers:
run_calibration.append_history. Readers: check_staleness (freshness), run_calibration (AMBER
promotion), check_scoreboard_integrity (append-only proof). Format knowledge lives here and
nowhere else — the previous arrangement (a writer, a date regex, and column-string asserts in
three files) was the parallel-list bug one level up.

Freshness rule: INVALID rows never extend freshness — an INVALID run is a run where nothing
was calibrated, and a cadence gate satisfied by one is asleep (§13).
"""
import datetime
import math
import os
import re

_ROW = re.compile(r"^\s*\|\s*(\d{4})-(\d{2})-(\d{2})\s*\|(.*)\|\s*$")

HEADER_7 = "| date | model | scenario | agent | runs | mode | verdict |"
SEP_7 = "|---|---|---|---|---|---|---|"


def _kind(verdict):
    v = verdict.strip()
    if v == "PASS":
        return "PASS"
    if v.startswith("**BLOCKING"):
        return "BLOCKING"
    if v.startswith("INVALID"):
        return "INVALID"
    if v.startswith("AMBER"):
        return "AMBER"
    return "OTHER"


def parse_rows(text):
    """All scoreboard rows, oldest first. Legacy rows get runs=None, mode=None."""
    rows = []
    for line in text.splitlines():
        m = _ROW.match(line)
        if not m:
            continue
        try:
            date = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            continue
        cells = [c.strip() for c in m.group(4).split("|")]
        if len(cells) == 4:      # legacy: model, scenario, agent, verdict
            model, scenario, agent = cells[0], cells[1], cells[2]
            runs, mode, verdict = None, None, cells[3]
        elif len(cells) == 6:    # run-block: model, scenario, agent, runs, mode, verdict
            model, scenario, agent, runs, mode, verdict = cells
        else:
            continue
        rows.append({"date": date, "model": model, "scenario": scenario, "agent": agent,
                     "runs": runs, "mode": mode, "verdict": verdict, "kind": _kind(verdict)})
    return rows


def latest_run_date(text):
    """Most recent date across rows that represent an actual calibration (INVALID skipped)."""
    dates = [r["date"] for r in parse_rows(text) if r["kind"] != "INVALID"]
    return max(dates) if dates else None


def wilson(k, n, z=1.96):
    """95% Wilson score interval for k successes in n trials — a pure STATISTIC (the
    format functions below only render it; consumers like the lift report re-derive from
    here, never from regexing the file). None when n == 0 (renders as [—]). At n=3, 3/3
    is consistent with a true rate from ~0.44 to 1.0 — the honesty the point estimate
    `recall 9/9` was hiding (lift/ratchet D4)."""
    if n == 0:
        return None
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    margin = (z / denom) * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, round(center - margin, 2)), min(1.0, round(center + margin, 2)))


def interval_cell(k, n):
    ci = wilson(k, n)
    return "[—]" if ci is None else "[{:.2f}–{:.2f}]".format(ci[0], ci[1])


def append_run_block(path, meta, rows):
    """Append one run block. meta: date, model, repo_sha, selected, total, shipped, corpus,
    controls, recall=(caught, plants), fp=(flagged, controls). rows: dicts with date,
    model_cell, scenario, agent, runs, mode (None -> em dash), verdict."""
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    new = not os.path.isfile(path)
    with open(path, "a") as fh:
        if new:
            fh.write("# Calibration history\n")
        fh.write(
            "\n### Run {date} — model {model} · repo {repo_sha} · selected {selected} of "
            "{total} ({shipped} shipped + {corpus} corpus · {controls} controls) · "
            "recall {r0}/{r1} {rci} · FP {f0}/{f1} {fci}\n".format(
                r0=meta["recall"][0], r1=meta["recall"][1],
                rci=interval_cell(*meta["recall"]),
                f0=meta["fp"][0], f1=meta["fp"][1],
                fci=interval_cell(*meta["fp"]), **{
                    k: meta[k] for k in ("date", "model", "repo_sha", "selected", "total",
                                         "shipped", "corpus", "controls")}))
        fh.write(HEADER_7 + "\n" + SEP_7 + "\n")
        for r in rows:
            fh.write("| {date} | {model_cell} | {scenario} | {agent} | {runs} | {mode} | "
                     "{verdict} |\n".format(
                         date=r["date"], model_cell=r["model_cell"], scenario=r["scenario"],
                         agent=r["agent"], runs=r["runs"], mode=r["mode"] or "—",
                         verdict=r["verdict"]))
