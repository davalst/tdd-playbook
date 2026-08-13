# Adversary scenario inventory (standing)

**Status:** STANDING REFERENCE — hand-maintained, append-mostly. Not generated.
**Schema:** 2 (v1.34.0: Route remapped to REAL agents; `Class` crosswalk and `Facts` join added)
**Origin:** the "I can't read the code" thread (2026-08-12). David has the product,
architecture, testing and security judgment of someone who ran a software business, and
cannot read Python fluently. Every existing code-comprehension tool assumes the reader can
walk into the source when something looks off. He can't — he dispatches an agent instead.
That inverts the requirement: the surface does not have to be **complete**, it has to be
**pointable**.

This file is the catalogue of things that go wrong, phrased as the question a human would
actually ask, with a stable ID so `/readable`, the review ledger and the calibration plants
can all refer to the same row.

---

## How to read the columns

| Column | Meaning |
|---|---|
| **ID** | Stable. Never reused, never renumbered. |
| **Question** | Plain language — the thing a human asks at 11pm, not the technical name. |
| **Role** | Whose loss function generated the row. Not an agent spec — see "Roles are not agents". |
| **Evidence** | `facts` = mechanically derivable. `agent` = needs judgment. `both` = facts narrow it, an agent decides. |
| **Route** | The REAL agent in `agents/` that carries this row's loss function, or `—`. Pinned by `test_readable_surface.py` against `host_parity.canonical_inventory()` — a route naming a nonexistent agent REDs the gate. |
| **Class** | Crosswalk into the shared failure taxonomy (`readable_surface.CLASSES`: §6c T1–T7, the §6a darkness classes, `seam`/`vacuity`/`flaky`/`write-only`), or `new` with the taxonomy silent. Prevents the same escape being counted twice in §13's repeat-class metric. |
| **Facts** | Which worry page(s) of `readable_surface.py facts` answer this row (joined `+`), pinned in BOTH directions against `readable_surface.PAGES`. `—` with Evidence `facts` means *derivable in principle, no standing page yet*; `—` with Evidence `agent` means *this needs the Route agent, not data*. |

**Roles are not agents.** A role label changes an agent's vocabulary and topic ordering,
not its detection capability. What roles genuinely carry is a **loss function** — a CISO
weights catastrophe, a product owner weights adoption, a CTO weights run cost — and that
reordering is real. Every armed route pairs a loss function with a named evidence source
and a plant (§13). Each of the four v1.34.0 agents states what it DE-prioritises, because
four agents returning overlapping findings in different registers is the documented
role-costume failure.

---

## The inventory

### Senior developer — how it is built

| ID | Question | Role | Evidence | Route | Class | Facts |
|---|---|---|---|---|---|---|
| S01 | Is this problem solved three different ways in three places? | senior-dev | both | architecture-adversary | new | — |
| S02 | Is an error being swallowed where nobody will ever see it? | senior-dev | facts | observability-adversary | new | — |
| S03 | Does something retry forever, or retry with no pause between tries? | senior-dev | facts | edge-case-adversary | new | — |
| S04 | Is something opened and never closed — a file, a connection, a lock? | senior-dev | facts | edge-case-adversary | new | — |
| S05 | Can two things now run at once that were never designed to? | senior-dev | agent | edge-case-adversary | new | — |
| S06 | Was this fixed where it broke, or where it was noticed? | senior-dev | agent | architecture-adversary | new | — |
| S07 | Is there a setting buried in the code that should be a setting? | senior-dev | facts | architecture-adversary | new | — |
| S08 | Is there code that looks alive but nothing reaches? | senior-dev | facts | integration-adversary | T3 | dark-inventory |

### CTO — shape and cost of the whole thing

| ID | Question | Role | Evidence | Route | Class | Facts |
|---|---|---|---|---|---|---|
| S09 | Is something low-level reaching up into something high-level? | cto | facts | architecture-adversary | new | — |
| S10 | Do two parts depend on each other in a circle? | cto | facts | architecture-adversary | new | — |
| S11 | Is there one piece that everything else now depends on? | cto | facts | architecture-adversary | new | — |
| S12 | Is the cost per turn creeping up without anyone watching? | cto | facts | architecture-adversary | new | — |
| S13 | Are we locked to one vendor at a seam we said we would keep swappable? | cto | agent | architecture-adversary | new | — |
| S14 | Has the test suite got slow enough that people skip it? | cto | facts | — | new | test-surface |
| S15 | Do two parts have to agree about something, with no shared source of truth? | cto | agent | architecture-adversary | new | flows |
| S16 | Was complexity added for a case that has never once happened? | cto | agent | architecture-adversary | new | — |

### CISO — what an attacker or an accident could do

| ID | Question | Role | Evidence | Route | Class | Facts |
|---|---|---|---|---|---|---|
| S17 | Can a secret reach somewhere that writes logs? | ciso | facts | security-adversary | new | — |
| S18 | Is there a check on one door and not on the identical door beside it? | ciso | facts | security-adversary | surface-drift | surfaces |
| S19 | Can something a user typed reach a shell, a query, or an eval? | ciso | facts | security-adversary | new | — |
| S20 | Does an internal call get trusted without being re-checked? | ciso | agent | security-adversary | new | — |
| S21 | Are the permissions wider than the job needs — container, token, database user? | ciso | facts | security-adversary | new | — |
| S22 | Is personal data showing up in logs, traces, or error messages? | ciso | facts | security-adversary | new | — |
| S23 | Is there an expensive path with no limit on how often it can be hit? | ciso | facts | security-adversary | new | — |
| S24 | Did something that used to require login stop requiring it? | ciso | facts | security-adversary | new | guards |

### Head of QA — what the tests actually promise

