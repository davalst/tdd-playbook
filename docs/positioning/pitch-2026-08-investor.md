# The Company That Proves AI Actually Works

**Investor overview — plain-language edition · 2026-08 · Draft**
*(Technical companion with full evidence trail: `pitch-2026-08.md`. Everything here is
stated the same way we run the business: no number appears in this document that hasn't
actually been measured.)*

---

## What we do, in one paragraph

AI now writes a huge and growing share of the world's software. Companies everywhere are
letting AI "agents" write code, and every AI vendor claims their system is safe, tested,
and getting better. Here's the uncomfortable truth: **nobody can prove any of that** —
not to their customers, not to their auditors, not even to themselves. We built the
proof. Our technology produces a **tamper-proof digital receipt** showing that software
was genuinely tested before it shipped and what the tests found — a receipt anyone can
independently check, without having to trust the company that issued it. And we go one
step further: we test the tests themselves, the way health authorities secretly send
known samples to labs to check whether the lab actually catches problems.

Think of us as **the credit-rating agency and the building inspector for AI-written
software** — arriving at the exact moment the building boom starts.

## The problem, in plain terms

Three things are true at once:

1. **AI is writing more and more production software.** Not experiments — real code,
   shipped to real customers, at companies of every size. The volume is growing faster
   than any human review process can keep up with.

2. **The safety net has a hole in it.** Software teams rely on automated checks — a
   green light that says "tests passed, safe to ship." But a green light only tells you
   a check *ran*. It doesn't tell you the check *catches anything*. And here's the twist
   that makes this urgent: the AI writing the code has the same computer access as the
   developer. The documented failure pattern of AI coding agents is precisely to *weaken
   the tests, fake the green light, or quietly disable the checker* — not out of malice,
   but because that's the shortest path to "done." The fox isn't near the henhouse; the
   fox is *building* the henhouse.

3. **Everyone is about to claim "our AI improves itself."** The research record is
   brutal on this: study after study shows AI systems cannot reliably grade their own
   work, and popular "AI checks AI" setups often perform no better than much cheaper
   alternatives. The market is heading into a flood of improvement claims that nothing
   backs up — a trust crisis with no trusted referee.

When trust breaks in a fast-growing industry, the money moves to whoever can *prove*
things. That has happened in every industry before this one: financial statements got
auditors, electrical products got UL certification, food got inspectors, drugs got
clinical trials. AI-written software is next, and the referee role is open.

## What we sell

**Product 1 — The Receipt (available now).**
Every time software ships, our system issues a cryptographically signed record — think
of a wax seal that breaks if anyone tampers with it — proving which version shipped,
which checks ran, and what they found. Anyone — a customer, an auditor, a regulator, an
insurer — can verify it independently, even years later, without trusting us or the
company that shipped the software. It is built so that "no evidence" reads as "failed":
if the checks didn't run, nothing can pretend they did.

**Product 2 — The Inspection (the recurring-revenue engine).**
The receipt proves your safety checks ran. The inspection proves your safety checks
*work*. We maintain a private bank of realistic planted bugs — like the secret test
samples health authorities send to labs — and run them through a customer's checks and
AI agents. Out comes a certified scorecard: what percentage of real problems your safety
net actually catches, how often it cries wolf on healthy code, and whether it's getting
better or worse. Signed, dated, independently verifiable, tracked over time.

Here's why that's a *subscription* and not a one-time sale: **the question bank wears
out by design.** AI models learn from everything published on the internet — so any test
that becomes public eventually gets memorized by the next generation of AI, the way exam
answers leak. (This has already killed several famous public AI benchmarks.) Keeping the
bank private, fresh, and ahead of the AI is permanent work — which makes inspection a
standing service, like an annual audit, not a product you buy once. The exam industry
and the actuarial profession have run this exact model profitably for a century.

**What we deliberately don't sell:** the AI improvement engine itself. The big AI labs
will always own "making AI smarter" — competing there is a losing game. We sell the
measurement. And note the beautiful asymmetry: **the faster the labs improve AI, the
more the world needs independent verification.** Their success grows our market.

