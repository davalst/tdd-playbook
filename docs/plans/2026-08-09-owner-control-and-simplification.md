# Owner Control & Simplification Plan — 2026-08-09

**Goal:** David holds every switch, the system can be reset or removed at will, and what
remains is only the parts that have been *measured* to earn their cost.

**Non-goal:** letting the AI cook the books. Preserved throughout — the model never holds a
signing key. The change is from *nobody has power* to *the owner has power, and every use of
it is recorded*.

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

### The yield data (`docs/calibration/gate_yield.md`, 6 cycles)

| gate | blocks | warns | overrides | reading |
|---|---|---|---|---|
| `testweaken` | 4 | 0 | **0** | **Earns its keep.** Every block stood. |
| `testlock` | 17 | 0 | **20** | Fires constantly, overridden *more often than it stands*. |
| `exitcode` | 0 | 24 | 0 | Never blocked anything. Pure noise. |
| `overmock` | 0 | 3 | 0 | Never blocked anything. |
| `exhaustive` | 0 | 2 | 0 | Never blocked anything. |
| `flaky` | 0 | 1 | 0 | Never blocked anything. |
| `redlock` | 0 | 1 | 0 | Never blocked anything. |

**One gate works. One is miscalibrated. Five have never caught anything** — 31 warnings, zero
blocks, across all recorded history.

And `guard_response.md`, the v1.28 mechanism built to tell compliance from routing-around:
**7 blocks, 0 accounted, 7 unaccounted.** A 0% response rate. It is not working.

*Caveat, stated because this plan otherwise argues from it:* 6 cycles is a small sample and
mostly one operator. It is suggestive, not conclusive. It is also the only evidence there is,
and the direction is not subtle.

---

## Phase 0 — Insurance (today, ~15 minutes, nothing destructive)

Do this **before any other decision**, including a decision to walk away. It is cheap and the
omissions are irreversible.

1. **Back up the CIVerd signing key off-box.**
   `civerd-signer`'s private key, `0400` on the VPS, "never left the box." If the VPS dies or
   is wiped without this, **every historical signed verdict becomes permanently
   unverifiable.** Copy it to your password manager. Two minutes.
2. **Archive the evidence** — not because it's sacred (it isn't; a new user has none of it and
   still gets value), but because a tarball costs nothing:
   `tar czf ~/tdd-playbook-evidence-2026-08-09.tgz docs/calibration/ calibration/corpus/ docs/reviews/`
3. **Make the three stuck releases addressable.** v1.29.0, v1.30.0 and v1.31.0 are shipped on
   `main` and untagged. Local annotated tags now; they become properly owner-authorized in
   Phase 1.
4. **Record the VPS state** you'd need to rebuild it (`repos.yml`, unit files, tailnet config)
   before any wipe.

**Exit:** nothing can be lost irrecoverably from here on.

---

## Phase 1 — Get the switch (half a day)

Ends the jam permanently. Everything here is buildable **today** — the gate is green and
nothing blocks it.

### 1a. Owner authorization in `release_verify.py`

- You generate an Ed25519 keypair. **Private key never touches the repo, the VPS, or any
  machine the model can read.** Public key vendored beside the CIVerd issuer key.
- New path: `release_verify.py --authorize --reason "<why>"`, requiring a valid owner
  signature over the release SHA. Refuses without one.
- The release record gains **provenance**: `engine-verified` (CIVerd signed) or
  `owner-authorized` (you signed, engine unavailable/bypassed, reason recorded).
- `current-state.md` reports the split: *N engine-verified, M owner-authorized*, and every
  owner-authorized release is enumerable forever.

This is v1.30's own doctrine — *a verification result is a CLAIM and carries its SCOPE* —
applied to CIVerd, which is the one place you never applied it. Two honest claims of different
strength beats one binary that deadlocks.

**The model still cannot forge either.** No CIVerd private key, no owner private key.

