# Finding what we didn't enumerate — a research pass on unknown-shape discovery

**Date:** 2026-08-15 · **Branch:** `claude/detection-deterministic-filter-ng073s`
**Occasion:** R6 of the detection-cascade plan established that a filter-then-escalate design buys
cost, not recall — it cannot find shapes nobody enumerated. David asked what else is out there,
including techniques we would not think to look for, and whether the patterns reveal gaps we did
not know we had.

**They do. Two of them, both in the instrument this repo calls "the ungameable anchor."**

---

## Method, and one honesty caveat that limits half this document

**Repo claims: fully verified.** Every statement below about what this repo does or does not have
was produced by a command run against the tree in this session, and the command is cited. Where a
first grep produced a hit that turned out to be a false positive, that is recorded rather than
quietly dropped — `STPA` appeared to be present in two files and was in fact the substring inside
`testpaths`.

**Literature claims: NOT verified at source.** `WebFetch` is egress-blocked in this environment for
every domain attempted — `arxiv.org`, `openai.com`, `anthropic.com`, `alignmentforum.org`,
`alphaxiv.org`, `homes.cs.washington.edu` — and a direct `curl` to arXiv returns `CONNECT tunnel
failed, response 403`. So the literature below rests on **search-result summaries, not primary text
I read.** Under §12 that is a weaker claim class and it is labelled as such throughout. Nothing in
the recommendations depends on a specific quoted number; where a number would have been
load-bearing, the recommendation is downgraded instead. **Before any of this is built, the three
papers behind R1–R3 should be read at source.**

---

## Part 1 — What the playbook already does about unknown shapes

Stated first, because the answer to "what are we missing" is worthless without it. All verified.

| mechanism | what it discovers that nobody enumerated | where |
|---|---|---|
| Mutation testing | tests that pass on code they should fail on — found by machine mutation, not by a list | §4 |
| Property-based testing + shrinking | counterexamples in input space nobody wrote down | §3, `SKILL.md:265-281` |
| Fresh-context refute-framed adversaries | design/integration failures the author's imagination excludes, dispatched unconditionally | `/edge`, `/mutate`, `/probe`, `/tdd-plan` |
| Generative plant corpus | new planted defects each cycle, authored by a model at ≥ the doer's tier | `author_plants.py` |
| Plant vitality | plants that have stopped discriminating — a decay signal, not a score | `plant_vitality.py` |
| UX probes | interface failures a scripted journey structurally cannot see | §5a |
| Recurrence → UNBUILT GUARD | repeated judgment findings converted into deterministic rules | `review_ledger.py:391` |
| Quarterly HACK_CATALOG refresh | new hack classes imported from system cards / METR / literature | `docs/HACK_CATALOG.md:314` |

That is a genuinely strong baseline. Six of the eight are mechanisms most teams do not have at
all. The gaps below are narrow, and two of them are inside this list rather than outside it.

---

## Part 2 — Two gaps we did not know we had

Both are in the calibration system. Both were found by taking a literature concept and asking the
tree a question, which is what David asked for.

### GAP-1 — The calibration fixture announces that it is a calibration fixture. Four ways.

**The concept that produced the question:** *evaluation awareness*. Recent work reports that
frontier models can distinguish evaluation contexts from deployment and change behaviour
accordingly — and that this is measured both behaviourally and through probes. Anthropic's Petri
2.0 release notes list countermeasures against eval-awareness as a headline improvement.
(Search-summary only; see the caveat above. But the *question* it prompts is answerable from our
own tree, and that answer is verified.)

**What the tree says.** The doer under calibration is handed four independent tells:

| # | tell | citation |
|---|---|---|
| 1 | the working directory is named after the harness — `tempfile.mkdtemp(prefix="tdd-cal-")` | `run_calibration.py:176` |
| 2 | the git identity is the harness — `user.name "calibration"`, `user.email "cal@tdd-playbook"` | `run_calibration.py:183-184` |
| 3 | **the commit message states that a defect was planted** — `git commit -qm "fixture (plant applied)"` | `run_calibration.py:186` |
| 4 | **the fixture source explains its own plant** — *"Deliberate design smell for the architecture-adversary calibration… the band-aid plant adds a name to this copy alone, the good-fix plant unifies the two"* | `calibration/fixture/tools.py:3-7` |