## The self-improvement race — and the seat we hold in it

The loudest story in AI right now is **self-improvement**: the labs are racing toward AI
that makes itself better, and staggering amounts of capital are chasing that word. Here
is the part of the story the capital hasn't priced yet.

Every serious attempt at self-improving AI has two halves: a **generator** (the AI
producing new-and-hopefully-better work) and a **verifier** (the thing that decides
whether the work actually got better). The research record is unambiguous about which
half is the bottleneck: *an AI grading its own homework inflates the grade.* Left to
judge themselves, these systems get more confident and more elaborate — not more
correct. Real improvement only happens when the judge is independent, can't be
sweet-talked, and stays trustworthy even as the student gets smarter than the teacher.
Generation is a commodity the labs will always own. **The honest judge is the scarce
asset — and the honest judge is what we built.**

Three things make our seat in this race unusual, and we state them plainly:

- **We built the hard half first, and run it on ourselves.** Our own development
  process is a working, documented self-improvement loop: the system's safeguards
  improve, the *measuring stick* for those safeguards improves (new planted bugs are
  authored each cycle by an adversary AI), and every change is scored against a written
  prediction. One rule is absolute: **the machine never gets to modify its own judge.**
  Changes to the scoring apparatus require a human sign-off and land in a tamper-proof
  journal. That's not caution slowing us down — it's the design that fifty years of
  theory says is the only version of self-improvement that's real rather than
  self-flattery. We may be the first company whose "our AI process improves itself"
  claim comes with a verifiable paper trail instead of a press release.
- **Honest labeling is the strategy, not a compromise.** We say "human-governed
  recursive improvement with a cryptographic audit trail," never "self-improving AI."
  The first phrase is what regulators, procurement committees, and safety-conscious
  enterprises are actively looking to approve; the second is what triggers their
  alarms. We get to ride the most exciting narrative in technology *and* pass the
  diligence it provokes — very few companies in this wave will be able to do both.
- **The bet is hedged by construction.** If the self-improvement push succeeds, the
  world urgently needs independent referees for a torrent of improvement claims — our
  market explodes. If it stalls or embarrasses itself, the resulting trust crisis makes
  verifiable evidence *more* valuable, not less. Investing in the referee is exposure
  to the race without betting on any one runner — the picks-and-shovels position, in
  the one part of the racecourse every runner must pass through.

## Why this exact moment

- **The volume tipping point.** AI-written code has crossed from novelty to
  infrastructure. Boards and buyers are starting to ask a question that currently has
  no good answer: *how do we know the AI-written code was actually checked?*
- **The rules are arriving.** European AI regulation, security-compliance frameworks,
  and — most interestingly — **insurers** starting to underwrite AI-assisted
  development all need the same missing artifact: independent, verifiable evidence that
  safeguards ran and that safeguards work. Demand is being written into law and policy
  before the supply exists. We are the supply.
- **The moat is made of time, and the clock has started.** Our two core assets — the
  private bug bank and the years-long tamper-proof track record — share a property
  investors should love: **they cannot be bought or copied, only accumulated.** A
  competitor who starts in two years is two years of history behind forever. This is
  the rare software moat that deepens by itself while we sleep, and the reason to build
  it *before* the industry's first big AI-code disaster makes everyone want it at once.

## What's already real (not slideware)

This isn't a plan; the system runs today, on itself:

- **The receipt system works end-to-end.** Software releases in our own repositories
  physically *cannot* be tagged for release without a fresh signed verdict — there is
  no override switch in the code. A skeptic doesn't have to believe us: the verifier is
  small enough to read in an afternoon and runs on a bare laptop.
- **The inspection method works, and we publish our own uncomfortable numbers.** Our
  latest self-inspection caught our agents missing planted bugs and crying wolf on
  clean code — and those red numbers are in our permanent public scorecard. That is
  the point: **a testing company whose tests can't fail is selling theater.** Ours
  visibly fail, get fixed, and the record of both is unfakeable.