| ID | Question | Role | Evidence | Route | Class | Facts |
|---|---|---|---|---|---|---|
| S25 | Does this test only check what our own code produced? | qa | both | test-quality-adversary | seam | — |
| S26 | Is there a test that cannot fail — no real assertion in it? | qa | facts | test-quality-adversary | vacuity | — |
| S27 | Is a flaky test being retried instead of fixed? | qa | facts | test-quality-adversary | flaky | — |
| S28 | Is the error path tested, or only the path where everything works? | qa | both | edge-case-adversary | new | — |
| S29 | Is the test data always tidy, when real data is not? | qa | agent | edge-case-adversary | new | — |
| S30 | Was a regression test added for the bug we just fixed? | qa | facts | red-first-verifier | new | — |
| S31 | Is there a whole surface with no test behind it at all? | qa | facts | test-quality-adversary | new | test-surface |

### Operations — what happens at 3am

| ID | Question | Role | Evidence | Route | Class | Facts |
|---|---|---|---|---|---|---|
| S32 | Can I tell right now whether this is working? | ops | both | observability-adversary | new | dark-inventory |
| S33 | If this fails, does anyone find out? | ops | facts | observability-adversary | new | flows |
| S34 | What happens if it dies halfway through writing something? | ops | agent | edge-case-adversary | new | — |
| S35 | Is there a queue that can grow without limit? | ops | facts | edge-case-adversary | T3 | — |
| S36 | Is there a way to turn this off in a hurry? | ops | facts | integration-adversary | dark-by-default | activation |
| S37 | Can this be undone, or is it one-way? | ops | agent | edge-case-adversary | new | — |

### Product owner — whether it lands

| ID | Question | Role | Evidence | Route | Class | Facts |
|---|---|---|---|---|---|---|
| S38 | Can a user find this without being told it exists? | product | agent | adoption-adversary | dark-by-default | activation |
| S39 | Does a brand-new user, with nothing set up, get through the first run? | product | agent | adoption-adversary | new | — |
| S40 | Does the error message tell them what to do next? | product | agent | adoption-adversary | new | — |
| S41 | Does anything tell us whether it got used? | product | facts | adoption-adversary | write-only | dark-inventory |
| S42 | Is what shipped what was asked for? | product | agent | tripwire-auditor | new | — |

**Distribution (stated so the shape of the blind spot is visible, §12):** 26 of 42 are
`facts` or `both` — mechanically narrowable, therefore cheap to check on every change. The
16 `agent` rows cluster in operations and product, which is the expected shape: those are
the rows where the failure is about *consequences* rather than about code. 41 of 42 rows
route to a real, dispatchable agent; **S14 keeps an honest dash** — "the suite got slow
enough that people skip it" is measured by `gate_yield`, not judged by an agent, and one
honest dash beats ten decorative routes. A `Facts` dash on a `facts`-Evidence row means
the data is derivable in principle but no standing worry page computes it yet — growing a
page is a deliberate act (G5), never an implied promise.

---

## Governance

### G1 — A row is not a control until it is routed, and not trusted until it is planted

Inventory membership means only that the question is worth asking. The four v1.34.0 agents
are trusted only as far as their plants: each ships a planted defect it demonstrably fires
on and a paired clean control it demonstrably stays quiet on (`calibration/corpus/`), and
**a live calibration run covering those pairs is a release precondition** — a route that
has never failed a plant is not known to work. **No plant, no arming.** Automated routing
(a table that fires adversaries on fact deltas) is deliberately NOT built; whether it ever
is depends on the usage record.

### G2 — Usage is recorded on every run; a run without a record is not evidence

`readable_surface.py` logs one machine event per `facts` run (scenario asked, rows
surfaced, host) through the single yield write path; `gate_yield.py rollup` commits it to
`docs/calibration/usage.md` — machine-written `uses` as the denominator, self-reported
`dispatched`/`changed_a_decision` via `gate_yield.py usage-note` as the numerators (a note
can never mint a denominator row — orphans are reported, not counted). Usage measures
whether the surface was ASKED, not whether it helped; the keep/kill criterion is **rows
nobody asks about**, and the record is append-only under `check_scoreboard_integrity`.

### G3 — Demote, never delete

A row that earns retirement leaves the routed set and keeps its line with Route `—` and a
stated reason. Nothing leaves this file; IDs are never reused. The single deletion case is
structural — the shape the row hunts can no longer exist in the codebase — recorded with
the structural reason, never on ask-count alone.

### G4 — Loosening is conspicuous

Rerouting a row to a weaker lens, blanking a route, or softening a question is the thing
you will want to do on the day it is annoying you, which is the day your judgment about it
is worst. Journal such changes (the `guard_note.py` pattern) so quiet erosion looks
different from a decision. Additions are free; this file is append-mostly.

### G5 — The inventory grows from what David actually reaches for

New rows come from two places and no others: **a real escape** (a defect that got past
every armed lens — the escape names the row, and its Class ties it to the shared taxonomy
so §13's repeat-class metric counts it once), or **a logged manual reach** (David asking,
unprompted, "look at this from angle X" — repeated reaches in recognisably similar
situations are a missing row). Rows generated from an org chart are the ones most likely
to be decorative; the 42 above are the deliberate exception, held to G1.

---

## Changelog

| Date | Change |
|---|---|
| 2026-08-12 | Created (S01–S42, role-lens generation; zero rows armed). |
| 2026-08-12 | Schema 2: Route remapped — 17 rows had named agents that did not exist (`reach`/`unchecked`/`silence`/`adoption` and friends); now 41/42 route to real agents in `agents/`, S14 keeps an honest dash. Added `Class` (anti-double-homing crosswalk) and `Facts` (the join to `readable_surface.PAGES`, pinned both directions). |
