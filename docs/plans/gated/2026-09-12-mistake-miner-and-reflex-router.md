# Mistake Miner → Error Corpus → Reflex Router

**Date:** 2026-09-12 · **Workstream:** `mistake-miner`
**Status:** PLAN FOR A FRESH SESSION. Nothing built beyond a validated prototype.
**Intended host:** David's laptop, where the full session corpus lives (tdd-playbook +
cheliped + everything else) and where the network is not egress-restricted.

---

## 0. Read this first — what this plan is and is not

**The goal.** Claude Code sessions constantly print the moment a mistake is discovered — an
adversary refutes a claim, a guard fires, a tripwire catches an unwired deliverable, the model
says "I was wrong, that function does not exist." Those printed moments are labelled training
data that currently evaporates. This plan mines them into a structured corpus, classifies each
by error type, and uses that corpus to train a small reflex model that answers a handful of
fast, narrow decisions the Playbook currently leaves to attention alone.

**What it is NOT.** It does not replace the four blocking guards. It does not replace the
large model's reasoning. It is not a general intelligence upgrade. It targets one family:
fast, context-sensitive routing decisions that a fixed pattern gets wrong.

**Why now.** Measured in this repo: ~68,300 tokens of doctrine (SKILL.md alone ~30,400), 14
guards of which 4 earn their keep and ~7 never fired usefully, one guard deleted after 701
ignored warnings, and 205 recorded findings from which **zero** guards were ever built. The
rule-per-case approach has a measured ceiling.

---

## 1. Step zero — fetch what this session could not

This container's egress policy blocked `arxiv.org`, `alphaxiv.org`, `emergentmind.com`,
`sites.google.com` and `awesomepapers.io`. Everything below about FlyGM comes from search
summaries, not from the paper. **On the laptop, fetch these before designing anything:**

- Paper: `arXiv:2602.17997` — *Whole-Brain Connectomic Graph Model Enables Whole-Body
  Locomotion Control in Fruit Fly* (Jin et al., 2026)
- Code + demos: `https://lnsgroup.cc/research/FlyGM` (project page:
  `sites.google.com/view/flygm`)
- The simulator it drives: `flybody` in MuJoCo
- Also relevant, released 2026-09-03: **MaleCNS v1.0** (HHMI Janelia FlyEM / Cambridge
  Connectomics / Google Research) — ~166,000 neurons, 125M synapses.

**What is known, and is load-bearing for this plan:**

| Property | What the sources say |
|---|---|
| Structure | The network's static structure IS the connectome — signed synaptic weights, neurons partitioned into afferent / intrinsic / efferent |
| What is learned | The weights; the *topology* is fixed from biology |
| Training | Two stages: imitation learning from expert trajectories, then PPO fine-tuning for task reward |
| Result vs baselines | Beat random-graph, degree-preserving rewired-graph, and MLP baselines on **sample efficiency** and **motor accuracy**, across locomotion and flight |
| Code | Released |

That baseline comparison is the single most important fact. It is the experiment that says
connectome topology is a genuinely better prior than a random or dense network — not decoration.

**The honest gap.** FlyGM's tasks were *embodied sensorimotor control*: continuous action, dense
reward, a body in physics. Ours is *discrete classification over symbolic features*. The prior is
proven on its home turf; transfer to our problem shape is unproven. §6 handles this.

---

## 2. The domain translation

| FlyGM | Here |
|---|---|
| Sensory neurons (afferent) ← joint angles, vision, contact | Afferent ← the feature vector of "what is happening right now" (§4.3) |
| Intrinsic neurons | Unchanged — the connectome interior |
| Motor neurons (efferent) → joint torques | Efferent → a small discrete head: which nano-decision fires, and how strongly |
| Imitation learning ← expert trajectories | Imitation learning ← **the mined corpus**: situation → the decision that would have been right |
| PPO ← task reward in MuJoCo | Deferred. See §6 — supervised first; reinforcement only if there is a reward signal worth the complexity |

**Read that table carefully.** The first stage of FlyGM's own pipeline — imitation learning
from labelled trajectories — maps cleanly onto supervised learning from the mined corpus. The
second stage does not map without an environment to act in. **This plan builds stage one only.**

---

## 3. The error taxonomy

Derived from this repo's recorded incidents and this session's own mistakes — not guessed.
Each class names what actually went wrong, not how it was discovered.

