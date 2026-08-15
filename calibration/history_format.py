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

# The inverse of the header this module WRITES (append_run_block below). It had no reader
# until v1.27 — the ledger needs `repo` to bind an entry to the first run measuring a tree
# strictly newer than the one it was written against. Keep this regex and the format string
# in append_run_block edited together; the round-trip test pins that they agree.
_RUN_HEADER = re.compile(
    r"^### Run (\d{4})-(\d{2})-(\d{2}) — model (.+?) · repo (\S+) · "
    r"selected (\d+) of (\d+) \((\d+) shipped \+ (\d+) corpus · (\d+) controls\) · "
    r"recall (\d+)/(\d+) \S+ · FP (\d+)/(\d+) \S+"
    r"(?: · form (dev|holdout|all))?\s*$")
_RUN_MARKER = "### Run "
# v1.29: `form` is an OPTIONAL trailing clause, and that is load-bearing. Every block written
# before the dev/holdout split lacks it, and a required group would make all 12 of them stop
# matching — parse_run_blocks would report them as `skipped`, and ledger.py (which binds and
# scores against these blocks, and does NOT assert the skipped count) would silently see an
# empty history and report every entry as PENDING. A header field added without a default is
# how a reader goes quietly blind to its own past.
_FORM_DEFAULT = "dev"


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


def split_runs(cell):
    """'3/3' -> (3, 3); None/'—'/malformed -> None; k/0 -> None.

    n == 0 is not a measurement, so it must never reach a comparator as a real pair — the
    ledger would otherwise read "0 of 0 reps passed" as a legitimate baseline. The formatter
    owns this because run_calibration writes the '{k}/{n}' cell.
    """
    if not cell:
        return None
    m = re.match(r"^\s*(\d+)\s*/\s*(\d+)\s*$", str(cell))
    if not m:
        return None
    k, n = int(m.group(1)), int(m.group(2))
    return (k, n) if n > 0 else None


def parse_run_blocks(text):
    """(blocks, skipped): run blocks oldest-first, plus the count of '### Run' lines that did
    NOT parse. Each block is the header's fields plus the rows that follow it:

        {date, model, repo_sha, selected, total, shipped, corpus, controls,
         recall: (k, n), fp: (k, n), line_no, rows: [...parse_rows dicts...]}

    `skipped` exists so callers can assert parsed + skipped == the number of '### Run' lines
    — a parser that silently matches nothing looks identical to a file with no runs, and the
    ledger would then report "no scoring run yet" forever instead of failing loudly.
    """
    lines = text.splitlines()
    blocks, skipped = [], 0
    for i, line in enumerate(lines):
        if not line.startswith(_RUN_MARKER):
            continue
        m = _RUN_HEADER.match(line.rstrip())
        if not m:
            skipped += 1
            continue
        g = m.groups()
        try:
            date = datetime.date(int(g[0]), int(g[1]), int(g[2]))
        except ValueError:
            skipped += 1
            continue
        blocks.append({
            "date": date, "model": g[3].strip(), "repo_sha": g[4].strip(),
            "selected": int(g[5]), "total": int(g[6]), "shipped": int(g[7]),
            "corpus": int(g[8]), "controls": int(g[9]),
            "recall": (int(g[10]), int(g[11])), "fp": (int(g[12]), int(g[13])),
            # A pre-v1.29 block has no form clause. It was, by definition, the whole corpus
            # with nothing held out — which is exactly `dev`.
            "form": g[14] or _FORM_DEFAULT,
            "line_no": i + 1, "_start": i,
        })
    for j, b in enumerate(blocks):
        end = blocks[j + 1]["_start"] if j + 1 < len(blocks) else len(lines)
        b["rows"] = parse_rows("\n".join(lines[b.pop("_start"):end]))
    return blocks, skipped


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
            "recall {r0}/{r1} {rci} · FP {f0}/{f1} {fci} · form {form}\n".format(
                r0=meta["recall"][0], r1=meta["recall"][1],
                rci=interval_cell(*meta["recall"]),
                f0=meta["fp"][0], f1=meta["fp"][1],
                fci=interval_cell(*meta["fp"]),
                # U2 (2026-08-15): `form` is a REQUIRED write key (in the meta[k] splat), not
                # a silent default. The producer omitted it and `.get(form, dev)` wrote `form
                # dev` under --form holdout for months. READING stays optional (old blocks
                # lack the clause, _RUN_HEADER defaults them); WRITING must never guess, or a
                # holdout run is indistinguishable from a dev run in the append-only record.
                **{k: meta[k] for k in ("date", "model", "repo_sha", "selected", "total",
                                        "shipped", "corpus", "controls", "form")}))
        fh.write(HEADER_7 + "\n" + SEP_7 + "\n")
        for r in rows:
            fh.write("| {date} | {model_cell} | {scenario} | {agent} | {runs} | {mode} | "
                     "{verdict} |\n".format(
                         date=r["date"], model_cell=r["model_cell"], scenario=r["scenario"],
                         agent=r["agent"], runs=r["runs"], mode=r["mode"] or "—",
                         verdict=r["verdict"]))
