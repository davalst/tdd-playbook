# The Readable Surface — an R&D release

**v1.33.1** (hotfix, today) · **v1.34.0** (the experiment)
**Slug on approval:** `docs/plans/gated/2026-08-12-readable-surface.md`

---

## Context — and what changed after review

David can't read Python. He plays CTO, CISO, head of QA, ops and product simultaneously, through AI. Two things are missing and they are different: **he doesn't know all the questions to ask** (hence the inventory), and **he doesn't know what deterministic data exists to answer them** (hence the surface). Adversaries can answer the questions — but 17 of the 42 inventory rows route to agents that don't exist.

Codex and Cheliped both reviewed the previous draft. **Both were right that it was over-scoped, and both mis-framed what it is.** They evaluated a governance subsystem — routing tables, exposure ledgers, retirement journals — and asked for proof before shipping. That proof cannot exist yet, because the thing being proven is whether David gets value from this at all.

This is R&D. The correct response is not to shrink the *experiment* (my first mistake) or to build the *apparatus* (my second). It is to build the smallest thing that can actually be used, and instrument it so the next decision is made on data.

**So the governance layer is DROPPED, not deferred behind machinery:** no routing table, no exposure ledger, no route plants, no demotion journal. David picks which adversary to dispatch by reading the surface — which is what he says he'd do manually anyway. Automating that choice before knowing which questions pay off is the premature half. The usage record (D5) is what would later justify building it.

---

## Repo-local conventions (layered on the universal floor)

- **No pytest.** Self-contained stdlib suites, local `check(name, cond, detail)` counter, `main()` ending `assert not _results["fail"]`. **The floor's `@pytest.mark.*` markers do not apply.**
- **One blessed gate:** `sh scripts/civerd_gate.sh`, never piped. New suites auto-glob, but `acknowledged_roster_sha256` pins the roster and **the refusal message printing the sha is the only affordance**.
- **Planted input + paired clean control**, `# PLANT:` / `# CONTROL:`. Boundary pins assert on the **violation string**, never a bare exit code.
- Stdlib-only under `bin/`. `_debt.py` is the one debt shape; `expires == today` is due, not expired.
- **Gate surfaces** additions are free; removals need `calibration/gate-changes.md`. This is additions-only.
- **Agents:** `model: opus` required on judgment verifiers; no `Edit`; two **forced verdict lines** — calibration oracles anchor on them.
- **Parity is mechanical**, and `test_host_parity.py:174-175` counts are hand-pinned on purpose.
- **Vendoring is by whole tree**; nothing outside `plugins/tdd-playbook/` vendors.
- **David tags.** No script creates a tag.

---

## Spec integrity

### Assumptions

1. **The reader cannot fall back to source.** The surface must be **pointable**, not complete. An omission is recoverable; a wrong statement is not.
2. **Roles carry loss functions, not detection capability.** A role label changes vocabulary and ordering; what it carries is what it *weights*. This is why four agents, not one "multi-role reviewer" — and why each brief must state what it **de-prioritises**.
3. **The 42 rows are unvalidated, and that is the point of the experiment.** Both reviewers flagged this as a risk to build machinery on. Correct — which is why no machinery is built on them. The usage record tells us which rows earn their keep.

### Readings

- **Followed:** a comprehension instrument that tells David what exists and what to worry about, so he can dispatch the right adversary himself.
- **Rejected — a new gate.** Prose never gates.
- **Rejected — automated routing in this release.** It presumes answers the experiment hasn't produced, and it was the source of every contradiction the reviewers found.

### Reviewer findings — dispositions

| Finding | Disposition |
|---|---|
| **Codex 1 — `R-CONSUMER` is underspecified.** The registry stores prose (`"David, reading the check mark…"`), not typed references. A nominal rule over prose either fails valid entries or needs an allowlist that makes it weak. | **ACCEPTED — DROPPED from this plan.** This is the "keying on a proxy" failure and Codex caught it. The real gap (a fabricated consumer passes `validate` today) is recorded as a finding needing a **typed consumer schema** (`kind: capability\|file\|human\|external` + a resolver per kind) designed before anything is enforced. Not shipped as prose-matching. |
| **Codex 2 — D5 measures nothing without a producer.** `/readable` is Markdown; it can't log. | **ACCEPTED, and specified.** The producer is **`readable_surface.py` itself** — an executable bin that logs its own invocation. The command is a prompt that runs it. If an agent narrates without running the bin, nothing logs, which is correct: the metric is "the facts tool was used." Tested through the **real CLI path**, not a synthetic event. |
| **Codex 3 — D6/D8 contradict the arming model.** | **DISSOLVED.** No routing in this release. |
| **Codex 4 — unrepresented host-parity exception.** | **DISSOLVED.** The inventory is **not vendored**. It lives at `docs/adversary-scenario-inventory.md` in this repo. No `reference/` tree, no `COPY_TREES` change, no parity family question. `/readable` degrades gracefully where the inventory is absent — a planted test covers it. |
| **Codex 5 / Cheli — far too large.** | **ACCEPTED.** Ten deliverables → one hotfix + five. |
| **Cheli 1 — D0 is a live defect trapped behind ten deliverables.** | **ACCEPTED.** D0(a) ships **today as v1.33.1**, standalone. |
| **Cheli 2 — the plan hasn't met its own review standard.** | **ACCEPTED as a precondition, not a first step.** The second fresh-context adversary pass runs **before any code**, and its findings come back to you before implementation starts. |
| **Cheli 3 — four `model: opus` agents with no cost model.** | **ACCEPTED, and the premise is wrong — numbers below.** |
| **Cheli 4 — "15 lines" undersells the migration.** | **ACCEPTED, specified below.** |
| **Cheli 5 — parity debt cliff.** | **ACCEPTED, and it needs your decision — see the open question.** |

### Round 2 — both reviewers re-read the R&D draft

Cheli: **approve with two conditions**, all three earlier blockers verified resolved (and it withdrew blocker 3 — the opus/haiku premise was wrong). Codex: **approve H1/v1.33.1**, four issues on v1.34.0. I verified each technical claim myself rather than accepting it:

| Finding | Verified? | Disposition |
|---|---|---|
| **Codex 2 — the 8-column migration crashes consumers.** `parse_md_rows` returns fixed 7-tuples; `:313` and `:432` destructure exactly seven. | **CONFIRMED, and worse than stated** — the parser is *shared across two record types* (gate + dataflow sweep, per the comment at `:426-429`), so widening one silently widens the other, where the cell is meaningless. Plus a documented latent `None`-vs-`int` sort hazard. | **Design changed: a fourth table, not an 8th column.** See D5. |
| **Codex 1 — D5 can't record what it promises;** `os.remove` drains the raw log, so `scenario_id`/`rows_surfaced` vanish. | **CONFIRMED** (`:290`). | **FIXED by the same redesign** — a purpose-built table keeps them durably, which the aggregate-column design could not. |
| **Codex 3 — "both hosts" is false for telemetry.** Both producer and consumer default to `.claude/playbook-yield.jsonl`. | **CONFIRMED** — `_common.py:212`, `gate_yield.py:87-89`; only `TDD_PLAYBOOK_YIELD_LOG` overrides. | **ACCEPTED: the experiment is Claude-only, stated.** Host-neutral telemetry is a real migration and is not what this tests. |
| **Codex 4 — D1 is too much; add adversaries as usage reveals gaps.** | Reasoning holds for future rows; not for the 17 already dark. | **PARTIALLY ACCEPTED — the bar moves, not the scope.** Live calibration of the four new pairs becomes a **release precondition**. Full argument in D1, including the re-sequencing option if you disagree. |
| **Codex extra — don't silently re-date the Codex debt.** | — | **ACCEPTED.** Scope growing means *more* urgency, not less. The default is removed; this is now the one item I will not decide for you. |
| **Codex extra — `/readable` can't literally "refuse".** It's prompt Markdown. | Correct, and it's the built-≠-wired rounding-up this repo exists to stop. | **ACCEPTED and rephrased** as a tested CLI check plus a required workflow. See D4. |
| **Cheli 1 — the hotfix ships the less serious bug; the gate bypass stays open.** | Correct. | **ACCEPTED as a stated trade, not hidden.** A capability declaring a fabricated consumer passes `validate` and the release gate through v1.34.0. Shipping a prose-matching rule would be the proxy failure; the typed schema is a v1.33.2 candidate. **Your call to accept.** |
| **Cheli 2 — usage measures usage, not value.** | Correct. | **ACCEPTED and written into D5's kill criterion**, plus Cheli's one-line-per-dispatch gut-check, now a durable column rather than a memory exercise. |

