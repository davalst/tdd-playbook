# Patterns Worth Stealing from `google/mantis` — repo best-practice review

**Date:** 2026-09-07 · **Prepared as:** senior-dev / repo review
**Input:** `google/mantis` README + repo layout (fetched 2026-09-07) compared against this repo's
plugin surface, skill, hooks, installer, gate, calibration harness and doc tree.
**Method:** §12 claims discipline — every finding carries a resolving citation, every negative is written as a checkable absence claim, and the whole
written as a checkable absence claim, and the whole document is re-verified by
`plugins/tdd-playbook/bin/verify_citations.py`.

---

## 1. The one-paragraph verdict

Mantis is a **staged pipeline of decoupled skills**; this repo is a **single always-on doctrine
with mechanical enforcement**. On rigor the comparison is not close in mantis's favour — it has
no planted-input calibration, no guard yield measurement, no append-only scoreboard, and its
central safety claim ("all findings must be manually verified") is doctrine with no mechanism
behind it. Import none of its verification content. But its *packaging* answers a question this
repo has never asked: **what does the agent have to read before it can start?** Mantis splits 15
stages across 18 skill directories so a stage loads only its own instructions; this repo loads
one 131 KB skill on essentially every build, fix and audit turn, and that cost appears nowhere in
the CHANGELOG, the plans, the recommendations or the registry. Second, mantis leads its README
with a threat model of *itself as installed software* — what it executes on your machine and why
you should isolate it — where this repo's threat model (`docs/HACK_CATALOG.md:1`) is scoped to
agents gaming tests, not to the four hooks it installs into strangers' repos. Those two are the
findings worth acting on. The rest of mantis's good ideas are already here, usually in a stricter
form, and section 3 says so rather than padding the list.

---

## 2. What mantis actually is (so we steal from the right layer)

A stack-agnostic security-review harness for coding agents: 18 `mantis-*` skill directories
implementing a 15-stage sequential pipeline (`/mantis-summarize` → `architecture` → `threat-model`
→ `plan` → `researcher` → `dedupe` → `review` → `critic` → `reproduce` → `chain` → `patch` →
`calibrate` → `reflect` → `report`, then a mandatory human stage 15). Stages exchange state
through a `workspace/` tree — `kb/` (synthesized knowledge base), `findings/`, `learnings.jsonl`
— plus a root `schema.json` data contract and a living `THREAT_MODEL.md`. Findings are stamped
with an immutable snapshot; the snapshot model is opt-in and default off. Execution of
agent-written code is confined to `--network none` containers, gVisor recommended.

Where it is weak, in this repo's terms: the pipeline trusts each stage's self-report, its
"calibrate" stage rates risk rather than proving the detector works, and it ships no planted
defect anywhere — a mantis stage that silently stopped finding anything would read as a clean
run. That is the exact failure class this repo built `calibration/` to close.

---

## 3. Mantis patterns we already have, in a stricter form — do not re-import

Stated explicitly because four of them looked like findings until they were checked, and an
unchecked negative is how a review ships false (§12).

| Mantis pattern | Already here, stricter |
|---|---|
| "You do not need the heaviest model for every stage" | Agents are consciously classified pinned-vs-inherit against the **real** directory listing, vacuity-guarded, with a planted unclassified member proving the detector fires — `plugins/tdd-playbook/tests/test_agents.py:605`. Mantis states the principle; this repo tests it. |
| Findings pinned to an immutable snapshot | Review records carry `review_range.base`/`head` commit shas, and `plugins/tdd-playbook/bin/with_snapshot.py:1` makes tree restoration a checked invariant rather than a promise. |
| `learnings.jsonl` for empirical adaptation | The yield log + escape ledger + `docs/calibration/history.md`, all append-only and integrity-checked by `calibration/check_scoreboard_integrity.py:266`. |
| Human-gating self-modification against prompt injection | The whole release-authority design: `hooks/scripts/tag_guard.py` blocking at the Bash seam plus a tracked-script scanner, with the residual ("a repo-side check cannot bind a human at a terminal") stated rather than assumed. |
| Sandboxing agent-written code | Out of scope — this repo does not execute untrusted findings. Importing container doctrine here would be cargo cult. |

