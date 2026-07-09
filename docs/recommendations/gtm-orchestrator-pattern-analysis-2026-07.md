# Patterns Worth Stealing from `janskuba/go-to-market-orchestrator` — CTO Analysis

**Date:** 2026-07-09 · **Prepared as:** CTO / senior-dev review
**Input:** full read of https://github.com/janskuba/go-to-market-orchestrator (README, QUICKSTART,
installer/validator/uninstaller, `orchestrator/dispatch.py` + 21 handlers, all 30 hook units,
skills/modules/templates, the `/outbound-pipeline` command, tests, CI) compared against this
repo's plugin, installer, hooks, calibration harness, and the 2026-07 roadmap.

---

## 1. The one-paragraph verdict

The GTM orchestrator is a **distribution artifact, not a verification system** — its testing is
smoke-level (fixture in, exit-code 0 out), it has no adversarial calibration, no planted inputs,
no versioning story, and some of its hook choices (CRM writes on `PostToolUse` matcher `*`) are
outright anti-patterns for us. On rigor we are years ahead and should import nothing. But it is
genuinely **better than us at the thing we're weakest at: adoption surface and operational
self-verification of the install itself**. It ships a CI gate (we don't have one), a
post-install doctor (`validate.sh`) that mechanically proves the hooks are live in the user's
actual settings, an install manifest + uninstaller, per-hook documentation cards, cherry-pick
installs, persona starter packs, and a quickstart with a visible first win in under five
minutes. Every one of those maps directly onto our own doctrine — a vendored Playbook install
is itself a feature that must be BUILT + WIRED + **ACTIVATED** + EXERCISED, and today we verify
that leg with a human checklist in a standing prompt. The asymmetric trade: take their
packaging patterns, fill them with our planted-input rigor, ignore their content.

---

## 2. What their repo actually is (so we steal from the right layer)

Three-layer bundle for GTM teams: **skills** (instruction modules → `~/.claude/skills/`),
**agents + a pipeline slash command** (5-stage sequential fan-out with checkpoint files), and
**hooks + orchestrator** (30 `settings.json` fragments firing `dispatch.py → py/<service>.py`
REST handlers for 17 SaaS tools). One-shot `install.sh` (copy or symlink, `--skills-only`,
`--hooks=a,b` cherry-pick), `validate.sh` doctor, `uninstall.sh` driven by an install marker,
`DRY_RUN=1` honored by every handler, and a CI matrix (py3.9/3.11) that compiles everything,
`bash -n`'s every script, schema-validates every hook, and dry-runs every handler on every push.

Where it's weak: "validation" means *liveness*, never *correctness* (the smoke fixture is
`{"action":"smoke", ...}` and the assertion is exit 0); no version stamping; installs mutate
`~/.claude` with `rm -rf dest`; side-effecting hooks fire on every tool use with no idempotency
guarantees; the sequential pipeline trusts each agent's self-report beyond file existence.
None of that threatens our position. The packaging does — because it's what a first-time user
touches, and ours is thinner.

---

## 3. Patterns to adopt, ranked

### P1 — CI that runs our own release gate (their weakest repo has it; we don't)

The most embarrassing finding, in the productive sense: a repo with smoke-level rigor enforces
its gate mechanically on every push, while **we — whose product is literally "mechanical gates
beat human checklists" (§13) — run our release gate as a human-executed checklist** in
CLAUDE.md. There is no `.github/` directory in this repo at all.

Adopt: `.github/workflows/ci.yml` running, on every push/PR:
- the six planted-input suites (`plugins/tdd-playbook/tests/test_*.py`, `calibration/test_harness.py`);
- JSON parse of `hooks.json` / `plugin.json` / `marketplace.json`;
- `capability_registry.py validate` on our own `capabilities.json`;
- `calibration/run_calibration.py --dry-run` (the free CI-safe validation, exactly as documented);
- the scratch-repo `install_into_repo.py` cloud-parity run (new bins + hooks present,
  `${CLAUDE_PLUGIN_ROOT}` rewritten) — this already exists as a manual release step; it belongs in CI.

Live calibration stays manual/scheduled (needs a real `claude` binary and budget — unchanged).
Everything mechanical moves to CI. Copy their matrix idea: test on the oldest Python we claim
to support and a current one, since hook scripts run under whatever python3 the user's machine
has. **Effort: half a day. Priority: this week.**

### P2 — A vendored `playbook_doctor.py`: the ACTIVATED leg, applied to ourselves

Their `validate.sh` is the best idea in the repo: schema-validate every fragment → compile every
handler → **dry-run every handler against a fixture payload** → report env readiness → **introspect
the user's actual installed `settings.json` and print which hooks are live**. It answers "is this
thing actually armed on THIS machine?" mechanically.