### Round 3 — Cheli approves; Codex approves H1 and holds on three specifics. All six points fixed.

| Finding | Disposition |
|---|---|
| **Cheli gap 1 — the scenario→facts mapping is unspecified, and it's the user-facing core.** Everything else was specified; the join between "what would a CISO ask" and "what deterministic data exists" was not. | **ACCEPTED — the best finding of this round.** New **`Facts` column** in D2, explicitly *not* the `Class` column (reusing a taxonomy crosswalk as the facts-join would be the proxy-keying this plan objects to everywhere else), with a two-directional mechanical contract. Settles what `/readable S17` actually does. |
| **Cheli gap 2 — the release precondition has no deadline**, so D2–D5 could sit on `main` untagged indefinitely. | **ACCEPTED.** Soft deadline **2026-08-31**, framed as a decision point, not an auto-ship. |
| **Codex 1 — no join between the machine row and the self-report.** A note could be orphaned, misattached, or create a row — so self-report *could* move the denominator, contradicting the claim it couldn't. | **ACCEPTED in full.** `usage_id` protocol: one durable machine row per ID, `usage-note --usage-id` updates only, refuses unknown or already-noted, and **a test proving a forged note creates no denominator row.** The property is now asserted, not asserted-about. |
| **Codex 2 — "Claude-only" is a decision without an implementation**; a missing classifier recreates the mislabelling. | **ACCEPTED in full.** Installer marker authoritative, `__file__` path fallback, unknown fails closed as not-Claude, and the real CLI tested from a simulated `.claude` and `.codex` install. |
| **Codex 3 — H2 presents a heuristic as a resolved connection check;** "symmetric" overstates, since `consumes` is topic-shaped and `emits[].consumers` is untyped prose. | **ACCEPTED.** "Symmetric" removed. Categories renamed to `known-local-reference` / `human-or-prose reference` / `unresolved reference — review needed`, with an explicit rule that the report never certifies wiring and ambiguity resolves toward review. |
| **Codex wording — D4's edge case still said "refused."** | **FIXED.** The pipeline exits non-zero; the Markdown never refuses. |

**Cheli's process observation, recorded rather than brushed off:** D5 was under-estimated three times — 15 lines → 30–40 → ~60 plus tests. The pattern says the `gate_yield` instrument is systematically more complex than it looks, so **any future extension there is estimated at 2× the first guess**, and this deliverable already carries the release's heaviest planted-test set.

### Round 4 — the committed re-review, run before any code. Both adversaries; one FATAL finding, verified by me.

`Loop closed: yes (integration-adversary — ISLANDS (6), the host classifier logs nothing on either real invocation path; architecture-adversary — BAND-AID (4), the caller compensates for a producer contract it never fixes)`

Both landed on the **same root cause** from opposite directions, which is the strongest signal this process gives. I verified every load-bearing claim myself rather than accepting it.

| Finding | Verified? | Disposition |
|---|---|---|
| **FATAL — the host classifier suppresses all logging.** This repo has no `.claude/bin/` and no `.tdd-playbook-version` marker; the bin runs from the checkout or the plugin cache. Both classify as not-Claude → nothing logged → the experiment produces an empty file and the 2026-09-30 keep/kill call reads "never used" regardless of use. | **CONFIRMED by direct inspection** — `.claude/` holds only runtime state; no marker exists. | **ACCEPTED. D5 rebuilt.** `log_yield_event` stamps `host` on every row; **no suppression anywhere**, so the "no producer silently drops out" invariant keeps no hole and Codex use is labelled rather than discarded. |
| **The phantom gate row.** `gate_yield.py:257-258` registers the gate key *before* inspecting the event, so any non-gate producer mints a zero-yield gate row — proven by execution, with `candidates` then reporting `2 gate(s) measured`. My "existing tables byte-identical" verification step was unachievable. | **CONFIRMED** — I had read this code and still designed around it instead of closing it. | **ACCEPTED.** Split the roster decision from the counting decision at the owner — fixes it **once for every future producer**, and is what makes the byte-identical claim true. |
| **`usage-note` reinvents `guard_note.py` as a mutable store.** Every committed record here is append-only; the numerator/denominator split is already solved append-only by riding the one write path with `source: "agent"`. | **CONFIRMED** — `guard_note.py:30-31,81`; all writes are `open(path,"a")`. | **ACCEPTED.** The note is an **event**, joined in the existing drain pass. The mutable store, both refusal branches and the bespoke anti-gaming test all disappear. |
| **`usage_id` was unreachable anyway** — nothing declared how David learns it, and rollup has no scheduled producer, so every ID would be refused until a manual drain. | **CONFIRMED.** | **DISSOLVED.** A per-cycle aggregate keyed on `scenario` needs no id at all. |
| **Sibling-path contract missed.** `default_response_md()` and `default_dataflow_md()` both derive from `TDD_PLAYBOOK_YIELD_MD`'s dirname — *"one instrument, one seam"* — so every harness that isolates the yield record isolates them too. I specified a literal path. | **CONFIRMED** (`:155-162`, `:368-377`). | **ACCEPTED** — `usage.md` derives the same way, and the pollution pin extends to it. This is a logged prior incident (`CHANGELOG.md:206,618`), which I would have repeated. |
| **The `model: opus` property test would silently not run.** `test_agents.py:553-558` iterates a hand-list with **no completeness guard**; nothing asserts `PINNED \| INHERIT == set(found)`. | **CONFIRMED.** | **ACCEPTED, per Codex's stronger form** — before D1: assert `PINNED | INHERIT == set(found)` (the real directory, vacuity-guarded) so an unclassified new agent REDs rather than slipping past; plus a **planted unpinned judgment agent** proving the check can fail. Every future agent must then be consciously classified pinned-or-inherit. |
| **A third "ships together" constraint.** `test_agents.py:95` symmetric-differences `AGENT_CONTRACTS` against the real directory, so four `.md` files without four contract entries RED immediately. | **CONFIRMED.** | **ACCEPTED** into D1's sequencing note, alongside the 8 corpus entries. |
| **H2's actionable bucket is empty where the gap is.** Prose is the easiest fabrication *and* the "not a finding" bucket. Measured: three consumer strings name things that do not exist (`public scoreboard (WS5)` — CLAUDE.md says WS5 is not started) and all read as prose. The deferred "right fix" is a **43-string** hand edit — smaller than the interim classifier plus its tests. | **CONFIRMED, and my own denominator was wrong**: I wrote "19 `emits` entries"; measured directly it is **16 capabilities carrying 43 consumer strings**. A plan that preaches independent denominators got its own wrong. | **ACCEPTED — H2 redesigned and moved.** Add `kind` to consumers as an **optional** R-SCHEMA field now (unset = today's behaviour, nothing breaks), report unset/unresolvable, require it later. The report becomes a set-membership check like the orphan check that already works *because* it is typed. |
| **`Class` would be the first machine copy of an unowned taxonomy.** T1–T7 exists only as prose in SKILL/commands, enforced by string-presence. | **CONFIRMED.** | **ACCEPTED** — one constant owns the vocabulary; the existing string pins and the inventory pin both assert against it. Same rule `Route` already follows. |
| **`Facts` — argument survives, direction wrong.** Reusing `Class` would be proxy-keying (refutation attempted and failed), but two hand-maintained sides of one join is the `Route` mistake. | **CONFIRMED.** | **ACCEPTED** — each worry page declares the scenario IDs it answers **in code**, beside the emitting logic. Both directions collapse into one derivation; the bidirectional contract becomes free. |
| **The README check keys on a proxy.** A bare substring is satisfied by a mention anywhere — `/tdd-unlock` appears in a routing cell, outside the roster. | **CONFIRMED.** | **ACCEPTED** — scope the assertion to the roster line and routing table specifically. |
| **README lists 8 of 10 agents** (`architecture-adversary`, `script-adversary` missing), and the four new ones ship downstream with no discovery surface at all. | **CONFIRMED** (`README.md:20-22`). | **ACCEPTED** — extend the family sweep to `agents/`, add the missing two plus the four. Downstream discoverability becomes stated dated debt. |
| **`usage.md` registered nowhere**, so a new durable artifact is invisible to `doctor`. | **CONFIRMED.** | **ACCEPTED** — registered on the `gate-yield` capability with consumers named. |
| **H2's decision has no dated owner** — "the noise level is the evidence" is a read nobody owns; the repo's own registry already records this failure class. | **CONFIRMED** (`capabilities.json:51`). | **ACCEPTED** — a dated `integration_debt` entry so the deferral has a mechanical trigger. |
| **H1 discards a join key.** `<cap>/<id>` is a cross-file reference; `host-parity-policy.json` cites three by value. | **CONFIRMED.** | **ACCEPTED** — render `<cap>/<id> — <what>` when an id exists, `<cap> — <what>` when it doesn't. |
| Append-only hypothesis I flagged as possibly fatal | **REFUTED** — rule (a) covers a fixed five-file tuple; `docs/calibration/*` is not globbed. | Kept anyway: `usage.md` joins the append-only list, so the record gains real protection rather than relying on nobody editing it. |

