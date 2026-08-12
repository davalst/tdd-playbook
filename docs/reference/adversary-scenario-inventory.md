# Adversary scenario inventory (standing)

**Status:** STANDING REFERENCE — hand-maintained. **A MANUAL CHECKLIST, NOT A MECHANISM.**
No row here is armed, routed, or enforced. Membership means only that the question is worth
asking.
**Schema:** 1
**Origin:** the "when code no longer matters" thread (2026-08-12). David has the product,
architecture, testing and security judgment of someone who ran a software business, and
cannot read Python fluently. Every existing code-comprehension tool assumes the reader can
walk into the source when something looks off. He can't — he dispatches an agent instead.
That inverts the requirement: the surface does not have to be **complete**, it has to be
**pointable**.
**Revised 2026-08-12** after `integration-adversary` (ISLAND, 16 findings) and
`architecture-adversary` (BAND-AID, 11 findings) reviewed the companion plan. The Route
column originally named six adversaries that **do not exist** in
`plugins/tdd-playbook/agents/`; it now names only real ones. See "What this file is not".

---

## What this file is not

Three honest limits, stated because a catalogue silently implies coverage (§12 — a control
carries its denominator):

1. **Not a mechanism.** Nothing reads this file. There is no routing table, no dispatcher,
   no gate. Rows are invoked by a human deciding to ask the question.
2. **Not vendored.** `scripts/install_into_repo.py:43-50` copies
   `skills/tdd-playbook, commands, agents, adapters, bin, hooks/scripts` — **`docs` is not
   in `COPY_TREES`**. This file therefore exists in this repo only and does **not** reach
   Cheliped or any other downstream repo. Registered as dated debt on `scenario-inventory`.
3. **Not reconciled with `docs/HACK_CATALOG.md`.** H1–H15 is this repo's existing ID-stable
   catalogue of failure classes *with an armed-mechanism map* (`HACK_CATALOG.md:294-312`).
   Two overlaps are confirmed: **S25 = H11** (`HACK_CATALOG.md:161`) and **S26 = H4**
   (`:51`). The rest of the S↔H mapping is unwritten — dated debt, because a second
   catalogue that does not reconcile with the first is how the two drift into disagreement.

---

## How to read the columns

| Column | Meaning |
|---|---|
| **ID** | Stable. Never reused, never renumbered. |
| **Question** | Plain language — the thing a human would ask at 11pm. Deliberately *not* the technical name, which is what David cannot use. |
| **Role** | Whose loss function this represents. See "Roles are not agents". |
| **Evidence** | `facts` = mechanically derivable. `agent` = needs judgment. `both` = facts narrow it, an agent decides. |
| **Agent** | An adversary that **exists today** in `plugins/tdd-playbook/agents/`, or `—` if none. `—` means manual-only: David asks the question in his own words. |

**Roles are not agents.** A role label changes an agent's vocabulary and topic ordering,
not its detection capability; two role-labelled agents over the same diff return
overlapping findings in different registers. What roles genuinely carry is a **loss
function** — a CISO weights catastrophe, a product owner weights adoption, a CTO weights
run cost — and that reordering is real. Roles are used here to *generate and group* the
inventory, never as the specification of an agent.

---

## The inventory

### Senior developer — how it is built

| ID | Question | Role | Evidence | Agent |
|---|---|---|---|---|
| S01 | Is this problem solved three different ways in three places? | senior-dev | both | architecture-adversary |
| S02 | Is an error being swallowed where nobody will ever see it? | senior-dev | facts | — |
| S03 | Does something retry forever, or retry with no pause between tries? | senior-dev | facts | — |
| S04 | Is something opened and never closed — a file, a connection, a lock? | senior-dev | facts | — |
| S05 | Can two things now run at once that were never designed to? | senior-dev | agent | edge-case-adversary |
| S06 | Was this fixed where it broke, or where it was noticed? | senior-dev | agent | architecture-adversary |
| S07 | Is there a setting buried in the code that should be a setting? | senior-dev | facts | — |
| S08 | Is there code that looks alive but nothing reaches? | senior-dev | facts | integration-adversary |

