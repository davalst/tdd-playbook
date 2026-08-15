# Plan — The hidden answer key: the one control that stays true as models improve

**Date:** 2026-08-15 · **Revision:** v1, pre-adversary
**Branch:** `claude/detection-deterministic-filter-ng073s`
**Status:** GATED — draft for David's review. Nothing here is built.
**Provenance:** three conversations. R6 of the detection-cascade plan (a cascade buys cost, not
recall) → a research pass that found two gaps in the calibration anchor → David's question of
whether a VPS-deployable, subscription-funded version of this is a business.

---

## The call, up front

**Build the private holdout store. Do not build the service.**

Of everything discussed across three conversations, exactly one control keeps working as the models
get better: **a test the model cannot read.** Every other control — the screen, the judge, the
guards, the plant corpus — is built out of somebody's understanding of how things go wrong, and
therefore covers only what somebody understood. A hidden answer key does not have that property. It
works regardless of how clever the thing being tested is, because cleverness cannot tune to what it
cannot see.

You designed it. `calibration/plant_forms.py` is built, the register is built, the leakage tripwire
is built, and `history_format.py:32` already parses a `form (dev|holdout|all)` clause. It carries
**zero entries** and self-reports as *"unarmed, not green"*. The one control that does not decay is
the one that was never turned on.

**And it just became urgent rather than nice-to-have.** Verified this session via the GitHub API:
`davalst/tdd-playbook` is `"private": false`, public since 2026-06-25. The fixture, all 26 shipped
scenarios, all 23 approved corpus plants and every oracle regex are on the public internet and will
be in the next training corpus. **The dev corpus is not merely at risk of being memorised; its
memorisation is now only a question of when.** After that point the dev scoreboard measures
recognition, not detection, and it will keep reporting PASS while it does so.

So: **D0–D3 now** (the invariant, the de-legibilisation, the private store, the CI path — call it
two weeks). **D4–D5 next** (one hardening pilot, one independence measurement). **D6–D7 only if
David wants the business question answered** — and that answer costs a week, not a company.

---

## The one invariant, and why it is deliverable #0

The last attempt at this — CIVerd on a VPS — sank under bureaucracy. It is worth being precise
about the cause, because "we'll keep it simpler this time" is not a mechanism.

**CIVerd did not collapse under bad engineering. It collapsed under its own authority.** It was a
verdict system: something that says pass/fail with standing. Authority is what *generates* the
signing, the ledgers, the integrity checks, the forgery resistance, the appeals. None of that was
optional decoration; all of it was the necessary consequence of being an authority. `v1.32.0`
resolved it by deletion rather than by a smaller wall, and `.github/workflows/gate.yml:13-16`
already states the resulting principle in the repo's own words: *"No verdict, no signature, no
ledger, no issuer key, no VPS, no tailnet, no polling, no artifact the release path consumes. There
is nothing here to forge, because nothing here authorizes anything."*

**THE INVARIANT: nothing built by this plan may authorize anything.** The holdout tells you a
number. A human reads the number. That is the whole contract. The moment it emits a badge, a
certificate, a "compliant" flag, or an artifact the release path consumes, it has become an
authority and it will regrow every piece of machinery that killed the last one.

Prose does not hold that line — this repo knows it and has the pattern for it already:
`test_installer.py:670` `test_no_script_creates_a_release_tag` scans every tracked `.py`/`.sh`/
`.yml` and REDs the gate if any creates a tag. **D0 is that pattern, pointed at authorization.**

---

## Spec integrity (§0, before the deliverables)

### Assumptions

**A1 — "The three opportunities" means: a hidden answer key, prevention over detection, and
checkers whose blind spots differ.** That is my summary of the last conversation, not David's
words. If he meant something else, D4 and D5 change; D0–D3 stand either way.

**A2 — The deliverable is a mechanism in this repo first, portable second, product never (in this
plan).** D6 makes it installable by someone else. It does not make it a service, and there is no
hosting, billing, tenancy, or account in scope.

