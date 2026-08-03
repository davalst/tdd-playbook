# Review: the Cheliped "Dataflow Liveness" amendment proposal (§6b)

**Date:** 2026-08-03 · **Reviewed against:** SKILL.md as of v1.23.0 (HEAD of `main`)
**Input:** `TDD_PLAYBOOK_AMENDMENT_DATAFLOW_LIVENESS.md`, submitted from the Cheliped repo's
2026-08-03 full-repo excavation (671 files, 92 verified findings, 12 post-safeguard escapes).

**Evidence caveat (§12):** the case study's numbers (12 escapes, the T1–T7 instances, the
0-node-escape result) live in the Cheliped repo and are SECONDHAND here — this review takes
them at face value as David-submitted, but nothing in this repo verifies them. The doctrinal
assessment below stands on the playbook's own text either way.

---

## 1. Verdict

**Adopt, with modifications.** The core diagnosis is correct and important: the playbook's
wiring discipline verifies **nodes** (a component exists, is registered, is attached, is
exercised, is running) and names consumers only at **capability/topic granularity**. It does
not mechanically verify **edges** at the granularity where the twelve escapes happened —
fields, enum values, template keys, dispatch order, per-surface events, eviction paths. That
the net went 114/114 on its home turf while every escape was an edge failure is exactly the
kind of result §13 says to feed back into the gates.

Two corrections before adoption:

1. **The gap is narrower than the proposal claims.** Several "why the current net missed it"
   cells under-credit doctrine that already exists (detailed in §2 below). The amendment
   should be framed and written as **sharpening existing sections into mechanical rules**,
   not as a parallel new discipline — smaller diff, no duplicated ceremony.
2. **§6b is already taken.** SKILL.md v1.2x added §6b "Onboard, don't hide" (the default-OFF
   onboarding contract). The proposal was written against a stale copy of the playbook —
   which is itself a finding: Cheliped's vendored `.claude/` copy is behind and should get
   the standing refresh prompt (CLAUDE.md). The new material lands as **§6c** plus edits to
   §0/§6/§6a/§12/§13.

The "would have caught 12 of 12" line should not be quoted forward: the taxonomy was derived
from those twelve escapes, so 12/12 retrodiction is true by construction. The honest forward
test is the proposal's own 6b.5 (planted-edge calibration) plus the escape count of the NEXT
excavation cycle, tracked by class in §13.

## 2. Where the proposal under-credits the current playbook

Worth recording so the amendment diffs against reality, not against the stale copy:

| Proposal claim | What actually exists today | Real residual gap |
|---|---|---|
| "R-WRITE-ONLY exists at capability granularity; nothing sweeps table/event/field granularity" (T2) | Correct — registry `emits[].consumers` + doctor's write-only-emitter inventory are topic-level | Field/table/event-type sweeps: **real gap, adopt** |
| "Wired was proven by the supply side" (T5) | §1 "Assert the outcome, not the proxy" and §12 "trace the wire end-to-end — who SETS, who CONSUMES" already state the doctrine | The doctrine is prose, not a named mechanical bar for "wired" claims. The **sentinel-at-the-output-end rule is the missing teeth — adopt into §12** |
| "Registration tests check presence, not uniqueness or dispatch reachability" (T6) | §6/§6a's symmetric reachability through the PRODUCTION composition root, taken seriously, catches a shadowed handler — the shadowed one is not reachable in the real build | In practice membership tests pass; the **raise-on-duplicate rule is the cheap sharp form — adopt**, and amend §6a to say reachable means *through the real dispatch order*, not present-in-a-list |
| "Per-surface event-parity was untested" (T7) | §0 Surface parity + §6a's assembly suite "per platform" already demand this; Cheliped's assembly suite simply never built two of its platforms | An implementation shortfall downstream, not a doctrine hole — but the **flow-row "lifecycle events per surface" makes it checkable instead of rememberable — adopt** |
| Absence-blind monitors (supporting discovery) | §6a passive liveness ("registered but zero runs in N days") is the same observation | The genuinely new refinement: **monitors must record SUCCESS, and a standing check compares scheduled-set vs observed-rows** — merge into §6a's canary/staleness bullet rather than adding a duplicate sweep |
| T3 (built, never called) / eviction paths | §4's survivor-reading has caught write-only emitters; nothing systematic | **Caller-existence for maintenance/eviction paths: real gap, adopt** (it's the flow-table's "who prunes" column) |
| T4 (accepted value, no reader) | Nothing. §6 ACTIVATED validates the switch, not each accepted value | **Real gap, adopt — the strongest of the eight sweeps.** A risk-ceremony flip that no-ops manufactures false confidence; that is worse than no switch |
| Ghost gates (`getattr(config, "x_enabled", True)` undeclared) | §6a's exemption-hatch companion test is adjacent but walks declared fields | **Real blind spot, adopt** — cheap grep-shaped sweep |

## 3. Item-by-item disposition

### 6b.3 Refactor consumer-parity (migration DoD) — **ADOPT UNCHANGED. Highest value.**
Nothing in the playbook covers it, and one refactor produced 5 of the 12 escapes. "A
migration is done when every consumer the OLD path fed is enumerated and fed / retired /
dated-debt" is exactly the same shape as §6's reverse check and §0's reverse sweep — but
pointed at the seam being replaced, which neither currently is. The "leftover references to
the deleted mechanism are defects, not cruft" rule slots straight into §12's
exhaustive-negatives pass. Home: **§6c**, plus one line in §0 making the old-path output
enumeration a mandatory plan answer for any migration/strangler deliverable.

### 6b.4 Output-end proof + evidence tiers — **ADOPT.** Home: §12 and §6a.
- "A 'now wired' claim is proven at the OUTPUT end or it is not proven" — one sentence, one
  sentinel, closes T5 structurally. Add to §12 beside the remote-runtime claims rule (it is
  the same move: a commit sha is not a running process; a supplied key is not a rendered
  value).