### CTO — shape and cost of the whole thing

| ID | Question | Role | Evidence | Agent |
|---|---|---|---|---|
| S09 | Is something low-level reaching up into something high-level? | cto | facts | architecture-adversary |
| S10 | Do two parts depend on each other in a circle? | cto | facts | architecture-adversary |
| S11 | Is there one piece that everything else now depends on? | cto | facts | — |
| S12 | Is the cost per turn creeping up without anyone watching? | cto | facts | — |
| S13 | Are we locked to one vendor at a seam we said we would keep swappable? | cto | agent | architecture-adversary |
| S14 | Has the test suite got slow enough that people skip it? | cto | facts | — |
| S15 | Do two parts have to agree about something, with no shared source of truth? | cto | agent | architecture-adversary |
| S16 | Was complexity added for a case that has never once happened? | cto | agent | architecture-adversary |

### CISO — what an attacker or an accident could do

**No security adversary exists.** All eight rows are manual-only. `script-adversary` covers
shell/script shape, not application security. This is the largest single gap in the file and
is stated rather than papered over with a route to an agent that would have to be written.

| ID | Question | Role | Evidence | Agent |
|---|---|---|---|---|
| S17 | Can a secret reach somewhere that writes logs? | ciso | facts | — |
| S18 | Is there a check on one door and not on the identical door beside it? | ciso | facts | — |
| S19 | Can something a user typed reach a shell, a query, or an eval? | ciso | facts | — |
| S20 | Does an internal call get trusted without being re-checked? | ciso | agent | — |
| S21 | Are the permissions wider than the job needs — container, token, database user? | ciso | facts | — |
| S22 | Is personal data showing up in logs, traces, or error messages? | ciso | facts | — |
| S23 | Is there an expensive path with no limit on how often it can be hit? | ciso | facts | — |
| S24 | Did something that used to require login stop requiring it? | ciso | facts | — |

### Head of QA — what the tests actually promise

| ID | Question | Role | Evidence | Agent |
|---|---|---|---|---|
| S25 | Does this test only check what our own code produced? (**= H11**) | qa | both | — |
| S26 | Is there a test that cannot fail — no real assertion in it? (**= H4**) | qa | facts | mutation-runner |
| S27 | Is a flaky test being retried instead of fixed? | qa | facts | — |
| S28 | Is the error path tested, or only the path where everything works? | qa | both | edge-case-adversary |
| S29 | Is the test data always tidy, when real data is not? | qa | agent | edge-case-adversary |
| S30 | Was a regression test added for the bug we just fixed? | qa | facts | red-first-verifier |
| S31 | Is there a whole surface with no test behind it at all? | qa | facts | tripwire-auditor |

### Operations — what happens at 3am

| ID | Question | Role | Evidence | Agent |
|---|---|---|---|---|
| S32 | Can I tell right now whether this is working? | ops | both | — |
| S33 | If this fails, does anyone find out? | ops | facts | integration-adversary |
| S34 | What happens if it dies halfway through writing something? | ops | agent | edge-case-adversary |
| S35 | Is there a queue that can grow without limit? | ops | facts | — |
| S36 | Is there a way to turn this off in a hurry? | ops | facts | — |
| S37 | Can this be undone, or is it one-way? | ops | agent | edge-case-adversary |

### Product owner — whether it lands

| ID | Question | Role | Evidence | Agent |
|---|---|---|---|---|
| S38 | Can a user find this without being told it exists? | product | agent | ux-probe-calibrator |
| S39 | Does a brand-new user, with nothing set up, get through the first run? | product | agent | ux-probe-calibrator |
| S40 | Does the error message tell them what to do next? | product | agent | ux-probe-calibrator |
| S41 | Does anything tell us whether it got used? | product | facts | integration-adversary |
| S42 | Is what shipped what was asked for? | product | agent | tripwire-auditor |