**What this round cost and bought:** the redesign *removes* an id protocol, a host classifier, a mutable store, two refusal branches and a bespoke test, and *adds* two one-line fixes at the producer. The plan got smaller and correct at the same time — which is the argument for running the pass before writing code rather than after.

### The cost number (Cheli's blocker 3 — withdrawn on verification)

**Calibration does not run on opus.** `run_calibration.py:558` defaults `--model` to **haiku** (`TDD_PLAYBOOK_CALIBRATION_MODEL`), deliberately — §13 runs verifiers at a cheap model as a conservative lower bound. The `model: opus` pin governs *dispatch*, not calibration.

- **Added calibration load:** 8 new scenarios × 3 reps = **24 haiku runs**, each capped at 600 s. Worst-case wall clock rises from ~15 h to ~19 h (30 → 38 scenarios); typical runs are far below cap. The README's chunking advice (`--agent <name>` so each chunk commits its own block) already covers it.
- **Standing dispatch cost: zero.** Nothing auto-dispatches. You dispatch when you choose. That *is* the spend control — S23 dogfooded — and it's why no spend cap is needed.

**One thing you should know before adding agents.** The last live calibration (2026-08-06) largely **did not execute**: ~20 rows are `INVALID — env failure on all reps`, plus one **`BLOCKING FAIL`** (`control-assert-red-then-green`, red-first-verifier, 0/3 missed-entirely) and one AMBER, all unresolved. So `--dry-run` will go green on the new agents' R1 coverage while **nothing has been calibrated live in six days**. Adding four agents doesn't cause that, but it does mean their briefs ship uncalibrated until a live run happens as a non-root user with budget.

### Open question — needs your call

## Decisions taken (2026-08-12)

