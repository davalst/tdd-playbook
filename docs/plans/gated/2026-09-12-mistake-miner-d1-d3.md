# §0 Plan — Mistake Miner D1–D3 (extractor, back-linker, feature extractor)

> **DATA MOVED TO A PRIVATE REPO — 2026-09-12.** The mistake miner reads real session
> transcripts, so its code, its corpus, its hand-built ground truth and its taxonomy
> sample now live in **`davalst/mistake-miner` (private)**. `davalst/tdd-playbook` is
> PUBLIC. This file is kept here as the §0 planning record the house rules require to land
> in-repo; every **verbatim session quote and session UUID has been redacted** out of it,
> and the unredacted copy is in the private repo under `docs/`.



**Date:** 2026-09-12 · **Workstream:** `mistake-miner`
**Parent plan:** `docs/plans/gated/2026-09-12-mistake-miner-and-reflex-router.md` (brought onto `main` from
`claude/flybrain-onboarding-gafjnh`; the branch copy and the Downloads copy were diffed and
are byte-identical).
**Reference materials, all now on `main` and all read from there:**
`docs/plans/gated/2026-09-12-mistake-miner-and-reflex-router.md` (the parent plan, with the
step-zero corrections appended as Appendix A), `tools/mistake-miner/README.md` (the
reference results and why they are not reproducible here), and
`tools/mistake-miner/mine_proto.py` (the prototype — **this path is the differential
oracle**, pinned here so it cannot silently resolve to the Downloads copy; verified
byte-identical to `2dd3311:tools/mistake-miner/mine_proto.py`).
**Scope of this plan:** step zero (FlyGM ground truth) + D1, D2, D3. **D4 onward is out of
scope** and gets its own plan (§7 below).

**Step zero is DONE and landed** — not in this file, but appended to the parent plan it was
ordered to correct, as `docs/plans/gated/2026-09-12-mistake-miner-and-reflex-router.md`
**Appendix A — FlyGM ground truth**. It answers the four questions asked (what is learned
versus fixed; the real trained parameter count; the concrete afferent and efferent
interfaces; library versus welded to MuJoCo) from the arXiv HTML full text and the
MIT-licensed code snapshot, and it corrects four rows of the parent plan's §1 table
including the one the parent plan leaned on hardest. Headline corrections: the synaptic
weights are **fixed buffers, not learned** (the parent plan had this backwards); the
trained set is **≈15.1M parameters** of which **0.085%** is the connectome-structured MLP;
the afferent interface **broadcasts one 32-vector identically to all 19,262 afferent
neurons**; and **the code is not released** — the parent plan's "Code | Released" row is
wrong, there is only an anonymous review snapshot with no checkpoints. The one row that
came out *better* than stated: the simulator weld is confined to stage 2, and this plan
builds stage one.

---

## 0. The acceptance problem, and the criteria that replaced it

The parent plan pinned acceptance to ONE transcript: 1,218 records -> 16 events, tally
`self_correction 10 · vacuous_test 5 · stale_fact 3 · nonexistent_ref 3 · refuted_claim 3
· wrong_threshold 1`, and four commission->discovery links at 613->715, 435->745, 232->324,
715->716.

**That transcript does not exist on this machine.** Established independently twice:

1. Exhaustive local sweep. `grep -rl` for each of the three named entities (<a fabricated function name, redacted>,
   `<a vacuous assertion, redacted>`, `<a stale claim, redacted>`) across all 3,252 `*.jsonl`
   under `$HOME`, plus `~/Downloads`, `~/.claude` and the repo, returns exactly four files
   and every one is a copy of the parent plan document itself (the Downloads `.md`, this
   session's transcript, this session's deliberation log, the paste-cache entry). No
   transcript contains them. Nothing under `~/.claude/sessions` or `~/.claude/cache` holds
   a cloud transcript either.
2. The originating cloud session said so itself, unprompted, and corrected its own brief:
   the transcript lived only in an ephemeral container, was never committed, and no local
   session can attach to a cloud session's history.

The reference numbers are therefore recorded as **the shape to expect, never as a test**
(`tools/mistake-miner/README.md`, commit `2dd3311` on
`claude/flybrain-onboarding-gafjnh`). The replacement criteria, as restated by the
originating session:

- **A1 — rate and mix.** Run the prototype against a spread of real local transcripts.
  Confirm the extraction rate is broadly comparable to ~16 events per ~1,200 records, and
  that the signal mix is plausible with self-corrections dominating. A *shape* check on a
  real population, not a number match on one sample.
- **A2 — a pre-registered hand-built ground truth.** Find five mistakes by hand in real
  local transcripts. Record, for each, the discovery record index and the record where the
  error was actually committed. **Write that table down and commit it BEFORE the linker is
  run against it.** The pre-registration is the whole point: it is the difference between
  testing the linker and fitting it. Landed at
  `calibration/mistake_miner/tests/ground_truth.json`, committed in its own commit that
  contains no linker code.
- **A3 — the gap=1 self-link is gone.** The linker must exclude the discovery record and
  text quoting it.

  **A3 as first drafted was unfalsifiable** and is rewritten. The draft said the event
  "must either link to a genuinely earlier assertion *or report no link*" — a disjunction
  that a linker returning `None` for every discovery satisfies perfectly. Three additions
  close it:
  - **a positive floor**: A2's five pre-registered links must resolve to the *correct*
    commission record. An always-`None` linker fails A2, so it cannot buy A3.
  - **a negative control for rule (b)**, which is over-broad and currently untested for
    precision. Rule (b) excludes *any* record carrying ≥1 signal, but in review-heavy
    sessions one assistant turn routinely discusses a correction to defect X *and* commits
    the assertion that becomes defect Y. The ground truth must include one such record with
    the correct verdict stated, so rule (b)'s false-negative rate is asserted rather than
    invisible.
  - **planted mutants.** This repo's own release rule is that every mechanical change ships
    with a planted-input test. Four mutants must turn the A2 score RED: rule (b) removed;
    earliest-match replaced by latest-match; a decoy-matching linker; and an unconditional
    `None` linker. A test that has never failed against a deliberately broken subject is an
    unvalidated gate.

  **And the ground truth needs decoys.** A pre-registered table of five true pairs still
  does not exercise the linker's real failure modes — picking the latest match instead of
  the earliest, matching a decoy, matching a substring inside a path. For each hand-found
  mistake, the entity's *other* earlier occurrences are enumerated and recorded alongside
  the true commission, so "picked the right one among N candidates" is what gets scored,
  not "found something".

**A supplementary check, deliberately NOT called acceptance: differential equivalence.**
The generalised extractor in `--compat` mode emits exactly the prototype's
`(record_index, sorted(signals), evidence)` triples on every transcript scanned, with the
unmodified prototype at `tools/mistake-miner/mine_proto.py` as oracle. This is worth having — it catches accidental drift in the
regexes, the record-index convention, and the `text_of` rule during generalisation. It is
NOT evidence that the extractor is *correct*: my code is derived from the prototype, so
the two can agree while both being wrong, and the check would still pass. It is a
regression harness, and it is labelled as one.

## 1. Deliverables

### D1 — the extractor
`calibration/mistake_miner/extract.py`

- Walks `~/.claude/projects/<PROJECT>/*.jsonl` **and**
  `~/.claude/projects/<PROJECT>/<session-uuid>/subagents/agent-*.jsonl`. (Note: the actual
  layout nests subagents one level deeper than the brief described — under a per-session
  directory, not directly under the project. Measured: 1,027 main + 253 subagent = 1,280.)
- `record_index` semantics preserved from the prototype exactly: index into the sequence of
  **successfully parsed** JSON lines, bookkeeping records included. Anything else
  renumbers every published index.
- `--compat` (default ON for the differential test): identical signal regexes, identical
  `text_of` (assistant `text` blocks only, thinking excluded), identical evidence rule
  (first sentence matching any signal, 220 chars).
- **Widened recall, additive and flagged** — `--include-thinking` adds assistant `thinking`
  blocks. Measured separately so A1 still holds with the flag off. Justified by finding 3
  (recall over precision) and by the schema: in a 10,214-record sample there were 983
  thinking blocks against 325 text blocks, so text-only discards the majority of assistant
  prose.
- Provenance on every event: repo, session id, transcript path, `is_subagent`.

