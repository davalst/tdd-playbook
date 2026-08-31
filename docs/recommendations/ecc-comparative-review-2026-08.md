# Comparative review: affaan-m/ECC -> tdd-playbook — 2026-08-31

**Subject:** <https://github.com/affaan-m/ECC> at `005eff40fd4a4ac005da7a70e713459175385516`,
`VERSION` = 2.2.0 (shallow clone, 2026-08-31).
**Question asked:** which of ECC's patterns would make THIS repo better.
**Status:** ANALYSIS ONLY — nothing here is built. Every recommendation is a proposal with a
stated cost and a stated scope limit. Six of the seven are small; one (R1) is a workstream.

**Method, and its limits (§12).** Claims below were verified by reading the cloned tree and,
where the tool had no dependencies, by RUNNING it. `validate-skills.js`, `validate-commands.js`,
`validate-hooks.js` and `validate-install-manifests.js` require `js-yaml`/`ajv`, which are not
installed here, so those four were read but NOT executed — findings about them are source-level,
and are marked as such. No claim below rests on the ECC README's self-description.

---

## The honest frame

ECC and this repo are not the same kind of artifact. ECC is a broad agent-harness distribution:
68 agents, 94 commands, 286 skills (`node scripts/ci/catalog.js --text`, run here, exit 0),
~1,500 files under `docs/`, adapters for a dozen harnesses, an npm package, a GitHub App. This
repo is one narrow, deep mechanism: a TDD doctrine plus the machinery that proves the doctrine
is still load-bearing.

So the comparison is asymmetric on purpose. **ECC's transferable value is breadth of cheap,
mechanical, fail-closed checks over the instruction/config surface** — the exact class of artifact
we ship into other people's repositories. **Our advantage is depth**: derived rosters, planted-input
tests, byte-exact regeneration, a calibration corpus. I found no calibration harness, no planted-
defect corpus, and no oracle-split policy anywhere in the ECC tree; the closest thing
(`scripts/gan-harness.sh`) scores work with an LLM evaluator against a numeric pass threshold,
which §5b forbids as a gate. We should not trade our depth for their breadth. We should take the
handful of surface checks we are missing.

---

## R1 — Doctrine-compliance measurement (the one that matters)

**What ECC has.** `skills/skill-comply/SKILL.md` + `skills/skill-comply/scripts/`. Given any
instruction file (a SKILL.md, a rule, an agent definition) it: generates the expected behavioural
sequence; generates three scenarios at DECREASING prompt strictness — `supportive` -> `neutral` ->
`competing` (`prompts/scenario_generator.md`, lines defining `level_name`); runs `claude -p` and
captures the tool-call trace; classifies each call against the spec steps; checks temporal
ordering; and reports a per-step compliance rate. Its stated key concept is **prompt
independence** — "whether a skill/rule is followed even when the prompt doesn't explicitly support
it" (`SKILL.md`, "Key Concept" section).

**Why this is the highest-value item for us.** Our calibration answers "is the VERIFIER still
sharp?" Nothing we own answers "is the DOCTRINE still followed?" — and our own CLAUDE.md records
the cost of that blind spot in the plan-landing lapse: **zero plans committed across the 18 commits
from 2026-08-21 to 2026-08-29**, including a multi-deliverable feature, two guard deletions and a
new adversary. The doctrine was in force the whole time. Nothing noticed for eight days. A
compliance run against SKILL.md §0 at `neutral` strictness is precisely the instrument that would
have.

It also supplies the ordering signal our findings backlog never had. The posture note records 205
findings, 12 UNBUILT-GUARD keys, and zero guards built from any of them. skill-comply ranks
doctrine steps by measured non-compliance and recommends hook promotion for the worst — a queue
sorted by evidence rather than a list sorted by nothing.

**Constraints if we build it.**
- The classifier is an LLM (`scripts/grader.py` -> `classify_events`). Under §5b that makes
  compliance rate a **TREND, never a gate**. The temporal-ordering half (`_check_temporal_order`)
  is deterministic and could gate; the classification half must not.
- Build it by generalizing `calibration/` — the model plumbing, hard caps and append-only history
  already exist — not as a second rig. That is the same call the 2026-08-17 §5b work made.
- It is the only recommendation here that is a workstream rather than an afternoon.

---

## R2 — Invisible-unicode / tag-smuggling scan over the instruction surface