**1. The Codex parity cliff — DECIDED: accept a known RED on 2026-09-30 — and the release report must make it impossible to forget (Codex's caution, accepted).** v1.34.0's CHANGELOG entry and release notes MUST state: `/readable` and the four agents are Claude-only; the `codex-command-agent-discovery` debt expires 2026-09-30; **on that date the repository gate deliberately goes RED unless Codex discovery is addressed or the debt is consciously re-dated.** A deliberate future RED that isn't written down where the operator reads is indistinguishable from a surprise. This adds 4 agents + 1 command as Codex-`unavailable` under the existing `codex-command-agent-discovery` debt, growing the gap from 32/33 to 37/38 unsupported. The debt is **not re-dated** — Codex was right that re-dating because scope grew is backwards, and it is the quiet-erosion move G4 exists to make conspicuous. It expires on schedule and the suite goes red, loudly, on a known date. By then the usage record says whether any of this was used, which is better information for deciding whether Codex support is worth building than anything available today.

**2. The gate bypass — DECIDED: fix it as a report, in the same hotfix.** See **H2**. Not a `validate` rule (Codex's proxy objection stands), not deferred entirely (Cheli's gap objection stands), and not a schema migration ahead of an experiment that may not survive review. `doctor` reports; the report's noise level is the evidence for whether the typed schema is worth building later.

**3. The four agents — DECIDED: ship them, with live calibration as a release gate.** David's constraint is explicit: the inventory doesn't work without them, and 17 of 42 rows have no answer path today. Codex's real objection was untested agents, not scope — so a live calibration run covering the four new plant/control pairs is a **precondition for tagging v1.34.0**, and the 2026-08-06 env failure must be fixed first. If that run cannot happen, the agents do not ship.

**4. Usage-pattern design — DECIDED without asking.** The record stamps timestamp, scenario asked, and whether the surface had anything to say. Whichever way the tool ends up being used — before a session, after a change, or when something feels off — the pattern emerges from the timestamps rather than needing to be predicted now.

---

## v1.33.1 — hotfix, ships standalone today

**H1 only.** H2 moved to v1.34.0 after the re-review: H1 is a display fix already pinned by a byte-equality test, while H2 introduces a new classification whose stated purpose is to *generate evidence* about whether a schema is worth building — that is experiment-shaped work, and it belongs where its noise can be weighed.

### H1 — Debts render anonymously

**What.** `render_reference.py:64` reads `debt.get("id", "unnamed")` — an optional, unvalidated field present on **4 of 55** entries. The **required** field is `what` (`_debt.py:15`), which `capability_registry.py:190-192` already prints. So `current-state.md` shows 51 debts as `<capability>/unnamed`, and every consumer of that file inherits it.

**Edge cases.** Empty `what` → already caught by `_debt`. A very long `what` (they run 200+ chars) → first clause, with the full text still reachable via `doctor`; truncation must be visible, never silent (§12). Idempotent render.

**UX test.** `python3 bin/render_reference.py render` then read `docs/reference/current-state.md` → 55 debts read as sentences.

**Integration surface.** *Consumes:* `_debt.py`, `capabilities.json`. *Emits → named consumer:* debt lines → `current-state.md` → David, and `test_reference_docs.py:35-45`'s byte-equality check. *Surface parity:* CLI, both hosts. *Reverse sweep:* every existing `doctor` consumer improves for free — `commands/integration-audit.md:14`, `agents/integration-adversary.md:35-37`, `agents/tripwire-auditor.md:19`. *Activation:* ON.

**Repo-local extras.** Planted: a debt with no `id` renders its `what`, not `unnamed`. **Paired clean control:** a debt *with* an `id` still renders it.

### H2 — Consumer references: add the typed field now, report on it — **moved to v1.34.0**

**What.** The registry is the instrument that says what is connected to what — the one David leans on because he cannot read the code. Today an entry can claim a consumer that does not exist: `R-WRITE-ONLY` (`capability_registry.py:126-131`) checks only that the `consumers` list is non-empty. So the instrument can report "wired" for something that was never built.

**Both reviewers framed the fix as a binary and it isn't.** Codex is right that a rule matching names against prose (`"David, reading the check mark…"`) would be the keying-on-a-proxy failure, and Cheli is right that leaving it entirely open is a live gap. The third path: **`doctor` already does the reverse direction** — it flags topics consumed but never emitted (`:225-229`). It is a **report, not a gate**: it cannot fail the release, needs no schema migration, and its noise level against the existing 19 `emits` entries is precisely the evidence for whether a typed consumer schema is worth building.

**⚠ I called this "symmetric" and Codex is right that it overstates.** The reverse check works because `consumes` is **topic-shaped data**; `emits[].consumers` is **untyped prose**, where a real external consumer and a fabricated one are both just strings. So the report's categories are named for what the tool can actually know, and **none of them certifies a connection** — its value is surfacing ambiguity:

- **`known-local-reference`** — resolves to a capability id, an emitted topic, or a real path in this repo. Not called "real": the resolver is concrete but the reference may still be stale.
- **`human-or-prose reference`** — describes a person or a process. Legitimate, unresolvable by construction, and **not a finding**.
- **`unresolved reference — review needed`** — matches nothing and doesn't read as prose. The bucket worth your eye.

**Edge cases.** *Vacuity:* zero entries scanned must not print "0 unresolved" — count against the real `emits` roster, an independent denominator (§12). *Boundaries:* a string that is both a plausible path and plain English lands in `unresolved`, never silently in `known-local` — ambiguity resolves toward review. *Second-order:* this must never migrate into `validate` without the typed schema, and must never be quoted as evidence that something IS wired; a comment in the code says both.

**Integration surface.** *Consumes:* `capabilities.json`. *Emits → named consumer:* the dark-inventory line → David, and the `/integration-audit` and `integration-adversary` dispatches that already run `doctor`. *Surface parity:* CLI, both hosts. *Activation:* ON, advisory — `doctor` exits non-zero only under `--strict` (`:305`), which nothing in the release path passes.

**Repo-local extras.** Planted: a fabricated consumer appears in the unresolvable count. **Paired clean control:** a real one does not, and a human-prose consumer lands in its own bucket rather than either extreme.

Then: regenerate `current-state.md`; bump the four identity files + CHANGELOG; push; wait for the `gate` check; **David tags v1.33.1**.

---

## v1.34.0 — the experiment

### D1 — The four missing adversaries

**What.** The 17 dangling rows resolve to exactly four missing loss functions. (`consent` and `waste` from the source draft appear in **no** inventory row — spurious, dropped.)

| Agent | Rows | Weights | Why nothing existing covers it |
|---|---|---|---|
| `security-adversary` | S17–S24 (8) | Catastrophe. Secrets reaching log sinks; a check on one door and not its twin; input reaching shell/query/eval; internal calls trusted unre-checked; over-wide permissions; PII in traces; an expensive path with no limit; auth quietly removed. | `/security-review` is a harness skill, not a Playbook agent — it can't be dispatched by name, calibrated, or planted. |
| `test-quality-adversary` | S25, S26, S27, S31 (4) | Whether the tests promise anything. Self-consistency tests; tests with no real assertion; flaky retried instead of fixed; a surface with no test at all. | `mutation-runner` measures a score and is **blind across a misunderstood seam by construction** (§4). §1's seam rule and §4a's vacuity rule are doctrine with no hunter. |
| `observability-adversary` | S02, S32, S33 (3) | 3am. Can I tell right now if this works; if it fails does anyone find out; is an error swallowed where nobody will see it. | Nothing. §6a's "dead and quiet look identical" has no agent. |
| `adoption-adversary` | S38–S41 (4) | Whether it lands. Can a user find it unprompted; does a new user with nothing set up get through the first run; does the error say what to do next; does anything tell us it got used. | `ux-probe-calibrator` tests a *probe*; `/probe` drives an interface. Neither reviews a change for adoption risk. |

Each ships `model: opus`, `tools: Read, Grep, Glob, Bash` (no `Edit`), a refute-framed stance, the repo-grounding rule (cite `file:line`, never an abstract "should"), a restraint clause (over-strictness on clean work is measured exactly like blindness on broken work), a **stated de-prioritisation** (the anti-role-costume guard), and the two forced verdict lines.

**⚠ Non-negotiable mechanical cost.** `run_calibration.py:243` enforces R1: every headless-calibratable agent needs **≥1 plant, and controls don't count**; `known_agents()` derives from `agents/`. The R2 pair quota then requires each plant carry a paired clean control. **Four agents = eight corpus entries, or `calibration/test_harness.py` — a fixed gate stage — REDs the moment the files land.** They ship together.

**Edge cases**
- *Vacuity:* a brief soft enough to return CLEAN on anything — exactly what R1 catches ("a softened brief keeps its verdict lines while losing its rules").
- *Boundaries:* the plant must fire **for the right reason** — `must_match` names the planted symbol, not just the verdict line. The `ghost-gate-undeclared-export-flag` plant is the model: verdict **and** symbol **and** a reason-shaped regex.
- *Auth-negative:* the paired control must **not** fire. A security adversary that flags every diff trains you to ignore it.
- *Scale:* `calibration/fixture/` is a tiny package. If it cannot host a defect shape honestly, **extend the fixture** rather than write a plant that fires on a toy.
- *Second-order:* new agents change `known_agents()`, recomputing every coverage count — verify the harness before and after.

**UX tests.** Dispatch `security-adversary` on a diff adding `requests.post` to a module with no prior egress → names the sink at `file:line`, answers S17/S23 in plain language. On a docs-only diff → `Verdict: CLEAN`, no invented findings. Dispatch `test-quality-adversary` on a test whose every assertion reads an object the test built → flags the §1 seam violation, in words, without you reading the test.

**Integration surface.** *Consumes:* `capabilities.json`, `capability_registry.py doctor`, `verify_citations.py`, the tree. *Emits → named consumer:* the forced `Verdict:` line → `run_calibration.oracle()` (string-only, no LLM judge) via each scenario's `must_match`; `Recommendation:` → David. *Surface parity:* Claude `supported`; Codex `unavailable` under the existing debt — see the open question. `test_host_parity.py:174-175` hand-pins move **33 → 38 assets, 66 → 76 dispositions**. *Reverse sweep:* `/edge`, `/integration-audit`, `/tdd-plan`, `/probe` dispatch adversaries on a prose rule today; citing scenario IDs there is **explicitly out of scope** for this release and is not registered as debt, because it depends on whether the inventory proves useful. *Activation:* ON.

**Property tests.** Frontmatter parses; `model: opus` present; `Edit` absent; both verdict lines present; **every agent in the real roster has ≥1 plant** — asserted from `known_agents()` with a vacuity guard, never a hand-list.

**Codex argues D1 should be cut and adversaries added one at a time as usage reveals gaps. Keeping it, with the evidence bar raised instead — and here is the reasoning, so you can overrule it.**

- **The gap is known, not hypothetical.** 17 of 42 rows have no lens *today*. Codex's loop discovers gaps you already know about, at the cost of 30–60 days in which the surface shows you questions you cannot pursue. That is the opposite of the point.
- **Codex's alternative was self-undermining as written.** "Add an adversary once the usage record shows a recurring unanswered question" requires the record to capture *which question was asked* — which Codex's own issue 1 says it does not. The redesigned usage table (D5) now captures `scenario` durably, so the loop becomes real. It is a good loop; it is the one for row **43**, not for the seventeen already dark.
- **Codex's strongest point is different and I'm accepting it:** the four agents would ship with **no live behavioral evidence**, since the 2026-08-06 run largely didn't execute. That is a real bar problem, so the bar moves rather than the scope: **a live calibration run covering the four new plant/control pairs is a release precondition for v1.34.0, not a follow-up.** The 2026-08-06 env failure must be fixed first, as a non-root user with budget. If that run cannot happen, the agents do not ship — which is Codex's caution honoured as a gate rather than as a scope cut.
- If you'd rather test the surface before expanding the roster, the clean split is **v1.34.0 = D2–D5 with existing agents; v1.34.1 = D1** once usage shows which lens you reach for first. Say the word and I'll re-sequence; I'm recommending against it for the reason in the first bullet.

---

### D2 — The scenario inventory

**What.** The 42-row catalogue at **`docs/adversary-scenario-inventory.md`** — this repo only, **not vendored**, which dissolves the parity exception entirely. Not `docs/reference/`, whose sole occupant is generated and stamped DO NOT EDIT.

Two corrections to the draft:

1. **Every Route names a real, dispatchable agent** — after D1, 32 of 42 route to one of 14. Of the 10 orphans: S02/S32 → `observability-adversary`; S03/S04/S35 → `edge-case-adversary` (resource exhaustion is its failure/rollback beat); S07/S11/S12 → `architecture-adversary` (knob sprawl, coupling, run cost); S36 → `integration-adversary` (the on/off-switch reachability bar it already enforces). **S14 stays `—` with a stated reason:** "suite slow enough people skip it" is measured by `gate_yield`, not judged by an agent. One honest dash beats ten.
2. **A `Class` column** crosswalking each row to the taxonomy §13 already reports against (§6 node classes + §6c T1–T7), or `new` with a reason. Without it, a finding tagged `S08` and one tagged `T3` are the same class counted twice — which `commands/integration-audit.md:50-56`'s anti-double-homing rule exists to prevent. **Both reviewers independently called the crosswalk right instinct**; Cheli's caveat that it's unvalidated prose mapping unvalidated rows is fair and is why nothing is built on top of it.

3. **A `Facts` column — the join Cheli found missing, and it is the user-facing core.** Cheli is right that everything else was specified and this wasn't: `/readable S17` promises to answer one scenario against the current tree, but nothing said *how a scenario ID maps to which facts surface*.

**It is NOT the `Class` column.** Class is a failure-taxonomy crosswalk; reusing it as the facts-join would be keying a check on a proxy — the exact thing this plan objects to everywhere else. So the join is explicit and its own column:

- `Facts` names the **worry page(s)** of `readable_surface.py` output that answer this row — e.g. S17 → `egress`, S25 → `test-seams`.
- `Facts` is **`—` for every row whose `Evidence` is `agent`**, and `/readable S<n>` on such a row says so plainly: *"no mechanical facts for this one — this needs `<Route>`."* That is the honest answer, and it gives the stated 26-facts/16-agent distribution real teeth instead of being a footnote.
- **The contract is mechanical in both directions:** a `Facts` value naming a page `readable_surface.py` does not emit → RED; a worry page no row points at → reported, because an unreachable page is a page nobody can get to from a question.

This makes the inventory↔facts edge a tested §6c flow rather than an implicit convention, and it settles what `/readable S17` actually does: show that row's Question as the frame, its `Facts` pages, and its `Route` as the next step.

**Edge cases.** *Malformed:* a Route naming a nonexistent agent → RED. *Boundaries:* IDs unique, never reused, count never decreases. *Vacuity:* zero rows parsed → non-zero exit, count compared against an **independent** expectation (the closed Role set), never `>= 0`. *Second-order:* implying complete coverage — mitigated by the stated 26-facts/16-agent distribution and G1 (membership ≠ control).

**UX tests.** You open the file and can answer "what would a CISO ask about this change?" without reading code. `/readable S17` answers it against the current tree. A `—` row reads as *not yet a control*, never *nothing to worry about*.

**Integration surface.** *Consumes:* nothing — it is data. *Emits → named consumer:* **Route** → the resolver test, which imports `host_parity.canonical_inventory()["agents"]` rather than re-globbing (the roster has an owner with a vacuity guard already attached; a third glob is one more thing to drift). **Class** → the same test. **ID** → `/readable S<n>`. *Surface parity:* this repo only — stated as a decision, not a gap. *Reverse sweep:* none this release. *Activation:* ON.

---

### D3 — `readable_surface.py` — what deterministic data exists

**What.** A stdlib bin that composes producers that **already exist** — `capabilities.json` (nodes), `dataflow-sweeps.json` + `dataflow_sweeps.py` (edges), `gate-manifest.json` (suites), `host-parity.json` (surfaces), `git ls-files` — into **worry-organised** output, every row carrying a resolvable `file:line`. This answers the half of your problem the inventory doesn't: *what data exists to answer these questions.*

**Stdout only. No committed artifact, no staleness gate, no snapshot, no diff.** That machinery only pays off if the surface is read repeatedly, which is the thing being tested. Dropping it also removes every duplication concern against `render_reference.py`.

**Edge cases.** *Empty/null:* no `capabilities.json` → fail loudly with "run `capability_registry.py init` first"; never an empty page reading as "nothing here." *Vacuity:* zero subsystems scanned → **exit 3**, reusing `dataflow_sweeps.py:90 EXIT_VACUOUS` — the constant, not a re-picked number. *Malformed:* an entry missing `activation`/`emits` renders **"not stated"**, never omitted — **an absent fact and a false fact must look different**. *Scale:* 63 capabilities must render to something a human finishes; anything capped **says what was capped** (a silent top-N is a lie by omission). *Idempotency:* two runs on an unchanged tree are byte-identical — stable ordering, no timestamps. *Second-order:* the output becoming authoritative — every row cites its source, so it is an **index, not a claim**.

**UX tests.** `python3 bin/readable_surface.py facts` → worry pages with resolvable citations. Pick a row → "explain this one" is a well-scoped dispatch. No registry → the exact command, exit non-zero.

**Integration surface.** *Consumes:* `capability_registry.py`, `dataflow_sweeps.py`, `_debt.py`, `gate-manifest.json`, `host-parity.json`, `hooks/scripts/_common.py::log_yield_event` (the `bin/guard_note.py:43` pattern). *Emits → named consumer:* rows → `/readable` and David; the pinned summary line → `test_readable_surface.py`, parsed field-by-field; usage events → D5. *Surface parity:* CLI on both hosts (`bin/` vendors to both and is not a parity family — existing precedent). *Reverse sweep:* none this release. *Activation:* ON — stdout-only, nothing to switch.

**Property tests.** Idempotent stdout; every citation resolves via `verify_citations.py`; summary counts equal row counts.

**Repo-local extras.** Pinned line, owned here and **imported** by consumers (`gate_yield.py:57-62` precedent — four regex dialects was the drift surface): `readable_surface facts: subsystems N · effects N · unproven N · not-stated N`. Planted: an entry missing `activation` renders "not stated", not omitted; **paired clean control:** a complete entry renders its real value.

---

### D4 — `/readable`

**What.** Runs `readable_surface.py facts` and narrates in plain sentences; `/readable S17` answers one scenario against the current tree.

**⚠ The reused citation gate has a vacuity hole — and my earlier phrasing overclaimed how it closes.** `verify_citations.py:108-110` exits **0** on zero citations, the one tool in the set where a scan of nothing passes. A confident, wholly uncited narration is exactly the load-bearing failure mode.

**Codex is right that a Markdown command cannot "refuse" anything** — it is a prompt, not an enforcer, and saying otherwise is precisely the built-≠-wired rounding-up this repo exists to stop. The honest split:

- **Mechanical half:** `readable_surface.py` emits citation-bearing facts, and a **tested CLI check** — `readable_surface.py facts | verify_citations.py -` plus a `Citations: N ≥ 1` floor — is what actually holds. The planted test runs that pipeline on a zero-citation input and asserts non-zero exit.
- **Workflow half:** `commands/readable.md` *instructs* the model to run that check before presenting findings, in the `commands/claims.md:24-28` shape, and to paste the tool's summary line rather than assert a count — because a self-reported N/N is narration with a colon in it.

The guarantee is "a tested CLI check plus a required workflow," never "the command refuses." **Fix the caller, not the tool** — permissive-empty is correct for `/claims`, where a findings doc may legitimately carry none (three consumers: `claims.md:28`, `integration-audit.md:69`, `tdd-lock.md:10`).

**⚠ It must be findable.** `README.md:19` is the canonical command roster, `:33-40` the routing table, and **nothing mechanically ties README to `commands/`** — verified. So: a roster entry, a routing row (*"What is this system, in plain language?"* → `/readable`), and **one check in `test_agents.py`'s existing commands family sweep** (`:120-140`) asserting every command appears in the README. Otherwise the on-switch is a source-directory listing, in the one repo whose premise is that the reader doesn't browse those.

**Edge cases.** *Empty:* nothing to show → an explicit line, never silence. *Malformed:* narration citing an absent fact → **the CLI check exits non-zero and the workflow requires running it before findings are presented** (Codex's wording cleanup — the Markdown never "refuses"; the pipeline is what holds). *Agent-evidence scenario:* `/readable S34` where `Facts` is `—` → says plainly there are no mechanical facts and names the Route agent, rather than dumping the whole surface. *Auth-negative:* never dispatches a paid adversary (S23) — pinned by a test that the command text carries no dispatch instruction. *Missing inventory* (a vendored downstream repo): degrades gracefully — facts still render, the scenario lookup says the inventory is absent rather than crashing or fabricating. **Planted test.** *Second-order:* becoming a gate — no exit-code consumer, joins no gate stage, pinned.

**Integration surface.** *Consumes:* D3's stdout, `verify_citations.py`, D2's IDs. *Emits → named consumer:* narration → David; usage → D5. *Surface parity:* Claude `supported`, Codex `unavailable` under the existing debt. *Activation:* **ON.** Prose never gates. **Not** added to `LOOP_CLOSING_COMMANDS` — it dispatches nothing, so a "Loop closed" line would be a false claim.

---

### D5 — The usage record — rebuilt after the re-review found it fatally wrong

**What.** You asked to track usage, the parameters of usage, and the results. This is that — redesigned, because both adversaries independently proved my previous version would have produced **zero data**, and my own checks confirmed it.

**What was fatally wrong, verified first-hand.** I had `readable_surface.py` classify its own host from an installer marker or its `__file__` path, logging only under `.claude/bin/`. **This repo has no `.claude/bin/` and no `.tdd-playbook-version` marker** — `.claude/` here holds only runtime state, because the repo dogfoods via the marketplace plugin. So the bin runs from `plugins/tdd-playbook/bin/` (checkout) or the plugin cache, neither matches, "unknown fails closed as not-Claude" fires, and **nothing is ever logged in the repo where the experiment runs.** The one deliverable that makes v1.34.0 an experiment would have shipped producing an empty file, feeding a keep/kill decision on 2026-09-30 that would have read "never used" regardless of use.

**The root cause is upstream of all of it, and both adversaries landed on the same seam.** `gate_yield.py:257-258` registers the gate key with `per_gate.setdefault(gate, …)` **before** inspecting the event name. So *any* producer riding the one write path with a non-gate name mints a phantom zero-yield gate row — the architecture-adversary ran it and got `| readable-surface | 0 | 0 | 0 | 0 | 0 |` alongside a real `testlock` row, with `candidates` then reporting **`2 gate(s) measured`**: a non-gate now sitting in the retirement instrument's denominator. My fourth table did not fix that; it added a second table beside it while the phantom row remained, which also made my own Verification step ("existing tables byte-identical") unachievable.

**So the fix moves to the producer, and the caller-side machinery disappears.** Four changes, each at the owner:

1. **`log_yield_event` stamps `host` on every row — from host-runtime-provided signals, precisely specified** (both reviewers asked what stamps it; here is the answer, stated not implied). It already stamps `source` (`_common.py:222-224`); `host` joins it, resolved as:
   - `"claude"` if `CLAUDE_PROJECT_DIR` is present — set by the Claude Code runtime when it invokes hooks and bins, the same variable the log path already keys on (`_common.py:158`, `gate_yield.py:84`). This satisfies Codex's "authoritative, not self-reported" bar: it is installer/runtime-controlled, not cwd, not source path, not a knob a config file supplies.
   - `"codex"` if `TDD_PLAYBOOK_PROJECT_ROOT` is present — the Codex adapter's own runtime variable (`adapters/codex/pre_tool_test_lock.py:32`).
   - `"unknown"` otherwise — **stamped and logged, never suppressed.** One stated divergence from Codex's prescription ("when absent, log no usage event"): silent non-logging on an unrecognised context is exactly the shape of the fatal flaw this round removed, and `_common.py:214-215`'s invariant is that no producer silently drops out of the record. A labelled `unknown` row is more honest than an absence — the Claude-only analysis excludes it at read time, visibly. Scope stated per §12: this labels by *invoking runtime*, which is the fact we want; it does not defend against someone deliberately exporting the variable, any more than the file defends against an editor.
   - Tests, per Codex: canonical checkout and plugin-cache dogfooding (→ `claude` when run under Claude Code, since it sets the variable in both), a vendored `.claude` install, a `.codex` install, and a bare-shell run (→ `unknown`, still logged).
2. **Split the roster decision from the counting decision** at `gate_yield.py:256-274`, with the predicate defined exactly (Codex's clarification 1): `GATE_EVENTS = {"block", "warn", "override", "suppressed", "response"}` — the closed vocabulary the counts dict already encodes — and **only those events mint a `per_gate` key**; usage events route to the usage-table writer without touching `per_gate`; any other unknown event is **ignored without a row** (today's deliberate old-vendored-copy tolerance, preserved). Planted regression, both directions: a `readable-surface` usage event produces a usage row **and leaves `gate_yield.md` byte-identical**; a genuinely unknown event produces neither. This fixes the phantom row **once, for every future non-gate producer**.
3. **The note is an event, not an edit.** `log_yield_event("readable-surface", "usage-note", {...}, source="agent")` — the `guard_note.py:81` pattern exactly, riding the one write path, joined during the drain pass that `_write_response_rows` (`:288`) already performs. Append-only is preserved; the mutable id-keyed store, its two refusal branches and its bespoke anti-gaming test all **disappear**.
4. **`usage_id` disappears entirely.** With a per-cycle aggregate keyed on `scenario` — the same shape as all three sibling tables — there is no per-invocation row to join to, so there is no id for you to learn, quote, or lose. That also answers the re-review's "nothing declares how David learns the usage_id": nothing has to.

**The table, now the same shape as its three siblings** — `(date, named-subject)`, per cycle, append-only:

`| date | scenario | uses | dispatched | changed_a_decision |`

- `scenario` — the ID asked about, or `full`. Machine-written. **This is what makes the "add an adversary when a question recurs without a lens" loop possible.**
- `uses` — machine-written count for that cycle. The denominator.
- `dispatched` / `changed_a_decision` — your one-line note per use, via `gate_yield.py usage-note --scenario S17 …`. Self-reported, stamped `source: "agent"` so a reader can always tell a self-report from a mechanical observation — and it **cannot move `uses`**, because that comes from machine events only. The property is now inherited from the existing write path rather than re-proven with new code.

**Path, per the sibling contract I had missed.** `default_usage_md()` derives from `TDD_PLAYBOOK_YIELD_MD`'s dirname exactly like `default_response_md()` (`:155-162`) and `default_dataflow_md()` (`:368-377`), whose comment states the rule: *"sibling of the yield record ON PURPOSE: every harness/test that isolates `TDD_PLAYBOOK_YIELD_MD` isolates this record too — one instrument, one seam."* I had specified a **literal path**, which would have leaked suite exhaust into the committed record — a logged prior incident (`CHANGELOG.md:206,618`). The pollution pin at `test_harness.py:2233-2237` extends to `usage.md`.

**Edge cases.** *Empty:* absent data stays **UNMEASURED, never zero** (`:31`). *Boundaries:* an extra same-day `rollup` appends a second row per subject while `candidates()` tracks cycles as a **set of dates** (`:317-322`) and sums per row — so same-day double-drain double-counts; the usage table must be idempotent per (date, scenario) or state that it isn't. *Malformed:* a note naming a scenario with no machine event that cycle is an **orphan — reported, not counted**. *Second-order:* rollup has **no scheduled producer** (only `run_calibration.py:751,768`), so running it is a manual step, stated; and `reset_plan.py:148` deletes the raw log under `tdd reset --repo`, so an un-drained cycle is lost.

**UX test.** Run `/readable` three times → `gate_yield.py rollup` → `docs/calibration/usage.md` shows the scenarios asked about with a count of 3; `gate_yield.md`, `dataflow_yield.md` and `guard_response.md` are **byte-identical** — now actually achievable, because of change 2.

**Integration surface.** *Consumes:* `_common.log_yield_event`. *Emits → named consumer:* `usage.md` rows → you; **registered in `capabilities.json` on the `gate-yield` capability** with its consumers named, so the operator's dark inventory can see the fourth record (the re-review caught that I had added a durable artifact and registered nothing). *Surface parity:* both hosts record, labelled by `host`. *Activation:* ON.

**Repo-local extras.** Planted: a real CLI run lands a `usage.md` row with the right `scenario`. **Paired clean controls:** a `/readable` run adds **no row to `gate_yield.md`** (the phantom-row regression pin, in the opposite direction from before); a note naming an unseen scenario is reported as an orphan and does not create a `uses` count; the three existing tables and both 7-tuple consumers are unaffected.

## Explicitly NOT in this release

Dropped, with reasons — not deferred behind machinery, because a deferral needs a trigger and none of these have one worth carrying:

- **Routing table, exposure ledger, route plants, demotion journal.** You pick the adversary by reading the surface — which you'd do manually anyway. These automate that choice, and they presume the inventory's rows are right. D5's usage record is what would later justify them.
- **`R-CONSUMER` as a blocking `validate` rule.** H2 reports it instead. Enforcement waits on a typed consumer schema (`kind: capability | file | human | external` + a resolver per kind), and H2's noise level is the evidence for whether that schema earns its migration. Until then the gap is **open and stated**: a capability declaring a fabricated consumer still passes `validate` and the release gate.
- **SKILL `## 6d` doctrine.** A vendored gate surface describing a mechanism that may not survive the experiment. Also: the SKILL `description` has **6 characters of headroom** (1018/1024), so any doctrine wanting trigger vocabulary needs a dedupe pass first.
- **Scenario-ID citations in `/edge`, `/integration-audit`, `/tdd-plan`.** Depends on the inventory proving useful.
- **Downstream vendoring of the inventory.** Dissolves the parity exception.

---

## Unenforceable deliverables (prose)

- **Whether the 42 rows are the right 42.** The usage record is the experiment; nothing mechanical validates the catalogue's content.
- **Route-to-agent assignment is judgement.** The mechanism enforces only that each target exists — never that it's the right lens. My reassignment of the 10 orphans wants your eye.
- **The four briefs' quality.** R1 proves each agent fires on its plant; nothing proves the brief captures the loss function you want.
- **Live calibration** needs a real `claude` binary, budget, and a non-root user — and the last run largely didn't execute.

---

## Flow table (§6c)

| Flow | Producer | Consumer | Liveness test |
|---|---|---|---|
| debt labels | `render_reference.py` (H1) | `current-state.md` → David | planted debt with no `id` renders its `what` |
| agent briefs | `agents/*.md` (D1) | host discovery + `known_agents()` | R1: every agent ≥1 plant, from the real roster |
| forced verdict lines | the 4 agents | `run_calibration.oracle()` `must_match` | plant fires; paired control does not |
| Route column | inventory (D2) | resolver test via `host_parity.canonical_inventory()` | unknown target → RED |
| Class column | inventory (D2) | taxonomy pin | a row homed in two taxonomies → RED |
| **Facts column** | inventory (D2) | `readable_surface.py` worry pages; `/readable S<n>` | **both directions**: a `Facts` value naming no emitted page → RED; a page no row reaches → reported |
| usage_id | `readable_surface.py` mints it (D5) | `usage.md` machine row; `usage-note --usage-id` appends a **note row** joined on it | forged note creates no denominator row (different row kinds); unknown/already-noted ID refused; orphan note reported not counted |
| `usage.md` integrity | `gate_yield.py` | `check_scoreboard_integrity.py` append-only list | a rewritten historical usage row fails the baseline byte-prefix check |
| host classification | installer marker, else `__file__` path | `readable_surface.py` logging decision | real CLI from a simulated `.claude` and `.codex` install — only Claude writes |
| fact rows | `readable_surface.py` (D3) | `/readable`, `test_readable_surface.py` | summary counts == row counts |
| citations | `readable_surface.py` (D3) | `verify_citations.py` | every citation resolves |
| command roster | `commands/*.md` | `README.md:19,33-40` | family sweep: every command is in the README |
| narration | `/readable` (D4) | David | **N ≥ 1 citations enforced**; zero-citation narration REFUSED |
| usage events | `readable_surface.py` **CLI** (D5) | `_common.log_yield_event` → `rollup`'s single pass → `docs/calibration/usage.md` | 3 real CLI runs → 3 rows carrying the right `scenario` cell |
| dispatch outcome | you, via `gate_yield.py usage-note` | `usage.md` `dispatched`/`changed_a_decision` | self-report can move these two cells, never the machine-written denominator |
| the three existing tables | `gate_yield.py` (unchanged) | `parse_md_rows` 7-tuple, `:313` and `:432` | regression pin: both consumers and all three headers byte-unaffected |

**Consumer parity:** no seam is replaced, so no old-seam enumeration is owed. Stated so its absence is a fact.

---

## Registered capabilities and dated debts

| id | activation | integration_debt (owner: david) |
|---|---|---|
| `role-adversaries` | on | Codex dispatch unavailable — folded under `codex-command-agent-discovery`, **date per the open question** |
| `readable-surface` | on | joins the existing `gate-yield` downstream-inert-emitter debt (`capabilities.json:348`); the experiment's keep/kill call — **2026-09-30** |

Each trigger **proven in the same commit** by `validate --as-of <expiry+1>` exiting **1**; exit 2 is usage, never proof.

---

## Tripwire

| # | Deliverable | BUILT | WIRED | ACTIVATED | EXERCISED |
|---|---|---|---|---|---|
| H1 | debt naming | `render_reference.py` | `current-state.md` render + byte-equality check | ON | planted no-`id` renders `what`; control with `id` unchanged |
| H2 | consumer report | `capability_registry.py doctor` | the dark inventory `/integration-audit` + `integration-adversary` already read | ON, advisory (non-zero only under `--strict`) | planted fabricated consumer counted; real one not; human-prose in its own bucket |
| D1 | 4 adversaries | `agents/*.md` ×4, `model: opus` | host discovery; `known_agents()`; parity 38/76 | ON | 8 corpus entries; R1 from the real roster; each plant fires, each control doesn't |
| D2 | inventory | `docs/adversary-scenario-inventory.md` | Route + Class + **Facts** read by the resolver test; Facts is the D3/D4 join | ON | unknown target RED; double-homed class RED; **Facts→page RED both directions**; vacuity guard |
| D3 | `readable_surface.py` | stdlib bin, exit-3 vacuity | gate roster (digest re-acked) | ON | idempotency; summary==rows; "not stated" plant + control |
| D4 | `/readable` | `commands/readable.md` | `host-parity.json`; README roster + family-sweep check | ON; never gates | zero-citation narration REFUSED; missing-inventory degradation; no-dispatch pin |
| D5 | usage record | `usage.md` — a **fourth table**, own header + own parser, `usage_id` keyed | `_common.log_yield_event` → `rollup`'s existing single pass, before the one drain; via the real CLI | ON; **Claude-only, by a tested classifier** | 3 real CLI runs → 3 rows with the right `scenario`; forged note creates no denominator row; unknown/already-noted ID refused; only the `.claude` install writes; existing 3 tables + both 7-tuple consumers unaffected |

**EXERCISED, at its weaker truth:** each row means *the test exists at this sha, unskipped, gate green.* Not "the behaviour was observed running." For D1 the RUNNING leg needs a **live calibration run**, which is your action and is listed as prose.

---

## Sequencing

1. **Second adversary pass on this plan — before any code.** Cheli is right that this is a precondition, not a first step. Findings come back to you.
2. **v1.33.1** — H1 + H2, both one-file changes to tools you already run. Push, gate green, you tag.
3. **D1** — 4 agents + 8 corpus entries together (the harness REDs otherwise). Push.
4. **D2** — inventory with corrected Routes + Class. Push.
5. **D3 + D5** — the facts tool and the usage record together (the producer and consumer are one flow). Push.
6. **D4** — `/readable`, citation floor, README. Bump the four identity files + CHANGELOG. Push, wait for the `gate` check on that sha, **you tag v1.34.0**.

## Verification

1. Each new suite standalone → plants RED, controls green.
2. `python3 calibration/run_calibration.py --dry-run` → 0; **R1 coverage clean for all 14 agents**.
3. `capability_registry.py validate` → 0; `--as-of <expiry+1>` → **1**; garbage `--as-of` → **2**.
4. `readable_surface.py facts` twice → byte-identical; piped to `verify_citations.py -` → exit 0 with `Citations: N ≥ 1`. Empty registry → **exit 3**.
5. `/readable` ×3 through the real CLI → `gate_yield.py rollup` → `docs/calibration/usage.md` shows 3 rows with the right `scenario` cells; `gate_yield.md`, `dataflow_yield.md` and `guard_response.md` are **byte-identical to before**, and `candidates` + `dataflow-trend` still run (the 7-tuple consumers at `:313` and `:432`).
5b. **Live calibration** covering the four new plant/control pairs — as a non-root user, with budget, after the 2026-08-06 env failure is fixed. **Release precondition for v1.34.0, with a soft deadline of 2026-08-31.** Cheli is right that an open-ended precondition lets D2–D5 sit on `main` untagged indefinitely, stalled on something only David can do. The deadline is a **decision point, not an auto-ship**: if calibration hasn't run by 31 August, the call is tag-without-the-agents, or wait longer, or drop them — made deliberately rather than by drift.
6. `host_parity.py render` → **38 assets / 76 dispositions**; re-acknowledge `acknowledged_inventory_sha256`; bump the hand-pins at `test_host_parity.py:174-175`.
7. New suites → paste the sha from the roster-mismatch refusal into `gate-manifest.json:4`; `render_reference.py render`.
8. `install_into_repo.py <scratch>` → the 4 agents, `readable.md` and the bin land; **the inventory does not** (by design); `/readable` degrades gracefully there.
9. `install_into_repo.py --doctor .` → H8 clean.
10. `check_scoreboard_integrity.py --baseline-rev v1.33.0` → 0 (additions-only). Then, with `usage.md` added to its append-only list: rewrite a historical usage row in a scratch copy and confirm it **fails** the byte-prefix check — the protection proven, not assumed.
11. **`sh scripts/civerd_gate.sh > /tmp/gate.out 2>&1; rc=$?`** — never piped. `rc` must be 0.

---

## Loop closure

`Loop closed: yes (integration-adversary — the usage counter is silently destroyed, PROVEN BY EXECUTION; architecture-adversary — the draft cited a one-line field-selection bug as structural evidence)` — **on the previous draft.**

Their findings are folded in above: the `gate_yield` defect (D5), the anonymous debts (H1), README discoverability (D4), the canonical-roster import and Route resolution (D2), the citation vacuity hole (D4), the shared-derivation concern (dissolved — no committed artifact), the `reference/` parity exception (dissolved — not vendored), the Class crosswalk (D2), and the two reverse-sweep sites (dropped with a stated reason, not silent debt).

**This version has not been adversary-reviewed**, and it differs substantially from what they judged: the whole governance layer is gone, `R-CONSUMER` is dropped, H1 is a standalone hotfix, and D5 gained a specified producer and migration path. That pass is **step 1 of the sequence, before code** — not after approval to start building.