*Done when:* A1's rate/mix check is satisfied on a real spread of transcripts, and the
differential-equivalence harness is green on every transcript scanned.

### D2 — the back-linker
`calibration/mistake_miner/backlink.py`

- Entity extraction from the discovery evidence: identifiers (`name`, `name()`),
  double/single-quoted spans, file paths, and numeric thresholds (`1%`, `0.5s`).
- Commission search over records with `index < discovery_index`, on the same transcript.
- **Exclusions (this is the gap=1 fix):**
  (a) the discovery record itself;
  (b) **any record that is itself a discovery record** (carries ≥1 signal) — the principled
      form of the bug: record 715 was the <a fabricated function name, redacted> *discovery*, and 716 back-linked to
      it because 715 restated the error while reporting it. A report about an assertion is
      not the assertion;
  (c) matches occurring inside quotation context or immediately after a correction verb
      ("I said X", "the claim that X", `"X"`).
- **Deliberately NO minimum-gap threshold.** A `min_gap=2` would make the fixture pass while
  being exactly error class E8 (`arbitrary-threshold`) committed inside the tool built to
  detect E8. Rule (b) is the mechanism; the gap distribution is an *output*, never an input.

*Done when:* the linker is scored against the PRE-REGISTERED A2 ground truth (written and
committed before the linker ran), and A3 holds. The score is reported as it comes out —
including a bad one.

### D3 — the feature extractor
`calibration/mistake_miner/features.py`

Built from the **commission** record and a bounded window before it, per finding 1. Per
finding 2, tool names are recorded but carry no weight; the vector is content-derived:

- **action**: tool name; for Bash the head verb + a `writes` boolean; target paths.
- **file class**: test / source / doc / config / fixture-data / plan / journal.
- **session state**: files read vs edited so far; **whether this path was read before being
  written**; failed tool calls in the window; repeat-edit count on this path.
- **claim shape**: asserts a `file:line`? a count? a negative? an `N/N` completion?
- **guard context**: guards that actually FIRED, detected structurally on the real emitted
  signature `⚠️  TDD Playbook · <gate>` (measured present: exitcode 528, tagguard 46,
  tripwire 36, testlock 18, cite 10, snapshotguard 4, testweaken 3, redlock 3,
  fixtureguard 2). **Not** by the substring `weakening_guard`, which in THIS repo matches
  the guard's own source being read — 217 such hits, essentially all of them file contents.
  That is the §12 proxy trap: a check literally true while describing something else.
- **plan context**: a committed plan exists for the branch; a TEST-LOCK is held.

*Done when:* the **named semantic** fields discriminate, asserted per field. The first
draft of this check — "the count of distinct feature vectors must be a large fraction of
the event count" — was unfalsifiable twice over and is replaced: it stated no threshold, so
the pass condition would have been chosen after seeing the number (the very move §6 warns
against, committed by the check meant to prevent it); and it was gameable by construction,
because target paths are near-unique per event, so vector distinctness approaches 100%
while every semantic field stays constant — the `['Bash','Bash','Bash']` degeneracy wearing
a unique path as a nonce. Note the inconsistency that gave it away: this plan refuses an
arbitrary `min_gap` on E8 grounds and then required an *unnamed* threshold here. An
arbitrary threshold can be written red-first and argued with; an unstated one can never
fail.

The replacement, with paths, session ids and record indices EXCLUDED from the computation:

- each of `file_class`, `read_before_write`, `claim_shape`, `guard_fired`, `writes` must
  take **≥2 distinct values** across the mined corpus, with the **minority value appearing
  ≥5 times** — so a field that is constant, or true twice in 264 events, fails;
- a hand-built contrasting pair must differ in **≥3 fields drawn from that named set**
  (not from the path/nonce fields);
- the stateable failing input: a corpus where `guard_fired` is False for all 264 events.

### D3 addenda forced by the review — `read_before_write` is the fragile one

It is the feature D3 exists for, and four defects were identified before any code:

1. **Path normalisation.** This filesystem is case-insensitive and this very session is
   configured with *both* `/Users/davidalston/Documents/GitHub/tdd-playbook` and
   `/Users/davidalston/documents/github/tdd-playbook` as working directories. Two spellings
   of one file would read as two files. Normalise case, `~`, and relative-vs-absolute.
