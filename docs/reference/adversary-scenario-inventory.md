# Adversary scenario inventory (standing)

**Status:** STANDING REFERENCE — hand-maintained, append-mostly. Not generated.
**Schema:** 1
**Origin:** the "I can't read the code" thread (2026-08-12). David has the product,
architecture, testing and security judgment of someone who ran a software business, and
cannot read Python fluently. Every existing code-comprehension tool assumes the reader can
walk into the source when something looks off. He can't — he dispatches an agent instead.
That inverts the requirement: the surface does not have to be **complete**, it has to be
**pointable**.

This file is the catalogue of things that go wrong, phrased as the question a human would
actually ask, with a stable ID so the routing table, the review ledger and the plants can
all refer to the same row.

---

## How to read the columns

| Column | Meaning |
|---|---|
| **ID** | Stable. Never reused, never renumbered. Referenced by `adversary-routes.json`, review-ledger records, and plant docstrings. |
| **Question** | Plain language. The thing a human would ask at 11pm. Deliberately *not* the technical name — the technical name is what David can't use. |
| **Role** | Whose loss function this represents. A role is **not** a specification for an agent; it is the lens that generated the row and the interest the finding serves. See "Roles are not agents" below. |
| **Evidence** | `facts` = mechanically derivable from source/config/tests. `agent` = needs judgment. `both` = facts narrow it, an agent decides. |
| **Route** | The adversary this row is expected to be handled by, once armed. `—` = not yet routed (inventory-only; manually invocable). |

**Roles are not agents.** A role label changes an agent's vocabulary and topic ordering,
not its detection capability; two role-labelled agents over the same diff return
overlapping findings in different registers. What roles genuinely carry is a **loss
function** — a CISO weights catastrophe, a product owner weights adoption, a CTO weights
run cost — and that reordering is real. So roles are used here to *generate and group* the
inventory, and never as the whole specification of an agent. Every armed route pairs a
loss function with a named evidence source and a plant (§13).

---

## The inventory

### Senior developer — how it is built

| ID | Question | Role | Evidence | Route |
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

| ID | Question | Role | Evidence | Route |
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

| ID | Question | Role | Evidence | Route |
|---|---|---|---|---|
| S17 | Can a secret reach somewhere that writes logs? | ciso | facts | reach |
| S18 | Is there a check on one door and not on the identical door beside it? | ciso | facts | reach |
| S19 | Can something a user typed reach a shell, a query, or an eval? | ciso | facts | reach |
| S20 | Does an internal call get trusted without being re-checked? | ciso | agent | reach |
| S21 | Are the permissions wider than the job needs — container, token, database user? | ciso | facts | reach |
| S22 | Is personal data showing up in logs, traces, or error messages? | ciso | facts | reach |
| S23 | Is there an expensive path with no limit on how often it can be hit? | ciso | facts | reach |
| S24 | Did something that used to require login stop requiring it? | ciso | facts | reach |

### Head of QA — what the tests actually promise

| ID | Question | Role | Evidence | Route |
|---|---|---|---|---|
| S25 | Does this test only check what our own code produced? | qa | both | unchecked |
| S26 | Is there a test that cannot fail — no real assertion in it? | qa | facts | unchecked |
| S27 | Is a flaky test being retried instead of fixed? | qa | facts | unchecked |
| S28 | Is the error path tested, or only the path where everything works? | qa | both | edge-case-adversary |
| S29 | Is the test data always tidy, when real data is not? | qa | agent | edge-case-adversary |
| S30 | Was a regression test added for the bug we just fixed? | qa | facts | red-first-verifier |
| S31 | Is there a whole surface with no test behind it at all? | qa | facts | unchecked |

### Operations — what happens at 3am

