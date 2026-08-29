# REVISED — check the CLAIM against the record. Drop the tree hash entirely.

**Supersedes** `gate-provenance-plan.md`, rejected by three independent reviews:
`architecture-adversary` **BAND-AID (5)**, `edge-case-adversary` **GAPS (14)**,
`intent-adversary` **DRIFT (1)**. Every load-bearing finding verified by me at source.

## Why the first plan died — three of these are my own errors

- **The trigger was the wrong fact.** It keyed on tree equality. `CLAUDE.md`'s release order
  gates at step 1 and bumps the version at step 2, so a release commit's tree can NEVER equal
  the gated tree — meaning `uncovered` would have fired hardest on the **best-verified commits
  in the repo**. Signal inverted at exactly the population it exists to protect.
- **My prior-art sweep missed a sibling.** `gate_plan.py:140::collect_changed_paths` already
  enumerates the exact file set D1 specified (committed + staged + unstaged + untracked
  non-ignored), and `gate_runner.py` **already imports `gate_plan`**. I swept for *how I would
  have built it* (`write-tree`, `tree_sha`) rather than *what it does*. The §0 rule I added
  yesterday failed on its second use, and that lesson outlives this plan: **sweep for the
  behaviour, not for your own intended implementation.**
- **My reverse sweep named three consumers and all three were wrong.** `gate_yield` reads the
  guard event log; `render_reference` and `readable_surface` read `gate-manifest.json`. The
  run store has **one writer and one deleter, and no reader at all** — so D1+D2 would have
  been a write-only loop, in a plan that cited §12's exhaustive-negative rule while breaking it.
- **D1 would have shipped green-and-dark.** `gate_runner.py:93-97` filters metadata through a
  12-key allowlist; a new field is silently discarded. A test on the in-memory dict passes.
- **`git notes` rots here.** No prior art in the repo, doesn't survive the rebases this repo
  does routinely, isn't pushed by default, and `reset_plan.py:168` lists the run store as
  resettable — so "no matching run" conflates *uncovered* with *pruned* (`keep=20`, about a
  week of history).

## The finding that replaces it

**The defect is a FALSE CLAIM, not an ungated tree.** The ask, verbatim, was *"warn when you
fake out a commit that never happened"* — a commit asserting a pass that did not occur. That is
a claim-vs-evidence question, which is the shape this repo already handles well
(`verify_citations.py`: *no claim before resolving evidence*).

Using the claim as the **trigger** while the run record stays the **evidence** does not violate
"compute the edge, don't assert it" — that rule forbids a claim being the *evidence*, which is
the opposite of this.

**And it needs no new field.** Verified against the live store: runs already record
`result: GREEN|RED`, `mode`, `commit`, `started_at`. A commit whose message asserts a green
gate, made when the most recent run was RED, is detectable **today**.

## D1 — `bin/gate_claim.py`: does the claimed verdict match the record?

Given a commit range, for each commit whose message asserts a gate verdict, resolve it against
the run store and report `HONOURED` / `UNSUPPORTED` / `CONTRADICTED`.

- **CONTRADICTED** — the message claims GREEN and the newest run before that commit was RED.
  This is the faked commit, and it is the only state worth speaking loudly about.
- **UNSUPPORTED** — a claim with no run record in range. Distinguish `pruned` (older than the
  store's 20-run window) from `absent` — absent data is UNMEASURED, never zero.
- **Commits that claim nothing are SILENT, by construction.** No WIP-checkpoint problem, no
  push-vs-commit compromise, no 90-day trial to discover the over-fire rate.

**Edge cases:** message claims a *focused* run but only a full run exists (and vice versa) ·
several runs between two commits · a run that started before the commit and finished after ·
the store empty or pruned · a repo with no store at all (downstream: **silent**, and it must
distinguish "no gate here" from "gate here, claim unsupported") · rebased/squashed commits ·
the claim appearing inside quoted text in a message (this very plan quotes the phrase).

**Integration surface.** *Consumes:* the run store `index.json` — **and it would be that
store's first reader ever**, which is the honest statement of the §6c loop this closes rather
than the three non-consumers I previously named. *Emits → named consumer:* the report line →
`commands/tripwire.md`'s existing `Means:`-style forced line, at field granularity.
*Activation:* a CLI, invoked; no hook, no mode, no tenth knob.

## Explicitly NOT built

- **No tree hash.** It was the over-fire source and it is unnecessary for the actual defect.
- **No `git notes` stamp.** No consumer, rots on rebase, duplicates
  `host_contract.append_event` — which already has `ASSURANCE_LEVELS` distinguishing
  `unmeasured` / `local_claim` / `ci_verified`, and already has a reader in `tdd doctor`.
  If a record is wanted later, that is the store.
- **No `git push` hook.** `tag_guard` logged two live false positives on 2026-08-27 from
  grepping a command instead of parsing it; a `git push` matcher would inherit that, and the
  push range is unknowable at hook time (bare `push`, no upstream, stale remote ref).

## §0.3 Tests (red first, every row twinned)

| test | proves |
|---|---|
| claim GREEN + newest prior run RED → **CONTRADICTED** | the motivating defect; twin: claim GREEN + run GREEN → HONOURED |
| a commit claiming nothing → silent | the WIP-checkpoint population, by construction |
| the claim inside a quoted block in the message → not a claim | this plan's own text would otherwise trip it |
| no run store at all → silent, and says "no gate here" | downstream repos; twin: store present, claim unsupported → speaks |
| pruned window → `pruned`, never `UNSUPPORTED` | absent ≠ zero, at the `keep=20` boundary |
| a run spanning the commit → attributed by `started_at`, not by `commit` | `gate_runner.py:222` already reads HEAD at the END of a run |
| vacuity: an empty range reports `0 claims checked`, never a clean pass | §4a |
| G5: the suite dirties no TRACKED file | fourth occurrence this week |

## §0.5 Decay contract
Metric: claims checked, and CONTRADICTED found. **Kill condition:** if 90 days pass with zero
CONTRADICTED and zero UNSUPPORTED, the honest reading is that the doctrine already works and
the tool is ceremony — delete it. **Never blocking** without a measured false-positive rate.

## Open question — DAVID'S, not review's
The first plan chose push-time warning over commit-time and I made that call myself; the
intent-adversary flagged it as a narrowing I should have asked about. This revision moots the
timing question — a claim check is silent on everything that doesn't claim — but it does NOT
warn at commit time. It reports when invoked. **If you want it to speak automatically, that is
a hook, and hooks are where the last two guards died.** Your call, not mine to settle quietly.