**Why this is not theoretical.** Tell #3 is visible to `git log`, and at least one calibrated agent
reads git by design: `red-first-verifier.md:28` instructs it to "locate or request the motivating
rev and replay it (`git show <pre-fix-rev>:<file>`)". Tell #4 sits in the file the
`architecture-adversary` is calibrated on, and it describes both the band-aid plant *and* the
correct fix — the answer key, in the source under review.

**Why it matters more than it looks.** The bias runs in the direction that inflates confidence. A
verifier that infers "this is a calibration fixture with a plant in it" tries harder and scores
better, and calibration is the instrument that certifies every other verifier in the system.
`CLAUDE.md` calls a surviving plant "a BLOCKING failure"; `child_env.py` calls the planted-error
anchor "the one ungameable calibration signal." The care taken elsewhere is real — `child_env.py`
exists solely to keep the answer key out of the capture store, and `plant_forms.LEAK_SCAN` guards
holdout ids across four surfaces. The fixture wrapper was simply never in scope for either. **This
is a blind spot, not a known-accepted risk**, which is the distinction worth reporting.

**Honest bound on the fix.** Removing the four tells does not make the run indistinguishable from
real work. A verifier handed a brief and a small synthetic repo may still infer it is being
exercised, and no amount of renaming changes that. This closes the *mechanical* tells — the ones
that require no inference at all — and nothing more.

**The uncomfortable consequence, stated because it would otherwise be discovered later.** If the
tells are load-bearing, scores will DROP after the fix, and pre-fix rows in
`docs/calibration/history.md` (300 rows) stop being comparable to post-fix rows. That discontinuity
must be journaled at the time, not explained afterward. A score drop would be the finding, not a
regression.

### GAP-2 — The corpus grows in volume, inside a taxonomy that cannot grow.

**The concept that produced the question:** *quality-diversity red teaming*. Rainbow Teaming and
its successors frame adversarial generation as a quality-diversity search over an explicit archive
of attack dimensions, because plain generative red teaming trades diversity away for success rate.
(Search-summary only.)

**What the tree says.** `author_plants.py:30-32` defines `CATEGORIES` as a fixed eight-item string:
faked red-first · unwired deliverable · false negative claim · missing edge coverage ·
vacuous/unmeasured mutation gate · band-aid fix at the wrong seam · island/dark-by-default plan ·
unsafe/passes-for-the-wrong-reason script probe. The adversary authors *within* that list. Corpus
state, verified: **23 approved plants, 1 proposed.**

**So the co-evolution mechanism co-evolves inside a frozen taxonomy.** The docstring's own argument
is that "a frozen plant library is itself a static gate" — correct, and the fix it implements
addresses plant *instances*. The categories are the ceiling, and they are as frozen as any library.
Nothing in the pipeline can propose a ninth cell. `plant_vitality` already computes the signal that
would drive the search — a saturated class is an exhausted cell — and `plant_vitality.py:16-18`
even names "a saturated CLASS is a rotation-to-holdout candidate", but no consumer turns that into
"go author somewhere else."

**And the loop that would drive the search is claimed but not wired.** `capabilities.json:794`
registers `plant_vitality` as one that *"Feeds the AUTHORING cycle (a saturated plant names the
target for its next harder sibling; a saturated class is a rotation-to-holdout candidate)"*, and
`plant_vitality.py:15-18` says the same. Verified: **`author_plants.py` does not import or read
`plant_vitality`** — its imports are stdlib plus `run_calibration` and `host_runner`
(`author_plants.py:19-42`), and the only mechanical consumer of vitality anywhere is
`run_calibration.py:817-824`, which *prints* it. A human reading a printout is a real consumer, but
it is not the one the registry sentence describes, and the authoring cycle has no code path that
can act on it. **This is §0's emits→consumer rule failing at field granularity, inside the registry
built to catch exactly that** — the summary asserts a consumer that reads nothing.