**What ECC has.** `scripts/ci/check-unicode-safety.js` (276 lines, zero dependencies, runs clean
here). It rejects the Unicode Tag block U+E0000–U+E007F with an in-source rationale naming ASCII
smuggling as the vector, plus bidi overrides U+202A–202E and U+2066–2069, ZWSP/ZWJ U+200B–200D,
U+2060, U+FEFF, U+180E, Hangul fillers U+115F/U+1160/U+3164, and invisible math operators
U+2061–2064. It takes its scan root from `ECC_UNICODE_SCAN_ROOT`, which is what makes
`tests/scripts/check-unicode-safety.test.js` able to plant violations into a temp tree — a
planted-input test in our sense, written the way we write them.

**Why we need it.** We vendor SKILL.md, `agents/*.md`, `commands/*.md` and executable hooks INTO
third-party repositories via `install_into_repo.py`. A tag-smuggled instruction in our doctrine
would render as ordinary prose to every human reviewer, propagate to every downstream repo on the
next refresh, and be consumed as agent instruction. **We have no check for this**: every match for
"invisible", "zero-width", "200B", "FEFF" or "homoglyph" across `plugins/`, `calibration/` and
`scripts/` is the English word "invisible" used in prose.

**Honest framing under §13.** I scanned our whole tree for those code points: **zero hits**. So
this is a PREVENTIVE guard with no motivating artifact — there is no pre-fix sha to replay it
against, and the doctrine requires saying so rather than inventing one. It ships with planted
fixtures only, and that limitation belongs in its docstring.

---

## R3 — Widen the count-pin's denominator (the `catalog.js` lesson, both directions)

**What ECC has.** `scripts/ci/catalog.js` counts the tree and asserts the counts in README.md,
AGENTS.md and three translated mirrors, failing closed when the expected marker is missing
(`replaceOrThrow`: "is missing the expected catalog marker"), with `--write` to sync.

**We already have the stronger version** — `test_guard_roster_derived_and_pinned`
(`plugins/tdd-playbook/tests/test_hooks.py:1408`) derives the roster from `hooks.json` x each
script's NAME x `_common._DEFAULT_MODES`, pins the prose in CLAUDE.md and README.md, catches
phantom guards in both dialects, and carries planted fixtures. It is better than catalog.js.

**But its denominator is a 530-character window.** `_roster_chunk` anchors on the literal
"blocking guards" and takes `[start-30 : start+500]`, and `_roster_problems` asserts the count word
only against `len(blocking)`. So:

> **D1 (verified defect, ours).** `README.md:251` reads
> `hooks/   # enforcement hooks (4 blocking, 5 opt-in)`. The machinery is **4 block / 4 off /
> 1 warn** (`_DEFAULT_MODES`, loaded and counted). The blocking half is right; "5 opt-in" is
> wrong however you read it — there are 4 `off` guards, and `fixture_guard` is warn-BY-DEFAULT,
> i.e. on, not opt-in. The claim sits 11,928 characters from the anchor, outside the pinned
> window. README.md:75-79 — inside the window — enumerates the partition correctly; the Layout
> block 176 lines later contradicts it, and nothing compares the two.

**ECC makes the same mistake from the other side, which is the useful part.** `catalog.js` names
the files it checks. `SOUL.md` is not one of them, and it still claims "30 specialized agents, 135
skills, 60 commands" against a verified 68/286/94. A count check that enumerates its inputs leaves
everything it did not enumerate to rot silently — and looks green while doing it. That is our own
"a control carries its denominator" rule (§12), demonstrated by someone else's repo.

**Proposal.** Either widen `_roster_chunk` to scan the whole file for count-bearing guard phrases
(all three tiers, not just blocking), or make the README layout block a generated region on the
`render_reference.py` pattern we already trust. The second is stronger and we already own the
technique. D1 is the motivating artifact §13 requires; freeze `README.md:251`'s current text as
the planted fixture.

---

## R4 — Two workflow-hardening fixes (and NOT the validator that found them)

**What ECC has.** `scripts/ci/validate-workflow-security.js` (278 lines): rejects checkout of
untrusted refs under `pull_request_target`/`workflow_run` (including the `refs/pull/N/{head,merge}`
form), requires `persist-credentials: false` on every `actions/checkout`, requires `--ignore-scripts`
on every package-manager install, and treats `permissions: write-all` as equivalent to named write
scopes.

**Two verified gaps on our side.**

> **D2.** `.github/workflows/gate.yml:41-44` checks out without `persist-credentials: false`, so
> the token stays in `.git/config` for the rest of a job that then executes repository Python
> (`sh scripts/civerd_gate.sh`). **Scope, stated rather than assumed:** the job declares
> `permissions: contents: read` and fork PRs get a read-only token with no secrets, so this is
> defence-in-depth, not an incident. One line.