One thing worth naming as a strength mantis lacks entirely: `plugins/tdd-playbook/hooks/scripts/capture.py:80` makes
the transcript store opt-in by an enrollment marker, so a stranger's marketplace install ships
with the recorder **off**. That is the right default and it is already implemented.

---

## 4. Findings

### F1 — The skill is a 131 KB monolith with no progressive disclosure, and the cost has never been costed · **high**

`plugins/tdd-playbook/skills/tdd-playbook/SKILL.md` is 131,277 characters (~33k tokens, ~20,700
words) in a single file with 22 `##` sections, spanning §0 planning through §13 the learning loop
(`plugins/tdd-playbook/skills/tdd-playbook/SKILL.md:53` through
`plugins/tdd-playbook/skills/tdd-playbook/SKILL.md:1344`). Its frontmatter description makes it
fire on building, fixing, testing, planning, auditing, reviewing, diagnosing and self-improvement
work — which is close to every turn. There is no bundled-reference directory to load sections on
demand `(absent: plugins/tdd-playbook/skills/tdd-playbook/references)`.

The reason this is a finding and not a preference: **it has never been considered.** A sweep of
`CHANGELOG.md` (2,567 lines), `docs/plans/gated/`, `docs/recommendations/` and `capabilities.json`
for `progressive disclosure`, `context budget`, `token cost`, `context window`, `split SKILL` and
`references/` returns nothing. Every other trade-off in this repo is argued in writing, often at
length and often reversed on evidence. This one is not a decision that was made; it is a shape
that accreted. Mantis's 18-directory split is the counter-example that makes the question askable.

The natural decomposition already exists and is already routed: `/mutate` → §4, `/probe` → §5a,
`/tripwire` → §6, `/integration-audit` → §6a/§6c, `/claims` → §12, `/grade` → §13. The spine that
must stay resident is small — the ceremony table, §0, §1, §2, and the marker registry. The
per-command depth is what the commands themselves already reach for.

**The constraint that makes this non-trivial, and that a naive split would quietly break.** Rule
(d) enumerates gate surfaces by *path*: `calibration/check_scoreboard_integrity.py:191` names
"SKILL `## ` headings, agent briefs, and command files", and the SKILL half reads headings out of
that one blob (`calibration/check_scoreboard_integrity.py:200`). So moving §4 into a reference
file is indistinguishable from deleting §4 — it goes RED without a `gate-changes.md` entry, which
is correct — and, worse, once moved it lands **outside** the roster the ratchet walks, so a later
deletion of the moved section costs nothing. A split done for context economy would buy tokens by
punching a hole in the anti-deletion ratchet.

**Recommendation.** Treat the split as a gate-surface change, not a refactor: extend rule (d)'s
roster to the references directory **in the same commit** that creates it, journal each moved
heading in `calibration/gate-changes.md`, and plant the obvious test — a reference section deleted
after the move must still go RED. Do the roster extension first and red-first, then move sections.
If that ordering is not worth the effort, the honest outcome is to record the monolith as a
deliberate, costed decision, which is more than exists today.

#### F1 addendum — the external evidence, and what the split actually costs (added 2026-09-07)

The draft above argued the split from mantis's shape alone and explicitly declined to claim a
measured benefit. Anthropic's own skill-authoring guidance settles the direction, and this repo's
line counts settle the cost.

**The published bar is numeric, and this skill is ~3x over it.** Anthropic's skill-authoring
best-practices page states it twice — in the Progressive disclosure section and again in the
pre-ship checklist: "Keep SKILL.md body under 500 lines for optimal performance. If your content
exceeds this, split it into separate files using the progressive disclosure patterns." This
SKILL.md is 1,459 lines.

**The caching objection is pre-empted by the same page, and it is the objection worth answering.**
Prompt caching makes re-sending a large prefix cheap in dollars, so "it's cached, it's free" is a
reasonable first reaction. The guidance addresses it directly: "Not every token in your Skill has
an immediate cost... However, being concise in SKILL.md still matters: once Claude loads it, every
token competes with conversation history and other context." Caching is a billing optimisation; it
does not return occupied context or undo attention dilution. Anthropic's context-engineering
write-up puts the mechanism plainly — a finite attention budget, diluted as context grows.

