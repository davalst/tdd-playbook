# Owner Control & Simplification Plan — 2026-08-09

*Rev 3 — release certification deleted outright rather than replaced with local signing.
David's challenge: if CIVerd produced no offsetting catch, keeping a signing ceremony at all is
the same cost with a smaller hat on. Correct — and Phase 1a had been building an override for a
wall that Phase 5 demolishes.*

**Goal:** David holds every switch, the system can be reset or removed at will, and what
remains is only the parts that have been *measured* to earn their cost.

**Non-goal:** letting the AI cook the books. Preserved throughout. Rev 3 achieves it by
subtraction rather than cryptography — with no verdict in the release path there is nothing to
forge, and what authorizes a release is David tagging it. The change is from *nobody has power*
to *the owner has power*.

---

## 0. Why this plan exists

Three symptoms, one cause.

| Symptom | Where it bites |
|---|---|
| Can't reset | State lives in 4 places that don't know about each other |
| Can't release | `release_verify.py` refuses without a CIVerd verdict; no human override |
| Can't keep up | Obligations grew 14 → 47 in four days; nothing retires |

All three are the same axiom: **nothing can be removed.** The corpus only grows, history is
append-only, the registry only grows, gate surfaces need a journal entry to delete, debts
accumulate. Applied to machine state you get "can't reset"; applied to release authority you
get "can't ship"; applied to obligations you get "drowning".

The fix is one principle, applied three times: **auditability instead of impossibility.**

### Measured facts this plan is built on

- **Development is not blocked.** A gate-surface edit (`SKILL.md`, new `##` section) with the
  full gate run: GREEN, 30/30 stages. Verified 2026-08-09.
- **Guards are not active in this repo.** No `.claude/settings.json`. Plugin-only host.
- **One wall exists**, and it is exactly one:
  `RELEASE REFUSED [ledger_unavailable] — no releasable verdict for 9b97779`.
- **A fresh clone fails its own gate.** Shallow clone → `ledger UNMEASURED` → RED, with no
  message telling you to `git fetch --unshallow --tags`. This is the default new-user and
  default CI experience.
- **Cost:** 11,457 lines of machinery + 8,171 lines of its tests vs 2,299 lines of actual
  doctrine — **8.5:1 apparatus-to-product**. Calibration is 40 scenarios × 3 reps = **120
  headless agent runs per weekly cycle**. `CLAUDE.md` is 2,176 words prepended to every session.

---

## 1. The evidence: what is the apparatus actually buying?

### 1a. Gates — what catches defects in *code*

From `docs/calibration/gate_yield.md`, 6 cycles:

| gate | blocks | warns | overrides | reading |
|---|---|---|---|---|
| `testweaken` | 4 | 0 | **0** | **Earns its keep.** Every block stood. |
| `testlock` | 17 | 0 | **20** | Overridden *more often than it stands*. |
| `exitcode` | 0 | 24 | 0 | Never blocked anything. |
| `overmock` | 0 | 3 | 0 | Never blocked anything. |
| `exhaustive` | 0 | 2 | 0 | Never blocked anything. |
| `flaky` | 0 | 1 | 0 | Never blocked anything. |
| `redlock` | 0 | 1 | 0 | Never blocked anything. |

**One gate works. One is miscalibrated. Five have never caught anything** — 31 warnings, zero
blocks, across all recorded history.

`overrides` is defined by that file's own header as *"journaled unlocks adjudicating a block as
false-positive"* — so `testlock`'s 20 are adjudicated false positives, not routine unlocks.

`guard_response.md`, the v1.28 mechanism built to distinguish compliance from routing-around:
**7 blocks, 0 accounted, 7 unaccounted.** A 0% response rate.

### 1b. The two test guards are not the same guard

This matters for the `testlock` decision:

- **`test_weakening_guard.py`** (`testweaken`) — *"flag edits that WEAKEN a test... INTEGRITY
  hook: defaults to BLOCK."* The direct anti-rewriting guard. Clean record.
- **`test_lock_guard.py`** (`testlock`) — enforces the *workflow* lock across four surfaces and
  both the structured-edit and shell channels while a lock is active. Far wider surface, hence
  the false positives.
