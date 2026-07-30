# Review — *Do Modules Stay in Their Lane? Role Drift in Compound LLM Systems*

**arXiv:** 2607.21627v1 [cs.AI], 7 Jul 2026 · **Authors:** Xiaoyang Cao (MIT), Siddarth Srinivasan
(Harvard), Michiel A. Bakker (MIT) · **Status:** Preprint, no venue stated
**Reviewed:** 2026-07-30 · Full text (15pp incl. appendices)

---

## Verdict

**Accept the phenomenon, send the method back.** The paper names a real and under-served failure
mode, and its best idea — *use the accuracy cost of role enforcement as a measurement of how much
of your RL gain was fake* — is a genuinely useful reframe that deserves to circulate. But the
empirical case for the proposed method is thinner than the writing implies: there is no
regularization baseline, the headline numbers are internally inconsistent across the abstract,
Table 1, and Figure 4, the mechanism analysis is circular by construction, and the method has a
blind spot derivable from the paper's own Proposition 1 that goes unmentioned. **Major revision.**

The gap between "this phenomenon is real and matters" (well supported) and "Role Anchor is the
right instrument for it" (not yet supported) is the whole review.

---

## What it claims

**Phenomenon (Role Drift).** In compound LLM pipelines optimized end-to-end against a terminal
reward, a module can improve the terminal metric by abandoning its assigned role. Terminal accuracy
rises; the division of labor the system was built around quietly dissolves. Two instances:

- **RAG** (QueryGen → frozen term-matching Retriever → Reader; Qwen2.5-3B; HotpotQA yes/no slice):
  the Reader stops using retrieved passages and answers from parametric memory.
- **DEC** (Decomposer Qwen2.5-7B → Solver Qwen2.5-0.5B; MuSiQue-Ans): the Decomposer plants
  gold-answer entities in its sub-questions, reducing the Solver to a copy mechanism.

**Method (Role Anchor).** Define the *role utility* as the log-ratio of the module's next-token
distribution under its role prompt vs. a neutral prompt, `u_r,θ(h,v) = log p_θ(v|h,s_r) −
log p_θ(v|h,s_0)` (Eq. 1). Mean-center it over the top-k candidate tokens (Eq. 2) and penalize
squared deviation from a frozen pre-RL reference (Eq. 3), added to the policy gradient with weight λ.

**Results.** Unanchored RL erodes both probes while accuracy climbs; Role Anchor holds the probes
near pre-RL levels at a pipeline-dependent accuracy cost (RAG −0.067; DEC 86%±19% of the gain).
Gradient analysis reports anchored updates project ≈0 onto a "drift direction."

---

## What the paper gets right

1. **The positioning is sharp and correct.** Framing Role Drift as *the compositional form of reward
   hacking*, and observing that RLVR does not help because "the verifier checks the final answer, not
   which module produced it" (§2), is the paper's cleanest insight. Verifiable rewards are widely
   credited with curbing reward hacking; this identifies a structural class they cannot touch. That
   observation alone justifies the paper.

2. **Accuracy cost as diagnostic, not as regrettable overhead** (§4.2, §4.5). Most method papers
   would bury a −0.253 accuracy delta. Instead the paper argues the delta *is* the measurement: it
   quantifies what fraction of the system's improvement was role violation. Reframing your worst
   number as your primary instrument is the right move and is argued honestly.

3. **Appendix A.2 is the strongest technical writing in the paper.** The decomposition (Eq. 5)
   showing that an uncentered anchor equals the centered loss *plus* a squared mean shift, followed
   by the worked example where RL sharpens the neutral distribution under a fixed multiplicative
   reweighting — so role behavior is perfectly preserved, the centered loss is zero, and the
   uncentered loss actively fights legitimate learning — is a real derivation that earns the design
   choice. This is not filler; it is the part I'd keep verbatim.

4. **Pre-registration instinct.** Checking before training that the role prompt actually beats the
   neutral prompt on the drift indicator (§3, Appendix B), and stating that the prompt "should be
   redesigned otherwise," is good practice for a method whose entire signal is that contrast. (The
   execution has problems — see M4 — but the instinct is right.)

