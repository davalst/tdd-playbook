#!/usr/bin/env python3
"""power — what the calibration instrument can and cannot detect (§13, v1.27).

Why this ships WITH the ledger and not "later": the ledger's job is to stop us adjudicating
narratives about noise, and it cannot do that without knowing where noise ends. Shipping the
scorer first and the noise floor two releases later would mean two releases of confidently
scored coin flips.

The arithmetic that motivated it, from this repo's own record. The original RSI plan scored
an entry CONFIRMED only at k/k, so P(confirm) = p**3 at 3 reps:

    plan bar >=80% of entries CONFIRMED  ->  needs true per-rep p >= 0.928
    plan KILL bar <50% CONFIRMED         ->  fires whenever p <  0.794

A fix taking an agent from 0% to 78% per-rep — an unambiguous, large improvement — counted
toward KILLING the plan. And per-entry significance is unobtainable at these reps at all:
`fisher_one_sided(3, 3, 0, 3)` is exactly 0.050, so 0/3 -> 3/3 is the ONLY single-scenario
movement that can reach alpha=0.05. Every weaker movement is descriptive, not significant.

Hence the division of labour: per-entry verdicts describe MOVEMENT, and significance is
claimed only at cycle level via a sign test over entries (5/5 -> p=0.031; 4/4 -> p=0.0625,
so five moved entries is the floor for any claim at all).

Seam note (the "ONE owner" boundary, stated so it is not re-litigated): `history_format`
owns statistics it RENDERS into history.md (`wilson` -> `interval_cell` -> the run header).
This module owns inference ABOUT the data and writes no file. `ledger.py` owns ledger.md's
format. Nothing here touches the clock, the filesystem, or a third-party import.
"""
from math import comb

ALPHA = 0.05


def fisher_one_sided(k1, n1, k0, n0):
    """P(observing >= k1 successes in the treated arm | same underlying rate), i.e. Fisher's
    exact test, upper tail. Returns 1.0 for a degenerate table rather than raising — callers
    are reporting a diagnostic line, not branching on an exception."""
    if n0 <= 0 or n1 <= 0:
        return 1.0
    k = k1 + k0
    total = n1 + n0
    if k <= 0 or k >= total:
        return 1.0
    denom = comb(total, k)
    lo = max(0, k - n0)
    hi = min(k, n1)
    if not lo <= k1 <= hi:
        return 1.0
    return sum(comb(n1, i) * comb(n0, k - i) for i in range(k1, hi + 1)) / denom


def sign_test_p(m_correct, m_moved):
    """One-sided sign test: P(>= m_correct of m_moved entries move as predicted | coin).

    Entries that did not move are EXCLUDED from m_moved, not counted as failures — a flat
    entry is an absence of evidence about direction, and folding it in as a loss would make
    a quiet cycle look like a refuted one."""
    if m_moved <= 0:
        return 1.0
    m_correct = min(m_correct, m_moved)
    return sum(comb(m_moved, i) for i in range(m_correct, m_moved + 1)) / (2 ** m_moved)


def min_detectable_reps(n0=3, n1=3, alpha=ALPHA):
    """Smallest rep improvement on ONE scenario that can reach `alpha`, or None if no
    movement can. At 3v3 this is 3 — i.e. only 0/3 -> 3/3 is ever significant."""
    for d in range(1, n1 + 1):
        k0 = max(0, n1 - d)
        if fisher_one_sided(min(k0 + d, n1), n1, k0, n0) <= alpha:
            return d
    return None


def min_entries_for_signal(alpha=ALPHA):
    """Fewest all-correct moved entries whose sign test reaches `alpha`. 5 at alpha=0.05."""
    m = 1
    while m <= 64:
        if sign_test_p(m, m) <= alpha:
            return m
        m += 1
    return None


def comparable_blocks(blocks):
    """The most recent PAIR of run blocks that actually share scenarios, or None.

    v1.34.0, found live. The floor used `blocks[-2:]` unconditionally. The calibration
    README's own advice for long runs — "chunk by agent (`--agent X`, then the next) so each
    chunk commits its own block" — produces adjacent blocks with a DISJOINT scenario set, so
    the intersection was empty and the floor came back 0 uncovered / 0 moved. A zero floor
    reads as "any movement at all is evidence", which is the exact inverse of what an absent
    measurement means, and it is the fabricated-zero this repo bans one file over ("a gate
    absent from the record is UNMEASURED, never zero").

    Scanning newest-first for the first pair with a non-empty intersection keeps the floor
    honest under both usage patterns; when no pair shares anything the caller must report
    UNMEASURED rather than a number.
    """
    for i in range(len(blocks) - 1, 0, -1):
        b = {r["scenario"] for r in blocks[i].get("rows") or []}
        for j in range(i - 1, -1, -1):
            a = {r["scenario"] for r in blocks[j].get("rows") or []}
            if a & b:
                return blocks[j], blocks[i]
    return None


def noise_floor(rows_a, rows_b, covered=()):
    """How much UNCOVERED scenarios moved between two runs — the empirical noise floor.

    `rows_a`/`rows_b` are parse_rows dicts from two run blocks; `covered` names the scenarios
    a ledger entry claimed, which are EXCLUDED (a covered scenario's movement is the thing
    being measured, so counting it as noise would launder a real effect into the floor).

    Returns {shared, uncovered, moved_1, moved_2, class_moves} where class_moves counts a
    change of verdict class (PASS/AMBER/BLOCKING) — the coarsest possible movement, and the
    one a reader is most likely to over-read as a result.
    """
    import history_format as _hf
    cov = set(covered)
    a = {r["scenario"]: r for r in rows_a}
    b = {r["scenario"]: r for r in rows_b}
    shared = sorted(set(a) & set(b))
    uncovered = [s for s in shared if s not in cov]
    moved_1 = moved_2 = class_moves = 0
    for s in uncovered:
        pa, pb = _hf.split_runs(a[s].get("runs")), _hf.split_runs(b[s].get("runs"))
        if pa and pb and pa[1] == pb[1]:
            d = abs(pb[0] - pa[0])
            moved_1 += d >= 1
            moved_2 += d >= 2
        # An INVALID row is the ENVIRONMENT refusing, not the plant behaving differently.
        # Counting PASS->INVALID as a verdict-class move inflated the floor to 8 of 16 on
        # 2026-08-06, when 23 scenarios had simply never run — the noise floor reporting
        # non-execution as noise, which is this repo's own narrowed-scope class inside the
        # instrument that exists to measure it.
        if "INVALID" in (a[s].get("kind"), b[s].get("kind")):
            continue
        if a[s].get("kind") != b[s].get("kind"):
            class_moves += 1
    return {"shared": len(shared), "uncovered": len(uncovered), "moved_1": moved_1,
            "moved_2": moved_2, "class_moves": class_moves}