---

## Denominators (§12 — stated, not implied)

- **26 of 42** rows are `facts` or `both` — mechanically narrowable in principle. Note "in
  principle": no extractor for most of them exists in this repo today.
- **22 of 42** map to an adversary that exists. **20 are manual-only**, and 8 of those 20
  are the entire CISO block.
- **0 of 42** are armed. Nothing here fires automatically.
- The 16 `agent` rows cluster in operations and product — the expected shape, since those
  are the rows where the failure is about *consequences* rather than code. An inventory
  where every row were mechanically detectable would be a static-analysis wish list wearing
  role costumes.

---

## Governance

These rules apply **if and when** rows are ever armed. They are written now because the
conditions are easier to agree before there is a mechanism to argue about.

### G1 — No plant, no arming

A row becomes a control only when it carries a **planted defect it demonstrably fires on**
(§13 guard calibration, v1.25). A control that has never failed a plant is not known to
work. Arming without a plant is refused.

### G2 — Exposure is recorded; a run without exposure is not evidence

"Fired twenty times, found nothing" has two indistinguishable readings: *nothing to find*,
or *never run where finding was possible*. Braking tests at 1 km/h say nothing about brakes.
Every run must therefore record its **exposure** — change class, area, delta size, risk tier
— not just its result. This is `gate_yield.py`'s existing rule verbatim: *"a gate absent
from the record is UNMEASURED, never zero."*

**Known obstacle, stated:** `gate_yield`'s candidate logic keys on adjudicated overrides,
and `capabilities.json` → `gate-yield` already carries dated debt (expires **2026-11-15**)
recording that `tdd_lock.py` is the only override producer and hardcodes `gate=testlock`, so
five of six existing gates "have overrides structurally 0 and can NEVER become retirement
candidates." Any future routing work inherits that hole and must fix it first or state it.

### G3 — Demote, never delete

A quiet control leaves automation and enters manual invocation with a long timer (default
120 days) that surfaces **as a question**, not a run. Demotions carry `{what, target, owner,
expires}` and an expired demotion REDs the gate.

**The single deletion case is structural, not statistical:** the shape the row hunts can no
longer exist (a raw-SQL row in a repo with no raw-SQL layer). That is "no hill left," not
"we never drove down one." Deletion on fire-count alone is refused.

### G4 — Loosening is conspicuous

Disarming, raising a threshold, or extending a timer is what you will want to do on the day
it annoys you — the day your judgment about it is worst. Every such change is journaled with
who, when and why (`guard_note.py` pattern), so quiet erosion looks different from a
decision.

### G5 — The inventory grows from escapes and from logged manual reaches

New rows come from a **real escape** (a defect that got past everything — the escape names
the row) or from a **logged manual reach** (David asking, unprompted, for angle X; repeated
reaches in similar situations are a missing row). Rows generated from an org chart rather
than an incident are the ones most likely to be decorative. S01–S42 are the deliberate
exception — a starting catalogue so coverage does not begin at zero — and they are held to
G1: none is a control.

---

## Dated debts

| What | Owner | Expires |
|---|---|---|
| Not vendored — `install_into_repo.py` `COPY_TREES` has no `docs`, so downstream repos (Cheliped first) never receive this file | david | 2026-11-30 |
| S↔H mapping incomplete — only S25=H11 and S26=H4 confirmed against `HACK_CATALOG.md` | david | 2026-11-30 |
| No security adversary — S17–S24 (8 rows, the largest block) have no mechanism at all | david | 2027-01-31 |

---

## Changelog

| Date | Change |
|---|---|
| 2026-08-12 | Created. S01–S42 seeded from role-lens generation. |
| 2026-08-12 | Revised after adversarial review: Route column re-mapped onto the ten agents that actually exist (six invented names removed); "not a mechanism / not vendored / not reconciled" limits stated; denominators added; dated debts registered. |