2. **Every write tool counts.** `Edit`, `Write`, `MultiEdit`, `NotebookEdit` — plus Bash
   writes a head-verb heuristic misses: `cat > x`, `sed -i`, `tee`, `python3 script.py`.
3. **Window scope was self-contradictory.** The draft said both "a bounded window before
   it" and "so far this session". Those are different answers. **Decision: session-to-date
   for the read/write ledger** (the question "was this path ever read before being written"
   is not a windowed question), and a bounded window only for the volatile counters
   (failed calls, repeat edits). Stated so it is asserted, not assumed.
4. **The parent/subagent boundary is a predictable systematic defect.** Subagent
   transcripts are mined as separate files, so a parent-session read followed by a subagent
   write reports `read_before_write=False` for every such pair. **Decision: the read/write
   ledger is keyed per SESSION TREE**, with subagent transcripts folded into their parent
   session's ledger by their `<session-uuid>/subagents/` parentage. Asserted with a test
   that spans the boundary.

### D3 addendum — the guard-fired detector has a live encoding hazard

It keys on the literal `⚠️  TDD Playbook · <gate>` (emoji + U+00B7). The prototype opens
files as `open(path, errors='replace')` with **no encoding argument**, and `--compat`
mandates matching that. Under an ASCII-preferred locale
(`PYTHONUTF8=0 PYTHONCOERCECLOCALE=0 LC_ALL=C`) the signature decodes to eight U+FFFD and
`guard_fired` silently becomes False for the entire corpus — and the `evidence` strings
change too. Latent on this Mac because Python 3.14 coerces C→UTF-8; live on any host or
cron/subprocess environment that sets those vars. **Decision: read with an explicit
`encoding="utf-8", errors="replace"`.** This is a deliberate, stated divergence from strict
prototype bug-compatibility: pinning the prototype's locale-dependence would pin a defect.
A test runs the extractor under the hostile locale and asserts identical output.

---

## 2. Integration surface

| Deliverable | consumes | emits → named consumer | activation |
|---|---|---|---|
| D1 extractor | transcript `*.jsonl` | `MistakeEvent` records → D2 `backlink.link()` and the CLI's JSONL writer | `cli.py` `mine` |
| D2 back-linker | D1 events + the same parsed records | `commission_record`/`gap` fields → D3 `features.extract()` | same CLI pass |
| D3 features | commission record + window | `features{}` dict → the D4 classifier's prompt payload (NEXT session) and D6's design matrix | same CLI pass |

**Honest island note.** D3's only consumer inside this session is the JSONL/discriminability
report; its real consumers (D4, D6) do not exist yet. That is deliberate sequencing, not a
dangling emit — but it is the one place where "built" is ahead of "wired", and it is stated
rather than glossed. It becomes a real island if D4/D6 never land, so this plan's own
follow-up (§7) is the consumer commitment.

**Nothing is wired into the gate.** Verified mechanically: `gate-manifest.json` discovers
`suite_glob = plugins/tdd-playbook/tests/test_*.py` plus four fixed stages
(`calibration/test_harness.py`, `dataflow_sweeps.py`, `calibration/ledger.py`,
`calibration/plant_forms.py`). Tests live at `calibration/mistake_miner/tests/test_*.py`,
which that glob does not match, and `calibration/mistake_miner/**` is in neither
`force_full` nor any `safe_rules` pattern. The tool runs by hand.

**Not vendored.** Verified first-hand, not taken from the parent plan: `COPY_TREES` in
`scripts/install_into_repo.py:47` is rooted under `plugins/tdd-playbook/` and lists
`skills/tdd-playbook`, `commands`, `agents`, `adapters`, `bin`, `hooks/scripts`.
`calibration/` is a top-level directory, appears nowhere in the installer
(`grep -n calibration scripts/install_into_repo.py` → no output), and therefore does not
ship downstream. Note the corollary the parent plan flagged and which also checks out:
`bin` IS vendored, so a trained weights file placed there WOULD propagate.

---

## 3. No guard is modified or deleted