5. **Honest reporting of scope and cost.** The limitations section (§6) correctly rules out API-only
   modules, non-probabilistic components, and prompt-optimized systems. Compute is reported including
   failed runs (~120 A100-hours reported, "roughly doubled" in practice). §4.5 explicitly disclaims
   any general accuracy benefit. These are the marks of authors not overselling.

---

## Major issues

### MAJOR-1 — There is no regularization baseline, so the method's central claim is untested

The experiments contain exactly two arms: RL, and RL + Role Anchor. The paper's claim to novelty is
specifically that preserving the **role-vs-neutral contrast** is the right thing to anchor, rather
than the distribution itself. §2 states the distinction explicitly — RLHF-style objectives
"regularize against a reference … without preserving how the role prompt changes predictions
relative to a neutral prompt." That is a conceptual distinction asserted, never an empirical one
demonstrated.

The obvious competing explanation is that **any** regularizer pulling toward the pre-RL reference at
strength λ would flatten these probes at some accuracy cost, because both probes are defined as
*distance from pre-RL role-faithful behavior*. Untested alternatives:

- **Plain KL-to-reference** under the role prompt — the standard RLHF control, and the one the
  related-work section positions against.
- **Early stopping.** DEC's insertion rate has an abrupt onset after epoch 4 (§4.2). Stopping at
  epoch 4 yields some gain at low insertion rate. What is the early-stopping frontier?
- **Generic capacity limits** — weight decay, lower LoRA rank, entropy bonus.

