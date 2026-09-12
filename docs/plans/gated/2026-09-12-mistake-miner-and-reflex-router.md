# Mistake Miner → Error Corpus → Reflex Router

> **DATA MOVED TO A PRIVATE REPO — 2026-09-12.** The mistake miner reads real session
> transcripts, so its code, its corpus, its hand-built ground truth and its taxonomy
> sample now live in **`davalst/mistake-miner` (private)**. `davalst/tdd-playbook` is
> PUBLIC. This file is kept here as the §0 planning record the house rules require to land
> in-repo; every **verbatim session quote and session UUID has been redacted** out of it,
> and the unredacted copy is in the private repo under `docs/`.



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
| E1 | `fabricated-reference` | Cited a function / file / symbol that does not exist | `<a fabricated function name, redacted>` cited twice as the lead consumer; repo-wide grep returns only the plan's own mentions |
| E2 | `stale-fact` | Asserted something that was true once and is not now | "<a stale claim, redacted> parameter" — that work had landed weeks earlier |
| E3 | `unverified-claim` | Asserted without checking the thing itself | quoting a sibling plan instead of source |
| E4 | `vacuous-check` | Wrote a test/assertion that cannot fail | `check('<a vacuous assertion, redacted>', True)` |
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
| invented a function (<a fabricated function name, redacted>) | 613 | 715 | 102 |
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
  "evidence_quote": "<a fabricated function name, redacted> ... does not exist",
  "entity": "<a fabricated function name, redacted>",
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

---

# APPENDIX A — FlyGM ground truth (added 2026-09-12, from the paper and the code)

**Why this appendix exists.** §1 above says plainly that "everything below about FlyGM
comes from search summaries, not from the paper," because the originating container
blocked `arxiv.org` and `sites.google.com`. Those blocks do not apply on this host. The
paper and the code have now been read first-hand. **§1's table is wrong on its single most
load-bearing row**, and the "Code | Released" row is wrong too. Corrections below; §1 and
§2 should be read through this appendix, and §5's D7 needs rewriting before anyone attempts
it.

**Sources, all fetched and read directly:**
- `arXiv:2602.17997v1 [cs.LG] 20 Feb 2026`, Jin, Zhu, Zhang, Sui (Georgia Tech / Tsinghua;
  corresponding `ysui@tsinghua.edu.cn`). Read via the arXiv HTML full text (`/html/2602.17997v1`),
  9,561 words, Method §3 and Appendices A–D in full.
- Project page `lnsgroup.cc/research/FlyGM` and its mirror `sites.google.com/view/flygm`.
- The code snapshot, MIT-licensed, linked from the authors' own project page:
  `anonymous.4open.science/r/flygm` — README, LICENSE, `src/flygm/*.py` (5 modules,
  ~53 KB) and `data/node_df.csv` (139,246 rows).