**Reference files are genuinely free until read.** The mechanism, stated by the same page: "No
context penalty for large files: Reference files, data, or documentation don't consume context
tokens until actually read." So the saving is real, not notional — a moved section costs nothing
on a turn that doesn't need it.

**What the split would move, measured.** Sections routed by an existing command or otherwise
rarely needed on an ordinary turn: §4 mutation (128 lines) + §4a gate integrity (103), §5a UX
probes (45) + §5b agent evals (64), §6a/§6b/§6c wiring and dataflow (155), §9 security (47),
§10 CI hygiene (54), §11 checkpoints (27), §12 claims (137), §13 learning loop (109) — **869
lines, 60% of the file.** The residual spine (preamble, repo-extensions, §0, §1, §2, §3, §5, §6,
§7, §8, markers) is ~590 lines; moving §0's plan template (153) to a `/tdd-plan` reference brings
it to ~437, inside the published bar. This maps onto Anthropic's Pattern 2 (domain-specific
organization), which is the pattern the command surface already implies.

**The four real costs, none of them hidden:**

1. **The gate-surface roster, as above** — `calibration/check_scoreboard_integrity.py:191` must
   learn the references directory in the same commit, or the split trades context for a hole in
   the deletion ratchet. Plus a `calibration/gate-changes.md` entry per moved heading.
2. **148 internal cross-references** (`§N` mentions) are the genuine design work, not the moving.
   Anthropic warns that nested references get partially read: "Claude may partially read files
   when they're referenced from other referenced files... Keep references one level deep from
   SKILL.md." The heavily-cited targets (§13 ×16, §1 ×16, §6a ×15, §4 ×14, §6c ×13, §12 ×13) are
   mostly in the move set, so reference-to-reference edges are unavoidable. The mitigation is
   structural: SKILL.md carries a complete index of every reference file so no file is reachable
   only through another.
3. **17 duplicated SKILL.md read sites in `test_agents.py`** (plus 32 text-needle assertions)
   would need a single doctrine-reading helper. Mechanical — but concatenating everything would
   let a section drift into an unread reference with the needle still green, so needles should
   declare which file they expect the text in. That is the version that does not weaken a gate.
4. **Reference files over 100 lines need a table of contents**, per the same guidance, so partial
   reads still see the full scope.

**What it does not cost: the installer.** `scripts/install_into_repo.py:44` vendors the directory
`skills/tdd-playbook`, not the single file, so a `reference/` subdirectory ships downstream with
no installer change.

**The argument for doing it here specifically.** Anthropic's guidance says to build evaluations
before writing extensive skill documentation, and warns about the failure mode where "Claude
repeatedly reads the same file" — meaning a section that turns out to be needed every turn should
come back into the spine. That is an empirical question, and this repo already owns the instrument
to answer it: `calibration/` runs live agents against planted defects with paired clean controls.
If moving §4 out made the mutation-class plants start slipping through, a calibration run would
show it as a MISS. Most projects facing this decision have to guess. This one can measure, which
is the strongest reason to treat the split as a proven change rather than a refactor of faith.

### F2 — No threat model, and no reporting path, for the Playbook as software installed in other people's repos · **high**

`docs/HACK_CATALOG.md:1` is the Playbook's threat model and it is explicitly the threat model of
*agents gaming tests* — H1–H15 are test-hacking and honest-miss classes, and
`docs/plans/gated/2026-08-15-two-tier-calibration.md:8` states the scope directly: the threat is
agent-side test-gaming and answer-key recognition, "not trusted human collaborators."

That is a coherent scope. What is missing is the other one. This repo publishes a marketplace
(`.claude-plugin/marketplace.json`) and an installer that writes four `PreToolUse`/`PostToolUse`
hook registrations into a third party's `settings.json` — `hooks/scripts/lock_guard.py` and
`snapshot_guard.py` on `Edit|MultiEdit|Write` and again on `Bash`, `tag_guard.py` on `Bash`
(`plugins/tdd-playbook/hooks/hooks.json:44`), `weakening_guard.py` on `PostToolUse`
(`plugins/tdd-playbook/hooks/hooks.json:63`) — each of which executes Python on every matching
tool call, reads the tool payload, and writes to per-repo and machine-scoped state. There is no
security policy `(absent: SECURITY.md)`, no vulnerability reporting path, and no contributor
guidance `(absent: CONTRIBUTING.md)`. Mantis, whose blast radius is comparable, opens its README
with the isolation requirements and states plainly that AI agents may bypass intended constraints.

