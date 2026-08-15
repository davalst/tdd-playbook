#!/usr/bin/env python3
"""plant_vitality — does this plant still DISCRIMINATE, or has the agent memorised it?

A frozen plant library is a static gate: a plant every agent passes every time has stopped
measuring anything, and a corpus of them reads as a rising score while the gates decay. This
derives per-scenario streaks from the scoreboard and classifies:

    saturated       — all-reps green for >= K consecutive runs; no longer discriminating
    discriminating  — mixed results; still telling us something
    failing         — currently red; the agent is genuinely missing it
    insufficient    — fewer than K runs of history; NOT a classification

WHAT THIS IS NOT. It is not a deletion driver, and it is not a ranking. The corpus only GROWS
(deletion-ratchet R4): vitality answers the ABSOLUTE question "does this plant still
discriminate?", never the comparative "which plant is worst?". Its consumers are the
authoring cycle (a saturated plant names the target for its next, harder sibling; a saturated
CLASS is a rotation-to-holdout candidate) and the quarterly review. Nothing here retires
anything, and nothing here is a gate.

HONEST SCOPING, stated because the number would otherwise flatter us. K defaults to 4
consecutive all-green runs, and this repo has ~12 runs total with the corpus only recently
grown — so most plants will report `insufficient` for a long time, and that is the correct
answer rather than a misleading zero. The default is PROVISIONAL: it was chosen before there
was enough history to calibrate it, and it should be revisited once the run count supports
it. A saturated-share TREND across quarters is the real signal (the escalation-ceiling
watch); a single reading is not.

No clock: `--as-of` is accepted for symmetry with the other calibration tools, and every
classification is derived from the scoreboard's own dates.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import history_format as hfmt  # noqa: E402

HISTORY = "docs/calibration/history.md"
DEFAULT_K = 4
SATURATED, DISCRIMINATING, FAILING, INSUFFICIENT = (
    "saturated", "discriminating", "failing", "insufficient")


def scenario_streaks(blocks, form=None):
    """{scenario: [verdict kinds, oldest first]} across run blocks.

    `form` filters to one plant population — a dev streak and a holdout streak are different
    measurements of different sets and must not be concatenated into one history. P
    (2026-08-15): the population is form + isolation; when a `form` is given, blocks whose
    isolation differs from baseline are also excluded (a no-playbook streak is a different
    measurement). `form=None` keeps the legacy "all forms" behaviour but STILL drops
    non-baseline-isolation blocks — a no-playbook run is never part of the normal streak.
    """
    out = {}
    for b in blocks:
        if form is not None:
            if not hfmt.population_matches(b, {"form": form}):
                continue
        elif hfmt.population_of(b)["isolation"] != hfmt.POPULATION_BASELINE["isolation"]:
            continue
        for r in b["rows"]:
            if r["kind"] == "INVALID":
                continue          # an env failure is not evidence about the plant
            out.setdefault(r["scenario"], []).append(r["kind"])
    return out


def classify(kinds, k=DEFAULT_K):
    """(label, detail) for one scenario's ordered verdict history."""
    n = len(kinds)
    if n == 0:
        return INSUFFICIENT, "no measured runs"
    if kinds[-1] != "PASS":
        return FAILING, "latest run {}".format(kinds[-1])
    trailing = 0
    for kind in reversed(kinds):
        if kind != "PASS":
            break
        trailing += 1
    if trailing >= k:
        return SATURATED, "{} consecutive PASS".format(trailing)
    if n < k:
        # Not enough history to distinguish "reliably passing" from "passed the few times we
        # looked". Reporting `discriminating` here would be a guess wearing a label.
        return INSUFFICIENT, "{} run(s) of history, need {}".format(n, k)
    return DISCRIMINATING, "{} consecutive PASS of {} runs".format(trailing, n)


def rollup(streaks, k=DEFAULT_K):
    counts = {SATURATED: 0, DISCRIMINATING: 0, FAILING: 0, INSUFFICIENT: 0}
    per = {}
    for sid, kinds in sorted(streaks.items()):
        label, detail = classify(kinds, k)
        counts[label] += 1
        per[sid] = (label, detail, len(kinds))
    return counts, per


def summary_line(counts):
    """The run-tail pointer. `insufficient` is reported FIRST when it dominates, so a young
    corpus never reads as a healthy one."""
    total = sum(counts.values())
    if counts[INSUFFICIENT] and counts[INSUFFICIENT] >= total / 2:
        return ("VITALITY: insufficient history for {} of {} plants — too young to classify; "
                "{} saturated / {} discriminating / {} failing so far (K={})".format(
                    counts[INSUFFICIENT], total, counts[SATURATED],
                    counts[DISCRIMINATING], counts[FAILING], DEFAULT_K))
    return ("VITALITY: {} saturated / {} discriminating / {} failing / {} insufficient "
            "(K={})".format(counts[SATURATED], counts[DISCRIMINATING], counts[FAILING],
                            counts[INSUFFICIENT], DEFAULT_K))


def main(argv=None):
    ap = argparse.ArgumentParser(description="plant vitality: does this plant still discriminate?")
    ap.add_argument("--history", default=None)
    ap.add_argument("--repo", default=os.path.dirname(HERE))
    ap.add_argument("--form", choices=("dev", "holdout", "all"), default="dev")
    ap.add_argument("-k", type=int, default=DEFAULT_K,
                    help="consecutive all-green runs before a plant counts as saturated")
    ap.add_argument("--as-of", help="accepted for symmetry; classification uses run dates")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args(argv)
    path = args.history or os.path.join(args.repo, HISTORY)
    try:
        with open(path) as fh:
            text = fh.read()
    except OSError:
        print("VITALITY: unmeasured (no scoreboard at {})".format(path))
        return 0
    blocks, skipped = hfmt.parse_run_blocks(text)
    if skipped:
        # Loud, because a header the parser cannot read is a run this instrument is blind to.
        print("VITALITY: {} run header(s) unparsed and EXCLUDED — the reading below is "
              "incomplete".format(skipped), file=sys.stderr)
    form = None if args.form == "all" else args.form
    counts, per = rollup(scenario_streaks(blocks, form), args.k)
    if args.verbose:
        for sid, (label, detail, n) in sorted(per.items(), key=lambda x: (x[1][0], x[0])):
            print("  {:52} {:15} {}".format(sid, label, detail))
    print(summary_line(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
