# REVISED — make *Consumes* citable. Do not build a drift detector.

**Supersedes** `drift-detector-plan.md`, which three independent reviews rejected:
Codex **DON'T-BUILD**, `architecture-adversary` **BAND-AID (5)**, `integration-adversary`
**ISLANDS (6)**. Every load-bearing finding below I verified myself.

## Why the original plan died

**The extraction was the whole design, and it fails on its own motivating corpus.** Measured:
`cite_guard.claims_in` extracts **1 of my 3** failure sentences. `verify_citations.find_citations`
— the reuse I called the plan's foundation — returns `[]` on failure 1, because its `_CITE`
grammar requires `:\d+`, and that anchor is most of what suppresses its false positives. So the
headline reuse was nominal and a new looser regex was always going to be written. That is
structurally identical to `cite_guard`, which fired on 11.1% of turns and was abandoned today.

**The frozen calibration would have failed in CI.** `d102bd9` and `57d1ffa` are on **zero refs** —
dangling objects in one working copy, because this morning's rebase rewrote them to `36fd97e`
and `523fdd4` (which differ by 27 files). `.github/workflows/gate.yml` clones by ref. Every
fixture would have passed locally and gone dark in the only independent re-execution there is.

**A `bin/` tool importing `cite_guard` breaks on Codex.** `CODEX_COPY_FILES` carries only
`_common.py` and `lock_guard.py`; `cite_guard.py` does not ship there. Silent degradation of a
fence-stripper is not a missing feature, it is a false-positive generator.

## The finding that replaces it

The §0 integration surface is **asymmetric**, and the failures land exactly on the soft half:

- ***Emits → named consumer:*** *"at FIELD granularity: cite the file:line in the CONSUMER that
  reads the specific field… if you cannot cite a line, the field is write-only."*
- ***Consumes:*** *"which EXISTING subsystems this plugs into."* Prose. Nothing resolvable.

**All three of my mechanically-detectable failures were consumes-side claims** — *"Refounded on
`bin/verify_citations.py`"*, *"I follow the `subagents/*.jsonl` sidecars"*, *"`capture.py` now
imports it from here."* One side of one clause demands a resolvable citation; the other accepts
prose; and the prose side is where the drift happened.

This repo already retired this exact defect shape ELSEWHERE, eight days ago. `review_ledger.py`
moved the answer to **authoring time** with a ref that is *"RESOLVED, not merely non-empty"* and
a validator that REFUSES the blank — because, per CLAUDE.md, *"nobody could honestly reconstruct
the answers"* after the fact. The original plan proposed reconstructing them from prose.

## D1 — Make *Consumes* citable (doctrine; no new tool)

`SKILL.md` §0 and `commands/tdd-plan.md`: a consumes row names `path::symbol`, not a subsystem.

    Consumes: bin/verify_citations.py::find_citations

Resolvable twice, both mechanically:
1. **At plan review** — does that symbol exist in that file? If not, the plan cannot be approved
   carrying it. **This catches failure 1 before a line of code is written**, which is strictly
   better than catching it after the diff.
2. **At Tripwire** — does the implementation actually reference it? Same subtraction as the
   abandoned detector, with **zero extraction surface**, because the plan DECLARED the row
   instead of a regex inferring it.

`bin/review_ledger.py::closure_evidence_exists` already parses and resolves `path::symbol`
against the real tree. Generalise it; do not write a second resolver.

## D2 — Pilot the untested simpler alternative FIRST

Codex's point, and it is fair: the one-sentence version has never actually been tried. Add to
`commands/tripwire.md` and `agents/tripwire-auditor.md` a forced line —

    Means: H honoured · A acknowledged · D drift

— and run it on several real Tripwire passes. **If the auditor honours it, no tool is needed.**
If it walks past it again, that is the evidence that justifies mechanism, and D1's structured
rows are what the mechanism reads.

## What is explicitly NOT being built

- No prose extraction. No commitment verb list. No path regex over plans. Ever.
- No `(instead: …)` grammar — it is a fourth dated-exemption shape with no owner or expiry, and
  `bin/_debt.py` exists because a previous review retired exactly that ("reuse, don't sibling").
  A deliberate deviation is recorded as debt in the shape the repo already has.
- No `--strict` flag: no stage would consume it.
- No git-rev fixtures: static files under `tests/fixtures/`, sha cited in the docstring.

## Honest limits, stated

- This catches *"you declared a means and didn't use it."* It does not catch *"you reasoned
  wrongly about how something behaves"* — failure 4, the one that actually cost the day.
- D1 only binds work that produces a §0 plan. Measured: **zero plan files committed in the last
  eight days**, including for the feature that produced this corpus. So the input channel is
  real but thinly used — that is a dated debt with an owner, not a silent deferral.
- If D2's pilot succeeds, D1 is doctrine-only and there is no code to review. That is the good
  outcome.