**A3 — No VPS.** The only hard requirement is that the answer key live somewhere the coding agent
cannot read. A private GitHub repo plus a scheduled workflow with a read-only deploy key delivers
exactly that property with zero servers, zero uptime obligation, and zero ops. CIVerd needed a
neutral machine because it was an authority that had to run somewhere nobody could tamper with. A
plant library is not an authority (see the invariant), so it does not.

**A4 — The holdout is private from the PUBLIC CORPUS, not from the model provider.** This bound is
load-bearing and it is the first thing an adversary would point at, so it is stated here rather
than discovered in year two. During a calibration run the doer *reads the plant* — that is the
point. So the model provider's systems see every holdout body at run time. `child_env.py` already
keeps them out of our own capture store, but nothing keeps them out of a provider's. **A holdout is
therefore a depleting asset, not a permanent one**: it is protected from the public-internet
training path (the fast, certain leak) and not from the provider path (slow, uncertain, invisible).
Consequences that must be designed in, not bolted on: holdout plants rotate, the register records
first-use date, and the corpus must keep growing regardless. Anyone who treats a holdout as
permanently clean will over-trust it exactly when it has quietly stopped working.

### The materially simpler approach, stated so review can take it

**Skip the private repo. Keep the holdout bodies in a local, never-committed directory on David's
machine**, referenced by hash from the register (the `PRIVATE` sentinel at `plant_forms.py:161`
already supports this). Zero infrastructure, zero secrets, zero CI changes — and it delivers the
core property today, because the coding agent's working tree is the repo, not `~/`.

**What it costs:** the holdout only runs where David is sitting, so it cannot run on a schedule,
cannot survive a laptop failure, and cannot ever be used by anyone else. **My recommendation: do
this first anyway, as the week-one version, and let D2's private repo be the durability upgrade
once there is something worth making durable.** It is strictly the fastest path to the one control
that matters, and it de-risks every later decision.

### Questions for David

1. **Q1 — Is the public repo a deliberate positioning choice?** It is currently the single largest
   threat to the calibration signal. Nothing here proposes making it private (the playbook's value
   as public doctrine is real), but the trade should be conscious: **public repo means the dev
   corpus is a marketing asset and the holdout is the only measurement.**
2. **Q2 — Deploy-key custody.** A read-only deploy key in a repo secret is fine; who holds the
   recovery path if it is lost, and is a rotation date wanted? (I will register a dated debt if
   there is no answer.)
3. **Q3 — Does the business question need answering now?** D6–D7 are a week and are severable. If
   the answer is "not yet", the plan ends at D5 and loses nothing structural.

---

## What is verified (all this session, all by command)

| fact | how |
|---|---|
| Repo is **public**, created 2026-06-25 | GitHub API: `"private": false`, `"visibility": "public"` |
| **0 stars, 0 forks** after ~7 weeks public | same call: `stargazers_count: 0`, `forks_count: 0` |
| Holdout register exists and is **empty** | `plant_forms.py check` → *"0 entr(ies); NO holdout classes assigned yet … Reported as unarmed, not green"* |
| Private-body mechanism already built | `plant_forms.py:41,161` (`PRIVATE` sentinel + hash rules) |
| Leakage tripwire already built | `plant_forms.py:201`, scanning 4 roots |
| Scoreboard already parses a `form` clause | `history_format.py:32`, default `dev` at `:40` |
| Corpus size | 23 approved, 1 proposed |
| The no-authority principle is already written | `.github/workflows/gate.yml:13-16` |
| The enforcement pattern exists | `test_installer.py:670` |
| CI is a single job, `contents: read`, runs on `push` **and** `pull_request` | `.github/workflows/gate.yml` |
| Four eval-awareness tells | `run_calibration.py:176,183-184,186`; `fixture/tools.py:3-7` |

**The 0-stars figure is not a jab, it is a planning input.** It is the strongest available evidence
on Q3: whatever this becomes, distribution is the binding constraint, not capability. A benchmark
published to an audience of zero measures nothing.