The material is already written and already true — it is just scattered where an adopter will not
find it: the capture store ships off for strangers, break-glass cannot silence a gate, a global
`off` is refused out loud, `uninstall` is the true inverse of the installer and both verbs are
dry-run by default. What is absent is the one page that says *this is what we run in your repo,
this is what we write and where, this is what we never do, and here is where to report it.*

**Recommendation.** A `SECURITY.md` (reporting path, supported versions, the state-locations
table, the known-residual list including double-registration) and a short `CONTRIBUTING.md`
(the blessed gate is the only entrypoint; planted-input test required for every mechanical
change; the four identity files move together). Low effort, and it is the surface a stranger
evaluates the project on before any of the rigor becomes visible to them.

### F3 — Every command re-derives the target repo's conventions from scratch; there is no per-repo knowledge base · **medium**

Mantis's `/mantis-plan` reads the knowledge base to "dynamically skip already analyzed areas."
Here, the equivalent discovery is re-run per invocation and never persisted:
`plugins/tdd-playbook/skills/tdd-playbook/SKILL.md:31` instructs the agent to discover the repo's
own testing conventions FIRST in each repo, and `plugins/tdd-playbook/commands/tdd-plan.md:8`
repeats the same instruction at command level. Nothing writes the answer down. `capability_registry
init` is the closest artifact and it registers entry points, not conventions
(`plugins/tdd-playbook/bin/capability_registry.py:63`).

So the discovery step is both **repeated** and, more importantly, **unauditable** — two sessions
in the same repo can reach different conclusions about what that repo's testing floor is, and
neither is reviewable. That is a claims problem wearing a performance problem's clothes.

The pattern to extend is already in-house: `plugins/tdd-playbook/bin/render_reference.py:73`
renders machine-owned facts with provenance into `docs/reference/current-state.md` — for this
repo only. The same shape pointed at a downstream repo gives a cited, diffable conventions record.

**Recommendation, with its own caution.** A cached KB that goes stale is worse than re-derivation,
because it converts an honest re-read into a confident wrong answer. So this is only worth
building with the discipline the registry already has: every row cites the file it was read from,
`validate` re-resolves those citations, and an unresolvable row degrades the record to
UNMEASURED rather than letting it pass. Without that, do not build it.

### F4 — The interpreter floor is undeclared and CI tests exactly one version · **low**

`.github/workflows/gate.yml:47` pins `python-version: "3.12"`, and nothing declares a supported
floor `(absent: pyproject.toml)` `(absent: setup.cfg)`. Meanwhile the installer vendors 25 bins
into an arbitrary repo's `.claude/bin/`, where they run under whatever `python3` that machine has.

The care is evidently there — eight files under `plugins/tdd-playbook/bin/` carry
`from __future__ import annotations`, which is what keeps their PEP 604 annotations from raising
at definition time on older interpreters, so the *intent* is broad compatibility. It is simply not
pinned by anything, which in this repo's own terms makes it a claim with no mechanism: nothing
would notice if a `match` statement or a 3.11-only stdlib call landed in a vendored bin tomorrow.
Note that the hook scripts — the downstream-critical surface, where a crash means a guard goes
dark — are already clean of version-specific annotation syntax.

**Recommendation.** Declare the floor in one place, and add a compile-only CI leg at that floor
(`python -m compileall` over `bin/` and `hooks/scripts/` on the oldest supported interpreter).
Cheap, and it converts the current good intention into something that fails loudly.

---

## 5. What mantis should have stolen from us

Recorded because the comparison runs both ways and because it calibrates how much of section 4 to
believe. Mantis has a `/mantis-calibrate` stage that rates the risk of findings; it has nothing
that proves the finding-generation works. No planted defect, no paired clean control, no recall
and false-positive rate reported separately, no append-only scoreboard. Its README's central
safety guarantee — every finding manually verified by a security expert — is exactly the
honor-system shape this repo spent thirteen sections closing. If mantis adopted one thing from
here, it should be the planted-plant-with-clean-control pair.

