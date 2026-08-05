<!-- Provenance: external working document uploaded by David 2026-08-05; compiled from a
design discussion on two-agent recursive-improvement loops. Committed verbatim below this
header as the motivating evidence for docs/plans/rsi-hardening-2026-08.md. -->

# Two-Agent Recursive Improvement Loops: Design, Evidence, and Precedent

*Working document. Compiled from a design discussion that started with "how do you prime a two-agent loop" and ended somewhere considerably less comfortable.*

---

## 0. The Short Version

**What we set out to design:** two AI agents in a listener/questioner/mentor relationship, challenging each other, recursively improving.

**What the argument actually converged on:** a closed loop of language models cannot improve itself. It can generate. It cannot verify. Every real gain in the design came from adding something *outside* the loop — a held-out set, a dated prediction, an independent reviewer, a control arm. The two-agent conversation is the hypothesis generator. The scaffolding around it is where improvement actually lives.

**The load-bearing sentence:** improvement requires contact with something that doesn't care how you feel about it.

**The structural conclusion, which turned out to be the same one that aviation, surgery, clinical trials, lab medicine, and standardized testing all reached independently:** you do not fix self-assessment by making the assessor more reflective. You fix it by moving the check into a role with different incentives, a rotation schedule, and criteria written down beforehand.

---

## Part I — The Argument Chain

This is the reasoning in the order it happened, because the order matters. Each step was forced by the failure of the previous one.

### Step 1: The priming question, and why it's the cheap problem

**The observation:** agents are trained to respond, not initiate. So you have to ask the first set of questions to prime the loop.

**True, and solvable in one line.** But it's the least of the problems. The expensive failures show up around turn four:

| Failure | Mechanism |
|---|---|
| **No gradient** | Two agents talking produce no error signal. The loop improves *articulation*, not correctness. You get more elaborate and more confident, not more true. |
| **Correlated priors** | Same base model means the "challenge" is bounded by what that model can already see. Two instances aren't two critics; they're one critic with extra steps. |
| **Agreeableness drift** | "Mentor" framing decays into "great point, building on that" within a handful of turns. RLHF'd models converge toward each other fast. Adversarial framing survives longer than collegial framing. |

**Design responses:**

- Use *different models* for the two roles to decorrelate the priors.
- Enforce asymmetry **at the harness, not in the prompt**. The questioner's output should be structurally constrained — must end in a question, must contain no assertions — because if you merely *ask* it to stay in role, it starts proposing solutions by turn three.
- Priming is not a one-time event. It is a **recurring injection**. Rotate a lens each round so the initiating pressure gets re-applied rather than decaying into mutual response mode.

### Step 2: The lens rotation

If the initiating pressure has to be re-applied every round, it needs a bank to draw from. Ten families of ten — sampling by family first, then within it, prevents drawing three near-synonyms in a row. **Full list in Appendix A.**

Two sampling rules that emerged:

- **Weight the meta family (family 9) higher after turn three or four.** That's when drift sets in, and it's the only family that can see the drift.
- **Draw without replacement within a session**, so you don't get falsification twice while never touching incentives.
- **Make lens #86 (ledger entry) mandatory on the final round.** Every session exits with at least one dated, scoreable claim. That is what turns a transcript into signal.

### Step 3: "How do we know there was improvement?"

**The reframe:** determinism is available on the *check*, not on the *claim*. You cannot get a deterministic verdict on "is this insight better." You can get one on "did the artifact pass a test it previously failed." So stop scoring the conversation and start scoring something the conversation produces that can be mechanically evaluated.

**Three tiers, by lag and rigor:**

1. **Mechanical** (instant, deterministic, shallow). Diff round N against N−1: claims added, retracted, unchanged. *Retraction count is the interesting one* — a loop that never retracts isn't reasoning, it's accreting. Also concept novelty (n-grams/embeddings absent from prior rounds), and whether the round produced any statement with a truth value at all. Reproducible with no model in the loop. Measures motion, not direction.

2. **Held-out task set** (fast, deterministic, meaningful). **The load-bearing tier.** A private set of problems with known answers in the target domain — cases where the outcome is already known, code with hidden tests, past decisions where the result is on record. The loop never sees them. After each round, run the artifact against the set. Score is a number. Improvement is the number going up. Deterministic because the answer key exists before the round runs.

3. **Prediction ledger** (slow, deterministic on resolution). Every round exits with dated falsifiable claims; Brier scores accumulate. Real signal, but the wait is weeks. It is the ground truth that eventually validates tier 2 — *if held-out scores climb while Brier scores don't, tier 2 is measuring the wrong thing.*

**The control arm matters more than the metric.** Run the identical task three ways at matched token budget:

- two-agent rotating loop
- single agent with the same lens prompts self-applied
- single agent, one shot

If the loop doesn't beat the cheap arms on the held-out set, the recursion is decoration.

**Anti-metrics — tracked to disqualify, not to celebrate:** output length, hedge density, confidence language, inter-agent agreement rate, citation of prior rounds. All rise monotonically in a degenerate loop. If they're up and held-out score is flat, that's drift, and that's the stop condition.

**Two disciplines:**

- **Pre-register the scoring function before the round runs**, or you will fit the metric to the output afterward without noticing.
- **Cap round count by marginal gain.** If held-out delta over the last two rounds is under noise, stop.

**The uncomfortable implication:** this only works in domains where you can build the held-out set. For "help me think about strategy" you can't — and there the loop is unfalsifiable by construction. Worth running for generativity, but it should not be called self-improvement.