Not one, per the brief and per parent-plan §6 (distribution shift: the corpus is drawn from
sessions where the guards were firing). This plan touches no file under
`plugins/tdd-playbook/hooks/`.

## 4. Mining scope, and where the corpus lives

### 4.1 Scope — gated on David, with the denominator corrected

The first draft of this section said "329 main transcripts", which was wrong. Measured
properly (a control carries its denominator, §12):

| scope | main `*.jsonl` | subagent `*/subagents/agent-*.jsonl` | total |
|---|---|---|---|
| `-Users-davidalston-Documents-GitHub-tdd-playbook` | 228 | 103 | **331** |
| whole store (189 project dirs) | 1,028 | 255 | **1,283** |

Only the tdd-playbook scope is mined in this session. `cheliped` (737 files) and the
remaining project directories are **counted but not read**, pending David's decision
(parent plan §6 privacy default: opt-in per repo).

**A scope trap found by review and NOT silently resolved.** An exact directory-name match
drops sibling project directories that hold this repo's own work:
`-Users-davidalston-Documents-GitHub-tdd-playbook-calibration` and ~33
`-private-tmp-...-scratchpad-...` directories created by this repo's own worktrees and
scratchpads. Including them widens "tdd-playbook" beyond what David authorised; excluding
them loses real sessions. **Decision: the exact-match scope is what runs, the siblings are
enumerated and reported as a named gap, and widening is David's call.** The scope selector
is pinned by a test asserting the exact directory roster it resolves, so the roster cannot
drift silently.

### 4.2 Where the corpus lives — the answer, not a deferral

**`calibration/mistake_miner/corpus/` — inside this repo, git-tracked, append-only JSONL.**

Why there, on four counts:

1. **It does not leave the machine except to David's own private remote.** The alternative
   — outside the repo, in a scratch or home directory — has no version history, no
   integrity story, and is the thing that happened to the reference transcript.
2. **It is not vendored downstream.** Verified first-hand, not inherited from the parent
   plan: `COPY_TREES` in `scripts/install_into_repo.py:47` is rooted under
   `plugins/tdd-playbook/` and lists `skills/tdd-playbook`, `commands`, `agents`,
   `adapters`, `bin`, `hooks/scripts`. `calibration/` appears nowhere in the installer
   (`grep -n calibration scripts/install_into_repo.py` → no output). So a corpus placed
   there cannot propagate into cheliped or any other repo that vendors the Playbook.
3. **`bin/` IS vendored, so that is where a trained model must NOT go.** The parent plan
   flagged this and it checks out. Recorded here as the propagation channel to watch at D7.
4. **It sits beside the calibration corpus it is a sibling of.** `calibration/corpus/` is
   already the repo's append-only, immutability-checked store of planted defects. Same
   discipline, same directory, same reviewer instincts.