---

## Deliverables

### D0 — The no-authority pin (~25 lines) · SHIPS FIRST

**Plain English:** a test that fails the build if anything from this plan ever becomes something
that authorizes a release.

**Spec.** Following `test_no_script_creates_a_release_tag`'s shape: assert that no holdout or
benchmark component appears in `gate-manifest.json`'s `fixed_stages`, that none is invoked by
`scripts/civerd_gate.sh`, and that none writes into the paths the release path reads
(`docs/reviews/`, `capabilities.json`, anything `gate_plan.py` digests). The docstring carries the
CIVerd lesson so the next reader knows why the constraint exists and does not "tidy it up".

**Red-first, calibrate-the-checker.** Per §13 the scanner is proven in both directions before it is
trusted: add a fake holdout stage to a temp copy of the manifest → RED; remove it → GREEN. A
scanner that cannot fire proves nothing.

**Why first.** A constraint written after the machinery is a preference. Written before, it is a
wall. This is thirty minutes of work that determines whether the next two years look like CIVerd.

**Note on scope, honestly:** this stops *committed automation* from wiring the holdout into
authorization. It cannot stop a human deciding one day that the holdout number is a release gate.
No repo-side check can. It makes the decision loud, not impossible.

### D1 — De-legibilize the fixture (~6 production lines) · BLOCKS D2

**Plain English:** stop the practice exam from announcing that it is a practice exam.

**Spec.** Remove the four tells verified above: neutral temp prefix (`run_calibration.py:176`),
neutral git identity (`:183-184`), a commit message that does not mention plants (`:186`), and the
plant-explaining prose moved out of `fixture/tools.py` into the scenario metadata where the oracle
already lives and the doer never looks.

**Why it blocks D2, and this is the sequencing argument that matters:** a holdout plant run inside
a fixture whose commit message says *"fixture (plant applied)"* is burned on first contact. The
agent does not need to recognise the plant — the wrapper tells it a plant exists. **Assigning
holdouts before D1 spends the one non-decaying asset on a compromised harness.**

**Red-first.** A `fixture_legibility` sweep assembles a scenario exactly as `run_calibration` does
and greps the result — file contents, docstrings, `git log`, `git config`, cwd — against a roster of
harness tells. **Run against today's tree it must go RED on all four, and red for those four
reasons.** Today's tree is the motivating artifact required by the v1.25 guard-calibration rule,
and it is available right now; the pre-fix state is then frozen as a planted fixture citing this
commit. Vacuity guard mandatory: a sweep that scanned nothing must fail, not pass
(`dataflow_sweeps.EXIT_VACUOUS` precedent).

**Blast radius, verified:** `grep -rn "tdd-cal\|scn-val"` returns only the two definitions.
Nothing asserts the prefix; there are no fixture victims.

**Journaling requirement.** Post-fix scores may drop, and if they do, *that is the finding*. Pre-fix
history rows stop being comparable to post-fix rows. The discontinuity is recorded in
`docs/calibration/history.md` when the change lands — not explained afterwards.

**Honest bound.** This removes the tells that require no inference. It does not make a calibration
run indistinguishable from real work: a checker handed a brief and a seven-file synthetic repo in
which a defect is nearly certain can infer the situation from base rates alone. D1 raises the floor
from zero. It is not a wall, and it should never be described as one.

### D2 — The private holdout store

**Plain English:** the bodies of some plants live where the coding agent cannot read them; only
their names and fingerprints stay here.

**Two-stage, per the simpler-approach argument above.**

**D2a — Local private directory (week one).** Bodies in a directory outside the repo, referenced
from the register by `content_sha256`, `form: holdout`. A `holdout_source.py` resolves the
directory from an env var, validates each body through the existing
`run_calibration.validate_scenario` (one owner, not a second validator), and refuses loudly if the
source is absent — **absent must never read as "no holdout failures"**, which is the
UNMEASURED-never-zero rule applied to the one instrument we cannot afford to have lie.