### Step 4: "This sounds like TDD"

It is, and the borrow is worth making explicit.

**The strongest transferable principle: if you can't write the test, you don't understand the requirement.** If you can't specify the scoring function before the round runs, you don't have a well-posed improvement target — which is a signal to stop and reformulate rather than proceed. Most self-improvement setups fail exactly there and never notice, because the round always produces *something*, and something feels like progress.

**Where the analogy breaks, and the breaks matter:**

| TDD | This |
|---|---|
| Green is boolean | Held-out deltas are continuous and noisy — you need a measured noise floor before "improved" means anything |
| Test cheap, implementation expensive | Held-out set expensive, round cheap — discipline moves from per-change to per-project |
| Tests are meant to be read by the implementer | The held-out set is burned the moment the loop sees it — closer to train/test split than red-green |
| "All green" is a terminal state | No equivalent — the stopping rule is early stopping on validation loss, not TDD |

**The additional steal — mutation testing.** How do you know the held-out set discriminates at all? Feed it deliberately degraded artifacts: the previous round's version, a knowingly wrong heuristic, a null baseline. Confirm the scorer ranks them below. A scoring function that passes everything is the failure mode you'd never otherwise catch, and it's the one most likely to be quietly present.

### Step 5: Hiding and isolating parts of the approach

**Reframe the threat model first.** You are mostly not defending against a scheming agent. You are defending against **contamination** — the answer key leaking into the thing being scored through paths nobody designed. That's the failure that actually happens, and it looks identical to improvement.

**What to isolate, in priority order:**

1. **The held-out set.** Separate storage the loop's context never touches. If the agents run tools, the set can't be on a reachable filesystem or in a readable repo. Leaks constantly via someone pasting a failing case into the conversation to debug it.
2. **The scoring code.** If the loop can read the scorer, it optimizes the scorer's shape rather than the target. Score out-of-process; return only the scalar.
3. **The score history.** The subtlest one. Feed back *improved / didn't* — not the per-item breakdown, not which cases failed. Per-item feedback lets a many-round loop reconstruct the set by inference. This is true with no intent to cheat; it's just gradient descent on whatever information you provide.
4. **The rotation seed.** If the lens sequence is predictable and visible, the loop pre-satisfies it — producing text shaped to *look* falsification-aware rather than actually being falsifiable.

**Structural defenses worth more than secrecy:**

- **Hold a second set the scorer never sees either.** A validation/test split of your validation. If performance on set A rises while set B stays flat, you've overfit A regardless of how well A was hidden. Catches most of the concern and doesn't depend on the loop being honest.
- **Rotate the held-out set periodically.** Any fixed set decays as it leaks through the very channel you're using it to evaluate.
- **Log the artifact at every round, immutably.** Post-hoc you can replay any version against a fresh set — converting "did it cheat?" from a question about intent into a reproducible experiment.

**Two honest limits:** isolation is unfalsifiable in the direction that matters — you can never prove nothing leaked, only fail to detect leakage. And a genuinely capable agent optimizing a proxy needs no deception to break the setup; it just needs the proxy to diverge from the goal, which it will. Isolation slows the leak; it doesn't change the fact that you're measuring a proxy.

### Step 6: What keeps humans improving vs. fooling themselves

The detour that reorganized everything.

**The short answer: contact with something that doesn't care how you feel about it.** Everything else is downstream.

**Mechanisms that produce real improvement**, roughly by load-bearing weight:

- **Consequence you can't reinterpret.** The bread rises or it doesn't. The trail drains or it floods. The company sells or it doesn't. Domains with unambiguous verdicts produce real skill; domains where the verdict is a matter of framing produce confident practitioners who never improve. This is why physical craft is a reliable teacher and thought leadership is not.
- **Short feedback loops.** Weather forecasters and anesthesiologists are famously well-calibrated. Pundits and long-horizon strategists are famously not. Same species, same intelligence — the difference is whether the answer returns fast enough to attach to the decision that caused it.
- **Prediction before the fact.** Written, dated, specific. Without it, hindsight rewrites what you believed and you experience learning while learning nothing. The human version of pre-registration, and the highest-leverage habit on the list.
- **Someone with standing to say no.** Not a supportive friend — someone who can see the work, has their own competence in it, and bears no cost for telling you it's bad. Rare, and it *degrades with your status*. The better you do, the fewer people will tell you the truth, which makes success a self-improvement hazard.
- **Difficulty that stays just past comfortable.**
- **Working at the edge of failure often enough to fail.** A record with no failures means the difficulty was set too low, not that you're excellent.
- **Retrospect on process, not outcome.** Good outcomes from bad reasoning are the most corrupting single event in a learning history — they install the wrong lesson at maximum confidence.

**Mechanisms of self-deception:**

- **Fluency mistaken for understanding.** You can explain it, so you think you can do it. Reliably wrong.
- **Effort mistaken for progress.** Hours logged, systems built, tools configured.
- **Insight mistaken for change.** The feeling of "oh, that's what I do" is genuinely pleasurable and almost entirely uncorrelated with behaviour changing. Especially seductive for people good at self-analysis — the analysis becomes the activity.
- **Audience substituting for verdict.** Approval from people who can't evaluate the work.
- **Ceaseless reframing.** If every outcome can be narrated as a learning experience, none of them are.
- **Novelty substituting for depth.** New method, new tool, new framework — perpetual restart at the shallow end.