- **`snapshot_guard.py`** also stays blocking — blind snapshot re-approval is the other cheap
  way to fake a passing test.

Demoting `testlock` costs the **workflow lock**, not the **weakening guard**.

### 1c. The value chain, layer by layer

| layer | what it verifies | recorded catches |
|---|---|---|
| Gates | defects in real code | `testweaken`: 4. Everything else: 0 |
| Calibration | defects in the gates/agents | small and real (e.g. the `vacuous-mutation-scope` BLOCKING FAIL → mutation-runner vacuity fix) |
| CIVerd signing/tagging | bad releases | **none recorded** |
| Improvement ledger | whether changes to the above helped | **3 scored HITs, ever** |

The ledger's entire scored history is three entries: claims-verifier 2/3→3/3, tripwire-auditor
1/3→3/3, control-parked-deferral 0/3→3/3. **All three are improvements to verifier accuracy on
planted scenarios. None is a defect in real code.** It also records a revert cycle where the
plant-immutability rule forced restoring known false positives — its own note: *"its false FAILs
return with it — the cost of the immutability rule... paid visibly rather than argued away."*

### 1d. The natural experiment, and the measurement that was never run

**v1.29, v1.30 and v1.31 all shipped untagged and uncertified, and are in use.** The absence of
CIVerd certification changed nothing observable. That is the clearest available evidence about
what the signing ceremony buys.

And the decisive one: the system contains an instrument designed to answer *"does this improve
outcomes?"* — the **lift diagnostic read**. `quarterly.md` contains one row: a HACK_CATALOG
refresh. The lift read is marked *"once unblocked by the holdout split + stub-freeze"* and
*"once funded."*

**The measurement that would tell us whether any of this improves code has never been run.**

### 1e. The shape of the problem

The layers verify **each other**, not the code. Calibration verifies the gates; the ledger
verifies the calibration; CIVerd certifies releases of the thing that verifies the calibration.
Four layers deep, and at the bottom sits one gate with four confirmed catches.

*Caveat, stated because this plan argues from it:* 6 cycles is a small sample, mostly one
operator. It is suggestive, not conclusive. It is also the only evidence there is, the
instrument built to produce better evidence was never funded, and the direction is not subtle.

---

## Phase 0 — Insurance (today, ~15 minutes, nothing destructive)

Do this **before any other decision**, including a decision to walk away.

1. **Back up the CIVerd signing key off-box.** Rev 3: this is now **purely archival** — with the
   release gate deleted, nothing operational depends on it. Do it anyway, because it takes two
   minutes, this is the last moment it is possible, and an unverifiable archive is worse than no
   archive. Those verdicts certify that a gate run happened at a SHA, for gates this plan
   deletes.
2. **Archive the evidence** — cheap, not sacred:
   `tar czf ~/tdd-playbook-evidence-2026-08-09.tgz docs/calibration/ calibration/corpus/ docs/reviews/`
3. **Make the three stuck releases addressable.** Local annotated tags for v1.29.0/v1.30.0/
   v1.31.0. Under rev 3 these are simply the releases — no certification step follows.
4. **Record the VPS state** you'd need to rebuild it (`repos.yml`, units, tailnet config).

**Exit:** nothing can be lost irrecoverably from here on.

---

## Phase 1 — Get the switch (a couple of hours; rev 3 made this smaller)

Ends the jam permanently. Buildable **today** — the gate is green and nothing blocks it.

### 1a. Remove the wall — do not build a key past it

**Rev 3 correction.** Earlier revisions had David generate an Ed25519 keypair and build a
`release_verify.py --authorize` path. That was wrong: it builds an override for a requirement
Phase 5 deletes. A key for a door being taken off its hinges.

Instead:

- **Drop the CIVerd verdict requirement from the release path.** Releasing becomes: blessed gate
  green → bump version → `git tag` → push. What every other project does.
- **`release_verify.py` is retired** along with the tag ceremony, the async verdict polling and
  the `ledger_unavailable` refusal that has been the only real wall.
- **`verify_verdict.py` is kept but unwired** — stdlib-only, self-contained, and the sole means
  of checking historical signed verdicts. It costs nothing at rest and it is the only way past
  bundles stay readable.
