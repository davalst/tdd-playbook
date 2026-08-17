# Gate change journal — APPEND-ONLY (lift/ratchet D3)

Removing a gate surface — a SKILL.md `## ` section, an `agents/*.md` brief, or a
`commands/*.md` file — is the deletion-ratchet's cheap direction, and
`check_scoreboard_integrity.py` rule (d) exits RED on it unless the removed name appears
HERE, in text appended since the trusted baseline. Additions never need an entry: gate
removal costs what gate addition costs; addition never pays the removal toll.

This file is itself append-only under rule (a): truncating or rewriting it to
retro-authorize a removal is an integrity RED. Entry format, one line each:

`- <YYYY-MM-DD> · <exact removed name (heading text or filename)> · <why, and what supersedes it>`

## Entries

## 2026-08-06 — ledger coverage: one window instead of two

`ledger.py cmd_check` diffed gate surfaces from the EPOCH while reading the AUTHORIZING
entries from `--baseline-rev`. Two windows, so the freshness control had no fixed meaning:
at v1.22.0/v1.26.0 no `ledger.md` existed, `git show` failed, the "added since baseline"
text was the whole file and EVERY entry read as fresh; the moment v1.28.0 was tagged that
text became empty and NO entry could be fresh. Vacuous, then impossible — and the flip was
triggered by `civerd_gate.sh` resolving its baseline with `git describe --tags`, i.e. by
cutting a tag, not by anything about the ledger. Five false RED lines, minutes after the
v1.28.0 tag.

Both halves now read from the same `rev` (the epoch). The freshness control is REPLACED,
not dropped: an entry that has already been SCORED cannot authorize a later change — a
prediction that has been priced is spent. That is what "new this cycle" was reaching for
and it does not depend on which tag happens to be newest.

Net: one clause loosened (append-window freshness, which was vacuous in every run this
repo has ever made), one added (scored entries are spent). Pinned by
`test_harness.py` — a unit pair on `fresh_ids_from` plus a whole-repo invariant that
`check` returns the SAME verdict under the newest tag as under an old one. Journaled here
because it changes what the gate enforces, and rule (d) exists so that is never a silent
edit. Related: the same-day `check_scoreboard_integrity` change to name the RESOLVED
baseline sha on success as well as failure — same class, found by CIVerd.

## 2026-08-17 — §5b lands; the open-upgrade placeholder is retired

Removed name, verbatim including its heading marker (rule (d) matches the exact string):

`## Open upgrade — circle back with David (don't silently bake in)`

`- 2026-08-17 · superseded by §5b "Agent evals — testing what an agent DOES", which is the
discipline that section existed to promise.`

The removed section was a standing IOU: it named the load-bearing rule to debate
(deterministic-oracle evals gate, LLM-judge evals trend) and told the reader to raise it with
David when agent-eval work came up. It had been pending for months while §8's `[→EVAL]` tag
pointed at it and §5a's MCP bullet forward-referenced it — a promise with two live callers and
no implementation.

§5b supersedes it and CORRECTS it. The IOU's framing — "deterministic-oracle evals are blocking
CI gates" — is too coarse, and shipping it verbatim would have installed a flaky gate: the
oracle is deterministic but its SUBJECT is not, so "did the agent refuse / pick the right tool /
get the count right" is stochastic no matter how mechanically it is checked. §5b splits on
agent-path INDEPENDENCE instead: invariants true regardless of what the agent chose may block;
path-dependent outcomes run k/k over N with AMBER, reusing `run_calibration`'s existing rule
rather than inventing a second one.

Net: one gate surface removed, one larger surface added in its place, and the removed section's
own claim is narrower in the replacement than it was in the original — the direction rule (d)
exists to make visible. The replacement is pinned by needles + a planted-stripped twin in
`test_agents.py`, so it cannot quietly regress to prose the way its predecessor sat unimplemented.