| ID | Question | Role | Evidence | Route |
|---|---|---|---|---|
| S32 | Can I tell right now whether this is working? | ops | both | — |
| S33 | If this fails, does anyone find out? | ops | facts | silence |
| S34 | What happens if it dies halfway through writing something? | ops | agent | edge-case-adversary |
| S35 | Is there a queue that can grow without limit? | ops | facts | — |
| S36 | Is there a way to turn this off in a hurry? | ops | facts | — |
| S37 | Can this be undone, or is it one-way? | ops | agent | edge-case-adversary |

### Product owner — whether it lands

| ID | Question | Role | Evidence | Route |
|---|---|---|---|---|
| S38 | Can a user find this without being told it exists? | product | agent | adoption |
| S39 | Does a brand-new user, with nothing set up, get through the first run? | product | agent | adoption |
| S40 | Does the error message tell them what to do next? | product | agent | adoption |
| S41 | Does anything tell us whether it got used? | product | facts | adoption |
| S42 | Is what shipped what was asked for? | product | agent | tripwire-auditor |

**Distribution (stated so the shape of the blind spot is visible, §12):** 26 of 42 are
`facts` or `both` — mechanically narrowable, therefore cheap to check on every change. The
16 `agent` rows cluster in operations and product, which is the expected shape: those are
the rows where the failure is about *consequences* rather than about code. An inventory
where every row were mechanically detectable would be a static-analysis wish list wearing
role costumes, not a catalogue of what goes wrong.

---

## Governance

### G1 — A row is not a control until it is routed, and not trusted until it is planted

Inventory membership means only that the question is worth asking. A row becomes a control
when `adversary-routes.json` arms a route for it, and a route is not trusted until it
carries a **planted fact-change it demonstrably fires on** (§13 guard calibration, v1.25).
A route that has never failed a plant is not known to work. **No plant, no arming.**

### G2 — Exposure is recorded on every run; a run without exposure is not evidence

The retirement question ("this fired twenty times and found nothing") has two
indistinguishable answers: *nothing to find*, or *never run under conditions where finding
was possible*. Braking tests conducted at 1 km/h say nothing about brakes.

So every route run records its **exposure**, not just its result: the change class it saw,
the area touched, the size of the delta, the risk tier. This reuses `gate_yield.py`'s
existing honesty rule verbatim — *"a gate absent from the record is UNMEASURED, never
zero"* — extended from guards to routes.

A route is a demotion candidate **only** after repeated runs under real exposure, on
committed rollups, never from a single clone's ephemeral log.

### G3 — Demote, never delete

A quiet route leaves the automatic table and enters the **manual inventory** with a long
timer (default 120 days) that surfaces as a *question to David*, not as a run. Nothing
leaves this file. Demotions carry an owner and an expiry in the house debt shape
(`{what, target, owner, expires}`) and an expired demotion REDs the gate — the R4.3 shape
`gate_yield.py` already specifies and defers to "when the first candidate actually
appears."

**The single deletion case** is structural, not statistical: the shape the row hunts can no
longer exist in the codebase (e.g. a raw-SQL row in a repo with no raw-SQL layer). That is
"there is no hill left," not "we never drove down one." Deletion on that ground records the
structural reason; deletion on fire-count alone is refused.

### G4 — Loosening is conspicuous

Raising a threshold, disarming a route, or extending a demotion timer is the thing you will
want to do on the day it is annoying you, which is the day your judgment about it is worst.
Every such change is journaled with who, when, and why — the `guard_note.py` pattern — so
quiet erosion looks different from a decision.

### G5 — The inventory grows from what David actually reaches for

New rows come from two places and no others:

1. **A real escape** — a defect that got past every armed route. The escape names the row.
2. **A logged manual reach** — David asking, unprompted, "look at this from angle X."
   Repeated reaches in recognisably similar situations are a trigger the table is missing.

Rows generated from an org chart rather than from an incident are the ones most likely to
be decorative. The rows above are the deliberate exception — a starting inventory so
coverage does not begin at zero — and they are held to G1: none of them is a control until
it is armed and planted.

---

## Changelog

| Date | Change |
|---|---|
| 2026-08-12 | Created. S01–S42 seeded from role-lens generation; zero rows armed (G1). |