**D2b — Private sibling repo (the durability upgrade).** `davalst/tdd-playbook-holdout`, private,
same schema. Fetched to a **temp directory, never into the working tree** — a clone inside the repo
is one `git add -A` away from publishing the answer key permanently. The existing leakage tripwire
(`plant_forms.py:201`) covers ids; D2b adds body-path containment as a second, distinct check.

**Edge cases.** A holdout id appearing in any scanned surface → burned, and the existing tripwire
already fails that way. A holdout body accidentally inside the repo tree → new blocking check. A
register entry whose hash no longer matches its body → blocking (drift means someone edited the
answer key). First-use date recorded per A4's depletion argument. A run with zero holdout entries
reports *unarmed*, exactly as the tool does today — that behaviour is already right and must not
regress once entries exist.

**Integration surface.** *Consumes:* `plant_forms` (register), `run_calibration.validate_scenario`,
`history_format` (the `form` clause). No new schema, no new validator, no new telemetry. *Emits →
named consumer:* `form: holdout` run blocks in `history.md`, read by `ledger.py:237` — which
already refuses to compare a dev number against a holdout number as a cross-population delta, so
the consumer for this data exists and is already correct. *Parity:* local + CI. *Reverse sweep:*
`plant_vitality` must classify holdout streaks separately — verified already true at
`plant_vitality.py:47`. Nothing else in the tree needs to change, which is the sign this is
activation rather than construction.

### D3 — The CI path, and its security posture

**Plain English:** run the hidden tests on a schedule, on a machine that has the key, without ever
publishing the answers.

**This is the deliverable with real failure modes, so it gets the security section.**

**A separate workflow, never a job in `gate.yml`.** `gate.yml` runs `on: pull_request`. A secret
reachable from a PR-triggered workflow is a classic exfiltration surface: a PR that modifies a
workflow or a script it calls can print the secret, or the plant bodies it unlocks. The holdout
workflow triggers on `schedule` and `workflow_dispatch` only, on `main` only, never on
`pull_request`.

**Least privilege.** `permissions: contents: read` on this repo, as `gate.yml` already does. Access
to the private repo via a **read-only deploy key** scoped to that repo alone — not a PAT, which
would carry the whole account.

**The constraint most likely to be missed: on a public repo, workflow logs are world-readable.**
The holdout job's stdout *is* a publication surface. A run that prints a scenario's diff publishes
the answer key to the internet permanently and irreversibly. So the runner needs a mechanical
redaction contract, not a convention: **the holdout path emits ids, verdicts, and counts only**,
and a test asserts that the emitted rows contain no substring from any body. That test is the
single highest-value assertion in this deliverable, and it goes red-first against a deliberately
leaky printer.

**Failure handling.** A surviving holdout plant exits non-zero, as `run_calibration` already does
— and per D0 that failure gates **nothing**. It is a signal to fix an agent, not an authorization
input. Stated explicitly because "the holdout is failing, therefore block the release" is the exact
step that recreates CIVerd, and it will feel reasonable at the time.

### D4 — Harden a blocker instead of adding a watcher (metamorphic pilot)

**Plain English:** check that a guard's answer doesn't change when you change something that
shouldn't matter.

Pilot on `test_weakening_guard` — the highest-stakes blocking guard — with five relations:
reformat whitespace, rename a local consistently, reorder independent hunks, move a file within its
role, duplicate an offending construct (must still block). A violation means the guard keys on
surface form rather than on what it claims to detect, which is a failure class nobody enumerates.

**Why this rather than more detection:** a blocking guard does not care whether the model knows it
is being watched. Prevention is unaffected by eval-awareness; detection is not.

**Honest note:** the relations are hand-authored, so this does not escape the enumeration problem —
it moves it from "list the bugs" to "list the invariances", which is a smaller and far more stable
list. That is the entire claim and it should not be sold past it. **If the pilot finds nothing
across all five relations, the doctrine change is unproven and §3 stays as it is.**