**A methodological note that belongs in the corpus this plan is building.** The first
attempt to read the paper used a fetch-and-summarise tool. It returned a confident,
well-formatted method summary describing *C. elegans*, 302 neurons, and a 7,000-synapse
graph — for a paper about *Drosophila*. It also invented a parameter count ("approximately
3,000–5,000 trainable parameters") that appears nowhere in the paper, and attributed the
connectome to "Dorkenwald et al. (2024)" while calling it *C. elegans* (Dorkenwald et al.
is the FlyWire *Drosophila* reconstruction). Every fact below comes from the primary text
instead. This is error class **E1/E3** committed by a summariser and caught only because
the species was checkable in one glance — a live instance of exactly what this plan wants
a reflex to catch, and a reminder that a fluent summary is a proxy, never the thing.

## A.1 What is learned versus fixed — §1's table has this BACKWARDS

§1 states: *"What is learned | The weights; the topology is fixed from biology."*

**Both the topology and the synaptic weights are FIXED.** The paper: the synaptic weight
matrix `W` "acts as a **fixed**, recurrent state-transition operator that dictates the
information flow through the network" (§3.1). `W` is not learned — it is *computed* from
the connectome as the net polarised synapse count, `W_vu = N_exc(u,v) − N_inh(u,v)`
(Eq. 1), with polarity assigned from neurotransmitter annotations (excitatory: ACH, GLU,
ASP, HIS; inhibitory: GABA, GLY).

The code settles it beyond argument. In `src/flygm/flygm.py`:

    self.register_buffer("edge_index", edge_index)
    self.register_buffer("edge_weight", edge_weight)

A PyTorch **buffer**, not an `nn.Parameter`. It receives no gradient. What *is* trainable
is everything wrapped around the connectome:

| trainable component | what it is |
|---|---|
| `encoder` | `nn.Linear(obs_dim → 32)`, the afferent input projection |
| `input_gate` | `nn.Linear(64 → 32) + Tanh`, injects encoded obs into afferent neurons |
| `node_init` | `nn.Parameter[1, |V|, C]` — a learned initial state **per neuron** |
| `intrinsic_features` (η) | `nn.Parameter[1, |V|, D]` — a learned descriptor **per neuron** |
| `FlyGMConv × 4` | the shared update MLP — `Linear(64→32) + SiLU + Linear(32→32)` + LayerNorm, **shared across all neurons** |
| `decoder` | `nn.Linear(C × |V_e| → 128)` over the FLATTENED efferent states |
| `mu_head` / `std_head` | `nn.Linear(128 → act_dim)`, Gaussian policy heads |
| (PPO stage only) | a separate MLP value network |

So the correct sentence is: **the connectome supplies fixed structure and fixed signed
edge strengths; learning happens in a per-neuron embedding table, a shared update MLP, and
the encoder/decoder at the two interfaces.**

## A.2 How big the trained parameter set actually is — ~15M, not "biologically compact"

The paper never reports a parameter count. Computed from the code and the paper's own
walking-task hyperparameters (`|V|=139,246`, `|V_e|=1,488`, `C=D=32`, 4 message-passing
layers, `obs_dim=1,253`, `act_dim=59`, `latent_dim=128` hardcoded in `FlyGMAgent`):

| component | params | share |
|---|---|---|
| `decoder` Linear(47,616 → 128) | 6,094,976 | 40.4% |
| `node_init` [1, 139246, 32] | 4,455,872 | 29.6% |
| `intrinsic_features` [1, 139246, 32] | 4,455,872 | 29.6% |
| `encoder` Linear(1253 → 32) | 40,128 | 0.27% |
| **`FlyGMConv` × 4 — the connectome-structured part** | **12,800** | **0.085%** |
| `mu_head` + `std_head` | 15,222 | 0.10% |
| `input_gate` | 2,080 | 0.01% |
| **total trainable** | **≈15,076,950** | |

Three consequences the plan must absorb:

1. **~15 million trainable parameters**, not a small biologically-compact set. Two
   `|V| × 32` embedding tables account for 59% of them and one dense decoder for another
   40%.
2. **The connectome-structured computation is 0.085% of the trained parameters.** The
   paper says the shared MLP lets "the connectome-conditioned recurrent dynamics carry out
   most of the computation"; in parameter terms almost all capacity sits in the per-neuron
   tables and the flattened decoder. The connectome is the *prior*; it is not where the
   learning lives.
3. **The parameter count scales with |V|, so it does not shrink for our problem.** Our
   afferent vector is a handful of symbolic features and our efferent head is six small
   decisions — but `node_init` + `intrinsic_features` stay at 8.9M because they are indexed
   by neuron, not by task. A reflex meant to answer in milliseconds would be carrying an
   8.9M-parameter embedding table through 4 rounds of message passing over ~139k nodes.
   **This is a new, measured argument for taking D6 seriously as a real decision gate**,
   and for considering a subgraph rather than the whole brain if D7 ever runs.

Also worth noting on the paper's own "beyond mere parameter count" framing (§4.1): the
ER-random and rewired baselines DO have identical parameter counts, so that comparison is
fair. The **MLP baseline is not** — same encoder plus two 512-wide layers is ≈350k
parameters, roughly **43× smaller** than FlyGM. And the graph baselines were run "unweighted
with unit strength" while FlyGM got the signed synapse counts, so that comparison mixes
topology with edge weighting rather than isolating topology.

## A.3 The afferent and efferent interfaces, concretely

**The neuron partition is exact** (counted directly from `data/node_df.csv`, 139,246 rows,
FlyWire FAFB v783 `flow` column):

    afferent   19,262      intrinsic  118,496      efferent    1,488

**Afferent.** Observations are NOT fed to individual sensory neurons. The whole observation
vector goes through one linear encoder to 32 dims, and that single 32-vector is
**broadcast identically to all 19,262 afferent neurons**, concatenated with each neuron's
current state, and squashed through a shared `Linear(64→32) + tanh` gate:

    H_t[V_a] ← tanh(W_g [ H_t[V_a] ‖ 1·x̃_tᵀ ] + b_g)

The `1·x̃ᵀ` is literally a broadcast. The paper is explicit about why — it avoids
"expensive per-neuron encoding." So the afferent interface carries **no per-neuron sensory
addressing at all**: all 19,262 afferent neurons receive the same 32 numbers and are
distinguished only by their learned `η` and their position in the graph. For our domain
this is *good news* — swapping in a symbolic feature vector means changing one
`nn.Linear(in_features=…)`, nothing more.

**Efferent.** The 1,488 efferent states (32 channels each) are **flattened to a single
47,616-vector** and pushed through one dense `Linear(→128)`, then the policy heads. There is
no per-motor-neuron readout and no structure in the decoder — it is a fully-connected
layer over the concatenation. Swapping in six discrete heads is again a one-layer change.

The efferent set decomposes as **descending 1,303 + motor 105 + endocrine 80 = 1,488**
(`super_class` tally). This resolves a concern worth recording: FAFB is a **brain-only**
connectome, and a fly's leg motor neurons live in the ventral nerve cord, not the brain —
there are only 105 motor neurons in the whole graph. The authors drive the body through
**descending neurons**, which is the biologically correct output channel for a brain
controlling a VNC. But it means "whole-brain … whole-body" does not include the VNC: the
model is a brain issuing descending commands to a body whose spinal-equivalent circuitry is
replaced by MuJoCo actuators. Relatedly, 77,531 of 139,246 neurons (56%) are `optic`, and
they are driven by two 16×16 greyscale images.

## A.4 Is the code usable as a library, or welded to the MuJoCo fly body?

**§1's "Code | Released" row is wrong.** The project page says **"Code (Coming soon)"**. A
GitHub search for the project returns zero repositories. What exists is an **anonymous
peer-review snapshot** at `anonymous.4open.science/r/flygm` (MIT, linked from the authors'
own page), whose README states: *"The source code is still being organized… You may
encounter potential environment incompatibilities, and some parts of the code may contain
legacy issues (e.g., hard-coded paths or settings without CLI support)."* **No checkpoints
are released** — "in future releases, we will provide more extensible code and also release
model checkpoints."

**On the weld — the answer is better than feared, and it is specific.** `flybody`,
`mujoco` and `dm_control` appear in **exactly one of the five source modules**:

    src/flygm/train_post.py:15  from flybody.fly_envs import walk_imitation
    src/flygm/train_post.py:19  os.environ.setdefault("MUJOCO_GL", "egl")

`flygm.py`, `connectome.py`, `flygm_message_passing.py` and `utils.py` import **zero**
simulator code — only `torch`, `pytorch_lightning`, `pandas` and `torch_geometric`. The
stage-1 imitation data path (`utils.ImitationDataModule`) loads plain `.npy` arrays into a
`TensorDataset`; it knows nothing about flies. So:

- **The core is body-agnostic**: connectome loader + graph model + agent wrapper +
  stage-1 supervised training is an `obs_dim → act_dim` learner over numpy arrays.
- **The weld is entirely in stage 2** (`train_post.py`, PPO in the flybody env).
- **This plan builds stage one only** (§2), so the weld is in the half we do not need.
  That is a genuine, verified point in the plan's favour — and it is the only §1 claim that
  turned out *better* than stated.

What you would still have to supply or fix:

- `connections.csv` (>100 MB) is **not in the snapshot**; you download FAFB v783
  `connections_princeton.csv` from `codex.flywire.ai` yourself. `node_df.csv` **is** included.
- Hard-coded paths, `LOG_DIR`, `accelerator="gpu"`, `devices=[0]`, no CLI. Trained on
  A100 80GB.
- **The shipped `train_pre.py` does not run the paper's headline configuration**: it sets
  `model_type="GraphSAGE"` and `node_channels=16`, not `model_type="FlyGM"` with 32
  channels. The custom intrinsic-feature operator is never instantiated by the entrypoint.
- `self.edge_weight` is set **only** on the `edge_profile` code path. The default path
  (`connections_file`) leaves `edge_weight = None`, i.e. **unweighted sum aggregation** —
  so the paper's signed `W` of Eq. 1 requires an extra CSV with a `weight` column that is
  neither shipped nor documented. This explains a discrepancy between the primary sources:
  the project page says "we model the connectome as an **unweighted**, directed graph" while
  the paper's §3.1 defines a signed weighted `W`. The default code path matches the project
  page; the paper's equation matches a path you must feed yourself.
- `hidden_channels` is accepted by `FlyGMMessagePassing` and then never used in the FlyGM
  path. `ConnectomeDataset` has a typo'd parameter (`connectome_chche_dir`) and a documented
  dead one (`idmapping_file`, "currently unused"). Cached tensors are loaded with
  `torch.load(..., weights_only=False)` — arbitrary-code deserialisation if a cache
  directory is ever shared. `LightningAgent.validation_step`'s docstring promises to
  "optionally log evaluation reward if environment is provided"; the body never touches an
  environment.

## A.5 What §1's table should say

| Property | §1 as written | Corrected |
|---|---|---|
| What is learned | "The weights; the topology is fixed" | **Neither** — topology *and* signed edge strengths are fixed buffers. Learned: per-neuron `node_init` + `η` tables, a shared 4-layer update MLP, and the encoder/decoder at the interfaces |
| Trained parameter set | not stated | **≈15.1M** (walking config); 59% in two `|V|×32` tables, 40% in the flattened efferent decoder, **0.085% in the connectome-structured MLP** |
| Afferent interface | "afferent ← joint angles, vision, contact" | one `Linear(obs→32)` **broadcast identically** to all 19,262 afferent neurons; no per-neuron addressing |
| Efferent interface | "efferent → joint torques" | 1,488 efferent states **flattened** into one dense `Linear(47,616→128)`; 1,303 descending + 105 motor + 80 endocrine |
| Training | "imitation then PPO" | **confirmed correct** — KL + annealed MSE behavioural cloning, then PPO with GAE and an MLP critic |
| Code | "Released" | **Not released.** "Coming soon"; an anonymous MIT review snapshot exists, self-described as unorganised, no checkpoints, and its stage-1 entrypoint does not run the paper's headline config |
| Baselines | "beat random, rewired, and MLP on sample efficiency and motor accuracy" | Sample efficiency: supported (imitation stage, Fig. 3). Motor accuracy: **partly** — in Table 1 the rewired graph beats FlyGM on *position* error in 2 of 4 conditions; FlyGM's consistent win is on *angle* error. The MLP appears in Fig. 3 only, never in Table 1, and is ~43× smaller |

## A.6 Consequence for §5's build order

D7 as written — "take FlyGM's released code, replace the afferent interface … and the
efferent interface … train stage-one" — has **no released code to take** and no checkpoint
to start from. It would mean training ~15M parameters from scratch, of which 8.9M are
per-neuron tables over a 139k-node graph, on a corpus of a few thousand events. The
interface swaps themselves are genuinely one `nn.Linear` each, which is the cheap part.
**D6 was already the decision gate; this makes it the load-bearing one.** If D7 is ever
attempted, the open design question to settle first is whether to use the whole 139k-node
graph or a task-relevant subgraph — the paper gives no guidance, because for a fly
controlling its own body the whole brain is the task.
