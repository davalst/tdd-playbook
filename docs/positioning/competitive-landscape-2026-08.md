# Competitive Landscape — 2026-08

**Status:** working analysis · first entry: Aviator Verify
**Sourcing note (read this before quoting anything below):** `aviator.co` returns HTTP 403
to automated fetching, so this entry is built from their own product and blog copy
retrieved via search snippets, not from full pages. Quoted phrases are theirs; the
coverage is partial. **Anything here that becomes load-bearing for a fundraise or a
pitch must be re-verified by a human reading the live pages.** Dated because competitor
copy moves: re-read at the quarterly review.

---

## 1. Aviator Verify

**URL:** https://www.aviator.co/verify · blog at `/blog/`
**What it is:** spec-first verification of an individual change, sold to teams whose
review process is drowning in AI-generated PRs. Adjacent to their existing merge-queue
and AI-code-review products.

**Mechanism, in their terms:**

1. **Spec approval before implementation** — you and your agent agree on scope plus
   concrete acceptance criteria ("returns 429 when rate limit is exceeded"); a human
   approves.
2. **Deterministic verification** — *"We parse your code, analyze the AST, and verify
   criteria through deterministic checks. AI is only used as a fallback for complex
   cases."* Structural claims go to AST code-scan; behavioral criteria are exercised
   against a running build ("runtime previews"); recurring team rules are matched as
   reusable **invariants**.
3. **Three layers of criteria** — org invariants (no hardcoded secrets, auth on every
   endpoint), domain contracts (per-area), and change-specific acceptance criteria.
4. **Evidence + audit trail** — *"every change produces an immutable, timestamped record
   linking spec approval, implementation, and verification results"*; screenshots,
   matched invariants and code-scan results attach to the criterion they verify.

**Their framing:** *"Instead of asking 'Does this code look good?', Verify checks whether
it does what you intended it to."*

### 1.1 Where we agree — convergence, stated honestly

Their published diagnosis of AI-reviewing-AI is close to identical to ours, reached
independently:

| Their failure mode | Our equivalent |
|---|---|
| **Non-determinism** — *"the same code can produce different reviews in multiple runs, which is not a quality gate"* | Mechanical verdicts over LLM judgment; oracles are regex/exit-code, not opinion |
| **Missing intent** — the LLM reads a diff in isolation | Pre-registered criteria; the check is written before the work |
| **Duplicate blind spots** — *"When the same model writes the code and reviews the code, it misses the same things both times. You have not added a check. You have added a mirror."* | The correlated-priors argument from `docs/evaluations/two-agent-recursive-loops-2026-08.md`, near-verbatim |
| *"every test can pass, even though the code is doing the wrong thing"* | Vacuous-suite / hollow-test plants (`shadowed-import-vacuous-suite`, `vacuous-mutation-scope`) |

Structural mapping: their **invariant catalog** ≈ our **guards**; their **acceptance
criteria** ≈ our **oracles**, scoped per-change; their **spec approval** ≈ our
**pre-registration + human `--approve`**.

**This convergence is good news and should be used as such:** a funded company selling
the adjacent layer proves the buyer, the budget, and the pain are real, and their content
engine is educating our market for free.

### 1.2 Where we differ — the three that matter

**(a) They verify changes; we measure whether verification works.** The load-bearing
difference. Aviator answers *"did this change meet its spec?"* Nothing in their stack
answers *"does your invariant catalog actually catch violations, and what fraction does
it miss?"* — and their own logic demands that question, because an invariant that
silently stopped firing is indistinguishable from an invariant with nothing to catch.
We run planted defects with paired clean controls and produce recall and false-positive
rates over time. Object level vs. instrument level. A customer can run both; the honest
pitch to an Aviator customer is *"we'll tell you how strong your Aviator gates are."*

**(b) Cooperative vs adversarial threat model.** Their premise is an agent that
*misunderstands intent*. Ours is an agent that *games the measurement* — weakens a test,
fakes a green, tampers with the checker, or ships a feature that satisfies every
criterion and is never actually turned on. Spec-first verification does not address a
test weakened after spec approval, and per-change criteria don't cover built-but-dark
features. Our test-weakening guards and the built → wired → activated → exercised
Tripwire exist exactly there.

**(c) "Immutable" inside their system vs verifiable outside anyone's.** Their audit trail
is immutable and timestamped *if you trust their database*. Ours is cryptographically
signed, offline-replayable against a pinned key, on an open spec, checkable by a third
party years later with no vendor involvement. Theirs answers "can we show what
happened?"; ours answers "can a skeptic prove it without trusting the issuer?"

Two further differences, lower weight: **scope** (they gate at PR time; we also run
lifecycle instruments — staleness clocks, calibration cadence, decay tracking), and
**model** (closed commercial product cross-sold to a merge-queue base vs our open-core
playbook + sealed exam + community-fed bank).

### 1.3 The uncomfortable read

1. **They are ahead on product and GTM, not architecture.** Funded, shipping, an
   existing customer base to cross-sell, and a content engine actively **claiming the
   vocabulary** — "verification," "evidence," "audit trail," "deterministic." Several
   are load-bearing words in our own pitch. Architecturally right and second to market
   is a real failure mode.
2. **Calibration is their natural next feature.** Adding planted-defect measurement on
   top of an invariant catalog is a short step once someone names it. What stays hard
   for them is what stays hard for everyone: the sealed bank, the community-contributed
   failure shapes, and the accumulated dated history.
3. **We must not fight them on the word "verification."** They will win a vocabulary
   war they started earlier with more content. Our terms are **measured gate strength**
   (recall / false-positive numbers on planted defects) and **third-party-verifiable
   proof** (signed, offline, open spec) — neither of which they can adopt without
   building the bank and starting the clock.

### 1.4 Consequences (folded into the live docs)

- **Positioning:** pitch differentiators restated in un-co-optable terms — measured gate
  strength and third-party verifiability — rather than "verification" generally.
  (`pitch-2026-08.md`, `pitch-2026-08-investor.md`.)
- **Kill criterion generalized:** the plan's #3 was GitHub-shaped ("platform ships
  attestation with calibration"). Broadened to **any verification vendor adding
  gate-strength measurement** — Aviator is currently the most likely, and the response
  is unchanged: accumulate the bank and the history now, because those are the parts
  that can't be fast-followed. (`docs/plans/rsi-hardening-2026-08.md` §11.)
- **Sales motion:** verification-tool customers are a qualified lead list for Gate
  Certification, not a market we're locked out of. Complements today; watch (2) for the
  turn.
- **Standing watch item:** re-read their live pages at each quarterly review; log
  material changes here. A competitor shipping recall/FP numbers is the signal, not
  more verification copy.

---

## Watchlist (no entry yet)

- **GitHub / Microsoft** — artifact attestation exists (SLSA); proves a check *ran*, not
  that it works. Kill criterion #3's original subject.
- **Frontier labs' own harnesses** — conceded market (agent improvement); their gains
  increase demand for independent measurement.
- **Eval / benchmark vendors** — public benchmarks are burned assets; LLM-judge scoring
  inherits judge bias. Different category, but watch for private-bank offerings.