| # | Class | What it is | Real instance |
|---|---|---|---|
| E1 | `fabricated-reference` | Cited a function / file / symbol that does not exist | `read_current()` cited twice as the lead consumer; repo-wide grep returns only the plan's own mentions |
| E2 | `stale-fact` | Asserted something that was true once and is not now | "two readers take no population parameter" — that work had landed weeks earlier |
| E3 | `unverified-claim` | Asserted without checking the thing itself | quoting a sibling plan instead of source |
| E4 | `vacuous-check` | Wrote a test/assertion that cannot fail | `check('spike times are ordered', True)` |
| E5 | `instance-not-class` | Fixed the reported case, left identical siblings | YAML defect fixed in SKILL.md, five agent briefs left dark |
| E6 | `scope-narrowed` | Quietly dropped or shrank a requirement | "and efficient" — never scoped, never disclaimed, nobody decided |
| E7 | `wrong-jurisdiction` | A rule fired on something outside its actual domain | lock_guard blocking a read because a loop variable was named `ln` |
| E8 | `arbitrary-threshold` | Invented a cutoff with no basis, and it mattered | the 1% drift band; the real effect landed at 1.3% |
| E9 | `unwired-deliverable` | Built, not connected; ships dark | six toggles built + wired + tested + registered yet unreachable |
| E10 | `undercount` | Enumerated a set and missed members | "four FIXTURE readers" — there are seven, across three modules |
| E11 | `premature-conclusion` | Concluded before the cheap check that would have settled it | eight build proposals, each killable by one measurement available before any plan existed |
| E12 | `unknown` | Classifier's escape hatch — **required**; a forced taxonomy is how a corpus lies |

**E12 is not optional.** Any classifier without an explicit "I don't know" bucket will smear
its uncertainty across the other eleven, and the resulting corpus will look cleaner than it is.

### 3.1 Mapping to the nano-decisions

The reflex does not predict the error class. It predicts **the decision that would have
prevented it.** This is the mapping, and it is the reason the taxonomy exists:

| Nano-decision (the reflex's output head) | Error classes it would have caught |
|---|---|
| `N1` — *has this already been checked / established?* | E2, E3, E11 |
| `N2` — *is this in this guard's jurisdiction?* | E7 |
| `N3` — *is this the instance or the class?* | E5, E10 |
| `N4` — *can this check actually fail?* | E4, E8 |
| `N5` — *does this claim resolve against the tree?* | E1, E3 |
| `N6` — *is this shipping dark / did scope move?* | E6, E9 |

Six heads. Every head is binary or small-multiclass, decidable in milliseconds from features
available at the moment of decision.

---

## 4. The miner

### 4.1 Validated prototype — results, not hopes

A prototype was run against ONE session transcript (1,218 records, 3.4 MB) in this container.
Reproduce it from `scratchpad/mine_proto.py` in the attached materials.

- **16 candidate mistake-events extracted** from one session.
- Signal tally: self_correction 10 · vacuous_test 5 · stale_fact 3 · nonexistent_ref 3 ·
  refuted_claim 3 · wrong_threshold 1.
- **Commission↔discovery back-linking works.** For four known errors, the discovery turn was
  linked back to the turn that committed the error by the named entity:

| error | commission record | discovery record | gap |
|---|---|---|---|
| invented a function (`read_current`) | 613 | 715 | 102 |
| vacuous test | 435 | 745 | 310 |
| arbitrary threshold (`1%`) | 232 | 324 | 92 |
| stale claim | 715 | 716 | 1 |

### 4.2 The two problems the prototype found — design around them

**Problem 1: the discovery turn is not the training example.** The turn that *prints* the
mistake is 100–300 records downstream of the turn that *made* it. Training on the discovery
state teaches the model to recognise an apology, which is useless — by then the cost is paid.
**The label comes from the discovery; the features come from the commission.** The back-linker
is therefore not a nicety, it is the core of the miner.

**Problem 2: tool names carry almost no signal.** Every extracted event showed preceding tools
of `['Bash','Bash','Bash',...]`, because most work flows through one tool. The feature vector
must be built from the *content* — the command text, the paths touched, the claim asserted —
not from the tool name.

**Problem 3 (precision, found in the same run):** the `gap=1` row above is suspicious — the
back-linker likely matched the discovery turn's own restatement. **The commission search MUST
exclude the discovery record and any text quoting it**, or the corpus fills with self-links.

### 4.3 Feature vector (the afferent layer)

Extracted from the commission record and a bounded window before it. All available from the
transcript; nothing new needs instrumenting.

- **Action:** tool name; for Bash, the head verb and whether it writes; target path(s).
- **File class:** test / source / doc / config / fixture-data / plan / journal.
- **Session state:** count of files read vs edited this session; whether *this* path was read
  before being written; count of failed tool calls in the last N; repeat-edit count on this path.
- **Claim shape:** is the assistant asserting a `file:line`? a count? a negative ("nothing
  does X")? a completion ("N/N")? These are cheap regexes and they map directly to N5.
- **Guard context:** any guard fired this session, and on what.
- **Plan context:** does a committed plan exist for this work; is a TEST-LOCK held.

### 4.4 The classifier

Per the user's instruction, a cheap model classifies each mined event.

- **Model:** `claude-haiku-4-5` (200K context, $1/$5 per MTok).
- **Structured outputs**, not free text: `output_config: {format: {...}}` with a schema pinning
  `error_class` to the E1–E12 enum, `nano_decision` to N1–N6 (nullable), `confidence`, and a
  short `evidence_quote` that must be a substring of the input. A classifier that cannot quote
  its evidence is hallucinating a label.
- **Batches API** for the bulk pass — asynchronous, **50% cost**. Hundreds of sessions ×
  ~16 events is a batch job, not a loop. Key results by `custom_id`; results arrive in any order.
- **Cost estimate:** at ~16 events/session and ~4K tokens of context per event, 500 sessions
  ≈ 8,000 events ≈ 32M input tokens ≈ **$32 at Haiku list, ~$16 batched**. Cheap enough that
  the classification pass is not the constraint.
- **The classifier is probabilistic and will be wrong on some fraction.** Therefore: (a) every
  row keeps its `evidence_quote` and record index so any label can be re-adjudicated; (b) a
  human-reviewed gold set of ~200 events is held out and never trained on; (c) classifier
  agreement against that gold set is measured and reported before the corpus is trusted.

### 4.5 Output schema — one row per mined event

```json
{
  "session_id": "...", "repo": "tdd-playbook",
  "commission_record": 613, "discovery_record": 715, "gap": 102,
  "error_class": "E1", "nano_decision": "N5", "confidence": 0.86,
  "evidence_quote": "read_current() ... does not exist",
  "entity": "read_current",
  "features": { "...": "§4.3" },
  "label": { "correct_decision": "flag", "source": "discovery" },
  "classifier": { "model": "claude-haiku-4-5", "schema": 1, "ts": "..." }
}
```

---

## 5. Build order

**D1 — the extractor.** Walk transcripts, emit candidate events with signals + evidence.
Recall over precision. *Done when:* it reproduces the 16 events from the reference session.

**D2 — the back-linker.** For each discovery, find the commission record by named entity,
excluding the discovery record itself and its quotations. *Done when:* it reproduces the four
back-links in §4.1 AND the `gap=1` false link is gone.

**D3 — the feature extractor.** §4.3, from the commission record. *Done when:* two events with
visibly different situations produce visibly different vectors — the failure this replaces is
every event looking like `['Bash','Bash','Bash']`.

**D4 — the classifier pass.** Haiku 4.5 + structured outputs + Batches. *Done when:* ≥200
events classified and agreement against the human gold set is measured and written down.

**D5 — the corpus.** SQLite + a JSONL export. Append-only. *Done when:* a query answers
"how many E4 events, in which repos, over what period."

**D6 — THE BASELINE. Do not skip this.** Before any connectome is involved: can logistic
regression / gradient boosting predict the nano-decision from the features? *Done when:* a
precision/recall number exists per head, with a stratified train/test split.

**This is the decision gate for the whole programme.** If a plain classifier cannot beat
chance on these features, the features are wrong and no fly will fix that. Finding that out
costs a day. Finding it out after building the fly costs a month.

**D7 — the reflex model.** Only if D6 clears. Take FlyGM's released code, replace the afferent
interface with §4.3's vector and the efferent interface with the six heads, train stage-one
(imitation/supervised) on the corpus. Compare against D6's baseline on the same split.

**D8 — replay evaluation.** Run held-out sessions through both models. Report, per head:
catches, misses, false alarms. **False-alarm rate is the headline** — the record shows an
ignored warning is an effective false positive, and 701 of them killed a guard.

---

## 6. Risks, stated

- **Transfer is unproven.** FlyGM won on continuous motor control. Ours is discrete
  classification. D6 exists precisely to find out cheaply.
- **Distribution shift.** The corpus is drawn from sessions where the guards *were* firing. A
  reflex trained there has learned a world shaped by those guards; removing them changes it.
  **Therefore deletion of any existing rule is out of scope for this plan** — the reflex runs
  alongside first, and each removal is a separate, measured decision.
- **Label noise.** A probabilistic classifier over prose. Mitigated by the gold set, the
  evidence quote, and keeping every row re-adjudicable.
- **Survivorship.** Only mistakes that were *discovered* are in the corpus. Mistakes that
  slipped through entirely are invisible — the corpus systematically under-represents exactly
  the failures nobody caught. State this wherever a number from it is quoted.
- **Privacy / scope.** Mining cheliped and other repos puts other projects' prose in the
  corpus. An earlier plan defaulted to no, opt-in per repo. That default should hold unless
  David changes it deliberately.
- **The corpus is not vendored.** `calibration/` is not shipped downstream by
  `install_into_repo.py`, verified. A trained weights file in `bin/` WOULD ship — that is the
  propagation channel, and it is a deliberate later decision, not a side effect.

---

## 7. What this plan does not do

No existing guard is modified or deleted. No doctrine is rewritten. Nothing is wired into the
gate. The deliverable is a corpus, a baseline number, and — if the baseline clears — one
trained model evaluated against it.

The review of the Playbook to remove the long tail comes *after* there is a measured
replacement, not before.