We preach exactly this — the Tripwire's ACTIVATED leg, §6a wiring liveness, the darkness
doctor — yet our downstream story is step 2 of the standing refresh prompt: *"VERIFY: confirm
`.claude/bin` contains tdd_lock.py…"* — a human checklist for the one leg we say humans always
skip. Adopt, and go one better than they did:

`plugins/tdd-playbook/bin/playbook_doctor.py`, vendored into every target repo, which:
1. confirms every guard registered in `.claude/settings.json` points at a script that exists
   and compiles;
2. **feeds each guard a planted violation payload and asserts it blocks** — their smoke test
   asserts exit 0; ours asserts the guard *catches the plant*. That is in-situ calibration of
   the vendored copy, at near-zero cost, in every downstream repo — a miniature of
   `run_calibration.py` that needs no `claude` binary;
3. prints the **demotion inventory**: every `TDD_PLAYBOOK_HOOK_*` env override in effect, so a
   guard silently demoted to `warn` months ago is as visible as a dark feature
   (the exact parallel of `capability_registry.py doctor`'s dark-feature inventory);
4. prints vendored-version-vs-upstream drift and the calibration-staleness flag (see P3) —
   automating what is currently prose in the standing prompt.

Wire it into the refresh prompt ("run doctor, paste its output in the report") and into the
scratch-repo CI parity check. **Effort: 2–3 days including planted-input tests for the doctor
itself. Priority: next release. This is the highest-leverage single item.**

### P3 — Install manifest + version stamp + uninstaller

Their installer writes `~/.claude/.gtm-installed.json` (what was installed, mode, root) and the
uninstaller consumes it; settings backups are timestamped. Our `install_into_repo.py` is
reconciling but **leaves no record**: a downstream repo cannot tell what Playbook version it
carries, so refresh-staleness detection depends on a human reading a temp clone's history file,
and there is no uninstall path at all.

Adopt: write `.claude/.tdd-playbook-manifest.json` on every vendored install —
`{version, source_sha, installed_at, files[]}`. That enables:
- the doctor's drift check ("vendored v1.5.0, upstream is v2.0 — re-run the refresh prompt");
- provable pruning on refresh (delete exactly what the previous manifest listed and we no
  longer ship, instead of prune-by-known-name);
- a real `--uninstall` mode (remove manifest-listed files, strip our hooks from
  `settings.json`, preserve everything else) — adoption is easier to say yes to when the exit
  is one command;
- timestamped `settings.json` backups before every merge (they do this; we should).

**Effort: 1–2 days, mostly installer tests. Priority: next release, alongside P2 (the doctor
reads the manifest).**

### P4 — Per-guard documentation cards + cherry-pick/profile installs

Every one of their 30 hooks is a directory: `hook.json` + a plain-English `README.md` — *when
it fires, what it runs, required env vars* — and `install.sh --hooks=a,b` cherry-picks. Our
`hooks.json` is one opaque blob; a user who wants to know what `overmock_guard` does, why it
exists, and how to demote it must read source or grep two long documents.

Adopt the card, upgrade the content — for each guard a `README.md` stating: the **attack vector
it defends** (linked to its `docs/HACK_CATALOG.md` entry), default mode (block/warn) and the
demotion env var, **the planted test that calibrates it** (file:test), and known false-positive
patterns. This makes the guard library auditable one unit at a time and turns the HACK_CATALOG
cross-reference into navigable structure instead of prose. Pair with install *profiles* rather
than raw cherry-picking (see P5) — unlike their independent webhooks, our guards are a
mutually-reinforcing system, and we should not encourage à-la-carte weakening.
**Effort: 1–2 days, docs-heavy. Priority: v2.0 positioning window.**

### P5 — Adoption-posture starter packs

Their five role packs (`full-settings-founder.json` …) are complete paste-ready configs — the
insight is *don't make users assemble; hand them a whole posture*. Our equivalent axis isn't
role, it's **strictness**:

- `strict` — everything blocks (post-calibration steady state);
- `standard` — integrity blocks, advisory warns (today's default, now named and documented);
- `legacy-onboarding` — warn-everything **plus a dated escalation entry** (owner + expiry,
  same shape as integration debt — a soft posture that never hardens is a silent demotion);
- `ci-only` — guards enforce in CI, advisory locally.

Ship each as a documented env-preset block the installer can apply (`--profile legacy-onboarding`),
and have the doctor (P2) print which profile is in effect. This converts our current all-or-nothing
+ ad-hoc env-var escape hatch into deliberate, visible, expiring postures.
**Effort: ~1 day on top of P2/P3. Priority: v2.0.**

### P6 — The five-minute first win

Their QUICKSTART lands a visceral payoff: *"give Claude any task and watch your Slack channel
light up."* Our README leads with doctrine — correct for depth, weak for conversion, and WS5
(positioning, public scoreboard) is on the roadmap. Our equivalent moment is better than
theirs, we just don't stage it: **watch the guard catch a cheat**.

Adopt: `scripts/demo.sh` — scratch repo, vendored install, then a scripted test-weakening edit
(delete an assertion) → `test_weakening_guard` **blocks**, message shown; then a journaled
`/tdd-unlock`-style legitimate path → allowed. Thirty seconds, seeing-is-believing. Because the
demo *is* a planted-input run, it doubles as a CI step (P1) and a doctor mode (P2) — one script,
three duties. Put the transcript at the top of the README.
**Effort: ~1 day. Priority: v2.0 positioning.**

### P7 — Ship the template we already promise

Their `skills/modules/` + `templates/` + `examples/` progressive-disclosure kit (fill-in
sections with inline comments explaining *why each section matters*, assembled starters,
filled examples) is good docs engineering. We have a doctrinal gap it maps onto exactly: the
Playbook says each repo layers stack-specific testing on top, *discovered from CLAUDE.md /
a testing addendum / docs/TESTING\** — **but we ship no template for that addendum**, so every
downstream repo improvises the interface our own skill goes looking for.

Adopt: `templates/testing-addendum.md` — fill-in sections for test runner + invocation,
extra gates beyond the floor, mock-policy exceptions, flaky-quarantine owner + expiry
convention, security-test scope — each with a one-line comment on why it exists, plus one
filled example. **Effort: half a day. Priority: anytime; it's cheap and closes a real gap.**

### P8 — Hostile-stdin contract for hooks (verify, probably small)

Their `dispatch.py` treats hook stdin as hostile: empty, non-JSON, non-dict, and undecodable
inputs all normalize to a payload instead of a traceback. For them that's tidiness; for us it's
a security property — **a guard that crashes on a malformed payload fails open**. Action:
audit `hooks/scripts/_common.py` for parity, and add planted *malformed-payload* cases
(empty stdin, truncated JSON, JSON scalar, wrong-shape dict) to `test_hooks.py` if not present.
A crash-to-open is exactly the kind of plant our own calibration should include.
**Effort: hours. Priority: fold into the next hooks touch.**

---

## 4. Patterns to explicitly NOT adopt

- **Side-effecting hooks on `PostToolUse` matcher `*`** (CRM upserts after *every* tool use):
  non-idempotent external writes on a firehose event, silent-failure by design. Validates our
  read-only-guard discipline; nothing to change, but worth citing when someone asks why our
  hooks never call out.
- **Their install mechanism** (copy into `~/.claude` with `rm -rf dest`, no version tracking,
  shell-profile mutation): take the *manifest idea* (P3), not the mechanism. Our
  plugin/marketplace + reconciling vendoring is strictly better.
- **Their testing bar** (exit-0 smoke with a universal fixture): the shape of `validate.sh`
  is right, the assertion is hollow. Everywhere we adopt the shape (P1/P2/P6), the assertion
  must be a planted violation being *caught*, per the release discipline of this repo.
- **Trust-the-agent pipeline checkpoints**: their `/outbound-pipeline` verifies only that a
  checkpoint file exists between stages. Our "Loop closed: yes/no" + adversarial dispatch is
  the stronger contract; no import needed. (Their *pause-and-review when the pipeline did
  something unrequested* — auto-enrichment triggers a human checkpoint — is a decent
  human-in-the-loop instinct, but our domain equivalents, journaled unlocks and blocking
  guards, already cover it.)

---

## 5. Sequencing recommendation

| When | Items | Why this order |
|---|---|---|
| This week | **P1** (CI) | Zero-risk, half a day, ends the "gates product with no gate on itself" exposure; prerequisite surface for P2/P6 checks. |
| Next release | **P2 + P3** (doctor + manifest/uninstaller), **P8** | One coherent installer/liveness release: manifest feeds doctor; doctor mechanizes the ACTIVATED leg and the staleness flag; P8 rides along. |
| v2.0 positioning window | **P4 + P5 + P6** (guard cards, postures, demo) | These are WS5 work items wearing different clothes — adoption surface for the public push. |
| Anytime | **P7** (testing-addendum template) | Half a day, closes a doctrinal gap, no dependencies. |

None of this touches the v2.0 hard gate (≥1 month live calibration history) — but P1 and P2
make that gate's *staleness* mechanically visible instead of a CLAUDE.md exhortation, which is
the same move the whole Playbook is built on.

---

## 6. Standing-requirement flag (unrelated to the GTM repo, raised per CLAUDE.md)

`docs/calibration/history.md` **still does not exist** as of 2026-07-09 — the calibration
scoreboard has never been seeded and the first live `run_calibration.py` run remains owed.
Every gate this analysis proposes to showcase is, per §13, a decaying asset with zero recorded
calibration. The v2.0 clock (≥1 month of live history) has not started. This needs a real
`claude` binary and budget — David's action in this repo.