- **If third-party authenticity ever matters** (the plugin is public and vendors into other
  repos), `git tag -s` is built into git, needs one flag, and requires no service, no issuer
  key, no verdict ledger.

**Nothing here weakens the model's inability to forge a verdict** — it removes the verdict from
the release path entirely, so there is nothing to forge. What stops a bad release is the same
thing that stops one in any repo: David reviewing what gets tagged.

**Ships the three stuck releases immediately**, with no new machinery at all.

### 1b. Break-glass for the guards

- `TDD_PLAYBOOK_BREAK_GLASS="<reason>"` demotes every blocking gate to warn for the session,
  prints a loud banner, journals the reason.
- Supersedes the per-gate `TDD_PLAYBOOK_HOOK_<NAME>=warn` knobs with one obvious switch.

**Exit:** no configuration of failures can jam you again. The three stuck releases ship as
ordinary tags.

---

## Phase 2 — Reset (half a day)

### 2a. `tdd reset`

One command over all four state locations, **dry-run by default**, printing every path first:

| location | contents |
|---|---|
| repo `.claude/` | `settings.json`, `settings.local.json`, `tdd-lock.json`, `tdd-lock-journal.jsonl`, `.tdd-playbook-version`, `hooks/scripts/` |
| git common dir | `tdd-playbook/active-lock`, `gate-runs/`, `events.jsonl` |
| `~/.claude/plugins/cache` | marketplace plugin install |
| capture store | `~/.claude/deliberation/ENABLED` |

Scopes: `--repo`, `--machine`, `--plugin`, `--all`. Evidence directories are out of scope
except under a separate, loud, journaled `--burn-evidence`.

### 2b. `tdd uninstall`

True inverse of `install_into_repo.py`: removes playbook hooks, leaves non-playbook hooks
untouched, drops vendored `.claude/bin/`, leaves the repo as if never installed.

### 2c. `tdd doctor` that repairs

Every failure line carries the command that fixes it. **First case: the shallow clone** —
detect, print `git fetch --unshallow --tags`, offer `--fix`.

### 2d. The test you spent three days doing by hand

`install → reset → install` into a scratch repo, asserting a byte-identical end state.

**Exit:** nuke and rebuild any machine state on demand, repeatably.

---

## Phase 3 — Delete by evidence (the main event)

### Guards — DECIDED

- **`testweaken` stays BLOCKING.** 4 blocks, 0 overrides. The one unambiguous winner.
- **`snapshot_guard` stays BLOCKING.** Covers the other cheap fake-a-pass route.
- **`testlock` → WARN, keep logging.** Wrong more often than right at 17/20. Warn mode keeps
  the yield rows accruing so the decision to fix-or-delete can be made on more data later.
  Tests are still defended from rewriting by `testweaken`.
- **`exitcode`, `overmock`, `exhaustive`, `flaky`, `redlock` → OFF by default**, opt-in.
  31 warnings, zero catches.
- **Retire `guard_note.py` / `guard_response.md`.** 0-of-7 accounted; it measures a behaviour no
  operator was ever going to perform by hand.

### Calibration — DECIDED: opt-in and reactive

Stays in the repo as **vendor-only, opt-in** tooling. **No weekly clock.** Its residual value is
authoring a plant *when a verifier actually misbehaves* — reactive, not a scheduled 120-agent
run. Leaves the release gate; leaves `CLAUDE.md`'s standing requirements.

### Measurement clocks — DECIDED: delete

`ledger.py` + `ledger.md`, `quarterly.md`, `check_staleness.py` and their gate stages all go.
They measure a system this plan deletes, and the one that would have mattered — the lift read —
was never funded and never ran.

### Registry, ledgers, debts

47 debts, most self-referential (debts about the debt system; calibration owed to gate surfaces
being deleted here). Sweep: **anything whose subject is deleted in this phase closes as
obsolete.** The registry survives only if it answers *"what did I build that never got wired"*
for real features — the question that motivated it.

### Doctrine