**The privacy consequence, stated rather than buried.** Mined rows carry *verbatim prose
from real sessions* — evidence quotes, command text, file paths. Committing them to
`davalst/tdd-playbook` means that prose is in a git history that is currently private but
whose visibility is one settings change away, and history is not easily redactable. Two
mitigations are in scope now: rows store the transcript path and record index so a quote
can always be re-derived, meaning **evidence quotes are capped at 220 characters** (the
prototype's own bound) rather than storing whole turns; and `calibration/mistake_miner/corpus/`
gets its own `.gitignore`-adjacent decision point — **if David prefers the corpus untracked,
that is a one-line change and the tooling is unaffected.** Raised as decision Q2 in the
report.

### 4.3 The taxonomy question needs a producer — D3b

Review found that the E1–E12 question had no deliverable: D1–D3 emit six *signals*, and
E-class assignment is D4, which is out of scope. The user asked for it ANSWERED, not
deferred. So:

**D3b — hand-labelled taxonomy sample.** Take a stratified sample of the mined events, map
each BY HAND to E1–E12 (no classifier — D4 is out of scope and a classifier's labels would
be the thing under question), and report which classes are empty, which are overloaded, and
which real events fit none of the twelve. Output:
`calibration/mistake_miner/corpus/taxonomy_sample.json` plus the verdict in the report.
This is judgement work done openly and at small scale, which is the honest way to answer
"does the taxonomy survive contact with the data" before spending money classifying
thousands of events into it.

### 4.4 The report IS a deliverable — D3c

Also missing from the first draft. **D3c — the session report**, containing: transcripts
scanned (with the corrected denominators), events extracted, the full signal tally, the
back-link success fraction and the gap distribution, **two or three real events walked
end-to-end** (commission record → features → discovery record → label), the FlyGM
corrections (Appendix A of the parent plan), and the three answers. Written to the
conversation and summarised in `docs/plans/gated/` alongside this plan.

## 5. Edge cases (`@pytest.mark.edge` equivalents — asserted in the test module)

- empty transcript; transcript of only bookkeeping records
- unparseable lines mid-file (must not shift `record_index` for parsed ones — the prototype
  skips them, so index counts parsed lines only)
- assistant record with `content` as a bare string, not a list
- assistant record with thinking blocks and no text block
- a signal firing in a `tool_result` (user record) — prototype scans assistant only; keep
- discovery with zero extractable entities → no link, not a crash
- entity appearing ONLY in the discovery record → no link (A3)
- entity appearing in an earlier record that is itself a discovery → skipped (rule b)
- multi-signal record (counted once as an event, all signals retained)
- a path written that was never read (the `read_before_write=False` case D3 exists for)
- CRLF / non-UTF8 bytes (prototype opens with `errors='replace'`; match it)

### 5b. Test categories the review found missing — each with its assertion

- **Determinism.** Mine twice; assert byte-identical output JSONL. Real hazards: `glob`
  order across 331 files, set/dict iteration over extracted entities, first-match-wins in
  the linker. The file roster is `sorted()` and that is asserted.
- **Ordering stability.** Event order = ascending `record_index`; signal order = the
  prototype's `SIGNALS` declaration order. Both asserted, neither left to `sorted()`.
- **Encoding.** A fixture carrying emoji, the guard signature, CRLF, a lone surrogate, and
  a 220-character evidence boundary landing mid-emoji (the prototype truncates at 220).
  Plus the whole extractor run under the hostile locale, asserting identical output.
- **Scale.** Measured largest real inputs: **22 MB / 8,486 records (44 events on its own),
  12 MB, 9.5 MB.** `load()` materialises every record and the linker's backward search is
  O(events x records x entities). Assert the largest fixture completes under a stated
  wall-clock and memory ceiling, so the practical limit is found here and not on D6's full
  corpus run.
- **CLI wiring.** `cli.py mine` is the sole activation surface and had no test. One test
  runs the CLI end-to-end over a fixture directory and asserts the three modules are wired
  to each other through it — units passing individually does not prove the pipeline exists.
- **`--include-thinking`.** The widened-recall path was to be "measured separately" with
  nothing asserted, i.e. shipped unasserted. It gets a test: a fixture whose only signal
  lives in a thinking block yields zero events with the flag off and one with it on.
- **Provenance fields.** `repo`, `session_id`, `transcript_path`, `is_subagent` asserted
  present and correct on every emitted row — including `is_subagent=True` for a
  `*/subagents/agent-*.jsonl` input.

## 6. What would falsify this work

- The differential harness fails on any transcript → my extractor drifted from the
  prototype during generalisation; fix mine, not the test. (Stated as the harness it is —
  the earlier wording called this "A1" and treated it as acceptance, which the acceptance
  rewrite superseded.)
- **A1's rate/mix check fails**: the extraction rate is nowhere near ~16 per ~1,200 records,
  or `self_correction` does NOT dominate the mix. The user named that second condition
  specifically, so it is a falsifier and not a curiosity.
- The mined corpus is tiny (say <50 events across 329 transcripts) → the signal set does not
  generalise off its one validation sample, and the programme is cheap to kill here.
- The back-link rate is near zero, or the gap distribution collapses to ~1 → D2's entity
  matching is the wrong mechanism and D6 has no features to learn from.
- Feature vectors are near-degenerate → finding 2 was not actually addressed.

Any of these is a reportable result, not a reason to reach for a flattering number.

## 7. NEXT SESSION (D4–D6) — written after this session's measurements land

Deliberately left to be filled from real data at the end of this session, because the
taxonomy question ("which E-classes are empty, overloaded, missing") can only be answered
against the mined corpus. See the appended section.