- Evidence tiers (`config-read < import < runtime-probe < composition-root`; import-existence
  can never render OK) — add to §6a's doctor doctrine. This also matches §1's
  "assert the outcome, not the proxy" origin story (the `RuntimeMaxSec` incident) — the tiers
  give that doctrine a rankable vocabulary for health surfaces.

### 6b.1 Flow table in §0 — **ADOPT, scale-gated.**
The flow-kinds list is the real asset — it is a checklist of edge types that bounded
imagination misses (enum values, template keys, dispatch order, eviction, per-surface
events). But a mandatory table on every deliverable violates the playbook's own
ceremony-scaling rule (§ preamble: numbers, not vibes). Gate it the way the Tripwire is
gated: full flow table for feature/multi-deliverable/migration work; for small diffs the
existing prose "Emits → named consumer" stands. The rule "empty consumer cell = dated debt
or don't ship" is already §0 doctrine (write-only loop → owned debt) — the table just makes
the cell impossible to leave silently blank.

### 6b.2 The eight sweeps — **ADOPT AS DOCTRINE + AUDIT CLASSES, not as shipped mechanism.**
These are repo-tailored tests; a universal AST sweep across every stack cannot ship from a
stdlib-only plugin and shouldn't try. Land them as:
1. a named list in **§6c** (the standing-suite shape each repo implements in its own stack,
   exactly like §6a's assembly suite is described, not shipped);
2. a **fifth darkness class in `/integration-audit`** — "dangling dataflow" — with T1–T7 as
   the hunt list, so the audit command finds these in repos that haven't built the sweeps yet;
3. one addition to the **`integration-adversary` brief**: refute-frame at flow granularity
   ("name a flow this plan writes that nothing reads; a value it accepts that nothing
   compares").
Modifications:
- **Sweep 1 (storage pairing) will grow an exemption list** — §6a's own doctrine says
  exemption lists are the most efficient darkness hatch there is. The companion-test rule
  must carry over verbatim: an exemption naming a user-facing flow fails the suite.
- **Sweep 3 (enum-value readers)** needs a stated escape for values consumed OUTSIDE the
  repo (passed through to an external API, read by humans, written for a peer service) —
  dated exemption with the consumer named, same shape as everything else.
- **Sweep 8 (scheduled-vs-recorded)** merges into §6a's existing passive-liveness bullet
  (add "record success, not only failure; silence goes red") rather than standing alone.
- **Sweep 5 (registry uniqueness)** — "duplicate registration RAISES; last-write-wins is
  banned" is cheap and universal; also amend §6a's symmetric-reachability sentence to say
  reachability is proven through the real dispatch order.

### 6b.5 Planted-edge calibration — **ADOPT; it is required anyway.**
This repo's release discipline already demands a planted-input test for every mechanical
change, and §13 demands plants for every new gate. The five listed plants are the right
ones. Note the pipeline limitation recorded in CLAUDE.md: corpus plants can only MODIFY
existing fixture files — the "plant a table with a writer and no reader" class may need the
`create` capability that was already flagged as a future enhancement.

### §13 escape-tracking by class — **ADOPT.** One line in §13: audits/excavations report
escapes by class (T1–T7 + node classes); a repeat class across cycles means the mechanism
for it isn't real yet. This is the learning loop doing exactly what it exists for.

## 4. What NOT to do

- **Do not extend `capabilities.json` to per-field/per-value flows.** The registry's value
  is that it is small and machine-checkable; flow granularity would bloat it into a parallel
  codebase. The proposal doesn't ask for this — keep it that way. Flows live in the plan
  table (point-in-time) and the repo's own sweeps (standing); the registry stays
  capability-level.
- **Do not renumber existing sections.** §6b (onboarding contract) keeps its name — v1.22
  rule (d) treats gate-surface removals/renames as journaled events, and there's no reason
  to spend that. New section is §6c.
- **Do not quote "12/12 caught" as forward evidence** (retrodiction on the deriving corpus).
  The honest line is: "the sweeps are calibrated by plants and measured by next cycle's
  escape count, by class."

## 5. Adoption plan (pending David's go-ahead — this doc is review only)

1. SKILL.md edits: §0 (flow table, scale-gated + migration old-path enumeration), §6 (FLOWS
   in the N/N accounting for multi-deliverable plans), §6a (evidence tiers; success-recording
   monitors; dispatch-order reachability), **new §6c Dataflow Liveness** (doctrine line, the
   eight sweeps, migration consumer-parity DoD), §12 (output-end proof rule), §13
   (escape-class tracking). All additions — no gate-changes.md entries needed under rule (d).
2. `/integration-audit`: fifth darkness class (dangling dataflow, T1–T7 hunt list).
   `integration-adversary` brief: flow-granularity refute prompts.
3. Planted tests per release discipline for anything mechanical; the SKILL/command/agent
   text changes are gate surfaces → live-calibrate before trusting (§13 standing rule; the
   ~2026-08-10 run is the natural slot).
4. Version bump both manifests + CHANGELOG; then push the refresh prompt through Cheliped so
   the repo that discovered the hole is the first to vendor the fix.
5. Cheliped side: implement the eight sweeps in its own stack, run the 6b.5 plants once at
   adoption, and wire the two never-built platforms into its assembly suite (T7 was an
   implementation shortfall of existing doctrine, and it stays open until that suite builds
   every platform).

**Claims: 9 load-bearing · 9 verified (all against SKILL.md/capabilities.json/command text
read in this session; the Cheliped case-study numbers are explicitly secondhand, §12 caveat
above) · 0 demoted.**