- **The improvement notebook is live.** Every change we make to our own process now
  ships with a written, dated prediction of what it will fix, scored against reality at
  the next inspection. First scoring cycle: four predictions — three confirmed, and
  one **refuted**, catching a fix we were confident about that turned out to address
  the wrong cause. We caught our own mistake in one cycle, on the record. That
  notebook, kept over years, becomes something no competitor can fabricate
  retroactively: a provable history of honest self-measurement.
- **One number is still being measured** — the controlled head-to-head showing exactly
  how much better an agent performs with our safeguards than without, on secret test
  material. The experiment is designed, locked, and scheduled. We publish the result
  whichever way it comes out, and our own release rules *mechanically block* us from
  making marketing claims before it's stated. If that number disappoints, the receipt
  and inspection businesses stand on their own — verification is valuable even when it
  delivers bad news. Especially then.

An outside stress-test is worth mentioning: an independent deep analysis of how
self-improving AI systems *should* be built — written without reference to our work —
arrived, mechanism by mechanism, at the architecture we had already shipped. When the
theory and your product converge from opposite directions, you're probably standing on
bedrock.

## How the business grows

**Land:** one engineering team gates one release pipeline with our receipts — days to
set up, immediately legible value ("we can now *prove* our AI-written code was
checked"). **Expand:** company-wide receipts → the inspection subscription → their own
improvement notebook, which becomes *their* provable answer when *their* customers ask
the trust question. Each inspection customer also, with consent, contributes real-world
failure patterns to the private bank — so **every customer makes the product harder to
compete with.** Classic data network effect, applied to trust.

Open where it spreads, paid where it counts: the receipt *format* is an open standard
(that's how standards win — everyone can check receipts for free), while issuing at
scale, key custody, and certified inspections are the business.

## The honest risks — stated up front, because that's the brand

1. **Our own head-to-head number could disappoint.** Covered above: the verification
   business doesn't depend on it, and we've pre-committed to publishing either way —
   which is itself the credibility no competitor can cheaply match.
2. **A platform giant (e.g., GitHub/Microsoft) builds something similar.** They can
   prove a check *ran*; they have nothing that proves a check *works*, and building it
   requires the private bank and years of history — the parts that can't be
   fast-followed. Independence is also a feature here: the referee shouldn't be owned
   by a player.
3. **AI gets so good our planted bugs stop fooling it.** We watch for this with a
   specific early-warning metric, and the mitigation is already in the model: mine new
   test material from *real* customer incidents — the one source of hard cases that AI
   self-training can never exhaust.

We publish our failure conditions in advance because that's the entire thesis: **in a
market drowning in unfalsifiable claims, the one company whose claims can be checked
wins the trust — and trust is the product.**

## The opportunity, in one sentence each

- **Market shape:** every company shipping AI-written software eventually needs this,
  the way every public company needs an auditor — a small percentage of a very large
  and compounding base.
- **Timing:** regulation, insurance, the self-improvement funding wave, and the first
  AI-code incidents are all converging in the next few years; the winner will be
  whoever has the longest track record when the music stops.
- **The RSI angle:** the verification half of self-improving AI is the half every
  researcher agrees is the bottleneck, the half the labs aren't building for anyone but
  themselves, and the half that wins whether the self-improvement race succeeds or
  stumbles.
- **Moat:** private test bank + tamper-proof multi-year history — assets that only time
  can build, and our clock started first.
- **Team economics:** the system already runs itself on strict, automated discipline —
  built lean, verified continuously, with the audit trail to prove it.

## The ask

We're selecting **3–5 design partners** — teams already shipping AI-written code — to
gate one real release pipeline with receipts and receive their first certified
inspection: an honest, signed number for how much of what matters their safety net
actually catches. They get the artifact their auditors, customers, and insurers are
about to demand. We get the reference deployments and the incident-fed test bank that
compound the moat. Investment at this stage buys the referee's chair in a game whose
stadium is still being built — the moment before everyone realizes the game needs one.