**The throughline:** humans improve when reality pushes back, and the reasons humans fool themselves are almost all *internal* — closed loops, self-narration, absent verdicts. Two agents talking is a closed loop by construction. It can generate hypotheses well. It cannot supply the pushback.

### Step 7: Gaps found by mapping the human list back onto the design

Nine mechanisms with no counterpart in what we'd built:

| Gap | Fix |
|---|---|
| **Insight ≠ change** (biggest gap) | **Decision-vector diff.** Compare decisions, not text. Run artifact N and N−1 over the held-out set and diff the *outputs*. Identical decisions with different prose is the loop's version of pleasurable insight that changes nothing — and as designed, it would have scored as a productive round. |
| **Difficulty calibration** | Target a failure band and auto-escalate the set when the loop clears it. If held-out score is near ceiling you've learned nothing and can't detect that. |
| **Process vs. outcome** | Log the reasoning trace separately; at resolution flag the quadrants. Right/bad-reasoning and wrong/good-reasoning are the two cells you actually need. |
| **Pre-specified resolution criteria** | Resolution condition *and judge* specified at claim time, not at resolution time. Otherwise "well, arguably it did happen." |
| **A critic with standing and no history** | Periodic cold reviewer: separate model, no transcript, no prior rounds — sees only the current artifact and the task. |
| **Effort ≠ progress** | Cost per unit of held-out gain, per round. Cheap, and it kills the "look how much we built" illusion fast. |
| **Novelty ≠ depth** | Lineage tracking: what fraction of round N descends from N−1 vs. greenfield. Perpetual reframing shows up as a low descent ratio. |
| **Ceaseless reframing of the target** | Metric change log. Redefining success is allowed but must be a logged event, and the old metric keeps getting reported alongside. |
| **Skill decay** | Regression suite of previously-passing cases, so frontier improvements don't silently break what already worked. |

**If you only add two:** the decision-vector diff and the failure-band difficulty control. Between them they close the loop's two most flattering failure modes — sounding different while doing the same thing, and passing a test that was never hard enough to fail.

### Step 8: What the literature says

Searched rather than asserted. **Full citations in Appendix B.** Summary of the checks:

**Strongly supported:**

- *The premise.* Intrinsic self-correction fails on reasoning; performance sometimes degrades after the attempt. A follow-up survey found no prior work demonstrating successful intrinsic self-correction from the model's own feedback alone; later work found correction can flip right answers to wrong.
- *The two-agent framing specifically.* An ICLR 2025 blog evaluation of five multi-agent-debate frameworks across nine benchmarks found they don't consistently beat simpler single-agent strategies even at higher compute. **The control arm isn't optional — it's the finding.**
- *Stopping rule.* Reward-overoptimization work shows a hump: gold reward rises, peaks, then falls while proxy score climbs monotonically. That's the degenerate loop with a measured shape. "Score still going up" is not evidence to continue.
- *Cold reviewer.* Better supported than expected — there's a documented "self-correction blind spot": models fail to fix errors in their own output while successfully fixing identical errors presented as external input. So the fix isn't fresh context, it's making the artifact *arrive as foreign input*. Use a different model family: self-enhancement bias runs 10–25% preference for self-generated content.
- *Isolation.* The named patterns are **private benchmarking** and **dynamic benchmarking**. Contamination *detection* has had limited success, pushing the field toward mitigation by design. Design for resistance; don't plan to catch leaks.

**Required revision:**

- **Difficulty band — the original guess (20–40% failure) was wrong.** The RLVR literature converges on **~50% pass rate**. Reward entropy, group-filtering survival, RLOO advantage energy under GRPO, and success–failure pair count all identify the same target. Prompt-selection methods prioritize items closest to 0.5 to maximize advantage and therefore learning signal. **Set the target at half.**
- **Anti-metrics — sharper than originally framed.** Judge verbosity ratings track raw response length at r = .87 versus .44 for human raters. Length isn't merely correlated with a degenerate loop; it's what an LLM scorer will actively reward. If any part of scoring is model-based, length-penalize explicitly.
- **Scoring validity.** The largest systematic judge evaluation to date found exact-match agreement overstates discriminative ability, with 33–41pp deflation once corrected to Cohen's κ, and high test-retest reliability coexisting with severe position bias. **Reliable ≠ valid.** Use chance-corrected agreement.
- **Mutation testing has a formal analogue:** item-response-theory discrimination. Filtering eval sets by discriminability scores has cut test size ~65% while holding accuracy.
- **Brier caveat.** Brier reflects the underlying distribution of true risks and random variation, not just accuracy, and doesn't directly measure calibration; cross-population comparisons mislead. Decompose into calibration and discrimination rather than tracking one number.

**Genuinely thin in the literature:** the decision-vector diff. Closest existing work distinguishes surface from structural change using dual judges with Krippendorff's alpha and criteria built around behavioural properties rather than alignment with user intent. Right shape, not the same thing. **Building it puts you ahead of the literature rather than behind it** — which is also the honest caveat.

### Step 9: How humans already solved each of these

The move that produced the most value per question: for each item, ask what mature high-stakes fields do. **Full detail in Appendix C.** The condensed mapping:

| Item | Human precedent | What to import |
|---|---|---|
| **Decision-vector diff** | Miller's pyramid; unannounced standardized patients; espoused theory vs. theory-in-use; clinical audit | Blind, criteria-first, third-party observation of *behaviour in situ* — never self-report of change |
| **Self-correction fails alone** | NTSB investigates, not the crew; surgical M&M; accounting separation of duties | Role separation enforced structurally, not by good intentions |
| **Multi-agent ≯ single agent** | Shared-information bias; Delphi; nominal group technique; estimate-talk-estimate | **Independence before contact** — produce independently, *then* aggregate. Discussion-first destroys what makes aggregation work |
| **Stopping rule** | Clinical trials: pre-specified interim analyses, independent DSMB, futility boundaries, investigators blinded to interim results; aviation go-around gates | Pre-commit the futility boundary before round one; alpha-spending logic because peeking every round means naive thresholds fire on noise |
| **Cold reviewer** | Mandatory audit partner rotation; independent vs. consensus double reads in radiology; the Devil's Advocate office (abolished 1983; canonizations rose sharply after) | Rotate the reviewer on a schedule; reconcile *after* independent judgment |
| **Isolation / contamination** | Standardized testing item banks: rotating forms, embedded non-scoring pretest items, exposure-triggered retirement, blinded proficiency samples | Item banks are a wasting asset. Case generation is an operating line item, not a build phase |
| **Difficulty band** | Computerized adaptive testing; Elo matchmaking; go/chess handicaps; autoregulated strength training | **Adaptive, not curricular** — adjust from measured performance each round rather than pre-ordering easy-to-hard |
| **Anti-metrics / verbosity** | Blind auditions (and carpeting the floor when footfall gave candidates away); anonymous grading; word limits; structured interviews | **Remove the channel; don't instruct the judge to ignore it.** Normalize length and strip formatting before scoring |
| **Judge reliability** | Large-scale essay scoring: anchor-paper qualification, tolerance thresholds before going live, seeded validity papers *during* live scoring, drift monitoring, third-rater adjudication | The judge is under continuous test, not validated once |
| **Mutation testing / discrimination** | Psychometric item analysis (point-biserial); lab medicine positive/negative controls on every plate | Embed known-good and known-bad artifacts in **every** scoring run; discard rounds whose controls fail regardless of how good the results look |
| **Brier / calibration** | Weather verification as a standing function; clinical risk models reporting c-statistic and calibration slope separately; triennial actuarial experience studies | Report discrimination and calibration separately — a model can rank correctly while being systematically overconfident |

**The through-line, and the actual conclusion of the whole discussion:** every one of these institutions solved the problem by moving the check out of the head of the person being checked and into a role with different incentives, a rotation schedule, and criteria written down beforehand. **Not one of them solved it by making the practitioner more reflective.**

For a two-agent loop that means: the answer isn't better prompting of the critic. It's an architecture where the critic's independence doesn't depend on the critic.

**Worth noting what these fields have in common** — aviation, surgery, clinical trials, lab medicine, standardized testing. All of them have body counts or liability. The rigor exists because someone counted the failures. Building this before anyone's counting is the good position to be in, and also the reason it'll feel like overkill right up until it doesn't.

---

## Part II — The Design As It Now Stands

### A. The loop

- **Two different model families**, not two instances of one. Decorrelates priors.
- **Role asymmetry enforced at the harness**: questioner output must end in a question and contain no assertions. Prompt-level role instructions decay by turn three.
- **Independent production before contact** each round (Delphi discipline), then exchange. Not discussion-first.
- **A lens injected each round** from the bank (Appendix A), sampled family-first, without replacement within a session, meta-family up-weighted after turn 3–4.
- **Final round mandatory: lens #86.** Session exits with at least one dated, falsifiable, resolution-criteria-specified claim.

### B. The measurement stack

**Tier 1 — Mechanical, every round.** Claims added / retracted / unchanged. Retraction count. Novelty vs. prior rounds. Presence of any truth-valued statement. Cost per round.

**Tier 2 — Held-out set, every round.**
- Private, never in the loop's context or reachable filesystem.
- Scored out-of-process; only a scalar returns.
- Feedback to the loop is **improved / didn't** — never per-item.
- Difficulty auto-targeted to **~50% pass rate**; escalate the set when the loop clears it.
- **Decision-vector diff:** artifact N and N−1 run blind over the same cases in shuffled order, diff scored by a party that doesn't know which is which, agreement reported.
- **Controls on every run:** known-good and known-bad artifacts embedded. Controls fail → discard the run's results.
- **Second held-out set the scorer never sees.** A rises while B is flat = overfitting A.
- **Regression suite** of previously-passing cases.
- Length normalized and formatting stripped before any model-based scoring.

**Tier 3 — Prediction ledger, resolving on its own clock.**
- Claim, date, resolution condition, and named judge all specified **at claim time**.
- Reasoning trace logged separately from the claim.
- At resolution, flag the quadrant: right/good-reasoning, right/bad-reasoning, wrong/good-reasoning, wrong/bad-reasoning.
- Report **calibration and discrimination separately**, not a single Brier number.

### C. The controls and stopping rules

- **Three-arm comparison at matched token budget:** two-agent loop / single agent with self-applied lenses / single agent one-shot. Re-run periodically, not once.
- **Noise floor measured** by repeat runs at fixed artifact, before any delta is called improvement.
- **Futility boundary pre-committed before round one.** Alpha-spending logic for repeated looks.
- **Anti-metric dashboard** — length, hedge density, confidence language, inter-agent agreement, self-citation. Rising while held-out is flat = stop.
- **Scoring function pre-registered** each round.
- **Metric change log** — redefinitions allowed but logged, with the old metric still reported.

### D. The independence apparatus

