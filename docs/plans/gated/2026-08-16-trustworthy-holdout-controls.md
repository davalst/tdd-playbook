# Plan — Trustworthy holdout controls: validate at authoring, judge fairness, supersede the bad

**Date:** 2026-08-16 · Follow-on to `holdout diagnose` (v1.38.0). Revised after TWO Codex adversary
reviews (13 findings total, all verified valid and folded in).

## PROGRESS (as of 2026-08-16)

- **DONE + shipped — D0 part 1 (register supersession schema):** commit `55f7756` (review record
  `docs/reviews/2026-08-16-holdout-control-validation-d0-schema.json`, gate green, pushed). The
  register now has `status` (current/legacy-invalid/known-overflag/asymmetric) + `supersedes`
  columns in `calibration/plant_forms.py` (`parse_register`/`format_register_row`/`ENTRIES_TABLE`/
  `VALID_STATUS`/`form_problems`), back-compat with 5-cell legacy rows; 9 red-first tests in
  `calibration/test_harness.py::_plant_form_tests` (search `D0:`). 449 harness checks green.
- **REMAINING (a fresh session picks up here):** the rest of D0 (status→scorer partition, reporting
  split, per-run population snapshot), D1 (validation gate + manifest), D2 (control-quality judge),
  D3 (authoring prompt), D4 (supersession remediation), + the integration ceremony. Everything below
  is the spec; the register-schema layer it builds on is now in place.

## Context — why this is being built

The first real holdout reading was **recall 8–9/10, FP 6–10/10**. `holdout diagnose` proved **0
misses are scoring quirks — all genuine**, concentrated entirely on the **controls** (10/10
flagged). Reading three confirmed the decisive finding: they are **broken controls, not verifier
over-flags** — one isn't actually clean (unguarded price arg), one has a greedy oracle regex that
punishes a *correct* explanation, one poses an ambiguous task.

**The FP number is measuring control-authoring quality, not verifier quality.** Root cause:
controls are authored by an adversary model *prompted to "bait a trigger-happy verifier"* and
approved **without ever running a verifier against them**. This plan closes that gap while
**preserving the vault's two load-bearing properties: immutability (hash-pinned bodies) and
eval-time containment (raw output / oracle never reach the eval verifier or persist).**

Reuse is the design center: the eval seams (`rc.stage`/`run_agent`/`oracle`/`verdict_for`/
`classify_failure`, `run_calibration.py:209/488/237/727/277`) and the authoring core
(`author_plants.generate_accepted_pairs` + `adversary_prompt`) already exist; the integration point
is the existing `cmd_approve_holdout` (`holdout.py:343`). No new engine.

---

## D0 — Immutability, status flow, and reporting model (specify FIRST)

Approved bodies are hash-pinned and **never edited or deleted** — bad items are SUPERSEDED.