`SKILL.md` (1,048 lines) and `CLAUDE.md` (2,176 words, every session) shrink to what remains.
Target: **SKILL.md under 300 lines, CLAUDE.md under 400 words.** Everything cut moves to
reference docs read on demand.

### Expected outcome

Roughly a **90% cut of the apparatus**, keeping the parts with evidence behind them.
Apparatus-to-product drops from 8.5:1 toward ~2:1. Per-feature token cost loses most of the
10–20× multiplier, because the adversary chain (`/edge` → `/mutate` → `/probe` →
`/integration-audit` → review records) becomes **opt-in per change** rather than mandatory.

**Deletion is reversible** — it is all in git, and Phase 0 archived the rest.

---

## Phase 4 — The new-user path

- **One command install** that works on a shallow clone, with no VPS, no CIVerd, no calibration
  history, no corpus. A dev with mid-flight projects gets value from the first commit.
- **Default profile:** `testweaken` + `snapshot_guard` blocking, `testlock` warning, red-first
  discipline, TEST-LOCK available. Everything else opt-in.
- **`tdd reset` and `tdd uninstall` on the front page.** The ability to leave is what makes
  adopting safe.
- **Version-update path tested** — install v_old → update to v_new → verify, as a test.

---

## Phase 5 — CIVerd — DECIDED: retire entirely (rev 3: no local signing either)

Drop the VPS, the tailnet, the heartbeat, the async verdict polling, the tag ceremony, the
release gate and the signing ceremony. Keep `verify_verdict.py` unwired so historical bundles
stay checkable.

**Rev 2 said "retire to local signing." Rev 3 deletes that too**, on David's challenge: if the
apparatus produced no offsetting catch, a signing ceremony with a smaller hat is the same cost.

Signing exists to make a claim credible to a **third party**. Here the issuer, the operator and
the only relying party are the same person, so a signature verifies something already known.
Three releases shipped without it with no observable consequence. `git tag -s` covers
distribution authenticity for free if it ever matters — a different claim (*this artifact came
from me*) from the one CIVerd made (*a gate run happened at this SHA*), and the only one with a
plausible audience.

*Reversible:* the verifier, the key format and the cross-validation corpus stay in the repo.

---

## Order, effort, and what unblocks what

| Phase | Effort | Gives you |
|---|---|---|
| 0 — Insurance | 15 min | Nothing irreversible can be lost |
| 1 — The switch | ~2 hrs | Jam ends permanently; 3 releases ship |
| 2 — Reset | half day | Nuke/rebuild on demand; new-user sim automated |
| 3 — Delete by evidence | 1–2 days | Noise stops; token burn drops ~90% of apparatus |
| 4 — New-user path | half day | Adoption is real |
| 5 — CIVerd retire | ~2 hrs | VPS, tailnet and signing burden all end |

**Phases 0–2 are ~1 day and give you full control.** Phase 3 is where the relief lands. Stop
after Phase 2 and you still hold every switch.

## Remaining open decisions

Most of the earlier list is now decided. What's left:

1. **Reset scope** — downstream repos only, or this repo's own state too? *(Recommend: both.)*
2. **The registry** — keep for real dark-feature detection, or delete with the rest?
   *(Recommend: keep, heavily trimmed. "What did I build that never got wired" is a real
   question that predates all this machinery.)*
3. **v2.0's "≥1 month live calibration" gate** — *(Recommend: drop. It gates shipping on an
   activity this plan makes opt-in.)*
4. **What to do with `history.md` and the corpus long-term** — archived in Phase 0 either way.
   *(Recommend: keep in-repo, unclocked. They cost nothing at rest.)*

## What is explicitly NOT in this plan

- **No rollback to a pre-CIVerd playbook.** Measured: the current version does not block
  development. A rollback costs the seam rule, dataflow sweeps, guard calibration, host
  adapters, the gate runner and the review ledger, plus a 20-version forward-port — to solve
  one refusal in one script.
- **No wiping evidence before Phase 0's archive.**
- **No path by which the model can self-certify a release.** Rev 3 achieves this by deletion
  rather than by cryptography: with no verdict in the release path there is nothing to forge,
  and what authorizes a release is David tagging it. This is the one property the plan is
  careful never to trade away, and it is now enforced by there being nothing to attack.