---

## 6. Claims

| # | Claim | Evidence | Verdict |
|---|---|---|---|
| 1 | SKILL.md is ~131 KB / ~33k tokens, one file, 22 `##` sections | `wc -c` = 131,277; headings §0–§13 at `plugins/tdd-playbook/skills/tdd-playbook/SKILL.md:53`–`plugins/tdd-playbook/skills/tdd-playbook/SKILL.md:1344` | VERIFIED |
| 2 | No progressive-disclosure reference bundle exists | `(absent: plugins/tdd-playbook/skills/tdd-playbook/references)` | VERIFIED |
| 3 | Skill context cost has never been discussed in-repo | sweep of `CHANGELOG.md`, `docs/plans/gated/`, `docs/recommendations/`, `capabilities.json` for six phrasings — zero hits | VERIFIED |
| 4 | Rule (d) enumerates gate surfaces by path and would read a section move as a removal | `calibration/check_scoreboard_integrity.py:191`, `:200` | VERIFIED |
| 5 | The threat model is scoped to agent test-gaming, not to the shipped hooks | `docs/HACK_CATALOG.md:1`, `docs/plans/gated/2026-08-15-two-tier-calibration.md:8` | VERIFIED |
| 6 | Four guards execute on every matching tool call in a downstream repo | `plugins/tdd-playbook/hooks/hooks.json:44`, `:63` | VERIFIED |
| 7 | No security policy or contributor guidance ships | `(absent: SECURITY.md)` `(absent: CONTRIBUTING.md)` `(absent: CODE_OF_CONDUCT.md)` | VERIFIED |
| 8 | Repo-convention discovery is per-invocation and never persisted | `plugins/tdd-playbook/skills/tdd-playbook/SKILL.md:31`, `plugins/tdd-playbook/commands/tdd-plan.md:8`, `plugins/tdd-playbook/bin/capability_registry.py:63` | VERIFIED |
| 9 | CI pins one interpreter; no floor is declared | `.github/workflows/gate.yml:47`, `(absent: pyproject.toml)` `(absent: setup.cfg)` | VERIFIED |
| 10 | Model tiering is already implemented and planted-tested — NOT a finding | `plugins/tdd-playbook/tests/test_agents.py:605` | REFUTED as a finding |
| 11 | PEP 604 in vendored bins is NOT a portability break — NOT a finding | 8 files carry `from __future__ import annotations` | REFUTED as a finding |
| 12 | The capture store ships off for non-enrolled installs — a strength, not a gap | `plugins/tdd-playbook/hooks/scripts/capture.py:80` | REFUTED as a finding |
| 13 | Anthropic publishes a 500-line SKILL.md bar; this file is 1,459 lines | skill-authoring best-practices page, stated in Progressive disclosure and in the checklist | VERIFIED |
| 14 | Prompt caching does not answer the objection — same page says tokens still compete once loaded | same page, "Concise is key" | VERIFIED |
| 15 | Unread reference files cost zero context | same page, Runtime environment: "No context penalty for large files" | VERIFIED |
| 16 | 869 of 1,459 lines (60%) are command-routed or rarely needed | per-section line counts, this tree | VERIFIED |
| 17 | 148 internal cross-references are the real design work | `§N` mention count in SKILL.md | VERIFIED |
| 18 | The installer needs no change — it vendors the directory | `scripts/install_into_repo.py:44` | VERIFIED |

**Claims 18/18.** Three of the twelve are refutations of findings this review carried in draft;
they are kept visible rather than deleted, because a review that shows only its survivors is
reporting its inventory, not its search (§12).

**Not claimed:** whether the F1 split would improve measured agent behavior in this repo. The
line-count budget and the vendor guidance are now settled (F1 addendum), and the 869-line /
60% reduction is counted from the real file — but no calibration run has been executed against
a split tree, and the token figure remains a character-count estimate, not a tokenizer result.
The instrument to close both gaps exists in `calibration/`; it has not been pointed at this. Whether any downstream repo has actually hit an interpreter-floor failure — no evidence
either way was sought. Both are leads, not findings.