- **Supersession is PAIR-LEVEL (Codex R2#2).** A plant+control pair is the unit. Retiring a bad
  control retires its paired plant too (→ a fresh replacement PAIR with new ids/hashes), so
  current recall and current FP never split across an asymmetric cohort. (If a future case needs an
  asymmetric retire, it must be explicitly labeled `asymmetric` in the register and excluded from
  paired-denominator reporting — not the default path.)
- **Status schema (versioned migration).** Extend the register (`plant_forms.parse_register`/
  `format_register_row`/`ENTRIES_TABLE`, `plant_forms.py:87/117/112`) to carry per-body
  `status ∈ {current, legacy-invalid, known-overflag, asymmetric}`, a `supersedes`/`superseded_by`
  link, and the content hash — with a bumped register schema marker and back-compat parse of old
  5-column rows. `vault_integrity_problems` learns the columns. Every transition is compare-and-swap
  on the body hash and validates the supersession graph has **no cycles / no dangling links**.
- **Status FLOW to the scorer (Codex R2#1 — else D0 is write-only).** `run_calibration` today
  receives only `TDD_PLAYBOOK_HOLDOUT_DIR=bodies/` and cannot see the register (it lives above
  `bodies/`). Add a trusted **`TDD_PLAYBOOK_HOLDOUT_REGISTER`** input, PARSED ONCE by the trusted
  parent (`run_holdout`), passing a `{id → status}` map into the aggregation (`:1016-1028`). The
  eval verifier never sees it (parent-only, like the sink env). Test: a `legacy-invalid` body
  **cannot enter** current recall/FP.
- **Reporting partition.** `legacy-invalid` → reported SEPARATELY (historical footnote), never in
  current recall/FP; `known-overflag` → COUNTED (a real, tracked verifier weakness the KEEP flag
  documents, never hides); `current` → the trustworthy number. `diagnose`/`--summary` print BOTH the
  legacy and corrected readings.
- **History snapshot (Codex R2#2).** Each run-history block records the **population snapshot**
  (the `{id → status, content-hash}` set as-of that run), so an old block is always interpreted with
  the status that was true then — deriving old results from today's mutable status is forbidden.

## D1 — Deterministically-SCORED validation gate (Codex R2#5) — build SECOND

**What:** before a body lands, run its target verifier against it under the SAME execution contract
the eval uses; block silent landing of a suspect one. The verifier is an LLM; the **SCORING is
deterministic** (`oracle`) — the gate is not "LLM-free," it is deterministically scored.

- **`validate_item(sc, vault_dir, contract, runner=None)`** composes `rc.stage`+`run_agent`+`oracle`
  for K reps (the `:952-978` loop) → a **k/n decision table** `{k, n, invalid, verdict}` with
  `verdict = rc.verdict_for(...)`: **HOLDS only at k/k**; a real pass/fail split → **`unstable`**;
  `n==0` → **`inconclusive`**. `unstable`/`inconclusive`/`fails` all **refuse approval**
  (fail-closed — never land on a mixed or unmeasured run). Plants mirror (caught at k/k, else weak).
- **Validation manifest, hash-bound (Codex R2#5 + R1#3/#6).** Records the FULL contract — target
  `agent`, `model`, `host`, `host-binary identity`, `isolation`, `turns`, `repeat`,
  `TDD_PLAYBOOK_CALIBRATION_ARGS`, **fixture SHA**, **runner + oracle source SHA**, and
  oracle-normalization version — plus rep outcomes, verifier-brief SHA, timestamp, and the
  **candidate content SHA**. The manifest is STRUCTURED-ONLY (no raw output, no oracle regexes).
  Approval REVERIFIES the content SHA (TOCTOU): a body edited after validation invalidates the
  manifest → re-validate. The contract MUST equal the eval contract or "holds" doesn't predict the
  reading.
- **Containment (Codex R1#5 + R2#3).** The eval verifier stays confined
  (`TDD_PLAYBOOK_HOLDOUT_DENY=<vault_dir>`) and never sees the oracle. No raw output persists. The
  verifier's reasoning is held IN MEMORY and handed to the judge (D2) in-process, then dropped.
- **Wire into `approve`** at `holdout.py:368` (after `rc.validate_scenario`, before the move):
  `HOLDS`/`caught` → land; else block → hand the in-memory reasoning to the judge. Read-only
  `holdout validate --vault-dir <dir> <id>` subcommand added to `main()`.

## D2 — Control-quality judge: ADVISORY, k/k, human-confirmed — build THIRD

A fresh-context reviewer explains *why* a flagged control is suspect and RECOMMENDS an action, so
David never reads code — the irreversible corpus change gets a one-line `y/n`. The judge **never
silently mutates the corpus.**

- New brief `plugins/tdd-playbook/agents/control-quality-adversary.md` (pin `model: opus`), refute-
  framed. Reads {control `edits`, `task`, oracle, the verifier's reasoning}; forced verdict:
  **`REJECT`** / **`FIX-ORACLE`** / **`KEEP`** (defined by the three motivating shapes).
- **Robustness:** run k times; require **k/k agreement**; disagreement → `INCONCLUSIVE` → no
  auto-action.
- **Custody, ONE model (Codex R2#3).** The judge is an AUTHORING-time review — the same class as
  the adversary AUTHOR, which already sends the answer to the provider — so its provider exposure
  (control + oracle + reasoning) is under the **already-accepted authoring-time policy** (private
  vault, David's account), and is DISTINCT from the tighter eval-time containment. Persist
  **only structured labels + hashes** to the manifest (audit); the free-text RATIONALE is shown
  **transiently** for the `y/n` and is **not durably persisted** anywhere. (No "persist rationale +
  no-persist raw output" contradiction; no false "no new exposure" claim.)
- **Disposition — the human-confirm interface (Codex R2 small).** The judge outputs a plain-language
  recommendation; the irreversible retire/replace/keep runs only on an interactive `y/n`.
  Non-interactive / no-TTY invocation → **ABORT, never auto-proceed**. A confirmation is bound to
  the manifest content-hash — it cannot be replayed for a different item or a re-edited body. The
  DETERMINISTIC block (D1) needs no confirmation (a suspect control simply doesn't land).
- **§13 guard-calibration (before trust):** three planted fixtures citing this session's shapes —
  not-clean control → `REJECT`, greedy-oracle-over-clean → `FIX-ORACLE`, clean-control-a-weak-
  verifier-flags → `KEEP` — frozen, replayed, plus a disagreement → INCONCLUSIVE case.
- **Contamination boundary:** a `KEEP` names a real weakness — do NOT tune the production verifier
  against that held item; promote-and-replace to fix it.

## Lifecycle rules (Codex R2#4) — proposed vs approved are DIFFERENT

- **Proposed suspect** (never landed): the gate simply does NOT approve it. It is DISCARDED or held
  in `proposed/` for re-authoring — **never "retired"** (there is no current status to transition).
- **Approved suspect** (D4, a historical body): append a status-transition event (CAS on the body
  hash), then land a SEPARATELY-APPROVED replacement pair — the old body + its historical results
  stay immutable.

## D3 — Better authoring prompt (fix the source) — build FOURTH (after acceptance policy settled)

Revise `author_plants.adversary_prompt` (`:86-131`): controls must be genuinely clean code a
*careful* verifier passes (temptable but refutable-by-tracing), clean **w.r.t. the task's own
question** (no unguarded sibling the task invites finding), oracles anchored on the **verdict line**
(never a greedy prose regex a correct explanation trips), task with one defensible reading. D1 is
the safety net; D3 lowers the bad-control rate.

## D4 — Remediate the current corpus via supersession — build LAST

Run D1+D2 over every existing body. Per k/k judge verdict + David `y/n`: `REJECT`/`FIX-ORACLE` →
retire the PAIR to `legacy-invalid` + land a superseding replacement pair; `KEEP` → `known-overflag`.
Re-run `holdout diagnose`; report BOTH the legacy and corrected readings (the number's change is
auditable, not silent).

---

## Ordered TDD sequence

1. **D0** register schema migration + status model + `HOLDOUT_REGISTER` flow + reporting partition
   + history snapshot: round-trip parse/format; back-compat old rows; legacy-invalid CANNOT enter
   current recall/FP; supersession-graph CAS + no-cycle/no-dangling; `vault_integrity_problems`
   columns.
2. **D1.a** `validate_item` k/n table (injected runner): k/k→HOLDS; 2/3→`unstable`(refuse);
   env-only→`inconclusive`(refuse). Manifest carries the full contract + fixture/runner/oracle SHAs,
   structured-only; **egress test** — stdout is the table only, a planted sentinel never leaks, no
   raw-output file persists.
3. **D1.b** `approve` gate + TOCTOU: `fails`/`unstable` BLOCKS the move; an edited body re-validates;
   `HOLDOUT_DENY` set.
4. **D2.a** the brief + §13 calibration (REJECT/FIX-ORACLE/KEEP + disagreement→INCONCLUSIVE), k/k.
5. **D2.b** dispatch + confirm interface (injected judge + injected `y/n`): confirm bound to manifest
   hash; non-interactive → abort; REJECT→supersede-on-confirm; KEEP→known-overflag-on-confirm.
6. **D3** `adversary_prompt` revision — contract pinned; `generate_accepted_pairs` still parses.
7. **D4** live supersession sweep; re-diagnose; report legacy + corrected.

## Integration ceremony (required)

- **capabilities.json:** register `holdout-control-validation` (activation on via the approve gate,
  `wired_by`=holdout.py, `exercised_by`=the harness tests) and `control-quality-adversary`;
  `validate` passes.
- **Tripwire N/N:** D0/D1/D2 each a named `file::test`, BUILT + WIRED + EXERCISED; report `N/N`.
- **Flow liveness (§6c):** validate-result → approve decision; register status → scorer denominator;
  manifest → judge; judge verdict → confirmed disposition — each a named liveness test.
- **Dated debt:** dev-calibration reuse of `validate_item` is an OWNED, DATED `integration_debt`
  (owner david, exp 2026-11-15), not "noted if deferred."

## Ranked risks

1. **Tautology trap** (filter to what the verifier already passes → ~100%). *Mitigated:* the gate
   surfaces disagreement; the judge KEEPS genuine over-flags (counted, tracked); only broken pairs
   are superseded.
2. **Judge as a decaying LLM gate.** *Mitigated:* advisory + k/k + human-confirm + §13 calibration.
3. **Validation ≠ eval contract.** *Mitigated:* manifest pins the full contract (incl. fixture +
   runner/oracle SHAs) to the hash; reporting flags a mismatch.
4. **Immutability/history rewrite.** *Mitigated:* supersession + per-run population snapshot.
5. **Public dev corpus likely has the same disease.** Out of scope; the dated debt covers reuse.

## Critical files

- `calibration/plant_forms.py` — register schema migration (status/supersede/hash columns), parse/
  format, graph integrity.
- `calibration/holdout.py` — `validate_item`, manifest, approve gate + TOCTOU, `validate`
  subcommand, judge dispatch + `y/n`, `HOLDOUT_REGISTER` wiring, `vault_integrity_problems` columns.
- `calibration/run_calibration.py` — reused eval seams; `HOLDOUT_REGISTER` status map + reporting
  partition (`:1016-1028`, `holdout_summary_lines`); per-run population snapshot in history.
- `calibration/author_plants.py` — `adversary_prompt` revision (D3).
- `plugins/tdd-playbook/agents/control-quality-adversary.md` — new judge brief (D2).
- `calibration/corpus/approved/` — §13 judge fixtures; `capabilities.json`; `docs/calibration/ledger.md`.

## Verification

- Inner loop: `python3 calibration/test_harness.py`; `holdout validate`/`approve` smokes (injected
  runner + judge); `run_calibration.py --dry-run`.
- Full: `sh scripts/civerd_gate.sh` (never piped) GREEN at each phase boundary.
- Build-time adversaries (§0): **architecture-adversary** (supersession-not-mutation at the right
  seam; gate a clean reuse; status flow not an Nth copy), **security-adversary** (no raw output /
  oracle regex persists or reaches the EVAL verifier; authoring-vs-eval exposure boundary; spawn
  confined), **integration-adversary** (validate→approve, register-status→denominator, manifest→
  judge, verdict→confirmed-disposition — no write-only wires; the `HOLDOUT_REGISTER` reaches the
  scorer), **test-quality-adversary** (D2 §13 anchors + the D0 denominator/snapshot tests are real).
- Closing review record (extends the two-tier ledger), gate, push, CI green on the exact sha; the
  new agent brief carries its ledger entry + planted calibration before it is trusted.
