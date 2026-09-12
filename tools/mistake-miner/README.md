# Mistake miner — reference prototype

Validated prototype for the plan at
`docs/plans/gated/2026-09-12-mistake-miner-and-reflex-router.md`.

    python3 tools/mistake-miner/mine_proto.py <path-to-a-transcript.jsonl>

Transcripts live under `~/.claude/projects/<encoded-project-path>/*.jsonl`, plus a
`subagents/` subdirectory per project whose files also matter — a large share of the
sharpest findings come from adversary subagents.

## Reference run — NOT reproducible off the originating machine

These numbers come from one cloud-session transcript (1,218 records, 3.4 MB) that exists
only in an ephemeral container and was never committed. They are recorded as the SHAPE to
expect, not as a test anyone else can run.

    candidate mistake-events: 16
    signals: self_correction 10 · vacuous_test 5 · stale_fact 3
             nonexistent_ref 3 · refuted_claim 3 · wrong_threshold 1

Back-linking (discovery record -> the earlier record that committed the error):

| error | commission | discovery | gap |
|---|---|---|---|
| invented a function (`read_current`) | 613 | 715 | 102 |
| vacuous test (`spike times are ordered`) | 435 | 745 | 310 |
| arbitrary threshold (`1%`) | 232 | 324 | 92 |
| stale claim (`two readers take no population`) | 715 | 716 | 1 |

**The gap=1 row is a KNOWN BUG, not a target.** It means the linker matched the discovery
turn's own restatement of the error. A correct back-linker excludes the discovery record
and text quoting it; that row should then link earlier or report no link.

## What the prototype proved, and what it did not

PROVED: mistake-events are extractable from a raw transcript at a useful rate (~16 per
session), and a discovery can be linked back to the turn that committed the error across
gaps of 100-300 records.

NOT PROVED: that the rate holds across many sessions; that the taxonomy survives contact
with a few hundred real events; that the extracted features carry enough signal to predict
anything. Those are D1-D3 and D6 in the plan.

## Two design facts this prototype established the hard way

1. The turn that PRINTS a mistake sits 100-300 records after the turn that MADE it.
   Features must come from the commission turn; the label comes from the discovery turn.
2. Tool NAMES carry no signal — every event's preceding tools read `['Bash','Bash',...]`.
   Features must be built from command content, paths, and the shape of the claim.