### 1b. Break-glass for the guards

- `TDD_PLAYBOOK_BREAK_GLASS="<reason>"` demotes every blocking gate to warn for that session,
  prints a loud banner, and journals the reason.
- The pattern already half-exists (`TDD_PLAYBOOK_HOOK_<NAME>=warn`, `HOOK_MODE`). This makes it
  global, documented, and one obvious thing instead of a knob per gate.

**Exit:** no configuration of failures can jam you again. Ship the three stuck releases as
owner-authorized.

---

## Phase 2 — Reset (half a day)

### 2a. `tdd reset`

One command over all four state locations, **dry-run by default**, printing every path before
touching anything:

| location | contents |
|---|---|
| repo `.claude/` | `settings.json`, `settings.local.json`, `tdd-lock.json`, `tdd-lock-journal.jsonl`, `.tdd-playbook-version`, `hooks/scripts/` |
| git common dir | `tdd-playbook/active-lock`, `gate-runs/`, `events.jsonl` |
| `~/.claude/plugins/cache` | marketplace plugin install |
| capture store | `~/.claude/deliberation/ENABLED` |

Scopes: `--repo`, `--machine`, `--plugin`, `--all`. **Never touches `history.md`, the corpus,
or reviews** — with `--burn-evidence` as a separate, loud, journaled flag, because you're the
owner and "I can never reset it" is the complaint we're fixing.

### 2b. `tdd uninstall`

True inverse of `install_into_repo.py`: removes playbook hooks, restores non-playbook hooks
untouched, drops vendored `.claude/bin/`, leaves the repo as if it had never been installed.

### 2c. `tdd doctor` that repairs

Every failure line carries the command that fixes it. **First case: the shallow clone.** Detect
it, print `git fetch --unshallow --tags`, or offer `--fix` to run it.

### 2d. The test you spent three days doing by hand

`install → reset → install` into a scratch repo, asserting a byte-identical end state. Your
new-user simulation becomes a test that runs in seconds.

**Exit:** you can nuke and rebuild any machine state on demand, repeatably.

---

## Phase 3 — Delete by evidence (the main event)

Triage driven by the yield table, not by taste.

### Guards

- **KEEP `testweaken`** — 4 blocks, 0 overrides. The one unambiguous winner.
- **`testlock`: recalibrate or demote.** 17 blocks / 20 overrides means it is wrong more often
  than right *as measured by your own adjudications*. Either fix the false-positive classes
  (v1.28 found three and there are clearly more) or demote it to warn. Do not leave it blocking
  at this ratio — it is the single largest source of daily friction.
- **Demote the five that have never blocked** (`exitcode`, `overmock`, `exhaustive`, `flaky`,
  `redlock`) to **off by default**, available opt-in. 31 warnings and zero catches is a
  notification budget spent for nothing.
- **Retire `guard_note.py` / `guard_response.md`.** 0-of-7 accounted. It measures a behaviour
  the operator was never going to perform by hand.

### Calibration apparatus → opt-in vendor tooling

120 agent runs weekly, plus manual adjudication of every row, for a product with one user. It
stays in the repo as a **vendor-only, opt-in** tool. It leaves the release gate, leaves
`CLAUDE.md`'s standing requirements, and stops generating staleness obligations. `check_staleness`
becomes informational.

### Registry, ledgers, debts

47 debts, most self-referential (debts about the debt system, calibration owed to gate surfaces
whose gates are being deleted here). Sweep: **anything whose subject is deleted in this phase is
closed as obsolete, not carried.** The registry survives only if it is answering "what did I
build that never got wired" for *real features* — which is the question that motivated it.

### Doctrine

`SKILL.md` (1,048 lines) and `CLAUDE.md` (2,176 words, every session) shrink to what remains.
Rough target: **SKILL.md under 300 lines, CLAUDE.md under 400 words.** Everything cut moves to
reference docs the model reads only on demand.

