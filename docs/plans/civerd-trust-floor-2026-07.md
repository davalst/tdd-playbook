# CIVerd trust floor — diff-integrity + engine-owned planted-error probe (contract)

*Drafted from the tdd-playbook repo (CIVerd's first subject), 2026-07-27, for the CIVerd engine to
implement. Companion to the trust-posture decision: a sha256 pin on a gate script cannot anchor trust
against a repo-writing agent, because the script's exit code is a function of agent-authored callees
that change every commit (proven by this repo's own v1.15.0 case — `git rm
test_aaa_suites_via_main.py` reverts the suite to a pytest false-green while the gate script's bytes
never change). Trust must move to checks the ENGINE owns and the agent cannot weaken. These are two.*

## 0. The trust boundary this establishes

| Layer | Who owns it | Agent can weaken? |
|---|---|---|
| Decomposition (which checks run) + target paths | ENGINE (root-owned `/etc/civerd/repos.yml`) | No |
| **Diff-integrity baseline** (last-green inventory) | **ENGINE** (its ledger/state) | **No** |
| **Plant recipes** (what defect to inject) | **ENGINE** (its own library) | **No** |
| The code being judged (tests, guards, source) | repo | Yes — and that's the point |

The honest ceiling, stated plainly so nobody over-claims: CIVerd attests *"the engine's chosen checks
exited 0 for this SHA, and the engine's own integrity checks passed."* It never attests *"the code is
correct."* These two checks close the specific forge the pin cannot: **the agent reducing what is
verified.** A green means "the checks the engine ran, including checks the agent could not author
away, passed" — and the exit code, not any parsed stdout, is the only trust-bearing signal (see §3).

---

## 1. Diff-integrity check — "verification surface did not shrink vs the last green"

**Catches:** the `git rm the guard` / gut-the-tests / add-a-`@skip` forge — invisible to any check
*inside* the repo (the agent authored those), trivial for the engine to see on the **diff against the
last green**, which the agent cannot author away because the engine remembers it.

### Baseline (engine-owned)
The engine records, for each `(repo, branch)`, the **inventory** of the last SHA it signed GREEN:
- every test file path + its byte size + a cheap structural count (`def test_` count, `assert`/`check(`
  count, `@pytest.mark.skip`/`xfail`/`pytestmark`-skip count);
- the same for a small set of **integrity-critical** files if the repo declares them (§1.3), but the
  general rule needs no declaration — the baseline is simply "what was present and how big at last green."

Stored in engine state next to the ledger, root-owned. The agent has no write path to it.

### Signal (computed by the engine on the candidate SHA)
Diff the candidate's inventory against the baseline. Flag any of:
1. **Deletion** of a test file present at last green.
2. **Shrinkage** of a test file beyond a threshold (e.g. `> 25%` fewer bytes OR `> 10` fewer lines).
3. **Test-count / assertion-count regression** (fewer `def test_` or fewer `assert`/`check(` calls than
   baseline, suite-wide) — catches gutting a file's bodies while keeping its name and size padding.
4. **New skip markers** (`@pytest.mark.skip`/`skipif`, module `pytestmark` skip, `xfail`) not at baseline.

### Verdict (fail-closed, no agent-usable override)
- Any signal 1–4 → **integrity RED** for the SHA, UNLESS the engine holds a **ratification token** for
  exactly this `(SHA, file)` (§1.4). A reduction is not always malicious (a real refactor consolidates
  tests) — so the escape hatch exists, but it is **human, out-of-band, engine-recorded**, never a repo
  file or an agent action. This is the one operation whose signature IS the forge, so it costs a human
  ratification — the §6a "decide-or-park with an owner" rule applied to verification surface itself.
- **Bootstrap:** the first commit has no baseline → integrity is `INCONCLUSIVE`, recorded as such; the
  first trusted green must be **human-established** (David inspects and the engine snapshots the initial
  inventory). You cannot diff-integrity the genesis commit — say so, don't fake a pass.
- **Fail-closed on error:** cannot fetch the last-green SHA, cannot parse the tree, ambiguous baseline
  → RED/`integrity_unknown`, never a silent pass (mirrors `verify_verdict`'s `ledger_unavailable`).

### 1.3 Optional hard floor (recommended)
A short engine-owned list of files whose deletion/emptying is **always RED, never ratifiable** — the
meta-files that make every other check honest: the test-honesty guard, `conftest.py`, `pytest.ini`,
the hooks dir, the test-weakening guard, the registry validator. Deleting these is never a legitimate
refactor. Keep the list in root config, not the repo.

**Extended watchlist (2026-07-28 sweep — the verification-surface files beyond tests):** the
baseline inventory (§1) and the hard floor should also cover, for this repo:
`plugins/tdd-playbook/agents/*.md` (a SOFTENED verifier brief keeps its verdict lines while
losing its rules — between live calibrations nothing else sees the edit), `calibration/
scenarios.json` + `calibration/oracle-changes.md` + `corpus/approved/` (§2b),
`civerd-integrity.yml`, `check_scoreboard_integrity.py`, and `hooks/hooks.json`. Agent-brief
*changes* are ratifiable (briefs legitimately evolve); *deletion/emptying* is hard-floor RED.

### 1.5 guard_env check — "no silent kill switch" (2026-07-28 sweep)
**Catches:** the demotion hole. Guards resolve their mode from `TDD_PLAYBOOK_HOOK_*` env vars;
an agent that plants `TDD_PLAYBOOK_HOOK_TESTWEAKEN=off` in `.claude/settings*.json` demotes a
blocking guard for EVERY future session — persistently, silently, without touching a guard
file (so §1's inventory never fires). Local visibility exists (the `suppressed` yield event +
the installer doctor + a planted settings test), but only the ENGINE can make it a signed
signal the agent cannot suppress. The check, pure git + JSON, cheap enough for every SHA:
1. Diff `.claude/settings.json` / `.claude/settings.local.json` vs last green; any
   introduced/changed `TDD_PLAYBOOK_HOOK_*` env key → **ratifiable RED** (a demotion David
   approved gets a token; one nobody approved blocks).
2. Assert `hooks/hooks.json` still wires the engine-expected guard set (root-owned list —
   the same shape as the decomposition): a guard dropped from the wiring is RED.
Also closes the shell variant of H2 in composition: `diff_integrity`'s assertion-count
regression (§1 signal 3) catches a test gutted via `python -c`/heredoc — the write path is
irrelevant to a tree diff, which is exactly why this check must live engine-side.

### 1.4 Ratification token
`ratify <sha> <path> --reason "<why>"` written on the box over admin SSH (root-owned store). Re-verify
consumes it. Tokens are per-`(sha,path)`, single-use, and logged. Solo-dev volume is low; the friction
is the point — a test deletion that no human reviewed should not clear the gate.

### Composition
Diff-integrity is a **required check in the decomposition**, run BEFORE `tests` (a shrunk suite that
then "passes" is exactly the case this exists to stop). Its exit code joins the verdict like any other
check. It does not run repo tooling — pure git + a small structural scan the engine performs itself.

---

## 2. Engine-owned planted-error probe — "the suite CATCHES a known bug"

**Catches:** the deeper forge diff-integrity can't — a suite that keeps its size and shape but no
longer *asserts anything real* (assertions loosened to tautologies, oracles widened to always-match).
The §13 ungameable anchor: don't ask "do the tests pass" (agent-gameable), ask "do the tests CATCH a
defect the ENGINE chose" (not gameable — the agent didn't author the defect).

### Plant source (engine-owned — the load-bearing property)
The engine holds its OWN library of **plant recipes** — generic, language-aware mutations applied to
critical modules: negate a boolean/condition, drop a `sorted()`/`.strip()`, off-by-one a bound, return
a constant, delete a validation branch, swap `==`/`!=`. The agent never sees which recipe lands where.
The library **only grows and is sampled randomly per run** (co-evolution — the same discipline as this
repo's `calibration/author_plants.py`; a frozen, fully-disclosed plant set invites overfitting).

### Targets (repo-declared, engine-verifiable)
A small repo-side manifest the engine reads (paths only — no recipes):
```yaml
# civerd-integrity.yml (repo root) — critical modules whose suite MUST catch mutations
plant_targets:
  - path: plugins/tdd-playbook/bin/verify_verdict.py
  - path: plugins/tdd-playbook/bin/_ed25519_verify.py
  - path: plugins/tdd-playbook/bin/capability_registry.py
suite_cmd: "for t in plugins/tdd-playbook/tests/test_*.py; do python3 \"$t\" || exit 1; done"
```
The agent can shorten this list — but a module dropped from `plant_targets` is itself a **diff-integrity
signal** (§1: the manifest is in the baseline inventory), so shrinking coverage is caught by check 1.
The two checks interlock: #1 stops "reduce what's declared critical," #2 stops "keep it declared but
gut the assertions."

### Procedure (on a throwaway clone — the agent's tree is never touched)
For each target, for K sampled recipes:
1. apply the plant to the clone;
2. run `suite_cmd` (the engine's decomposition command, exit-code judged — §3);
3. record CAUGHT (suite went non-zero) or SURVIVED (suite stayed green);
4. revert the plant.

### Pass criterion (BLOCKING)
Every applied plant on a declared-critical module MUST be CAUGHT. **A survivor is a BLOCKING failure**
— the suite does not cover a defect it claims to (§13: "a planted error surviving to a clean verdict
is a blocking failure; fix the agent/suite, never the plant"). The engine records survivors with the
exact recipe+location so the gap is actionable, and marks the repo's green **not trustworthy for that
module** until the suite is strengthened and re-probed. It never weakens the plant to get green.

### Cadence (not every commit)
The probe mutates the tree and runs the full suite K times — too heavy per-commit. Run it:
- before the **first** trust of a repo/branch (establish the floor);
- on a **schedule** (weekly — the "monthly live probe" from the F4 brief, but tighter);
- on a **doer-model upgrade** (this repo's §13 rule: re-calibrate before trusting a stronger doer).
Between probe runs, per-commit trust rests on the decomposition + diff-integrity; the probe is the
periodic proof that the suite it trusts is not theater.

### Anti-gaming
Overfitting (a suite that catches exactly the known recipes while weak elsewhere) is countered by the
same three mechanisms this repo already uses: the recipe library GROWS, it is SAMPLED (not exhaustive-
disclosed), and survivors expand it (co-evolution). A suite that catches a broad, growing, sampled
mutation set is a genuinely strong suite — "gaming" it converges on actually writing good tests, which
is the win condition, not a loss.

### Reuse (don't reinvent)
This is `/mutate` + `planted-error-probe` from the Playbook, moved to the trusted side. The engine can
invoke the same mutation tooling the repo uses; the ONLY thing that must move engine-side is **choice
of plant + scope + reading the result** — because those are what the agent must not control.

---

## 2b. Calibration-integrity check — "the scoreboard the claims rest on was not forged" (v1.17)

**Catches:** the forge neither §1 nor §2 sees — the calibration SCOREBOARD itself. Every
calibration claim (recall, FP rate, the WS5.5 public numbers) rests on three artifacts a session
agent can write: `docs/calibration/history.md`, `calibration/corpus/approved/`, and the shipped
oracle regexes in `calibration/scenarios.json`. §1's inventory covers *test files*; none of these
are. An agent that edits a BLOCKING FAIL row green, deletes an inconvenient plant, or loosens a
`must_match` has weakened the verification surface without touching a test.

**Rules (deterministic, engine-side baseline = last green):**
1. `history.md` at baseline is a **byte-prefix** of the candidate (append-only — an edited,
   truncated, or deleted row is a forged scoreboard).
2. Every `corpus/approved/*.json` at baseline exists **byte-identical** ("the corpus only grows"
   becomes enforced, not aspirational; a bad plant is superseded by a new one, never edited).
3. **Directional oracle rule:** removing or replacing a baseline `must_match`/`must_not_match`
   regex, or removing a scenario, is RED **unless journaled in `calibration/oracle-changes.md`
   in text appended since the baseline**. Pure additions/tightenings always pass — a legitimate
   oracle tightening (the 2026-07 count-regex fix after a live false-fire) must always ship.
   The journal is itself append-only under rule 1, so it cannot retro-authorize. Engine-side,
   an unjournaled weakening may additionally be cleared by a §1.4 ratification token.

**Reference implementation:** `calibration/check_scoreboard_integrity.py` (stdlib-only) — exit
sentinels `0` clean · `2` integrity_red · `3` baseline-unreadable (fail closed). Locally it runs
in the release gate and the test suite against the previous release tag; the engine adapts it
with its root-owned baseline. **`check_scoreboard_integrity.py` joins the §1.3 never-ratifiable
hard floor** — the checker the agent it polices could otherwise delete.

**Honest limit:** this cannot prove a calibration run was *live* — the engine has no `claude`
binary by design, and a well-formed forged row appended by a local session survives these rules.
The controls for that residue are: append-only visibility (any history-touching commit is
inspectable in the signed verdict), and the fact that David runs the harness. Stated so the
floor is trusted for exactly what it delivers.

---

## 3. How these compose with the verdict (Fork 2: exit-code, not stdout)

Each check — `diff_integrity`, `calibration_integrity`, `guard_env`, `venv`, `deps`, `tests`,
`dryrun`, `registry`, `staleness`, and the
periodic `planted_probe` — is a **separate engine-run command whose EXIT CODE is the signal**.

> **Engine implementation note (verified 2026-07-28, against the engine source):** the shipped
> check names differ from this contract's working names — grep the engine for THESE:
> `integrity` (the §1.3 floor: declared meta-files exist, non-empty, non-symlink; exit 116),
> `integrity_baseline` (§1 diff-integrity, shrink-vs-last-green; exits 117/118/119),
> `planted_probe` (§2; exits 114 vacuous / 115 survivor — first live firing caught a real
> `capability_registry.py` gap, fixed at `2c350e1`). Ratification is a root-owned PIPELINE
> (`read_ratifications`, `/etc/civerd/ratifications`), not a check name. **Not yet built:**
> `calibration_integrity` (§2b) and `guard_env` (§1.5) — both tracked as dated registry debt. The
verdict's `checks[]` records each command's name + exit code (engine-owned decomposition), never a
`name=pass` string parsed out of attacker-controlled stdout. Stdout is captured only as a
**hard-truncated advisory blob** (cap it BEFORE the spool boundary) that never affects pass/fail — so
">64 KiB stdout" cannot erase a RED and attacker text cannot reach the signer's schema. New states are
**exit-code sentinels** (e.g. `2 = integrity_red`, `3 = planted_survivor`), not new schema fields.

Fail-closed everywhere (the amplifier fix): a check that raises persists an **error/RED verdict for the
SHA and marks it seen** — never re-poll into a crash-loop; spool rejection is a **RED, not a no-entry**.
A failing build must never be able to erase its own verdict.

---

## 4. What this repo hands over vs what the engine owns

- **Repo provides:** `civerd-integrity.yml` (critical-module paths + the real `suite_cmd`,
  **which since v1.21 is `sh scripts/civerd_gate.sh` — the ONE blessed entrypoint**: the
  plugins loop + the calibration harness. Probe run 2 (2026-07-28) proved the prose-loop
  era wrong three ways at once — pytest collects ~0 items from script-style suites, the
  loop never included calibration/, and the aaa-guard's harness path was wrong AND inert
  under `python3` — so the gate false-greened every calibration-side module while its 110
  checks sat unexecuted. The engine's `tests` check and `planted_probe` MUST exec this
  script, nothing else) and the `check_scoreboard_integrity.py` reference implementation
  (§2b). Nothing else.
- **Engine owns:** the last-green baseline, the plant-recipe library, the ratification store, the
  hard-floor list, and the decomposition — all root-owned, no agent write path.
- **This repo will also provide** (on request) a reference `planted-error-probe` recipe set and a
  `diff_integrity.py` reference implementation the engine can adapt, so CIVerd has runnable starting
  points rather than only a spec.

## 5. Honest limits (what these still do NOT catch)
- A suite that is genuinely weak *and always was* (no reduction to flag, catches the sampled plants by
  luck) — mitigated only by growing the recipe library over time.
- Source correctness the tests never spec'd — out of scope for any CI; that's what review is for.
- A compromised ENGINE — a different threat, handled by the runner/signer privilege split and the
  signed-verdict chain, not here.
These are stated so the floor is trusted for exactly what it delivers and no more.
```