> **D3.** `.github/` contains only `workflows/` — there is no `dependabot.yml`. We pin two actions
> by SHA (checkout v4.2.2, setup-python v5.6.0), which is right, but a pin with no update channel
> is a pin that silently ages out of security fixes. ECC's `.github/dependabot.yml` runs a weekly
> `github-actions` ecosystem update with security updates grouped separately.

**What I am NOT recommending.** Porting the 278-line validator. We have exactly one workflow;
the validator's denominator would be 1. Take the two fixes and pin them with a small test against
`gate.yml`; revisit the validator if we ever have a second workflow.

---

## R5 — Named hook profiles, recorded at install time

**What ECC has.** `scripts/lib/hook-flags.js`: `ECC_HOOK_PROFILE` = `minimal|standard|strict`
(default `standard`), `ECC_HOOKS_ENABLED`, `ECC_DISABLED_HOOKS`, each falling back to a Claude
plugin option and then to a managed `ecc/setup.json` written at install. Every hook declares the
profiles it belongs to (`run-with-flags.js <id> <script> standard,strict`).

**Our mode system is richer per-hook and poorer per-user.** `_common.resolve_mode` has
precedence (per-hook > global > default) and a break-glass CLAMP whose invariant is structural
rather than asserted — genuinely better engineering than ECC's flat lookup. What it has no concept
of is a **named tier a user can choose once and have recorded.**

That absence is what killed two guards. The v1.47.0 record: `exitcode_guard` deleted on 701
warnings with zero acted on; four more retired to `off` on 31 warnings and zero blocks; and the
verdict "a dark feature nobody will ever switch on is worse than none". The opt-in path exists —
`TDD_PLAYBOOK_HOOK_OVERMOCK=warn` and four siblings — and it requires a downstream user to read
CLAUDE.md closely enough to find five undiscoverable env var names. A `strict` profile that flips
the four `off` guards on as a set converts that into one documented switch, and `gate_yield` would
finally accrue rows from someone other than us. Cost: one branch in `resolve_mode` reading
`TDD_PLAYBOOK_HOOK_PROFILE`, plus an installer flag that records the choice.

**The counter-argument, stated.** This re-opens a decision v1.32.0 made deliberately. It is not a
proposal to re-enable those guards by default; it is a proposal to make the existing opt-in
reachable, so that "nobody opted in" becomes a measurement rather than an inference about
discoverability.

---

## R6 — A conditional registration checklist in a PR template

ECC's `.github/PULL_REQUEST_TEMPLATE.md` has a section that fires only on a triggering condition:
"If you added a skill, command, agent, hook, or CLI tool" — then lists the manifests, catalogs,
publish-surface allowlist and cross-harness copies that must be updated, each item backed by a
mechanical check elsewhere.

We have no `.github/PULL_REQUEST_TEMPLATE.md`. This fits the posture note precisely — conditional,
so it is silent on the commits it does not concern, and every line is a pointer to a check that
already exists (`host_parity`, `capability_registry validate`, the four identity files). **Honest
value estimate: low while David is the only committer**, since the audience for a PR template is
contributors. Worth ten minutes, not more.

---

## R7 — SECURITY.md with an explicit trust boundary

ECC's `SECURITY.md` names supported versions, a private reporting path with response SLAs, an
explicit **Scope** and **Out of Scope** list, and supply-chain rules (SHA-pinned actions, no
untrusted GitHub context shelled into `run:`). It also names impostor packages by name.

We ship executable hooks into third-party repositories and have no SECURITY.md and no stated
vulnerability-report path. For a project whose deliverable IS executable policy running inside
other people's checkouts, that is a real omission — modest effort, and the "Out of Scope" section
is the part worth copying, because it prevents the report queue from filling with
local-shell-already-owned findings.

---

## What NOT to take from ECC

- **Frontmatter contracts that ship dark.** `scripts/ci/validate-skills.js:17,34` demotes all
  frontmatter findings to warnings unless `--strict` or `CI_STRICT_SKILLS=1`. Neither appears
  anywhere in `.github/workflows/` or `package.json` (verified: zero occurrences). So the
  documented skill-frontmatter contract for 286 skills is, in CI, advisory-only. This is exactly
  the class of gate v1.47.0 deleted here, at 286x the surface.
- **Two entrypoints for one suite.** `package.json`'s `test` script runs ten validators plus
  `tests/run-all.js`; the CI `validate` job runs eleven, including `validate-workflow-security.js`,
  which appears **zero times** in `package.json`. A contributor can be green locally and red in CI
  on a check they cannot run. This is precisely the divergence probe run 2 (2026-07-28) found here,
  and the reason `civerd_gate.sh` is the ONE blessed entrypoint. Keep ours.
- **`continue-on-error: false`** on eleven steps in `ci.yml`. That is the default. Config that
  restates a default reads like a control and is not one.