Without at least the KL arm at matched accuracy, the results are fully consistent with "reference
regularization prevents drift," and the role-utility machinery — two extra frozen-reference forward
passes, ~18–22% wall-clock overhead — is unmotivated. The λ=0.02 RAG result *sharpens* this concern
rather than resolving it: a small penalty that improves both accuracy and the probe is the classic
signature of a well-tuned generic regularizer on a noisy RL run, yet §4.4 reads it as
role-specific ("mild role enforcement can help when the drift shortcut is noisier than the intended
pathway"). Plausible, but indistinguishable from the generic story on present evidence.

**This is the one experiment that would most change my assessment.**

### MAJOR-2 — The headline numbers are mutually inconsistent

There are three different values for unanchored RAG evidence-following accuracy and two for
unanchored RAG accuracy, all presented as the same quantity:

| Quantity | Abstract / §4.2 | Table 1 (ep9, 3-seed) | §4.4 / Fig. 4 (λ=0) |
|---|---|---|---|
| RAG evidence-following, no anchor | **0.54** | **0.589** | **~0.75** |
| RAG accuracy, no anchor | ~0.45 (Fig. 2a) | **0.447** | **0.34** |

Figure 4b's y-axis spans 0.70–0.90, so its λ=0 point cannot be 0.54 or 0.589 — the disagreement is
structural, not rounding. This directly breaks a claim the paper flags as surprising: §4.4 says
λ=0.02 reaches accuracy 0.41, "the highest value across all tested settings including the unanchored
baseline (0.34)." Table 1 reports the unanchored baseline at **0.447** — higher than 0.41. The
paper's only free-lunch result is contradicted by its own table.

Either Figure 4 is at a different epoch / seed / eval slice than Table 1 (in which case say so, and
stop calling it the same baseline), or one set of numbers is wrong. Related, smaller: the "0.86"
pre-RL starting point in §4.2 is never reconciled with Appendix B Table A1's base-model value of
0.659 — presumably the 3-epoch SFT checkpoint sits between them, but "pre-RL" is used loosely
throughout and the reader is left to infer it.

### MAJOR-3 — The drift-direction analysis is circular

§4.3 defines the drift direction as *the mean unanchored update vector during peak drift epochs*,
then reports that unanchored updates project +0.50/+0.22 onto it while anchored updates project
≈0 (Fig. 3c). Unanchored updates projecting positively onto their own mean is arithmetic, not
evidence. And in high dimension, *any* intervention that changes the update trajectory — including
one that merely adds noise or shrinks along an unrelated direction — yields ≈0 projection onto
another run's mean.

Two controls are needed and absent:
- Project a **held-out unanchored seed's** updates onto the drift direction. Is +0.50 reproducible
  across seeds, i.e. is there a shared drift direction at all?
- Project a **non-role regularizer's** updates (KL, weight decay) onto it. If those also land at ≈0,
  Fig. 3c shows nothing role-specific.

The prose is appropriately hedged in §4.3 ("suggests," "appears to"), but contribution bullet 3
states it flatly: "we show that Role Anchor curbs drift by redirecting updates away from the
role-violating direction, not by suppressing learning." That is overclaimed. Note also that the
"doesn't suppress learning" claim rests essentially on RAG alone: on DEC the anchor demonstrably
does suppress most learning (+0.057 vs +0.310), and §4.3's own reading of DEC's cosine collapse to
0.07 is that "the model has little consistent direction left to follow." The paper's explanation
(there was nothing legitimate to learn on DEC) is coherent — but it means the mechanism claim is
carried by one pipeline whose accuracy delta is within noise (see MOD-1).

### MAJOR-4 — Proposition 1 implies a blind spot the paper never acknowledges

Proposition 1 establishes that `L_role = 0` iff `u_r,θ = u_r,ref + c(h)`: the anchor pins the
*contrast* between role- and neutral-conditioned predictions while leaving absolute predictions
free. The paper presents this purely as a feature ("RL can keep improving task accuracy," §3).

It is also a hole. If RL shifts `p(·|h,s_r)` **and** `p(·|h,s_0)` toward memory-based answering by
the same multiplicative reweighting, the log-ratio is unchanged, centering absorbs the normalizer,
and `L_role ≈ 0`. **Role Anchor is blind to drift that moves both conditionals together** — and
that is precisely the RAG drift pattern under study. A Reader that has learned to ignore passages
regardless of which prompt it receives is maximally drifted and maximally invisible to this loss.

This is structurally the same invariance that Appendix A.2 exploits deliberately in token space, now
appearing unbidden in conditioning space. The paper is rigorous enough about the first to make the
silence about the second conspicuous. Two consequences worth stating in the paper:

1. The anchor's empirical success on RAG is evidence that drift there *happened* to be
   contrast-visible — a contingent fact about these runs, not a property of the method.
2. It follows that Role Anchor cannot be trusted without a probe, which undercuts the §3 selling
   point that the anchor "supervises each module without any task-specific probe design." If you
   need a probe to know the anchor worked, the natural baseline is regularizing against — or early
   stopping on — the probe directly. Also untested.

### MAJOR-5 — The 86% headline is a property of a pipeline built to produce it

The paper is transparent that the 0.5B Solver was chosen deliberately because it "amplifies drift
pressure" (§4.1), and §4.2 concedes DEC's Decomposer "has little room for genuine improvement."
Those two statements together make the 86% figure close to tautological: construct a pipeline where
role violation is nearly the only path to reward, and removing role violation removes nearly all the
gain.

That is a legitimate stress test, but the abstract promotes 86% as support for a general claim —
"terminal accuracy alone can badly overstate how much a compound system has genuinely learned." The
generalization is carried by a deliberately pathological instance, and the paper's own explanation
of *why* it's 86% (capability asymmetry) is the variable never swept.

**A Solver-capacity sweep (0.5B / 1.5B / 3B / 7B), plotting drift fraction against capability
asymmetry, would convert the paper's most quotable anecdote into its strongest result.** The
hypothesis is already written in §4.2; it just isn't tested. This is the second experiment I'd ask
for.

### MAJOR-6 — The RAG story's key cell is missing, and a reported probe contradicts it

Table 1 reports "Acc. without passages" for DEC (0.050 / 0.080) but **not for RAG** — the pipeline
whose entire narrative is parametric memory. Memory-only accuracy for the RAG Reader, tracked across
RL epochs, is the direct measurement of the pathway the paper claims RL is reinforcing. Its absence
is conspicuous.

Worse, the probe that *is* reported points the other way. §4.2 says the random-passage result
confirms the unanchored Reader "has learned to answer from parametric memory regardless of what the
passage says" — citing 0.187. But this is a **yes/no** task. A Reader answering from memory
regardless of the passage should score at or above its memory-only accuracy, and unconditional
guessing alone yields ≈0.5. Scoring 0.187 means the unanchored Reader mostly *abstains or fails to
answer* when handed an unrelated passage — which is not the behavior of a memory-driven reader. The
number is consistent with a Reader that has become passage-*dependent* in a degenerate way, and it
does not support the causal story built on it.

---

## Moderate issues

**MOD-1 — Statistical power is insufficient for the precision claimed.** Eval sets are 176 (RAG
yes/no slice) and 200 (MuSiQue-Ans dev), with 3 seeds. At n=176 on a binary task, per-arm SE ≈ 0.038
and the difference SE ≈ 0.053 — so RAG's headline "modest cost" of −0.067 is ~1.2 SE, not
distinguishable from noise. No confidence intervals or significance tests appear anywhere except
86%±19%, and it is not stated whether ±19% is SD or SEM over 3 seeds; the difference is a plausible
range of roughly 67–105% vs. 48–124%. Since the abstract quotes 86% bare, the interval belongs
there. The reported seed spread on DEC insertion rate — "a factor of two to five" (§4.2) — indicates
high variance that the point estimates conceal. Figures show no error bars.

**MOD-2 — λ appears to be selected on the reported eval set.** λ differs 20× between pipelines
(0.05 RAG, 1.00 DEC) with no selection procedure described, and no dev/test split is mentioned —
Table A2 lists one evaluation set per pipeline, and the λ sweep and headline results appear to run
on it. If so, every reported number is optimistically biased and the frontier's shape in Figure 4 is
partly fitted. For a paper whose contribution is "λ gives practitioners a tunable frontier," how to
choose λ without touching test data is a first-order question, not an appendix detail.

**MOD-3 — The probes are proxies, and one is a lower bound the method could satisfy vacuously.**
Insertion rate counts sub-questions "containing the gold-answer entity" — a surface entity match. A
Decomposer can leak an answer by paraphrase or unique description ("the county whose seat is Fort
Stockton") and score clean. So insertion rate bounds leakage from below, and a reduction in measured
insertion is compatible with leakage persisting in unmeasured form. Relatedly, D.2's worked example
leaks *Pecos County*, an intermediate answer, and states the gold entities as "Pecos County and
Crockett County" — leaving unresolved what counts as "the gold-answer entity" in a multi-hop chain.
On the RAG side, evidence-following measures passage *sensitivity*, which is necessary but not
sufficient for grounding: on a binary task, a Reader that flips its answer whenever the passage
changes scores well without reading anything.

**MOD-4 — The calibration check was run on a different model than the anchor reference.** Appendix B
verifies the role-vs-neutral premise on the **base** model; Appendix C states the anchor reference
for RAG is the **post-SFT** checkpoint. The premise is therefore validated for a model that is not
the one anchored to — and the implied change is large (evidence-following apparently 0.659 → ~0.86).
Separately, the Table A1 margins are small enough to strain the word "meaningfully": +0.079,
−0.067, −0.080 on sets of 176/200, i.e. roughly 1–1.5 SE each. The method's entire supervisory
signal is this contrast; if it is near-vacuous at the reference, that is itself an argument that the
anchor works for reasons other than the contrast (→ MAJOR-1).

**MOD-5 — Trainable modules go undocumented, and drift may simply relocate.** §4.1 says "all
trainable modules use independent LoRA adapters," and the penalty is summed over modules
(`λ Σ_{i∈V_R}`). But Appendix C.1 gives prompts only for the RAG Reader and the DEC Decomposer.
QueryGen is trainable and its prompts are absent; the Solver's role prompt is absent. So it is
unclear which modules are anchored at all. This is both a reproducibility gap and an unexamined
confound: an unanchored QueryGen could learn to retrieve memory-consistent passages, producing
compound-level drift that a Reader-side probe cannot isolate.

**MOD-6 — "Invisible to system-level evaluation" overstates it.** Both probes *are* system-level
evaluations — counterfactual ones rather than i.i.d. accuracy. The defensible claim is "invisible to
i.i.d. terminal accuracy." The paper also doesn't engage the existing literature on measuring
context-faithfulness vs. parametric priors in RAG (knowledge-conflict benchmarks, context-conflict
probes); §2 covers *inference-time* faithfulness degradation but not the measurement tradition. The
RAG half is closer to "RL makes the known parametric-vs-context tradeoff worse" — a solid result,
but the evidence-swap probe is not new and shouldn't read as though it were.

**MOD-7 — The HotpotQA yes/no slice is a load-bearing choice, unjustified.** 176 binary examples
maximize the availability of the memory shortcut (0.506 floor), make the swap probe clean, and keep
resolution low. The standard HotpotQA setting is extractive short-answer. The choice may well be
right; it needs a sentence, and it bounds how far the RAG conclusion travels.

**MOD-8 — Single model family, single RL algorithm.** Qwen2.5 throughout, REINFORCE + group baseline
throughout, LoRA rank 16 only. No PPO/GRPO, no second family. The claims are stated about compound
LLM systems in general. Drift dynamics that depend on the optimizer's exploration behavior are
exactly the kind of thing that changes between REINFORCE and PPO.

---

## Minor / presentation

- **Table 1 is not "matched operating points"** (§4.2). The arms are matched in *epoch*, and differ
  in accuracy by 0.067 (RAG) and 0.253 (DEC). For a method claiming a frontier, the comparison
  should be at matched accuracy, or a full frontier plot should replace the table.
- **Inverted y-axis** in Figures 2d and 4d, footnoted rather than avoided. Plot `1 − insertion rate`
  and label it; a caption note is not a defense against a reader who scans figures.
- **No error bars** in any figure despite 3 seeds.
- **Unlabeled aggregates** in §4.3: DEC coherence is quoted as "0.23 → peak 0.55" in prose and
  "0.36 → 0.07" in the Fig. 3 caption; 0.36 is presumably a training mean but is never said to be.
- **Table 1 vs Figure 2b** disagree at epoch 9 (0.589 vs ~0.54) even setting MAJOR-2's larger
  inconsistency aside.
- **No code or data availability statement.** For a method that is "a single added term in the policy
  gradient," release is cheap and its absence is notable.
- §6's extension to non-LLM modules (vision module drifting to "emit whatever coordinates make that
  controller succeed") is a genuinely good example and is underused — it belongs in the introduction.

---

## The three experiments I'd require

1. **A KL-to-reference arm at matched accuracy, on both pipelines** (MAJOR-1). This is the paper's
   load-bearing missing control. Report role fidelity per unit accuracy sacrificed for KL vs. Role
   Anchor. If Role Anchor doesn't dominate, the contribution is the phenomenon and the diagnostic,
   not the method — which is still publishable, but a different paper.
2. **A Solver-capacity sweep on DEC** (MAJOR-5): drift fraction vs. capability asymmetry, 0.5B →
   7B. Converts the 86% anecdote into a law.
3. **RAG memory-only accuracy across epochs** (MAJOR-6), plus reconciliation of the random-passage
   number with the parametric-memory story.

Plus, cheaply: fix the Table 1 / Figure 4 inconsistency, state whether ±19% is SD or SEM, report
CIs, and add one paragraph acknowledging the both-conditionals-move blind spot (MAJOR-4) — that
paragraph would strengthen the paper's credibility more than it costs.

---

## Relevance to this repo

The paper is a near-exact external statement of the failure mode this playbook exists to catch, in a
different domain. Map the terms:

| Paper | Playbook |
|---|---|
| Terminal reward / accuracy | A green test suite |
| Role utility | What a test was written to *verify* |
| Role Drift | A suite that stays green while losing its purpose (vacuous suite, weakened oracle) |
| RLVR doesn't help — verifier checks the final answer, not which module produced it | Why "tests pass" is not evidence the tests test anything |
| Accuracy cost of the anchor as a *diagnostic* | The AMBER/BLOCKING verdict as a measurement, not an obstacle |

Two transferable ideas worth considering for `docs/HACK_CATALOG.md` at the next quarterly refresh
(not now — catalog entries require planted tests, per release discipline):

1. **The role/neutral contrast as a guard primitive.** The paper's move — measure the *differential*
   effect of the instruction rather than the absolute behavior — is a plausible detector for
   "the agent stopped being steered by its instructions" that doesn't require a task-specific oracle.
2. **MAJOR-4 as a catalog entry in its own right.** "Both conditionals move together, so the contrast
   looks preserved" is a general shape for defeating differential guards, and it generalizes past
   this paper: any check comparing *guarded* to *unguarded* behavior is blind to a regression that
   degrades both equally. Worth a planted test against our own differential checks.

The paper's own conclusion is the playbook's thesis in one line: *"it is worth evaluating not only
whether the final answer improves, but whether the improvement arrives through the module pathway
the system was designed around."*