### D5 — Measure checker independence (a measurement, not machinery)

Run one calibration cycle with a verifier from a **different model family** and compare per-scenario
outcomes against the current family. The number that matters is *correlation of misses*: three
checkers with the same blind spot are one checker. The scoreboard already records the model per row
(`history.md` rows carry `model` in the run header), so this is a run and a comparison, not a build.

Result is a trend line, never a gate. If miss-correlation is high, "add another verifier" is a bad
investment and we will have learned that for the price of one cycle.

### D6 — Portable install (only if Q3 says yes)

**Plain English:** someone else can set this up without a server.

`holdout init` scaffolds: a private-repo skeleton with the schema, a workflow template with the
security posture from D3 baked in (schedule/dispatch only, read-only deploy key, redaction test
wired), and a README naming the depletion property from A4 so nobody treats their holdout as
permanent. **The answer to "how do I deploy this on a VPS" is a documented "you don't need one",
with the private-repo path given instead.**

### D7 — The benchmark (the cheapest possible business test)

**Plain English:** run the public plants against several current models, publish the table, see if
anyone cares.

**Dev corpus only. Holdout bodies are never published, and holdout results are published only as
aggregate recall** — ids are already public by design (`plant_forms.py:50-52` explains why), bodies
are not.

**Why a benchmark rather than a subscription.** A subscription sells an unauditable number from a
vendor whose revenue improves when the number looks bad — the exact epistemic posture this
playbook's cite-or-refuse discipline exists to reject. A published benchmark with open methodology
inverts it: you become the referee rather than the vendor, the auditability problem dissolves
instead of being managed, and being right matters more than being trusted. It also needs no
billing, no tenancy, no hosting, and no anti-spoofing.

**Kill criteria, pre-committed, before anyone has a stake in the answer.** Publish, then pair it
with **3–5 direct conversations** (the 0-star figure means silence is ambiguous — it could mean the
work is uninteresting or that nobody saw it, and publication alone cannot tell those apart). Then:

- someone cites, disputes, or asks you to run their setup → there is a wedge; scope v2 from what
  they actually asked for, not from this plan;
- interest but no willingness to act → it is a reputation asset, not a product; keep publishing
  quarterly and stop building;
- silence in both the publication and the conversations → **stop.** No subscription, no service, no
  further infrastructure.

**What is explicitly NOT in scope, named so it cannot creep in:** billing, accounts, multi-tenancy,
hosting, a VPS, per-model plant tuning, model-identity anti-spoofing, dashboards, certificates, and
any artifact a customer could present to a third party as evidence. Every one of those is an
authority or a step toward one (see the invariant). Per-model tuning and anti-spoofing in
particular are v3 problems being solved before v1 has a user — which is the CIVerd failure mode in
a new costume.

---

## Flow table (§6c)

| flow | producer | consumer | liveness test |
|---|---|---|---|
| holdout register entries | `plant_forms` (exists) | `holdout_source` resolution | fixture: entry with no body → refuse, never "clean" |
| holdout bodies | private dir / private repo | `run_calibration` scenario loader | hash-drift fixture (edited answer key → blocking) |
| holdout run rows | `run_calibration --form holdout` | `history.md`; `ledger.py:237` cross-population guard | round-trip: a holdout block parses and is NOT compared against dev |
| redacted CI output | holdout workflow | GitHub Actions log (public) | **leak test: emitted rows contain no substring of any body** |
| legibility verdict | `fixture_legibility` sweep | gate stage exit code | replay vs today's tree → RED on all four tells |
| authority isolation | D0 scanner | gate exit code | planted manifest entry → RED |
| miss-correlation | D5 comparison | a journaled trend line | n/a — a measurement, not a mechanism |

Every row has a consumer. The rows that already have one — register, run blocks, cross-population
guard — are why this is mostly activation.

## Deploy surface (§0)

- **Runs where:** David's machine (D2a); GitHub Actions on `main` (D2b/D3); downstream repos if D6
  ships. **No VPS anywhere.**