- **`scripts/gan-harness.sh`.** An LLM evaluator scoring against `GAN_PASS_THRESHOLD` to decide
  whether to iterate. §5b: an LLM judge is a trend line, never a gate.
- **The breadth itself.** 286 skills and 68 agents with no calibration corpus, no planted-defect
  harness and no staleness instrument anywhere in the tree. Their `SOUL.md` drift is the small
  visible symptom of the general condition.

## Where we are already ahead (so the list above is not misread)

- `docs/architecture/host-parity.json` records status per ASSET per host with `liveness_test`,
  `debt_ref`, `owner` and `expires`. ECC's `scripts/lib/harness-adapter-compliance.js` records one
  coarse row per harness. Theirs adds two fields worth stealing cheaply — `last_verified_at` and
  `risk_notes` — and nothing else.
- Rosters DERIVED from `git ls-files` (`test_no_script_creates_a_release_tag`) versus ECC's
  hand-listed `TARGETS` arrays in several validators.
- Whole-file regeneration with byte-exact equality and a planted manual-edit refusal
  (`test_reference_docs.py`) versus catalog.js's regex-region replacement.
- Non-vacuity assertions on scanners ("the derived roster is non-trivial"). I found no equivalent
  in ECC's validators: an empty target directory returns `[]` and exits 0.
- The break-glass clamp, whose invariant cannot express the failure its first draft had.

---

## Verified defects in THIS repo, surfaced by the comparison

| id | file | claim | status |
|----|------|-------|--------|
| D1 | `README.md:251` | "4 blocking, 5 opt-in"; machinery is 4 block / 4 off / 1 warn | verified, outside the roster pin's window |
| D2 | `.github/workflows/gate.yml:41-44` | checkout without `persist-credentials: false` | verified absent; low severity (read-only token) |
| D3 | `.github/` | no `dependabot.yml`; two SHA-pinned actions with no update channel | verified absent |
| D4 | repo-wide | no invisible-unicode scan over the vendored instruction surface | verified absent; tree currently clean (0 hits) |

D1 is the only one that makes a shipped document say something false, and it is the motivating
artifact for R3.

---

## Claims 14/14

Every load-bearing claim, and how it was checked. Nothing here rests on either repo's prose.

1. ECC counts are 68 agents / 94 commands / 286 skills — RAN `node scripts/ci/catalog.js --text`, exit 0.
2. `SOUL.md` claims 30/135/60 and is not among catalog.js's checked files — read both.
3. `check-unicode-safety.js` blocks the U+E0000-E007F tag block — read `isDangerousInvisibleCodePoint`; RAN the script, exit 0.
4. Its test plants violations into a temp root via `ECC_UNICODE_SCAN_ROOT` — read `tests/scripts/check-unicode-safety.test.js`.
5. We have no unicode/smuggling check — grepped `plugins/ calibration/ scripts/`; all hits are the English word "invisible".
6. Our tree contains zero dangerous code points — ran a code-point scan over all `.md/.py/.sh/.json/.yml/.yaml/.txt`.
7. `_DEFAULT_MODES` is 4 block / 4 off / 1 warn — imported the module and counted.
8. `README.md:251` says "4 blocking, 5 opt-in" — read; measured 11,928 chars from the roster anchor.
9. `_roster_chunk` windows `[start-30 : start+500]` and the count word is asserted against `len(blocking)` only — read `test_hooks.py:1356-1404`.
10. `gate.yml` has no `persist-credentials` — grepped; absent.
11. `.github/` has no `dependabot.yml` — `ls -a .github/` returns only `workflows`.
12. `validate-skills.js` defaults frontmatter findings to WARN and neither `--strict` nor `CI_STRICT_SKILLS` appears in CI or package.json — read the source; grepped both.
13. `validate-workflow-security.js` appears zero times in `package.json` while `ci.yml` runs it — grepped both.
14. ECC has no calibration/planted-defect harness — searched the tree for calibration, planted-fixture and oracle-split machinery; found `skill-comply` (compliance measurement, LLM-classified) and `gan-harness` (LLM-scored iteration), neither of which is one. **This is a NEGATIVE and the documented false-positive trap**: it is a bounded-search claim over a ~1,500-file docs tree, not an exhaustive proof of absence. Treat it as "not found where such a thing would live", not "does not exist".

**Not verified, stated as such:** `validate-skills.js`, `validate-commands.js`, `validate-hooks.js`
and `validate-install-manifests.js` were read but not executed (`js-yaml`/`ajv` absent). ECC's
`ecc-agentshield` scanner is a separate repository and was not reviewed at all; the README's
security claims about it are unchecked here.