**GAP-2 is therefore the single highest-leverage item in the document**, because it bounds how much
unknown-shape discovery the system can ever do *and* the signal that would steer it already exists,
already runs, and is already registered as connected. Every other recommendation tightens a known
shape; this one raises the ceiling and closes a dangling edge at the same time.

**Not a finding, checked and cleared:** the dev/holdout split is designed and currently carries zero
entries, but the tool self-reports it — `plant_forms check` prints *"0 entr(ies); NO holdout classes
assigned yet … Reported as unarmed, not green"*, and `plant-forms.md:57` records that assignment
waits on a private sibling repo that does not yet exist. Known, owned, dated. (It also answers Q1
of the detection-cascade plan: the private store is designed but unbuilt, so that plan's D3 stays
blocked on building it, not on deciding whether to.)

---

## Part 3 — Techniques surveyed, with a verdict on each

Verified present/absent by tree-wide case-insensitive grep across `*.md`/`*.py`/`*.json`.

| technique | in repo? | verdict |
|---|---|---|
| **Metamorphic testing** — no oracle needed; transform the input, assert the *relation* between outputs | **0 hits** | **ADOPT (R3)** — the one technique here that finds bugs when you don't know the right answer |
| **Quality-diversity red teaming** (Rainbow Teaming and successors) | **0 hits** | **ADOPT (R2)** — the fix for GAP-2 |
| **Eval-awareness countermeasures** | **0 hits** | **ADOPT (R1)** — the fix for GAP-1 |
| **Honeytokens / canary tokens** — bait that only misbehaviour touches; zero false positives by construction | **0 hits** ("canary" in `capability_registry.py:75` is a liveness probe, a different concept) | **CONSIDER (B1)** — real but narrower than it looks; see below |
| **Differential / N-version testing** — two implementations disagree ⇒ one is wrong | only `debug.md:12` "differential (good-vs-bad)", which is bisection, not N-version | **CONSIDER (B2)** — worth one guard, not a program |
| **Dynamic invariant inference (Daikon)** — machine infers likely properties from traces; you never wrote them | **0 hits** (§3's "invariant" at `SKILL.md:267,278,281` is hand-authored properties) | **REJECT for now** — inferred invariants are unsound by construction and the maintenance tax lands on a one-person repo |
| **CoT / reasoning monitoring** | `capture.py` captures `UserPromptSubmit` + `Stop` — prompts and finals, not reasoning | **REJECT** — three reasons below |
| **Control evaluations** (red/blue game, adaptive attacker choosing *when* to strike) | plants are static edits applied to a fixture | **REJECT as a program, note as a direction** |
| **STPA / HAZOP** systematic hazard generation | **0 hits** (earlier apparent hits were `testpaths`) | **REJECT as a method, adopt one question** |
| **Near-miss / precursor reporting** | `review_ledger`'s `judgment` finding class + `recurrence` | **ALREADY COVERED** — do not build |

### Why CoT monitoring is rejected despite being the most-cited technique

Three independent reasons, any one sufficient. **(a) No access:** the hook surface gives
`UserPromptSubmit` and `Stop` — the human's turn and the assistant's final. Reasoning tokens are
not on that surface, so there is nothing to monitor. **(b) The literature's own warning:** the
finding most often quoted alongside "CoT monitoring works" is that applying optimisation pressure
against the monitor produces obfuscated hacking rather than less hacking (search-summary). A gate
built on it would degrade the signal it reads. **(c) R6:** it is an expensive-model layer, and
expensive-model layers in a cascade do not extend coverage. If reasoning ever becomes available on
the hook surface, `capture.py` is the seam — and the same three questions apply again.

### Why STPA becomes one question rather than a method

STPA systematically generates hazards a designer did not imagine, which is exactly the target. But
it is a facilitated workshop method sized for aircraft and reactors, and the playbook already has a
lightweight cousin: fresh-context refute-framed adversaries. The portable kernel is STPA's habit of
enumerating *unsafe control actions* by type — provided when it should not be, not provided when it
should be, provided too early/late, stopped too soon. **Refit: add that four-way enumeration to
`architecture-adversary`'s brief**, applied to each new gate or guard. Roughly four lines, no new
machinery, and it asks a question the current brief does not.

### Why honeytokens are narrower than they first appear

The zero-false-positive property comes from "no legitimate actor touches this." In an agent repo
that property mostly fails, because agents legitimately grep and read everything — a read-bait
fires on ordinary exploration. **Only write-bait keeps the property.** The one concrete instance
worth doing: a decoy artifact that looks like guard state (a plausible-but-unused lock-state or
snapshot file) that nothing in production reads or writes, so any modification is unambiguous. That
is a single file plus one assertion, and it is the honest scope — not a deception program.

---

## Part 4 — Recommendations, TDD-shaped

Ceremony scaled per the §0 preamble: R1 is small and mechanical, R2 is feature-shaped, R3 is a
doctrine extension with a pilot.

### R1 — De-legibilize the calibration fixture · ~6 production lines · DO THIS FIRST

**Spec.** Remove the four mechanical tells. Neutral temp prefix; neutral git identity; a commit
message that does not mention plants; and the plant-explaining prose moved out of the fixture
source into the scenario metadata, where the oracle already lives and the doer never reads it.

**Red-first, and §13-compliant.** The new check is a guard, so it obeys the guard-calibration rule
before it is trusted: **replay it against the motivating artifact, which is the current tree.** A
`fixture_legibility` sweep assembles a scenario exactly as `run_calibration` does and greps the
result — files, docstrings, git log, git config, cwd — against a roster of harness tells. Run today
it must go **RED on all four**, and it must go red *for those four reasons*, not merely red. Then
the pre-fix state is frozen as a planted fixture citing this commit, per the v1.25 rule.

**Edge cases.** The sweep must fail if it scanned nothing (vacuity guard — `dataflow_sweeps`'
`EXIT_VACUOUS` precedent). A new scenario that reintroduces a tell must fail. The roster is
name-based, so a tell phrased differently escapes — stated as a known bound, not asserted away.

**Integration surface.** *Consumes:* `run_calibration.build_root`, the scenario schema. *Emits →*
exit code, consumed by a `gate-manifest.json` stage; the sweep's own summary line into the
`gate_yield` record. *Parity:* CI + local. *Reverse sweep:* `author_plants` spawns children the
same way and needs the same treatment in the same commit — it is the second spawn site, and
`child_env.py`'s docstring already establishes that both sites must move together. *Blast radius,
verified:* `grep -rn "tdd-cal\|scn-val"` returns only the two definitions; **nothing asserts the
prefix**, so there are no fixture victims.

**Journaling requirement.** Post-fix history rows are not comparable to the 300 pre-fix rows. The
discontinuity is recorded in `docs/calibration/history.md` at the time of the change.

### R2 — Let the taxonomy grow · feature-sized · the highest-ceiling item

**Spec.** Three changes to `author_plants.py`. (1) Accept a proposed category the list does not
contain, carrying a one-line rationale. (2) Human approval promotes the **category**, not just the
plant — the eight-item constant becomes an append-only registered list with the same review gate
the corpus already has. (3) Feed `plant_vitality`'s saturated-class output into the authoring
prompt as an explicit instruction to author *away* from exhausted cells — the quality-diversity
objective, with the human as the acceptance function.

**Why this is safe to do here.** The dangerous half of automated red teaming is unreviewed
generation. This repo already has the answer: proposed plants land in `corpus/proposed/` and only a
human moves them to `approved/`. R2 routes a *new dimension* through that same gate. Nothing
becomes automatic that is not automatic today.

**Red-first.** A test that a plant in a novel category cannot land without approval; a test that it
CAN land with approval (both directions, §13); and — the one that matters — a test that the
saturated-class signal actually **reaches the authoring prompt**, asserted at the seam
`author_plants` does not currently touch. That third test goes red today for the reason GAP-2
names, which makes it a legitimate red-first anchor rather than a test written after the fact.

**Registry correction, in the same commit.** `capabilities.json:794`'s summary claims a consumer
that does not exist. Either the wiring lands and the sentence becomes true, or the sentence is
corrected to "printed for human reading" — it must not stay as-is, because a registry entry
asserting a connection nobody made is the exact failure the registry exists to prevent.

**Integration surface.** *Consumes:* `plant_vitality.classify`, the existing approval flow.
*Emits → named consumer:* the promoted category list, read by `author_plants`' prompt builder and
by `plant_forms`' registration. *Reverse sweep:* `docs/HACK_CATALOG.md` and this list are two
taxonomies of the same thing; a new approved category should become a catalog row, or the divergence
is dated debt. **That reverse-sweep hit is real and should not be waved through** — two drifting
taxonomies is the shape `review_ledger.py:27-30` warns about in the small.

### R3 — Metamorphic relations for the guards · doctrine + a pilot

**Spec.** §3 currently covers property-based testing, which requires knowing the invariant. Add the
no-oracle case: **when you cannot say what the right output is, say what must stay the same.** For
this repo's guards the relations are concrete and cheap, because guards are near-pure functions
over text:

- reformat whitespace / reflow a line → verdict unchanged;
- rename a local variable consistently → verdict unchanged;
- reorder two independent hunks → verdict unchanged;
- move a file to a different path within the same role → verdict unchanged;
- duplicate an offending construct → still blocks (monotonicity).

Any violation means the guard keys on surface form rather than on what it claims to detect — a
failure class no one enumerates, found without an oracle.

**Pilot before doctrine.** Apply to **one** guard first — `test_weakening_guard`, the highest-stakes
one. If it finds nothing across the five relations, the doctrine claim is unproven and §3 stays as
it is. If it finds something, that finding is the origin story the SKILL entry cites, which is how
every other durable rule in this playbook was born.

**Honest note:** metamorphic relations are themselves hand-authored, so this does not escape the
enumeration problem — it *moves* it from "list the bugs" to "list the invariances", which is a
much smaller and more stable list. That is the whole claim, and it should not be oversold beyond it.

### Sequencing

R1 → R3 pilot → R2. R1 first because it is small, verified, and it repairs the instrument every
later measurement depends on. R3's pilot next because it either earns its doctrine change or dies
cheaply. R2 last because it is the largest and because R1 must land before any new calibration
evidence is worth comparing.

---

## Claims

Repo claims: every one carries a `file:line`, a command output, or a string quoted from the tree,
all produced in this session. **No tally is given, deliberately** — a precise "N of N" here would be
a number I did not compute, and inventing a denominator is the C1 error from the 2026-08-14 record
(reading a union of two row types as one count) repeated in a document about verification. The
check that matters is per-claim and is inline.

One false positive was found and is recorded (`STPA` ← the substring in `testpaths`). One suspected
finding was checked and **cleared** (the holdout split is self-reported unarmed and dated, not a
blind spot). One claim was checked and came back **stronger** than first written
(`plant_vitality`'s registered consumer does not read it).

Literature claims: **0 verified at source.** Every one rests on search-result summaries because
`WebFetch` and `curl` are both egress-blocked here for all six domains attempted. Under §12 that is
a labelled weaker class, not a citation. The three papers behind R1–R3 — evaluation awareness,
Rainbow Teaming, and the metamorphic-testing survey — should be read at source before implementation,
and any recommendation whose rationale does not survive that reading should be dropped.

Judgment claims, not measured: that GAP-1's tells actually change agent behaviour (untested — R1's
own score discontinuity is the experiment); that R2 is the highest-leverage item; that five
metamorphic relations are the right five.

## Loop closed: **NO**

No adversary was dispatched against this document — the session is constrained from dispatching
subagents, and recording that as a visible decision rather than a default. The pass I would most
want is `architecture-adversary`, refute-framed: *"R2 adds a second taxonomy alongside
HACK_CATALOG and R3 adds a fifth test type to §3. Is either an Nth copy of something that already
exists?"* The reverse sweep in R2 already suspects the answer is partly yes.
