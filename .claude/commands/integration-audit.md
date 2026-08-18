---
description: Run the Playbook §6a/§12 integration audit — sweep the platform for the five darkness classes (broken wiring, dark-by-default, surface drift, old-blind-to-new, dangling dataflow), adversarially verify every negative, ship findings with owners and expiries.
argument-hint: [scope — default: the whole repo]
---

Run the **integration audit** on: $ARGUMENTS (default: the whole repo).

This is the codified "built but is it running?" sweep (origin: a full-platform wiring audit
of a production multi-surface agent system — 11/11 confirmed findings, several whole
subsystems dark). The deliverable is CLAIMS, so §12 governs every line of it.

**1. Enumerate what SHOULD run — never audit from runtime traces alone** (dead and quiet look
identical from the run side). Sources, in order: the capability registry
(`capabilities.json` — also run `python3 "$CLAUDE_PROJECT_DIR/.claude/bin/capability_registry.py"
doctor` for the current dark inventory); else build the inventory from entry points — the
daemon/app factory, schedulers/cron registrations, tool/toolset registrations, event topics,
config gates, per-surface adapters. **A missing registry is itself Finding #0.**

**2. Sweep per subsystem (parallel subagents for a large repo), each hunting the five
darkness classes:**
- **Broken wiring** — emitter and consumer on DIFFERENT seams (private vs global bus);
  components nothing ever starts; tools advertised in prompts/toolsets but never attached to
  an agent build; handlers whose event categories have no emitter anywhere.
- **Dark by default** — built + tested but config-gated off with NO named user-reachable
  switch; gates that silently no-op because a parent gate is off; delivery targets shipping
  as "none". Also the two-surface test for user-facing toggles: a switch that reads its flag
  but is absent from the canonical control surface (`/features`/settings) or the health
  surface (doctor/dark-inventory) is dark even though "the flag works when set". And the
  darkness HATCH — a user-facing gate silenced out of a coverage/registration test via an
  exemption / ignore / allow-list entry: one such entry hides the feature from BOTH surfaces
  at once. Grep the exemption lists and flag any entry that names a user-controllable capability
  (exemptions are for non-user-facing internals only).
- **Surface drift** — the same feature/turn not equal across surfaces (full pipeline on one,
  stripped on another; a fast path or auto-continue that exists on two surfaces out of four).
- **Old-blind-to-new** — existing features never upgraded to consume a newer capability;
  WRITE-ONLY loops (produced from N places, read by nothing); allowlists/snapshots frozen
  before newer tools existed; telemetry aggregation that can't see the newest engines.
- **Dangling dataflow** (§6c) — EDGE darkness the four node classes miss: a repo can be
  100% wired at capability level while individual flows dead-end. Hunt list = the T1–T7
  escape classes, one-line signatures: T1 a refactor orphaned a consumer (the new seam
  never feeds what the old one fed) · T2 written, never read (a table/field/telemetry row
  with no query site) · T3 built, never called (a pruner/cleaner nothing invokes —
  unbounded growth) · T4 accepted value, no reader (an enum value you can set that no code
  compares) · T5 render-seam gap (key supplied, no placeholder — `str.format` drops it
  silently) · T6 registry collision/interception (a shadowed handler behind a passing
  membership test) · T7 event never fired on a surface (consumers starve on the platforms
  that never emit). Plus: ghost gates (undeclared `*_enabled`-shaped reads),
  absence-blind monitors (dead and quiet look identical — no scheduled-vs-observed check),
  and exemption PROSE contradicting the artifact of record ("always-on" over a default-off
  config). **Partition boundary (keeps §13's repeat-class metric honest — never
  double-home a finding):** capability/topic-level write-only stays class 4 (the
  registry's R-WRITE-ONLY granularity); field/value/event-INSTANCE-level dangling goes
  here; exemption-prose inconsistency is class 5, but an exemption used AS a darkness
  hatch stays class 2. The standing mechanism to name in step 5 is the Tier-1 sweep
  (`dataflow_sweeps.py`), a Tier-2 pairing sweep with its FP budget, or — for a pluggable
  family consumed by a shared host — the repo-local §6c FAMILY PARITY SWEEP (enumerated from
  the real registry, vacuity-guarded).

**3. Claims discipline (§12) — non-negotiable here, because every juicy finding is a NEGATIVE:**
- "X is dead / never wired / never called" requires the EXHAUSTIVE sweep (all reference,
  registration, config, and dynamic-dispatch sites) with the sweep cited.
- Prefer a cheap RUNTIME probe over static inference (import/registration probe, subscriber
  count on the real bus, hit the route) — one probe kills or confirms what pages of reading
  can't.
- Subagent sweep reports are UNVERIFIED claims until spot-checked.
- **Every trap-category finding (the big negatives) goes to a fresh-context, refute-framed
  `claims-verifier` pass before publication**, and citations run through the mechanical gate:

      python3 "$CLAUDE_PROJECT_DIR/.claude/bin/verify_citations.py" <findings-file> --base <repo-root>

  Findings that fail verification are REFUTED or demoted to leads — a hedged claim cannot
  carry a severity.

**4. Report in plain language, per confirmed finding:** what the user loses while it's dark ·
evidence (file:line / probe output) · the smallest one-seam fix · an **OWNER and an EXPIRY**
(an unowned finding rots — the documented case is a review doc that flagged a dead subsystem
months before the audit re-found it). Anything half-built-and-silent gets a **decide-or-park**
verdict: wire it (deliverable) or park it loudly (registry removal with a stated reason) —
never leave it silent.

**5. Close by making the audit obsolete, not just done:** for each finding, name the standing
mechanism that would have caught it continuously — the registry entry, the `@assembly` test
through the production composition root, the planted-event canary, the staleness sweep (§6a) —
and propose those as follow-up deliverables.

End with:
`Claims: N load-bearing · N verified (grep/runtime/cited) · N demoted to leads` (paste the
verify_citations summary — a self-reported N/N is narration with a colon in it), and
`Loop closed: yes (claims-verifier dispatched — <verdict summary>)` or `Loop closed: NO — <why>`.