- **Cold reviewer**: different model family, no transcript, no prior rounds, artifact presented as foreign input. Rotated on a schedule.
- **Judge under continuous test**: anchor cases, tolerance qualification, seeded validity items during live scoring, drift monitoring, chance-corrected agreement (κ / Krippendorff's α), not exact match.
- **Item bank treated as a wasting asset**: rotating forms, exposure-triggered retirement, ongoing case generation budgeted as operating cost.
- **Immutable artifact log** at every round, so any version can be replayed against a fresh set.

---

## Part III — What Remains Unproven

Honest inventory of where this document is asserting rather than demonstrating.

1. **Whether the loop beats the control arms at all.** The literature says multi-agent debate often doesn't. This design has not been run.
2. **The decision-vector diff** has no direct precedent in the ML literature. The human precedent (clinical audit, standardized patients) is strong, but the transfer is untested.
3. **Whether the held-out set can be built for the domains you actually care about.** For strategy, judgment, and open-ended thinking, probably not — and there the loop is unfalsifiable by construction.
4. **Proxy divergence is unsolved, not mitigated.** Isolation slows leakage. It does not stop a capable optimizer from finding the gap between the proxy and the goal. Only the ledger — dated claims against the real world — is resistant, and it's slow.
5. **Whether ~50% is the right target outside RLVR.** The result is from binary-reward RL training. Transfer to artifact evaluation is plausible but assumed.
6. **Cost.** Multi-agent reflexion pipelines have been reported at roughly 3× single-agent cost for the same task. Cost per unit of held-out gain is on the metric list for exactly this reason.

---

# Appendix A — The Lens Bank (100)

Ten families of ten. Sample family-first, then within family.

### 1. Falsification & evidence
1. Falsification — what observation would prove this wrong?
2. Disconfirming search — what haven't we looked for because we expect nothing there?
3. Base rate — how often do things in this reference class actually work?
4. Sample bias — who's missing from the evidence?
5. Survivorship — what does the graveyard look like?
6. Measurement validity — does the metric measure the thing, or a proxy?
7. Calibration — state a number; would you bet at those odds?
8. Load-bearing assumption — which single one collapses the rest?
9. Provenance — where did this claim originate, and has repetition laundered it?
10. Null result — what's the most boring explanation that fits the data?

### 2. Causal & systems
11. Second-order effects
12. Third-order — effects of the effects
13. Feedback loops — reinforcing or balancing?
14. Delay — where's the lag between action and signal?
15. Stock vs. flow
16. Bottleneck — what's the actual constraint?
17. Substitution — what fills the space if this is removed?
18. Coupling — what fails together?
19. Equilibrium — where does the system settle after everyone adapts?
20. Counterfactual — what happens if we do nothing?

### 3. Stakeholders & harm
21. Who's harmed
22. Diffuse cost — harm too spread out for anyone to complain
23. Who pays vs. who decides
24. Non-consenting participants
25. Power asymmetry — who can't walk away?
26. Worst-served user, not the median one
27. Inheritor — who maintains this in three years?
28. Externalities
29. Consent quality — informed, or nominal?
30. Empty chair — whose absence is shaping the answer?

### 4. Adversarial
31. Smartest opponent
32. Motivated attacker — how is this abused?
33. Steelman the rejected option
34. Bad-faith reading — how does this get quoted against you?
35. Competitor response
36. Regulator's reading
37. Goodhart — how does this get gamed once it's measured?
38. Insider threat
39. Hostile cross-examination
40. Cynic's motive — what would they say you're really doing?

### 5. Time
41. Pre-mortem — it failed; why?
42. Ten-year view
43. Reversibility — one-way or two-way door?
44. Decay — what rots first?
45. Why now — why not two years ago, or two from now?
46. Path dependence — what does this foreclose?
47. Compounding — what accrues quietly?
48. Legacy debt
49. Cadence mismatch — fast layer bolted to slow layer
50. Sunk cost audit

### 6. Framing & abstraction
51. Reframe the question
52. Wrong problem — is this the real one?
53. Zoom out one level
54. Zoom in — the concrete single instance
55. Definitional — one word doing two jobs?
56. Category error
57. Analogy — what is this structurally like?
58. Disanalogy — where does that analogy break?
59. Inversion — solve the opposite
60. Constraint removal — what if the binding limit vanished?

### 7. Incentives & economics
61. Follow the money
62. Incentive alignment
63. Principal–agent
64. Unit economics
65. Opportunity cost
66. Who profits from the status quo
67. Marginal vs. average
68. Scale break — what fails at 10x, 100x?
69. Free-rider
70. Cost of being wrong vs. cost of delay

### 8. Execution
71. First failure — what breaks first in practice?
72. Smallest version that tests the core claim
73. Dependencies — what must be true elsewhere?
74. Operational load — who's on the hook daily?
75. Skill assumption — who has to be good at what?
76. Handoff points
77. Edge cases
78. Recovery — how do we detect it's wrong and undo it?
79. Boring alternative — what does off-the-shelf do?
80. Deletion test — what if we just removed this?

### 9. Meta — aimed at the loop itself
*(Up-weight after turn 3–4. Only family that can see drift.)*

81. Drift check — are we converging or just agreeing?
82. Novelty audit — what did this round actually add?
83. Confabulation risk — where is the model most likely inventing?
84. Training shadow — is this the consensus answer or the true one?
85. Absent discipline — who would see this completely differently?
86. **Ledger entry — extract one falsifiable claim with a date** *(mandatory final round)*
87. Disagreement surfacing — where do we two actually differ?
88. Question the questioner's frame
89. Cost of continuing — is more analysis the right move?
90. Stop condition — what would end this productively?

### 10. Lateral & generative
91. One-tenth resources
92. Extreme scale — for one person; for a million
93. Domain transplant — how does biology/logistics/law solve this?
94. Historical precedent
95. Jurisdiction swap — different country, different rules
96. Aesthetic — is it ugly, and does that matter?
97. Receiving end — what does this feel like to the person it happens to?
98. Taboo — what's the thing nobody says out loud?
99. Five-second dismissal — the option you discarded instantly
100. Silence — what hasn't been mentioned at all?

---

# Appendix B — Sources

Retrieved during the discussion. Grouped by the claim they support.

### Self-correction limits
- **Huang et al., "Large Language Models Cannot Self-Correct Reasoning Yet"** — ICLR / arXiv:2310.01798. Defines *intrinsic self-correction*; finds LLMs struggle without external feedback and sometimes degrade after the attempt. Notes that where a verifier exists (e.g. unit tests, code execution), external feedback works well.
- **Kamoi et al. (2024), self-correction survey** — no prior work demonstrates successful intrinsic self-correction using only the model's own feedback.
- **Zhang et al. (2025)** — self-correction can flip correct answers to incorrect via prompt bias and cognitive-like biases.
- **Tsui (2025), "self-correction blind spot"** — models fail to correct errors in their own outputs while correcting identical errors presented as external input. *(Via "Cross-Context Review: Improving LLM Output Quality by Separating Production and Review Sessions," arXiv:2603.12123.)*
- **Wu et al. (EMNLP 2024), "LLMs Can Self-Correct with Key Condition Verification"** — the partial counter-result: masking a key condition to construct a verification question does improve self-correction without external feedback.
- **"Self Correction without External Feedback"** (ResearchGate, 2026) — decomposes into error detection / localization / correction; identifies the *verification bottleneck*. Notes models often produce revisions that are superficially different without addressing the underlying error — directly relevant to the decision-vector diff.

### Multi-agent debate
- **"Multi-LLM-Agents Debate — Performance, Efficiency, and Scaling Challenges,"** ICLR Blogposts 2025. Five MAD frameworks, nine benchmarks; fails to consistently outperform simpler single-agent strategies even with more compute.
- **Du et al. (2023), arXiv:2305.14325** — the original multiagent debate result. Note the caveat in the write-ups: different initialization prompts/personas per agent yield further gains, and cost is the primary limitation.
- **Chen et al., "Towards Scalable Oversight with Collaborative Multi-Agent Debate in Error Detection,"** arXiv:2510.20963 — the pro-heterogeneity argument: models differ in knowledge and error tendencies, so they're unlikely to make the same mistakes simultaneously, providing complementary signals.
- **"Multi-Agent Evolve,"** arXiv:2510.23595 — Proposer/Solver/Judge triplet; explicitly notes that self-play methods depend on grounded environments (interpreter, game engine) and that extending to general domains is the open problem.
- **"MAR: Multi-Agent Reflexion,"** arXiv:2512.20845 — reports ~300–400 API calls per task, roughly 3× single-agent Reflexion cost.

### Contamination and held-out sets
- **Chen et al. (EMNLP 2025), "Benchmarking LLMs Under Data Contamination: A Survey from Static to Dynamic Evaluation."**
- **Zhang et al., GSM1k** — difficulty-matched held-out benchmark; accuracy drops up to 13% for some model families, systematic overfitting across sizes.
- **Deng et al. (2024)** — GPT-4 guessed missing MMLU answer options at 57% exact match, indicating memorization.
- **"LLM-as-an-Interviewer,"** arXiv:2412.10424 — contamination *detection* efforts have had limited success; the field has shifted to mitigation.
- **Rajore et al. (2024), TRUCE / private benchmarking**; **White et al., LiveBench** (monthly refresh, objective ground truth, no LLM judge); **Zhu et al., DyVal** (procedural generation with controllable complexity).

### Judge reliability and bias
- **Norman, Rivera & Hughes, "Reliability without Validity,"** arXiv:2606.19544. 21 judges, nine providers, ~541,000 judgments. κ deflation vs. exact match is universal (33–41pp on MT-Bench); judge rankings shift up to 14 positions across benchmarks; high test-retest reliability coexists with severe position bias.
- **Zheng et al. (2023), MT-Bench / Chatbot Arena** — GPT-4 >80% agreement with humans, comparable to human-human at 81%; also the origin of the position/verbosity/self-enhancement bias taxonomy.
- **Position bias up to 75% preference for first-positioned responses; self-enhancement bias 10–25%** *(via arXiv:2511.04133).*
- **Panickssery et al. (2024); Wataoka et al. (2025)** — self-preference bias in LLM evaluators.
- **"An LLM-Native Psychometric Instrument,"** arXiv:2606.09843 — judge verbosity ratings track raw response length at r = .87 vs. .44 for humans; standard defenses (ensembling, order reversal, agreement reporting) address variance within the judge population but not biases shared across it.
- **"Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge"** — 12 bias types; CALM framework.
- **Practitioner guidance** (W&B, Braintrust, Evidently): randomize order, mask model identity, state verbosity handling explicitly, separate reasoning text from decision fields, run multiple judges and analyze disagreement.

### Difficulty targeting
- **"Rollout Pass-Rate Control,"** arXiv:2605.05112 — four independent criteria (reward entropy, group-filtering survival, RLOO advantage energy, success–failure pair count) all maximize at 50% pass rate.
- **"Prompt Replay,"** arXiv:2603.21177 — prioritizes prompts closest to 0.5 to maximize advantage and learning signal.
- **"Learning-Zone Energy,"** arXiv:2605.17003 — Bernoulli variance 4p(1−p) governs GRPO gradient variance; retaining 40% of prompts matches or beats full-data baselines.
- **Counter-note:** in a vulnerability-detection domain (arXiv:2602.14012), difficulty filtering *hurt* relative to full data, and curriculum scheduling gave no gain over random. Transfer isn't automatic.

### Overoptimization and stopping
- **Gao, Schulman & Hilton, "Scaling Laws for Reward Model Overoptimization,"** arXiv:2210.10760 / ICML 2023. Proxy vs. gold gap; coefficients scale smoothly with RM parameters.
- **Rafailov et al. (NeurIPS 2024)** — same degradation patterns in direct alignment algorithms.
- Characteristic **hump-shaped curve**: gold reward and true win-rate rise, peak, then fall while proxy reward increases monotonically. Larger RMs and more data mitigate; larger policy capacity alone does not.
- **KL penalty caveat:** increases achievable proxy score at a given KL without measurable improvement on the gold–KL frontier.

### Discrimination and eval efficiency
- **MetaEval (AAAI 2026)** — Signal Detection and Item Response model; high-discrimination items capture greater performance variation and align better with full-benchmark rankings.
- **Discriminability-based filtering** — ~65% test size reduction while maintaining evaluation accuracy *(via Label Studio, 2026).*

### Calibration
- **"On misconceptions about the Brier score in binary prediction models"** (PMC12818272) — a Brier of zero doesn't indicate a perfect model; the score reflects the distribution of true risks and random variation, doesn't directly measure calibration, and cross-population comparison misleads. Complement with calibration metrics and utility measures.
- **Murphy / Yates decompositions** — calibration vs. discrimination; extensions for heterogeneous tournaments *(Judgment and Decision Making).*
- **Mellers et al. (2015)** — Brier feedback over a multi-year tournament benefits calibration; Actively Open-Minded Thinking and general intelligence also predict.
- **Counter-finding** (Cambridge, accountability study) — aggregated Brier scores of *trained* forecasters didn't differ significantly from untrained. Training effects are not automatic.
- **Process vs. outcome accountability meta-analysis** (PMC9094407) — outcome accountability judges the final product; process accountability judges the decision-making course regardless of outcome.

### Surface vs. structural change
- **arXiv:2605.00113** — dual-judge design, Krippendorff's α with an α ≥ 0.67 threshold below which dimensions are treated as exploratory; evaluation criteria built around *behavioural properties* rather than alignment with user intent, citing Sharma et al. (2023) on sycophancy.

---

# Appendix C — Human Institutional Precedents, In Detail

The move that produced the most value in this discussion: for each design problem, ask what mature high-stakes fields already do.

### C.1 — Measuring whether behaviour actually changed

**Miller's pyramid (medical education).** Knows → knows how → shows how → does. The insight: each level requires a *different instrument*, and passing a lower level predicts the higher one poorly. Written exams measure *knows*. OSCEs measure *shows how*. Only chart audit measures *does*. A text diff of loop output is "knows how." The decision-vector diff is "shows how." Nothing in the current design reaches "does."

**Unannounced standardized patients.** The strongest human answer to this exact problem. Trained actors present to real clinicians who don't know it's a test, embedded in normal caseload. It is a held-out set injected into live operation, and it is the only method that reliably reveals the gap between what practitioners say they do and what they do — a gap that is consistently large. **Mechanizable version: seed probe cases into the loop's real workload** rather than running a separate eval batch it can recognize as an eval.

**Espoused theory vs. theory-in-use (Argyris & Schön).** Don't ask what someone believes. Take a transcript of what they actually did, and infer the operative rule from the behaviour. Then show them the gap. Structurally identical to the decision-vector diff, and it predates the ML literature by fifty years — *including* the finding that people are reliably unaware of the divergence, which is why self-report cannot be part of the instrument.

**Clinical audit.** Pre/post abstraction against explicit pre-written criteria, by blinded abstractors who don't know which period a record came from, double-coded with agreement reported. **The blinding is the part most people skip and the part doing the work.**

**Shared principle across all four:** replace *self-report of change* with *third-party observation of behaviour in situ, against criteria written before the intervention*. Nobody in these fields believes an account of one's own improvement.

**Two supporting details worth carrying over:**
- **Response-shift bias** — retrospective self-assessment is actively corrupted, not merely weak. People unconsciously re-rate their former selves.
- **Kirkpatrick level 3** (behaviour on the job, measured later by others) is the level organizations universally skip because it's expensive, while levels 1 and 2 get measured constantly because they're cheap. Expect to feel that same pull.

**Concrete build:** freeze the criteria, run artifact N and N−1 blind over the same cases in shuffled order, have the diff scored by someone who doesn't know which is which, report agreement. That's clinical audit with the names changed.

### C.2 — The performer can't be the verifier

Aviation and medicine both concluded this and fixed it *structurally* rather than attitudinally:

- The crew doesn't investigate its own accident — the NTSB does.
- Surgical morbidity & mortality review is mandatory and public, not private reflection.
- Accounting separates the person who records from the person who reconciles.

The mechanism is **role separation enforced by the org chart**. Nobody trusts independence that depends on the practitioner's good intentions.

### C.3 — Why groups underperform their members

The human literature on the multi-agent-doesn't-beat-single finding, and the more useful half of it.

**Shared-information bias:** discussion converges on what everyone already knew. Groups systematically fail to surface uniquely-held information.

**The fixes that worked are all forms of independence before contact:**
- **Delphi** — anonymous, written, iterated rounds
- **Nominal group technique** — silent individual generation before discussion
- **Estimate-talk-estimate** — independent estimate, discussion, independent re-estimate

**Import:** both agents produce independently before seeing each other's output, and you aggregate. **Discussion-first destroys the very independence that makes aggregation beat the individual.**

### C.4 — Knowing when to stop

**Clinical trials** are the mature answer:
- Pre-specified interim analyses
- A Data Safety Monitoring Board **independent of the investigators**
- Stopping boundaries for **futility** as well as success
- The part people skip: **investigators stay blinded to interim results.** The people who want it to work don't get to see the numbers.

**Two imports:**
1. Pre-commit the futility boundary before round one.
2. Borrow alpha-spending logic — peeking every round means naive thresholds will fire on noise.

**Aviation's version:** the go-around gate. Pre-commit the abort at a point where you know you'll be tempted not to.

### C.5 — Independence has a half-life

Institutions treat this as a scheduled maintenance problem:

- **Mandatory audit partner rotation** exists because familiarity erodes skepticism on a predictable schedule.
- **Radiology distinguishes *independent* double reads from consensus reads.** Consensus anchors; independence catches more.
- **The Devil's Advocate** was a staffed office in the Catholic Church. Abolished 1983; canonizations rose sharply afterward.

**Import:** rotate the reviewer model on a schedule, and reconcile *after* independent judgment rather than reviewing together.

### C.6 — Item banks are a wasting asset

Standardized testing solved contamination, and its solution is an admission:

- Rotating forms
- Embedded pretest items that don't count toward the score
- Exposure-triggered item retirement
- Unannounced blinded proficiency samples sent to labs

**Nobody believes items stay secret; they budget for continuous item writing as an operating cost.** Do the same — case generation is a line item, not a build phase.

### C.7 — Adaptive difficulty

- **Computerized adaptive testing** selects the next item at the examinee's estimated ability, because that's where information is maximized — the same mathematics that produced the 50% target.
- **Elo matchmaking**; **go/chess handicaps** — both target roughly even odds.
- **Autoregulated strength training** adjusts by proximity to failure rather than a fixed schedule.

**Transferable bit: adaptive, not curricular.** Adjust from measured performance each round rather than pre-ordering easy-to-hard. *(Consistent with the RLVR counter-finding that curriculum scheduling gave no gain over random.)*

### C.8 — Remove the channel, don't instruct the judge

- **Blind auditions** — and when orchestras found candidates were still identifiable by footfall, they carpeted the floor. The lesson is in the follow-through.
- **Anonymous grading**
- **Word limits**
- **Structured interviews** — unstructured ones reward fluency and confidence, which don't predict performance.

**Import:** normalize length and strip formatting *before* scoring. Telling a judge to disregard verbosity does nothing.

### C.9 — The judge is under continuous test

Large-scale essay scoring is the closest analogue, and it is more aggressive than anything in the ML eval literature:

- Raters qualify against **pre-scored anchor papers**
- Must hit tolerance **before going live**
- Receive **seeded validity papers during live scoring**
- Are **monitored for drift and pulled if they drift**
- **Third-rater adjudication** on disagreement

The judge is validated continuously, not once.

### C.10 — Controls on every run

Two traditions converge:

- **Psychometrics:** item analysis, point-biserial discrimination, retire items that don't separate.
- **Lab medicine:** every plate runs positive and negative controls, and **if the controls fail you discard the entire run's results** no matter how good they look.

The second is stronger than spot-checking discrimination occasionally. **Embed known-good and known-bad artifacts in every scoring run; discard rounds whose controls fail.**

### C.11 — Calibration as a standing function

- **Weather forecasting** made verification a permanent institutional function with reliability diagrams — not an afterthought.
- **Clinical risk models** report discrimination (c-statistic) and calibration (slope, calibration-in-the-large) **separately**, because a model can rank cases correctly while being systematically overconfident. Different failures, different fixes.
- **Actuarial experience studies** run assumed-versus-actual on a fixed triennial cycle, whether or not anyone suspects a problem.

---

# Appendix D — Discarded and Revised Positions

Kept for the audit trail, because a document with no retractions isn't reasoning, it's accreting.

| Original position | Status | Why |
|---|---|---|
| Target a 20–40% failure band | **Revised to ~50% pass rate** | Four independent criteria in the RLVR literature converge on 0.5 |
| Length is a correlate of degenerate loops | **Strengthened** | It's not a symptom — it's what a model-based scorer actively rewards (r = .87) |
| Fresh context is enough for a cold reviewer | **Revised** | The self-correction blind spot means the artifact must arrive as *foreign input*, and the reviewer should be a different model family |
| Isolation prevents gaming | **Downgraded** | Isolation slows leakage. It cannot be verified, and proxy divergence needs no deception |
| Use agreement/exact match to validate the judge | **Revised** | Exact-match agreement overstates discrimination by 33–41pp; use chance-corrected κ or Krippendorff's α |
| Track a Brier score | **Revised** | Decompose into calibration and discrimination; a single Brier number conflates accuracy with the underlying risk distribution |
| Spot-check the scorer with degraded artifacts | **Strengthened** | Lab-medicine practice: controls on *every* run, discard the run if controls fail |
| Priming is a one-time setup step | **Revised in step 1** | It's a recurring injection; without it the loop decays into mutual response mode |
| Two agents = two critics | **Rejected** | Same base model = one critic with extra steps. Different families, and independence before contact |