### Expected outcome

Apparatus-to-product drops from 8.5:1 toward roughly 2:1. Per-feature token cost drops by most
of the 10–20× multiplier, because the adversary-agent dispatch chain
(`/edge` → `/mutate` → `/probe` → `/integration-audit` → review records) becomes **opt-in per
change** rather than mandatory per feature.

**Deletion is reversible** — it is all in git, and Phase 0 archived the rest. Anything cut can
come back if the evidence later says it should.

---

## Phase 4 — The new-user path

The thing you have been trying to simulate for three days becomes the supported path.

- **One command install** that works on a shallow clone, with no VPS, no CIVerd, no calibration
  history, no corpus. A dev with mid-flight projects adopts it and gets value from the first
  commit.
- **Default profile = the gates that earn their keep** (`testweaken`, `testlock` if
  recalibrated, TEST-LOCK discipline, red-first). Everything else opt-in.
- **`tdd reset` and `tdd uninstall` documented on the front page**, not buried. The ability to
  leave is a feature; it is what makes adopting safe.
- **Version-update path tested** — install v_old → update to v_new → verify, as a test.

---

## Phase 5 — The CIVerd decision (explicit, deferred until here)

With Phase 1 done, CIVerd is no longer load-bearing and you can decide it calmly.

- **Option A — keep it, optional.** Signed verdicts stay the strong claim for releases you care
  about; owner-authorization covers the rest. VPS stays.
- **Option B — retire to local signing.** You sign releases; drop the VPS, the tailnet, the
  heartbeat, the async polling and the whole availability coupling. Keeps the verifier and the
  provenance record.
- **Option C — wipe and rebuild** on the simplified design, if the VPS itself is a mess.

**Recommendation: B**, unless the signed-verdict property is doing work for someone other than
you. A signing service exists to make a claim credible to a *third party*; today the issuer,
the operator and the sole relying party are all you. Decide after Phase 1, when it is a
preference rather than a jam.

---

## Order, effort, and what unblocks what

| Phase | Effort | Gives you |
|---|---|---|
| 0 — Insurance | 15 min | Nothing irreversible can be lost |
| 1 — The switch | half day | Jam ends permanently; 3 releases ship |
| 2 — Reset | half day | Nuke/rebuild on demand; new-user sim automated |
| 3 — Delete by evidence | 1–2 days | Noise stops; token burn drops |
| 4 — New-user path | half day | Adoption is real |
| 5 — CIVerd | decision | VPS burden ends or is chosen |

**Phases 0–2 are ~1 day and give you full control.** Phase 3 is where the relief actually
lands. If you stop after Phase 2, you still hold every switch — which is the thing you asked
for in the first place.

## Open decisions for David

1. **Reset scope** — downstream repos only, or this repo's own state too? *(Recommend: both.)*
2. **`testlock`** — recalibrate, or demote to warn now and revisit? *(Recommend: demote now,
   revisit with data. It is the main daily friction.)*
3. **Calibration** — opt-in vendor tooling as above, or delete outright? *(Recommend: opt-in.
   Cost falls to zero when unused, and the co-evolution idea is genuinely good — it just cannot
   run weekly against one person.)*
4. **CIVerd** — A, B, or C.
5. **v2.0's "≥1 month live calibration" gate** — keep, or drop as self-imposed? *(Recommend:
   drop. It gates shipping on an activity this plan makes opt-in.)*

## What is explicitly NOT in this plan

- **No rollback to a pre-CIVerd playbook.** Measured today: the current version does not block
  development. A rollback would cost the seam rule, dataflow sweeps, guard calibration, host
  adapters, the gate runner and the review ledger, then demand a 20-version forward-port — to
  solve a problem that is one refusal in one script.
- **No wiping evidence before Phase 0's archive.**
- **No removal of the model's inability to forge a verdict.** That property survives every
  phase intact.