- **Gets there how:** `bin/` auto-vendors by directory walk (`COPY_TREES`), so no per-file roster.
  Holdout bodies never vendor — they reach CI by deploy key only.
- **Verified how:** a holdout run block appears in `history.md` with `form holdout`. Absent block =
  the instrument did not run, and the tool already reports *unarmed, not green*.
- **Divergence:** a downstream repo without a holdout source reports unarmed. Who notices: whoever
  reads the run output — which is the honest answer, since per the invariant nothing here alerts.

## Sequencing

D0 (30 min, and it constrains everything after) → **D1 (blocks D2 — do not assign holdouts into a
self-announcing fixture)** → D2a (week one, local) → D3 (the CI path + the leak test) → D2b
(durability) → D4 pilot → D5 measurement → **stop and decide Q3** → D6/D7 only on a yes.

## Risks

**R1 — The public corpus is already compromised and we cannot know how much.** Verified public
since 2026-06-25. Any future model may have read all 23 plants. Mitigation: the holdout *is* the
mitigation. Residue: the dev scoreboard's 300 rows may already be measuring recognition rather than
detection, and there is no way to tell from inside. **Treat pre-holdout dev trends as historical
context, not as evidence about current model capability.**

**R2 — A holdout leak is irreversible.** The corpus only grows and a burned plant cannot be
un-burned. Three independent guards: the existing id tripwire, the new body-containment check, and
the CI redaction test. All three are cheap. None is optional.

**R3 — The holdout depletes invisibly** (A4). It is private from the public corpus, not from the
model provider. Mitigation: rotation, first-use dates, a corpus that keeps growing. **There is no
mechanism that detects this depletion**, which is the honest statement — a holdout that has silently
leaked through a provider looks exactly like a holdout that is working.

**R4 — The instinct to make the holdout number authoritative.** It will feel reasonable, probably
within a month, and it is how CIVerd comes back. D0 makes it loud; nothing can make it impossible.

**R5 — D7 measures distribution, not value.** With 0 stars, silence is ambiguous. Mitigated by
pairing publication with direct conversations, which is why the kill criterion requires both.

**R6 — N=1.** One repo, one fixture, one operator. A benchmark from that base is weak evidence and
should be published with the denominator stated plainly, per §12. Anyone quoting it as an industry
figure is misusing it, and the methodology section should say so in its own words.

---

## Claims

Repo and infrastructure claims: each carries a `file:line`, a quoted command output, or a named API
field, all produced this session. No tally is offered — a count I did not compute is the C1 error
from the 2026-08-14 record.

Judgment claims, not measured, listed so they are not read as findings: that the hidden answer key
is the highest-value item; that D1 must precede D2; that a benchmark beats a subscription; that five
metamorphic relations are the right five; and A4's assessment that provider-side exposure is slower
than public-corpus exposure — **that last one is an assumption about training pipelines I cannot
verify and it is load-bearing for the whole holdout thesis.** If it is wrong, holdouts decay as fast
as dev plants and the plan's central claim weakens considerably.

## Loop closed: **NO**

No adversary was dispatched; this session is constrained from dispatching subagents, and that is
recorded as a visible decision rather than a default. The three I would want, refute-framed:

1. **`architecture-adversary`** — *"D2 claims to be activation rather than construction. Is that
   true, or is `holdout_source` a second scenario loader alongside `run_calibration`'s?"*
2. **`security-adversary`** — on D3 specifically, with §9's three questions: what reaches the
   private key without the workflow's guard; does every error path fail closed (a fetch failure
   must report UNMEASURED, never "no failures"); and does the redaction test resolve "body content"
   exactly as the printer does?
3. **`adoption-adversary`** — *"D7's kill criteria depend on David running 3–5 conversations. Nothing
   in this plan makes that happen. Is the business test stranded?"*

Findings from any of those must be verified against the tree before acceptance (§12): a subagent
report is an unverified claim.
