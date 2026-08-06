# Changelog

All notable changes to the TDD Playbook plugin. Versions are the plugin `version` in
`plugins/tdd-playbook/.claude-plugin/plugin.json` (and the matching marketplace entry).

## 1.30.0 — 2026-08-06

**The narrowed scope reported as the whole (H15)** — a verification result is a CLAIM and
carries its SCOPE. Adopts Cheliped's second field report: `-m "not flaky"` reported
"13754 passed" while the unfiltered suite was RED. The quarantine was sanctioned, the
exclusion was policy, the gate did what its docs said — every decision legitimate, only the
report wrong. You cannot catch this class by hunting for mistakes.

It is the generalisation of a rule this repo already had: §4a's vacuity guard is the same
failure at scope=0. Everything between zero and complete is the same failure, quieter.

- **Fixed an armed time bomb in the ledger.** `coverage_problems` compared each entry's
  baseline against a FIXED rev (the EPOCH), which does not test "written before the change"
  — it tests "this surface has not moved since the epoch", permanently false once a surface
  legitimately changes. SKILL.md had crossed that line; once the covering entries were
  scored and spent, no new entry could ever cover it and the gate would RED on every
  doctrine edit. Replaced with an ancestry test (`is_ancestor` was already a parameter and
  never used). My bug, from the fix for the moving-baseline defect — the same class one level
  down, inside the correction, which is exactly the recursion the field report warns about.
- **Live: 3 dataflow sweeps declared, 1 armed.** `ghost_gates` and `exemption_prose` were
  absent from the config and never ran — `exemption_prose` was specified BLOCKING in v1.24.
  `all` now reports `N of M armed` and REFUSES a shortfall that is not declared in the
  config's `unarmed` array. Absence and decision are otherwise indistinguishable.
- **The gate stopped saying "ALL suites green" with no number.** It now reports suites ·
  harness checks · sweeps armed · ledger baseline, and fails closed on a glob matching
  nothing. The stale "110 planted checks" prose (it read 272) is gone.
- **The harness asserts every defined section is registered** — parsed, not grepped, because
  a text match finds the name in its own comment.
- **The ledger names the set its claim is about** (`covered N of M changed gate surfaces`,
  not a count of ledger entries) and no longer discards `skipped` run headers.
- §12 gains the scope rule and the corollary Cheliped supplied: **doctrine is
  recall-at-authoring-time**, so "the rule already covers it" is necessary but not sufficient
  — their sprint was three loaded rules, three misses. Ship the mechanism; the doctrine line
  exists so the mechanism has something to cite.
- Selectors are **decided out of scope** for `exitcode_guard`, pinned as ALLOW rows: the hook
  fires on the call, where a scoped run and a scoped report are indistinguishable.
- Three dated debts opened: arm the two dark sweeps (09-30), the ~9 self-referential
  denominators (10-31), and substring-authorization in the integrity checker plus Cheliped's
  parse-don't-text-match lint (11-15) — deferred deliberately, because rewriting what
  authorizes an integrity decision inside a doctrine release is how the release becomes the
  incident.

## 1.29.0 — 2026-08-06

**The dev/holdout split — the reporting set stops being the set we tuned against.** Item 3
of the ratified deletion-ratchet plan, deferred since v1.22. Today one corpus serves both
loops: "fix the agent, never the plant" means we iterate until a plant passes and then quote
the catch rate on that plant. A holdout set is the only way the number we publish is not the
one the tuning loop has been shaping.

- **`calibration/plant-forms.md` + `plant_forms.py`.** The form lives in an APPEND-ONLY
  register beside the corpus, not in the plant files. The obvious design — `_meta.form` —
  is unbuildable: rule (b) pins every approved plant byte-identical forever, which blocks
  back-filling the 14 legacy plants (foreseen) and also blocks **burn-on-failure** (not
  foreseen), because a holdout plant that fails must rotate into dev and that is a change to
  a file that can never change. A burn is now an append; the corpus only grows and so does
  its form record. An id with no entry is `dev` — absence is a decision, and that is the safe
  direction: an unassigned plant gets tuned against, never quietly reported as clean.
- **Every entry pins a `content_sha256`.** Form assignment is name-keyed, and yesterday's
  `d5dec34` lesson is that name-keyed authorization is only sound when something pins the
  content behind the name — asserted, not assumed. `check` recomputes the hash for any id in
  the corpus and refuses a mismatch; a privately-held body records `private` and the tool
  says it could not verify rather than implying it did.
- **The leakage tripwire.** A holdout id in a gate surface or a vendored tree is a burned
  plant. Blocking in `civerd_gate.sh`, with a vacuity guard: scanning zero files is a
  finding, and an unarmed tripwire reports itself unarmed instead of green. `history.md` is
  deliberately NOT scanned — the scoreboard records every id by design, and the first draft
  would have burned every holdout plant the instant it ran. Ids are public; BODIES are not.
- **`form` joins the run-block header**, optional on read so all 12 pre-split blocks still
  parse (a required group would have made `parse_run_blocks` skip them and the ledger go
  silently blind to its own history), mandatory on write. `ledger.py` gained form-matched
  binding and baselines: a holdout run must never become a dev entry's comparator, or a
  cross-population delta gets presented as an effect.
- **`plant_vitality.py`** — saturated / discriminating / failing / insufficient per plant,
  as an authoring-cycle pointer and never a gate or a deletion driver. First real reading:
  **11 saturated, 11 discriminating, 13 failing, 3 insufficient**. K=4 is provisional and
  carries a dated debt saying so.
- **Fixed a live instrument-record leak:** `test_gate_yield.py` drove the real rollup seven
  times while only two call sites passed `--response-md`, so 88 fixture-dated rows had been
  written into the committed `docs/calibration/guard_response.md` — the 2026-07-28 G5 class,
  one file over. Redirected at the source, pinned by a byte-identity check, and the
  fabricated rows removed with a dated correction in the file. The two real rows stand.
- No SKILL.md change, deliberately: the doer must not learn which plants are held out.

## 1.28.0 — 2026-08-06

**Guard calibration in BOTH directions — a guard's claim about itself is an unverified
claim.** Two field reports and one question from David converged on the same spine. He
watched a guard block a compound command and watched me "re-run it in pieces", and asked
the right question: is that compliance, or the model routing around the guard? The audit
said compliance in all four blocks — the flagged action was dropped every time, never
performed by another route — but the question was better than the answer, because from
outside the two are indistinguishable and my narration never said which it was.

Then the guard itself turned out to be wrong. Its docstring promises "reads are always
fine"; it blocked a READ of the unlock journal, because its write-verb list matched a
Python loop variable named `ln`. Two more false-positive classes came out of the same
read. Meanwhile Cheliped's field report carried the mirror image: a guard meant to block
privileged commands matched program basenames case-sensitively while the only copy on the
host lived in a capitalised app bundle, so running the test suite reconfigured the
developer's machine for months — and the docstring, the handoff and three later docstrings
all repeated the false claim. Nobody tests the safety net, because testing it feels like
distrusting it.

### The new house bar
- **Every blocking guard ships a two-directional calibration table** — BLOCK rows are every
  documented bypass, ALLOW rows are the guard's own stated contract, and each real false
  positive or real bypass is frozen as a dated fixture. Narrowing a guard is not amnesty:
  the block rows must survive every narrowing. (§13; HACK_CATALOG **H13**.)
- **`test_lock_guard` fixed in three classes** and calibrated against all four of this
  session's real false positives: write verbs now only count at a command position, an
  inline write is matched against ITS OWN target path, and a `cd` outside the project root
  takes the command out of scope.

### Auditable guard interactions
- **`bin/guard_note.py`** — at every guard block, record the three clauses: what it
  objected to · whether that action was performed by ANY other route · what was dropped.
  Rows ride the existing single write path (`_common.log_yield_event`) stamped
  `source: "agent"`.
- **`gate_yield rollup` prints `blocks N · accounted M · UNACCOUNTED N−M`** per gate into
  `docs/calibration/guard_response.md`. The property that makes a self-report worth
  anything: the HOOK writes the blocks, the agent writes only the responses — silence
  cannot produce a clean record, only a visible unaccounted count. `PERFORMED ELSEWHERE`
  is reported by name.

### New advisory guards
- **`exitcode_guard`** (PreToolUse Bash, warn) — a verifier piped into another command
  reports the PIPE's status, not the checker's. Two live instances in two days in the two
  repos that check each other: I gated a commit chain on a piped gate run and pushed a
  repo-red commit; the CIVerd runner masked a pytest exit the same way.
- **`exhaustive_claim_guard`** (PostToolUse, warn) — a test whose name or message claims
  *every / all / no other / exhaustive* must say in one line what a violating case looks
  like and how it would SEE it. Cheliped's parity test was genuinely exhaustive over
  deletions and structurally blind to the path that deleted nothing; it could not have
  failed on the real bug. (HACK_CATALOG **H14** — and note a 100% mutation score is blind
  to it: mutants perturb the listed paths.)

### Doctrine (Cheliped's five asks, all adopted)
§2 adversarial content as its own edge category · §12 the exhaustiveness rule · §13 guard
self-claims · §9 `/security-review` at the phase boundary that INTRODUCES the surface, not
at merge · §7 a quarantine marker is not real until something deselects it.

### Ledger and corpus integrity
- **`calibration/ledger.py`: the EPOCH is now the primary baseline**, not a fallback —
  CIVerd's correction. Their runner deepens to `--depth 200`, so my shallow-clone diagnosis
  was wrong; the real mechanism is that the box has ZERO TAGS, so `--baseline-rev v1.22.0`
  never resolves there. Right fix, wrong reason, corrected in the docstring rather than
  only in a commit message.
- **Three more approved corpus plants reverted to their v1.26.0 bytes.** Once CIVerd
  shipped its `--tags` fix, the integrity check ran against v1.26.0 instead of v1.22.0 and
  caught 2026-08-05 oracle edits that had been legal only because the older window could
  not see the files. My journal entry that day said the rule did not cover them — reasoning
  from the baseline WINDOW rather than the RULE, which is unconditional. Six plants now
  await supersession; all six are in `PROMOTION_QUARANTINE` so a known-defective oracle
  cannot harden a false miss into BLOCKING. The lesson generalises: an integrity floor
  implemented against a moving baseline is weakest on the NEWEST material.

## 1.27.0 — 2026-08-05

**The measured update loop — stop experiencing improvement and start verifying it.**
Process mutations (agent-brief fixes, oracle adjudications, guards, knobs) landed with an
IMPLICIT expected effect that nothing ever checked. Plan-review adversary dispatched
(ISLANDS 10); all findings folded — including the fatal one, that no shipped surface would
ever have passed the new `--class`, leaving the fix dark by starvation.

- **testlock override semantics, PAID.** `gate_yield` counted EVERY journaled unlock as a
  block adjudicated a false positive, so four cycles of the normal red-first
  lock/implement/unlock rhythm printed `RETIREMENT CANDIDATE: testlock` — the instrument
  recommending retirement of the strongest anti-gaming defense there is, with zero real
  false positives. `tdd_lock.py unlock --class {phase|feature-end|test-wrong|gate-wrong}`
  now names WHY; only `gate-wrong` adjudicates. `test-wrong` is deliberately not a false
  positive — stopping to say why a test was wrong is the lock working. A 7th `fp` column
  carries it; `parse_md_rows` reads a missing cell as `None`, never 0. Pre-fix rows stay
  byte-identical and report as UNCLASSIFIED HISTORY — never retroactively classified.
  Replayed against the motivating artifact (`119e2de`) with a negative control proving a
  genuine candidate still flags (§13 v1.25).
- **H12 — self-serving adjudication**, the vector this necessarily creates: the agent
  picking the class is the one that wants out. Defended by asymmetric cost (`gate-wrong`
  refused under 30 chars naming which block), a `class_mismatch` flag recorded beside the
  stated class and never rewriting it, and a `/grade` read.
- **The improvement ledger** (`calibration/ledger.py`, `docs/calibration/ledger.md`,
  append-only under integrity rule (a)). Entries pre-register scenario + direction + claimed
  rep movement + mechanism BEFORE the diff; the first run measuring a strictly-descendant
  tree scores them. Binding is commit-ordering, not a date — the original spec's date rule
  missed its own scoring run. Verdicts describe MOVEMENT, not k/k: scoring CONFIRMED only at
  k/k means `P = p³`, so an 80% bar demands per-rep `p ≥ 0.928`. Coverage is sha-cited, so a
  back-filled entry cannot cover. The gate blocks on PROCESS, never the hit rate.
- **`power.py`** ships with it, because it is the source of the INCONCLUSIVE threshold: at
  3 reps only 0/3→3/3 is significant (Fisher p=0.050), so significance is a cycle-level
  sign-test claim needing ≥5 moved entries.
- **The 08-04 cycle, scored honestly:** 6 HIT · 5 FLAT · 1 REGRESSED · 2 INCONCLUSIVE, with
  aggregate recall unchanged across the two runs. Seven dated four-cause follow-ups. The
  original ≥80%/<50% bars retired as mis-specified, with the arithmetic recorded.

## 1.26.0 — 2026-08-05

**Seam contract — a test cannot catch a mistake it also makes.** Adopts the Cheliped
seam-contract proposal (`/runmode`/`/apps` shipped green through every gate and did
nothing visible: handlers returned `message`, the adapter contract was `post_message`,
and the tests asserted on the return — implementation and tests shared one wrong belief).
Both plan-review adversaries dispatched (ISLANDS 5 / MIXED 4); all findings folded.

- **§1 "Test at the seam you don't own":** the value must be observed ARRIVING at the
  caller you did not write, never merely leaving yours. Review-checkable tells: every
  assertion reads an object your own code constructed with no consumer represented =
  SELF-CONSISTENCY test; corollary (the §1 trigger question at the seam) — if the test
  still passes with the other side of the seam DELETED, you tested yourself. Partition
  sentence locates it among §1's seam-shaped rules.
- **§4 "What mutation score does NOT cover":** the score grades tests against YOUR code
  and is structurally blind where test and code sit on the same side of a misunderstood
  seam (100% and invisible in production). Landed on ALL FOUR claim-bearing surfaces —
  SKILL §4, the mutation-runner brief, /mutate, README (G1/F1: agents receive briefs,
  not SKILL; the score-delivering surface must carry the limit).
- **§0 emits at FIELD granularity** (+ /tdd-plan mirror): cite the file:line in the
  consumer that reads the specific field; granularity partition stated once
  (topic → registry R-WRITE-ONLY; field-instance → §0/§6c). integration-adversary brief
  sharpened to match ("a consumer is named by the LINE that reads the specific field";
  dangling-flows demand gains received-but-never-read fields).
- **§6c family parity sweep — the Tier-1 registration bullet rewritten in place (F2):**
  registration uniqueness + dispatch-order reachability + HOST-CONTRACT parity as ONE
  repo-local, vacuity-guarded test enumerating the family from the REAL registry
  (repo-local by construction — a generic scanner cannot import arbitrary registries;
  resolves the doctrine-declared-but-never-implemented scanner entry). Parity naming
  disambiguated (surface/consumer/family). /integration-audit standing mechanisms +
  /tdd-plan prompt gain it (G6). Dogfood (G5): this repo's own commands family sweep
  gained the mandatory independent-roster vacuity guard it lacked.
- **HACK_CATALOG 2026.08:** H11 (self-consistency test) with the H9 partition
  (existence vs direction); framing widened to threat-model (honest-miss classes named);
  H11 guard-map row = family parity sweeps + the corpus pair.
- **Corpus:** H11 pair live-authored and fixture-verified (plant: suite green + cli
  silent, exit 0 — the origin shape; control: single variable flipped, message rendered),
  queued for approval. §13 deviations stated: the motivating artifact is cross-repo, so
  the pair cites the proposal doc + HACK_CATALOG H11, not a local pre-fix sha; the prose
  family-parity doctrine itself carries no calibration artifact — the pair calibrates the
  adversary leg.
- **CIVerd (Phase 0, house channel):** `docs/recommendations/civerd-seam-contract-2026-08.md`
  — one engine ask (parity-sweep vacuity check class, planted-probe calibrated), the
  armed-surface piece restated as David's dated root-config action (mechanism shipped
  2026-08-03), repo-side parity-roster precondition named. SEAM-CONTRACT FORWARDED +
  REPORT-BACK debts (2026-09-15, string-pinned) so the doc cannot rot unactioned.
- Debts: V1.26 GATE-SURFACE CALIBRATION + V1.26 CORPUS QUEUE (2026-08-17), TIER-2
  FIELD-PAIRING SWEEP deferral (2026-09-15, David's call — the mechanical form of field
  granularity gets its own red-first cycle). All boundary-pair pinned.

## 1.25.0 — 2026-08-04

**Guard calibration — a guard is not trusted until it has failed on the bug that birthed
it.** Adopts the Cheliped proposal (a guard that excused the pre-fix shape of its own
motivating defect: red-first in ritual, never failed for the right reason); both
plan-review adversaries dispatched, all 14 findings folded — including two live v1.24
sweep bugs their probes proved.

- **§13 guard-calibration rule:** a defect-born guard is REPLAYED against the motivating
  artifact (`git show <pre-fix-rev>:<file>`) before trust; the defect shape is frozen as
  a planted fixture citing the pre-fix sha (the anchor shared with corpus plants and any
  engine-side replay recipe). Reachability cross-refs from §6 (tripwires) and §6c
  (sweeps). Briefs adopt it: red-first-verifier (right-reason includes the pre-fix
  artifact), tripwire-auditor (EXERCISED asks for the motivating defect shape),
  planted-error-probe (prefer real historical defects over synthetic mutations).
- **§1 single-home additions:** the generalized trigger question ("what would still be
  true if this were broken?" — fixture form kept as its special case); assert the
  resulting STATE, not the action; an `except` hiding a programming error is a proxy for
  "this worked" (never wrap the guarantee line); the seam-fabrication rule — a double may
  fake BEHAVIOR, never supply a seam production lacks (`create_autospec`/`hasattr`
  checks). §12 applies the trigger question to claims evidence. HACK_CATALOG gains H9
  (seam fabrication) + H10 (guard excuses its motivating bug) with guard-map rows.
- **dataflow_sweeps fixes (adversary-proven live bugs):** `checked` credits only VERIFIED
  sites — an all-dynamic scan now refuses instead of exiting 0; exemption-entry
  violations (malformed/expired/stale/user-facing) ALWAYS block, even under ghost-gates'
  advisory tier; stale exemptions fail closed only when the target's file was actually
  scanned (outside-scan targets print non-blocking); unresolvable sites carry per-site
  `<dyn:EXPR>` names an exemption may target — §6c's "dynamic templates get a NAMED dated
  exemption" is now mechanically true; the Cheliped layer_10 shape frozen as the sweep's
  motivating-artifact fixture (sha slot awaits the pilot's report-back).
- **overmock_guard:** `create_autospec` de-listed from the mock-delta (it is the
  prescribed seam check); H9 fabricated-seam advisory (SimpleNamespace grafting a
  callable member), planted pair in test_hooks.
- Corpus: four H10 proposals live-authored (plant+control per target agent), queued for
  approval; V1.25 GATE-SURFACE CALIBRATION + V1.25 CORPUS QUEUE debts (2026-08-17,
  string-pinned). Gated plan: `docs/plans/gated/2026-08-04-guard-calibration.md`.

## 1.24.0 — 2026-08-03

**Dataflow Liveness (§6c) — nodes are necessary; edges are the truth.** Origin: the
Cheliped excavation (2026-08-03) — the node-level wiring net caught 0 of 12 post-safeguard
escapes because every one was an EDGE failure (flows with no live consumer, values with no
reader, fixes verified at the supply end). Plan:
`docs/plans/dataflow-liveness-implementation-plan-2026-08.md` (adversaried at plan stage —
10 findings + 2 minors, all folded; upstream review doc never committed, T1–T7 grounded
inline from the excavation table).

- **SKILL §6c (D1–D6):** new section — flow-kinds checklist (incl. silent-default
  boundaries + schedule overlap), the T1–T7 escape taxonomy, two decidability tiers,
  sweep governance (exemptions = house debt shape; excluded share audited mechanically),
  migration consumer-parity DoD. §0 gains the scale-gated flow table
  (`flow · producer · consumer · liveness test`); §6 + /tripwire report
  `Tripwire: N/N (+ FLOWS M/M)`; §6a sharpened (evidence-tier ladder
  `config-read < import < runtime-probe < composition-root`, monitors record SUCCESS,
  reachability through the real dispatch order — last-write-wins banned); §12 gains the
  output-end proof rule; §13 tracks escapes BY CLASS.
- **Gate surfaces (D7–D9):** /integration-audit gains the FIFTH darkness class
  ("Dangling dataflow", T1–T7 hunt list, explicit partition boundary);
  integration-adversary hunts a SIXTH island pattern (dangling flows — forced verdict
  lines untouched); /tdd-plan renders the flow table + migration old-seam enumeration.
- **`bin/dataflow_sweeps.py` (D10):** stdlib-only Tier-1 reference sweeps —
  render-pairing (AST, both directions reported distinctly; blocking), ghost-gates
  (Tier 2, ADVISORY by default, `--strict` opt-in, promoted only on pilot data),
  exemption-prose (fail closed). Exit 0/1/2/3 (vacuous-refusal = 3, distinct from
  usage 2); pinned summary line; exemptions in the house debt shape via the extracted
  `bin/_debt.py` (capability_registry now shares the same date logic — one debt shape).
- **Registry (D12):** capability-level `user_facing` audience attr (bool, R-SCHEMA);
  all 14 entries annotated; `dataflow-sweeps` registered (activation ON) with the two
  dated D19 debt lines; `civerd-integrity.yml` plant_targets += dataflow_sweeps.py.
- **Self-sweep + trend (D13):** `civerd_gate.sh` runs a BLOCKING render-pairing sweep on
  this repo's own bins (140 sites; planted-probe verified live);
  `gate_yield.py dataflow-rollup`/`dataflow-trend` commit one row per sweep per
  calibration cycle and flag a growing excluded share; run_calibration prints both.
- **Installer (D11):** vendored-SKILL == canonical rewrite-aware equality assertion in
  test_installer (subsumes all future content markers); refresh prompt VERIFY/ADOPT
  carry §6c + dataflow_sweeps.py.
- **Calibration (D14–D16):** 43-check planted/paired-control suite for the sweeps;
  first §6c corpus batch authored (2 plants + 2 controls in `corpus/proposed/`, awaiting
  human approval); `apply_edits` create-capability promoted to owned dated debt
  (calibration-loop, 2026-09-15, trigger string-pinned). Changed gate surfaces are NOT
  trusted until their live-calibration rows land (~2026-08-10 run).
- Gated plan: `docs/plans/gated/2026-08-03-dataflow-liveness.md` (inert until the
  existing repos.yml arming debt is paid).

## 1.23.0 — 2026-07-30

**The two ratified CIVerd briefs: plans-in-repo + deliberation capture** (built in a
worktree during the live calibration run; plan adversaried twice + CIVerd-CTO amendments
folded; David's ships-on-or-triggered directive applied to every OFF state).

- **Runs-guard (D0, arch-F9):** in check()-style suites a `def test_*` that main() never
  calls satisfies the engine's `test_passes` (exists + unskipped + gate-green) while never
  running. New AST guard in test_aaa: every module-level test_ function must be REFERENCED
  in its own module — upgrades every current and future `test_passes` predicate in this
  repo from "exists" to "runs". Planted-orphan test proves the guard can fail.
- **plans-in-repo (D1):** `bin/plan_block.py` — `scaffold` writes
  `docs/plans/gated/<slug>.md` with exactly one engine-conformant `civerd-plan` block
  (`--repo` REQUIRED — a dirname default from the mandated worktree is an instant
  MALFORMED); `validate` re-parses strictly, requires byte-identical re-emission for
  active plans, and shells to `civerd plan-check` when on PATH. `satisfied`/`abandoned`
  are structurally unemittable (no argument path). Slug boundary tested AT 59/60
  ("plan."+slug ≤ 64). **Engine-blessed conformance corpus** (19 cases; verdicts from the
  engine's own parse path via `civerd plan-hash`; stamped `blessed_by_engine_version`):
  its FIRST replay caught 4 live unsafe drifts — our charset regex accepted `/etc/passwd`
  and `../` escapes the engine refuses; fixed by mirroring `_safe_relpath` exactly. The
  path-escape cases stay in the corpus as permanent plants. `/tdd-plan` now closes with
  the land-approved-plans-in-repo section (weaker-truth semantics table, permanent slugs,
  prose section for research/docs, never gate small work).
- **Deliberation capture (D2+D3):** the capture plan itself is the dogfood — authored by
  the new tool at `docs/plans/gated/2026-07-30-deliberation-capture.md` (4 predicates).
  `hooks/scripts/capture.py` (UserPromptSubmit + Stop, explicit `--event` args in
  hooks.json = the registration is the fact): append-only per-day JSONL store (dir 0700,
  files 0600, single-os.write lines), 10-field whitelist with deliberately NO status
  field, v1 redaction with sha256 over POST-redaction text only (no crackable residue of
  redacted credentials), backward chunked transcript scan for long assistant finals with
  `truncated: true` never a silent partial, O_EXCL+TTL sentinel dedupe (plugin+vendored
  double registration collapses to one record; a deliberately repeated identical prompt
  is still captured), fail open always exit 0 never stdout, sidecar error log.
  `bin/deliberation.py close/stats` — the ONLY emitter of the closure shape
  (event-sourced; conveyed ≠ ratified; only David closes). 38 planted-input tests.
- **Answer-key exclusion:** `calibration/child_env.py` pins `TDD_PLAYBOOK_HOOK_CAPTURE=off`
  for BOTH nested-claude spawn sites (`run_calibration.run_agent` AND
  `author_plants.cmd_author` — the plant-authoring adversary's output IS the answer key),
  proven by hostile-parent env-dump stubs; env `off` BEATS the enrollment marker by a
  named test.
- **Activation (David's nothing-ships-dark directive):** enrollment marker
  `<store>/ENABLED` written BY THE BUILD on David's machines; doctor gains the
  informational `capture: ON/OFF` line; the weekly calibration bundle now includes the
  doctor check. Every OFF state carries an ARMED dated trigger: engine-side plan arming
  (debt 2026-09-15), enrollment sweep (2026-08-31), store consumer (2026-10-31) — all
  string-pinned by --as-of boundary tests that name their debt in the violation (an exit
  code alone passes for the wrong reason once earlier debts expire).
- **Registry:** `plan-authoring` (deploy_surface mirroring the release gate's: divergence
  = plans land inert) + `deliberation-capture` (emits → named consumers; v2 shingle
  matcher is the PRIMARY candidate with the label constraint binding NOW: unmatched spans
  are "unattributed", never "David's own words"). Docs:
  `docs/plan-gating-and-deliberation-capture.md` (no-README brick hazard, store posture
  with honest labels, guard_env hand-off).

## 1.22.0 — 2026-07-30

**The deletion ratchet, dismantled — lift/ratchet proposal set A** (three review passes +
two plan-adversary passes; 18 findings folded, three of them refuting the plan's own
premises before build):

- **Coverage invariant (R1 part 1):** every calibratable agent needs a PLANT — controls
  prove restraint, not coverage. Landed RED on `integration-adversary` (the agent whose job
  is finding uncovered things was itself uncovered — §6a at the meta level) and turned
  green with the `island-write-only-plan` pair. The authoring loop consumes it: uncovered
  agents become priority targets in the adversary brief.
- **House output contracts:** `integration-adversary` gains `Verdict: CONNECTED/ISLANDS`,
  `edge-case-adversary` gains `Coverage: ADEQUATE/GAPS` — AGENT_CONTRACTS-pinned, so
  calibration oracles anchor on shipped contracts, never task-invented formats.
  `TREE_TOUCHING_AGENTS` → `NOT_HEADLESS_CALIBRATABLE`, pinned exactly (the post-invariant
  exemption list is the darkness hatch).
- **Symmetric-harness-break plants:** `red-first-symmetric-break` (fails-both-sides proves
  nothing → NOT VERIFIED) and `mutation-phantom-run` (the 2026-07-28 stale-pyc twin
  incident, designed in → UNMEASURED), each with a clean control. Suite 24 → 30; all six +
  both amended briefs live-calibrate at the ~2026-08-10 run.
- **Gate-surface removal rule (d):** SKILL `##` sections, agent briefs, and command files
  removed vs baseline are integrity-RED unless journaled in the new append-only
  `calibration/gate-changes.md`; additions stay free. Gate removal now costs what addition
  costs — and the rule closed a live hole: 7 of 11 command files were silently deletable.
- **Wilson intervals** on recall AND FP, header + stdout (`3/3 [0.44–1.00]` — what a point
  estimate at three reps hides). **Vendoring containment** pinned on the fact (COPY_TREES
  can never escape the plugin). **The quarterly clock**: `docs/calibration/quarterly.md` on
  the existing staleness gate (100 days, release-gate loud) carries the deferred
  lift/cross-tier bundle; the QUARTERLY BUNDLE registry debt (expires 2026-11-01, trigger
  proven by violation-string, never exit-code) is the backstop. Nothing deferred is prose.

## 1.21.0 — 2026-07-28

**The gate itself was theater over `calibration/` — probe run 2's deepest catch.** CIVerd's
planted-error probe reported `check_scoreboard_integrity` "essentially untested"; local
sweeps killed 7/7 vs the harness. Both were right: the module's 110-check harness existed
but the GATE never ran it — four stacked failures (pytest collects ~0 items from
script-style suites; the python3 loop never included `calibration/`; `test_aaa`'s harness
path was `dirname²` off, so the isfile guard silently skipped it since the file was
written; and `test_aaa` was inert under `python3` — no `__main__` runner). The v1.15
false-green class, one layer up, caught only because an engine-owned probe measured the
gate from outside.

- NEW `scripts/civerd_gate.sh` — THE blessed gate entrypoint (plugins loop + calibration
  harness); `civerd-integrity.yml` `suite_cmd` now execs it; planted-tested (a failing
  suite must fail it). CIVerd's `tests` check and `planted_probe` point here.
- `test_aaa`: REPO path fixed (harness genuinely in SUITES, 13 suites), standalone
  `__main__` runner added (failure via bare assert — the H5 guard correctly BLOCKED a
  `sys.exit` form first, live), and a new guard: pytest-collectable `test_*` functions
  must need zero args (the fixture-error class that had the gate RED at `5abe347` — my
  own bug, fixed by renaming the offender).
- Kernel probe survivors killed (run-2): `_ed25519_verify` — non-bytes inputs now proven
  to fail CLOSED (the or→and mutants raised TypeError; contract says never raise);
  `verify_verdict` — non-list records / non-dict snapshot/claimed_report refuse as
  `malformed` (reason strings are contractual), `_cache_dir` + `fetch_ledger` asserted
  offline. Re-sweeps: 12/12, 18/18, 7/7 killed.

## 1.20.0 — 2026-07-28

**H8 — the guards' own RUNNING leg.** Live incident: plugin enablement is USER-scope, and a
mis-click disable in another repo darkened the entire guard layer across all repos for a
full working day — three releases shipped with zero mechanical enforcement and zero alarms
(release verification held: suites + CIVerd are command-line; every session-side guard was
theater). Committed ≠ deployed ≠ RUNNING was doctrine for everything except the enforcement
layer itself.

- `intent_nudge` (UserPromptSubmit) beats `.claude/playbook-guards-heartbeat` on every
  prompt — unconditionally, before the `NUDGE=off` check, never raising.
- `_common.guards_dark`: a latest commit that postdates the heartbeat = work committed
  while no guard fired. Installer doctor → `GUARDS DARK`, exit 1 (with the user-scope
  enablement explanation); `run_calibration` → loud warning on the David-run surface.
  Missing heartbeat is informational only — fresh clones never false-RED.
- Suites isolate the heartbeat path (tests must not fake liveness); planted tests for the
  beat, the dark verdict, and the fresh-clone case. HACK_CATALOG H8 + map row; release
  gate gains `install_into_repo.py --doctor .` (would have caught the incident at v1.17).
- Honest limit stated: local + forgeable — catches the accidental outage; the adversarial
  variant is the engine's contracted `guard_env`/diff-integrity territory.

## 1.19.0 — 2026-07-28

**Bypass sweep — the remaining evasion routes, closed locally or contracted to the engine.**
Adversarial pass with David ("what's a smart model's next move?"), five verified holes:

- **Silent demotion (closed locally, contracted engine-side).** `emit()` now logs a
  `suppressed` yield event when findings fire under `off` — a muzzled gate is never a quiet
  one; `gate_yield` (6-col rollups) surfaces SUPPRESSED FINDINGS loudly; the installer
  doctor flags STANDING DEMOTION env blocks in settings; a planted test keeps this repo's
  committed settings demotion-free. Engine contract gains **§1.5 `guard_env`**: settings
  env-key diffs become a ratifiable signed signal.
- **H2-via-shell on unlocked files (engine-side).** A `python -c` test-gut never passes the
  Edit-event guard; the write-path-independent counter is §1 diff-integrity's
  assertion-count regression — now explicit in the contract and carried as dated debt.
- **Grandfather growth (closed).** `GRANDFATHERED_PLANT_IDS` pinned exactly — the pair
  quota can no longer be bypassed by adding to the list.
- **Self-journaled oracle weakening (visibility now, token engine-side).** The integrity
  checker prints every journal addition since baseline; the §1.4 ratification store makes
  it need a human.
- **Agent-brief softening (engine-side).** §1.3 extended watchlist covers `agents/*.md`
  (deletion/emptying hard-floor RED; changes ratifiable).
- **Weak-plant streak flag.** A plant that never failed across recorded live runs is
  flagged by the runner — easy plants inflate recall while the gate decays.
- **`validate --as-of` (new flag) + an honest catch:** the previous trigger "proof" was an
  argparse error exiting 2 — nonzero for the wrong reason, the script-adversary's own
  class, self-inflicted. The flag now exists with clean semantics (1 = EXPIRED, 2 = usage,
  planted-tested) and doctrine cites the precise form.
- **Yield-record hygiene:** suite-level env isolation + a pollution-guard planted test;
  removed a committed `gate_yield.md` that contained this session's own test exhaust
  masquerading as cycle data (`git add -A` swept it in — the record restarts clean with
  the first real cycle).
- Engine-side closures consolidated as dated debt on `integrity-guards`
  (owner david, expires 2026-09-15; proven: `--as-of 2026-09-16` → exit 1).

## 1.18.0 — 2026-07-28

**H7 — roadmap laundering becomes a named, guarded attack vector.** David's insight, from a
live instance the same day (the doer model deferred R3 — doer calibration, the instrument
that would test the doer itself — to a roadmap section with no owner): scope deferral without
a trigger is the one maneuver every existing guard is blind to, because guards watch
artifacts that exist and laundered scope was never in any baseline. It also looks like
discipline, so it is repeatable and selective.

- `docs/HACK_CATALOG.md` gains **H7** (+ guard↔entry map row): the maneuver, why it evades
  H2/H5/diff-integrity, the selection-pressure signature, the live evidence.
- `tripwire-auditor` gains the **PARKED leg**: every deliverable disposed of by deferral is
  audited as a disposal — `Parking: LEGITIMATE` needs a named owner + dated expiry + a
  mechanism that fails loudly at expiry; anything less is `Parking: DARK` and blocks. Legal
  decide-or-park is explicitly NOT a finding (the paired control measures that).
- SKILL.md §0 spec-integrity: deferral needs a trigger, proven in the same commit
  (`validate --as-of <expiry+1>` nonzero) — prose deferral is the maneuver.
- Calibration pair shipped: `roadmap-laundering` + `control-parked-deferral`
  (24 scenarios: 14 plants / 10 controls), with stub-planted harness tests for both
  directions. Live calibration of the amended auditor rides the ~2026-08-10 run
  (agent-prompt change → calibration before trust, §13).

## 1.17.0 — 2026-07-28

**Eval-discipline hardening — the calibration suite now meets the standard the doctrine sets
for everything else** (from the 2026-07 CTO analysis, all four recommendations, adversary-
reviewed plan; R3 premise-plants deferred to the next corpus cycle — roadmap §E):

- **R1 — repeat sampling + three-state verdicts.** `run_calibration.py --repeat` (default 3;
  §5a — one roll is a coin flip): `PASS` only at k/k, `AMBER` on a partial catch (nonzero by
  default, promotes to BLOCKING on consecutive AMBER — matched per scenario id, mechanically),
  `**BLOCKING FAIL**` at 0/k, `INVALID` when nothing ran (excluded from n, never extends
  staleness freshness). Mechanical failure-mode column (`missed-entirely` / `found-but-hedged`
  / `wrong-verdict-line` / `env-failure` / `timeout`) derived from typed runner status + the
  pure oracle. Run blocks carry the repo SHA + DERIVED composition (`selected N of M`).
- **D0 — one validator, one parser.** `validate_scenario` (agent roster DERIVED from
  `agents/` minus tree-touching) now serves shipped scenarios, corpus plants, and proposals;
  NEW `history_format.py` is the sole owner of the scoreboard format (check_staleness imports
  it).
- **R2 — paired clean controls; FP measured.** Every plant class ships a `control_for` clean
  control (9 controls / 13 plants across 22 scenarios); pair quota enforced at authoring, at
  `--approve`, and as a dry-run set-invariant with a self-cleaning dated grandfather list.
  The scoreboard reports recall AND false-positive rate separately.
- **D3 — calibration trust floor.** NEW `check_scoreboard_integrity.py` (exit 0/2/3, fail
  closed): history.md append-only vs a git baseline, approved corpus immutable + growing,
  DIRECTIONAL oracle rule (removals/replacements RED unless journaled in the append-only
  `calibration/oracle-changes.md`; tightenings always pass). Runs in the suite vs the latest
  release tag. CIVerd contract §2b + `civerd-integrity.yml` handoff created.
- **R4-lean — gate yield.** §13 names BOTH decay directions; `_common.emit()` logs every
  block/warn to one event log (env-pointable, fail-safe), `tdd_lock` unlocks land as override
  events, NEW `bin/gate_yield.py` rolls the log into committed per-cycle rows and prints
  retirement candidates only from ≥2 committed cycles (absent data = UNMEASURED). Wired into
  `run_calibration` end-of-run. `.gitignore` + installer-written `.claude/.gitignore` keep
  runtime exhaust out of git here and downstream. Demotion machinery deliberately deferred
  until the first candidate exists.
- Registry: `scoreboard-integrity` + `gate-yield` capabilities registered;
  `calibration-loop` debt re-dated to the first live run under the new instrument.

## 1.16.0 — 2026-07-27

**Operational-surface discipline — deploy-surface plan block + script-adversary agent (CIVerd
capability-gaps report, Deliverables B & C).** Closes the remaining two proposals from the report;
Gap 2.1 (operational planted-error calibration) stays deferred as owned registry debt.

- **B — §0 deploy-surface plan block.** Alongside the integration surface, a deliverable that RUNS
  where the session doesn't control it (VPS, daemon, installed plugin, vendored copy) now answers
  four questions in the plan: *Runs where / Gets there how / Verified how / Divergence*. "I'll paste
  files" is a FINDING, not a plan. And the **deploy path is deliverable #1** — build the thing that
  proves/updates the running state (`update.sh` + a version-echoing `verify_install.sh`) before the
  feature, same logic as red-first.
- **C — the `script-adversary` agent** (`model: opus`, F3). A fresh-context, refute-framed safety
  review of operator-facing scripts (health checks, probes, deploy/verify scripts). One load-bearing
  rule — *a probe must take its target as an argument, never touch stdin, never write, and
  distinguish "refused" from "failed for any other reason"* — and four failure modes: blocks-on-stdin,
  destructive-probe, passes-for-the-wrong-reason, guessed-diagnostics. Verdict `SCRIPT-SAFE /
  UNSAFE(n) / MIXED(n)`. Dispatched from §0 on any operator-facing script; added to the §13 model-floor
  list, `author_plants.py` KNOWN_AGENTS, and `test_agents.py` AGENT_CONTRACTS + the F3 pin set.
- Calibration scenario `script-unsafe-probe` (fixture `calibration/fixture/verify_install.sh`): a
  key-readability control rewritten into a `tee`-based, any-nonzero-is-PASS probe — the agent must
  flag it UNSAFE. Live suite now 10 shipped scenarios (14 with corpus); dry-run 14/0.
- Pinned by `test_agents.py` (§0/§13 needles, agent brief, planted fixtures — 230). This completes the
  remote-runtime/operational discipline arc: v1.14.0 (A) + v1.15.0 (gate-honesty) + v1.16.0 (B+C).

## 1.15.0 — 2026-07-27

**Gate-honesty guard — `pytest` could false-green a failing suite (found by stress-testing the
CIVerd gate).** Before shipping the next doctrine work, we planted errors to prove CIVerd's gate can
actually go RED. It exposed a real false-green: CIVerd runs `pytest -q plugins/tdd-playbook/tests
calibration/test_harness.py`, but this repo's suites are SCRIPT-STYLE — `check()` counts failures
and only `main()` sums them and `sys.exit(1)`. Under `pytest`, a `test_*` function calls `check()`,
the check fails, and the function returns normally → **pytest reports pass**; and the main()-only
suites (no `test_*` functions) are collected as zero tests and never run. Confirmed empirically:
a planted `check()` failure gave `pytest` exit 0 while `python3 file.py` gave exit 1. Every green
CIVerd verdict had been verifying little more than "imports without raising."

- **`tests/test_aaa_suites_via_main.py`** closes it with the one construct pytest cannot miss — a raw
  `assert`: it runs every sibling suite AND `calibration/test_harness.py` through their real `main()`
  (`python3 file.py`) and asserts exit 0. Now `pytest` and the `python3` loop agree, so even CIVerd's
  current bare-pytest command catches a real regression. A self-calibration test proves the guard can
  fail (a nonzero exit must be observed).
- The proper complementary fix is CIVerd's side: point its `tests` check at the repo's real gate
  command (`for t in …/test_*.py; do python3 "$t" || exit 1; done && python3 calibration/test_harness.py`),
  not bare pytest — documented for the `repos.yml` update. This release makes the gate honest
  regardless.
- Also a standing caution now in the record: a NEW script-style suite must expose its failures
  through a raw assert or this guard, never `check()` alone, or `pytest` will not see it.

## 1.14.0 — 2026-07-27

**Remote-runtime discipline — the RUNNING Tripwire leg (CIVerd capability-gaps report, Deliverable
A).** The Playbook's mechanical oracles (Tripwire wiring-liveness, planted-error calibration) were
scoped to *code in the repo you're sitting in*. The moment a deliverable runs elsewhere — a VPS, a
daemon, a vendored `.claude/` in another repo — there was no mechanical oracle, so verification fell
back to *reading output*, which is exactly where over-confidence lives. (Origin: a deployed engine
ran code 97 minutes / six commits behind while all four Tripwire legs "passed" about the laptop.)

- **§6 — a fifth Tripwire leg, RUNNING**, required only for remote deliverables: the deployed
  instance echoes the sha/version it runs, and a probe asserts it equals the intended sha. Report
  `Tripwire: N/N (+ RUNNING M/M)`. The SKILL description now names the fifth leg (968/1024).
- **§6a — version-echo convention**: "running == intended," the same assertion `verify_verdict.py`
  (`commit == SHA`) and `install_into_repo.py --doctor` (vendor stamp) already make. Deploy drift is
  wiring rot's remote twin; a health check that inspects the local checkout can't see it.
- **Capability registry — `deploy_surface` field** `{runs_on, gets_there_by, running_version_probe,
  divergence}`. `validate` FAILS a remote surface with no `running_version_probe` (`R-DEPLOY`);
  `doctor` lists remote surfaces and flags a missing probe. `civerd-release-gate` registered with a
  real `deploy_surface` — our own first RUNNING-leg example.
- **Folded Deliverable D doctrine**: §1 "assert the outcome, not the proxy" now reaches every CHECK
  (not just tests); §12 — "done" about a remote runtime is a claim needing a probe, never a commit
  sha, and the human-run step ships in the SAME message; §13 — grade WHO CAUGHT IT
  (self/accidental/human/peer) as the over-confidence signal.
- Pinned by planted-input tests: `test_capability_registry.py` (R-DEPLOY, 29), `test_agents.py`
  (§6/§6a/§1/§12/§13 needles + planted fixtures, 210). Deliverables B (§0 deploy-surface block) and
  C (`script-adversary` agent) follow as their own releases; operational planted-error calibration
  (Gap 2.1) is deferred as owned registry debt. Comprehensive plan:
  `docs/plans/remote-runtime-discipline-2026-07.md`.

## 1.13.0 — 2026-07-27

**Calibration staleness made mechanical (audit finding F5).** The 14-day calibration cadence — the
Playbook's ungameable anchor, whose scoreboard "IS the product" — was enforced only by a human
remembering to check `docs/calibration/history.md`. A decaying gate whose decay nobody is forced to
notice has been asleep for an unknown duration (§13).

- **`calibration/check_staleness.py`** (stdlib) reads `history.md`, finds the most recent dated run,
  and exits nonzero when it is missing, future-dated (broken scoreboard), or older than the
  threshold (default 14 days). `--as-of` injects the date so tests never touch the real clock;
  `--warn-only` surfaces the finding without hard-blocking.
- **Wired three ways** so staleness is impossible to miss: the release gate runs it `--warn-only`
  (loud, but a code release isn't wedged on a calibration chore); CIVerd runs it as a `staleness`
  check so the independent engine flags decay on its daily timer; and the `calibration-loop`
  capability's liveness probe now names the mechanical script instead of a prose reminder.
- Pinned by 9 planted-date tests in `calibration/test_harness.py` (a planted-stale scoreboard MUST
  be detected — a staleness gate that can't fail is theater). Harness 45/45.

## 1.12.0 — 2026-07-27

**CIVerd release gate — off-box, signed release verdicts (audit finding F4).** The Playbook could
verify its own work but had no INDEPENDENT check that the code shipped actually passed CI on a
machine the coding agent can't reach. F4 adds the hub side of CIVerd (the VPS CI engine): a release
is permitted only for a fresh, signed, GREEN run verdict of the exact release SHA, from a live
engine.

- **`bin/verify_verdict.py`** — verifies a memproof-2 bundle end to end (version, pinned issuer key,
  every Ed25519 signature, the `count`/`leaf_index` set rule, the Merkle fold, freshness, `ok`, and
  engine liveness). A lone heartbeat (commit `0x00…`) can never satisfy a real-SHA request; a
  forged `ok` flip is caught because it breaks the signature; absence (no verdict / stale /
  unreachable ledger / silent engine) is each its own RED reason, never a silent pass. No `--force`.
- **STDLIB-ONLY, by invariant.** Every bin here runs in any Claude Code sandbox / vendored repo with
  just `python3`. CIVerd's own runner installs only `pytest`, so a `cryptography` import would make
  the engine emit a permanent RED for its only subject. Ed25519 verification is therefore a vendored
  pure-Python verifier (`bin/_ed25519_verify.py`, verification-only — no signing/keygen).
- **Validated against the reference, not just itself.** `bin/_ed25519_verify.py` is pinned by RFC
  8032 §7.1 known-answer vectors plus negative controls (tampered msg/sig/key, non-canonical `S ≥ L`,
  small-order key) and an anti-fail-open `return True` mutant check. `verify_verdict.py` is
  cross-validated against **memrebel's golden corpus** — canonicalization (incl. the RFC 8785 UTF-16
  key-order trap that ASCII fixtures can't catch) and all 10 bundle-case reason strings must match
  the reference implementation exactly.
- **`scripts/release_verify.py` (decision D5)** — the EXECUTABLE release gate: the release tag is
  created only after `verify_verdict.py` returns 0 for the release SHA. A checklist line is a wish;
  this script (no bypass flag) is the control. Gates the release SHA actually shipped, not its parent
  (the parent skips the agent-written bump commit). CIVerd signs post-commit, so use `--wait-s`.
- New suites: `test_ed25519_verify.py` (14), `test_verify_verdict.py` (32), `test_release_verify.py`
  (10) — all stdlib-only. NOTE: `verify_verdict.py` ships IN 1.12.0, so the tag-gate is the standing
  control from 1.13.0 on (1.12.0 is dogfooded live against CIVerd's verdict for its own SHA).

## 1.11.0 — 2026-07-27

**Verifier-strength floor made mechanical (audit finding F3).** §13's verifier-strength policy
("never let the thing generating code outrun the thing checking it") was prose: every agent
inherited the session model, so a verifier silently ran on the doer's own tier — the same mind
checking itself. The two live BLOCKING FAILs earlier today (Fable-authored plants a haiku verifier
missed) were the empirical proof.

- **Model floor pinned** on the six judgment/adversary verifiers (`claims-verifier`,
  `tripwire-auditor`, `architecture-adversary`, `integration-adversary`, `edge-case-adversary`,
  `mutation-runner`) via `model: opus` frontmatter — live dispatch no longer floats down to a cheap
  session model. The three mechanical test-runners (`red-first-verifier`, `planted-error-probe`,
  `ux-probe-calibrator`) stay inherit: they run suites, not judgment, so tier barely moves them.
- **Calibration/production relationship documented (§13):** the frontmatter pin governs PRODUCTION
  dispatch only — calibration strips frontmatter and runs verifiers at a cheap tier (`haiku`) as a
  CONSERVATIVE lower bound (a plant a weak verifier catches, the pinned production verifier catches
  too). Two rules stated: raise the pins if the doer routinely runs above the pinned tier; the
  scoreboard surfaces the lag.
- **Scoreboard now shows the verifier-vs-adversary tier:** `docs/calibration/history.md` corpus rows
  record `<verifier> vs <plant-author>` (e.g. `haiku vs claude-fable-5`), so a verifier weaker than
  the model that authored the plant is VISIBLE, not just policy (the §13 ratio made mechanical).
- Pinned by `test_agents.py::test_verifier_model_pins` (+ planted fixture) and a `test_harness.py`
  scoreboard check. Suites: test_agents 191/191, harness 36/36, all 8 plugin suites, registry OK,
  description unchanged (958).

## 1.10.0 — 2026-07-27

**TEST-LOCK closes its shell bypass + protects its own state (audit findings F1+F2).** A
self-audit of the enforcement layer (mechanical vs prose) found the lock was Edit-only: the
`test_lock_guard` hook fired on `Edit|MultiEdit|Write` but the ONLY Bash PreToolUse hook was the
snapshot guard — so while a lock was active, a locked red test could be rewritten with `sed -i` /
`> file` / `git checkout -- test` / `rm` / inline-python, and the lock file itself (`tdd-lock.json`)
could simply be `rm`'d to self-unlock without the journaled reason. The shell IS the channel a
capable model reaches for; the guard now covers it.

- **F1 — shell channel.** `test_lock_guard.py` gains `bash_findings`: write-shaped commands
  (`sed -i`/`perl -i`, `>`/`>>` redirection, `rm`/`mv`/`cp`/`tee`/`truncate`/`dd`, `git checkout`/
  `restore` incl. revert-all `git checkout .`, and inline `open(path,'w')`) targeting a protected
  path BLOCK. **Reads and running the locked tests stay free** (only writes block — a guard that
  wedges legitimate work is the adoption killer). Wired into the Bash PreToolUse matcher in
  `hooks.json`. Honest bound: heuristic on the shell side (common write verbs, not every possible
  command) — the deeper backstop is the independent verifier (CIVerd/memrebel), not a perfect parser.
- **F2 — lock self-protection.** The lock's own state (`tdd-lock.json`, its journal,
  `tdd-pending-red.json`) and the enforcement itself (guard scripts, `hooks.json`, `settings.json`)
  are now protected surfaces (both channels) while a lock is active — deleting the lock or disabling
  the hook is blocked. The one sanctioned exit remains `tdd_lock.py unlock --reason` (which the guard
  does NOT block — verified).
- 24 planted-input tests (`test_hooks.py::test_lock_shell`) — every bypass blocks, every read/run/
  branch-checkout/journaled-unlock passes; the fifth test caught a real gap (a needle inside a
  `dir/path` redirection target) that was fixed before ship. SKILL §1 TEST-LOCK doctrine updated.
  Suites: hooks 89/89, all 8 plugin suites green, registry OK, description unchanged (958).

## 1.9.1 — 2026-07-27

**§4 consolidation — behavior-preserving refactor (no doctrine changed).** §4 had accreted ~16 flat
bullets mixing four concerns. Treated as a REFACTOR, not a rewrite: every load-bearing sentence kept
VERBATIM (so the `test_v16…v19_doctrine` pins — 176 of them — are the regression suite that
mechanically proves no rule was lost), only sub-headers and connective intros added.

- **§4 now reads scope → run → triage → hygiene** under four inline sub-headers: *Scope* (critical-
  only, roster admission, function-tier gating) · *Run & discover* (diff/phase/full cadence,
  per-module discovery loop, targeted-mutant mode + preflight) · *Triage survivors* (weak-vs-
  equivalent, the filter, the ledger, string-role classing) · *Anti-gaming hygiene*.
- **New §4a "Gate integrity — a gate can report green on nothing"** collects the false-green
  machinery into one navigable home (matching the §5a/§6a subsection pattern): the mechanical gate
  + floor, roster-entry-wired-to-gate, the two-axis vacuity guard, account-for-every-mutant, and
  killing-suite collection. A reader asking "why is my gate green?" now goes straight to §4a.
- Verified: 177/177 doctrine pins green (no rule lost), each moved bullet appears exactly once,
  SKILL description unchanged (958 chars), scratch-install parity holds. The §4 change is structure
  only — no doctrine reworded.

**First full live calibration since 2026-07-09 (`docs/calibration/history.md`).** All 9 scenarios
run on haiku — **8/9 caught on the first pass**, then 9/9 after one agent fix:
- The five scenarios added this session all validated LIVE on the first pass: `red-baseline-false-
  green` and `unmeasured-not-certified` (mutation-runner accounting), and both architecture-adversary
  scenarios — including `good-fix-single-source`, confirming the agent does NOT false-positive on a
  genuinely clean fix (the risk flagged when it shipped).
- One BLOCKING FAIL, fixed per the standing rule (fix the agent, never the plant): on
  `vacuous-mutation-scope`, given a scope naming the typo `apply_discuont`, the model "helpfully"
  hand-analyzed the real `apply_discount` and certified GREEN — it never noticed the named function
  doesn't exist. The `mutation-runner` vacuity guard now RESOLVES the named scope first and refuses a
  name that doesn't resolve, explicitly forbidding silent substitution of a similar real function.
  Re-run live → PASS. Pinned by a new `test_v19_doctrine` needle.

## 1.9.0 — 2026-07-27

**Mutation-discipline + test-honesty amendments** — three grounded lessons from a downstream session
that took a mutation score 52.5% → 91.2% across 8 modules / ~2,100 mutants. Each abstract rule was
already implicit in the Playbook and still didn't prevent the mistake, so the concrete cases are kept
(that's what makes them land).

- **§1 — new "Tests that cannot fail" subsection (the fixture-VALUE trap).** Red-first proves a test
  fails without the fix; it does NOT prove the test can fail AT ALL once the fix is in — a fixture can
  pick values where correct and mutated code produce identical output (11 in one session, all
  review-clean). Five recurring shapes (clamp/floor hides the diff · happy path takes the same branch ·
  sibling branch, same observable · correlated `i%4`/`i%2` fixtures · the unconditionally-true
  `False is not None`). The check: *what value would make this pass with the bug present?* Prefer exact
  values to orderings. "A mystery in a test is usually the test."
- **§4 — phase-boundary gating + the per-module discovery loop.** Each PHASE of a multi-phase program
  is a feature for gating (run the gate at every phase boundary — deferring lets one weak-test habit
  compound across every module built before the first measurement). Full passes VERIFY; to DISCOVER,
  iterate one module at a time and READ the actual survivor lines (which found five production bugs no
  passing test could) — guessing finds none.
- **§4 — three further false-green modes for the gate itself:** (a) **killed + survived < generated =
  UNMEASURED** — segfault/timeout/no-covering-test/skipped mutants are invisible to a `": survived"`
  collector while the vacuity guard counts GENERATED, so an all-segfault scope reads "0 survivors —
  PASS"; refuse to certify. (b) A too-permissive equivalence filter is a **GATE DEFECT**: SQLite is
  case-SENSITIVE for VALUES (only keywords/identifiers are case-insensitive), so `type='table'` →
  `'TABLE'` is a REAL mutant — **corrects the Playbook's own previously too-broad case-only filter**;
  every exclusion rule now ships a negative test and you audit the excluded SHARE trend. (c) A **roster
  entry with no gate invocation is a comment** — §6 BUILT-vs-WIRED applied to the gate itself. Plus:
  CHECK baseline-green at HEAD as an explicit precondition (a shared red test disables every scoped gate).
- Carried into the `mutation-runner` agent + `/mutate` command. **New live calibration scenario**
  `unmeasured-not-certified` (live suite 8 → 9) with stub-harness proof (all-segfault-green BLOCKING-
  FAILs; a correct refusal PASSes). Pinned by `test_agents.py::test_v19_doctrine` (+ planted-fixture).
  SKILL description unchanged (958 chars, within budget).

## 1.8.1 — 2026-07-23

**Targeted-mutant revert-safety — `with_snapshot.py preflight`** (origin: downstream telemetry —
a hand-rolled targeted-mutant script `git checkout`'d away UNCOMMITTED work mid-pass; the lesson
"commit before a revert-based tree-mutating op" was half-covered by §11 but never stated at the
targeted-mutant step, and detect-after-the-fact — `with_snapshot verify` — is worse than
refuse-before). This makes refuse-before mechanical:

- **New `with_snapshot.py preflight` subcommand** — REFUSES (loud exit 1) when the tree has
  uncommitted changes to TRACKED files, because a revert-via-`git checkout` pass would clobber
  them. Untracked-only files don't block (a checkout leaves them alone). This is the guard for the
  bare-checkout pattern; `begin`/`verify` remains the other pattern (it RECORDS a dirty tree and
  restores it, so it doesn't need a clean tree). Backed by 5 planted tests in `test_with_snapshot.py`
  (clean passes · uncommitted tracked refused · staged refused · committed passes · untracked ignored).
- **Doctrine:** SKILL §4 targeted-mutant mode gains a clean-committed-tree precondition (gate any
  revert-based script on `preflight`, or use `begin`/`verify`); §11 cross-references it on the
  worktree line; the `mutation-runner` agent and `/mutate` command carry the precondition.
- Pinned by `test_agents.py::test_v181_doctrine` (+ planted-fixture). SKILL description unchanged.

## 1.8.0 — 2026-07-23

**New agent: the `architecture-adversary`** — the design-quality counterpart to the
`integration-adversary`. Origin: on a real multi-surface agent codebase, a false-positive was
"fixed" by adding a tool name to ONE of THREE already-disagreeing "read-only tool" lists instead of
unifying them to a single source of truth. Every existing gate passed it — the wiring was fine
(integration-adversary), the claim was true (claims-verifier), the tests were green (Tripwire) —
because none of them evaluates DESIGN quality. A human caught it: "don't band-aid our architecture
into a spaghetti net of crap." This agent makes that check mechanical.

- **`agents/architecture-adversary.md`** — a fresh-context, refute-framed reviewer ("assume the fix
  is a band-aid and try to prove it"), tools `Read, Grep, Glob, Bash`, mirroring the
  integration-adversary's structure/tone. Hunts seven band-aid patterns: WRONG SEAM, DUPLICATION,
  SPECIAL-CASE CREEP, REUSE MISS, LAYERING VIOLATION, GATE-BY-PROXY, CONFIG/KNOB SPRAWL. Refute-frame:
  "what is the earliest seam where this class of bug is impossible?" Deterministic output
  (`seam_where_fix_landed` / `seam_where_it_should_land` / pattern# / why / smallest_fix) and a forced
  `Verdict: ARCHITECTURAL / BAND-AID(n) / MIXED(n)` + `Recommendation:` line. §12 claims discipline
  binding (negatives need the exhaustive grep sweep); it must say so when it finds nothing (never
  invents debt). Ships with a worked example (the origin incident).
- **Wired at two points** (advisory, never a hard block): SKILL §0 plan-close dispatches it alongside
  the integration-adversary ("does this PLAN fix the root or a symptom?"); SKILL §6 adds a diff-time
  design-quality pass ("does this DIFF add debt?"); SKILL §12 folds its findings under the claims
  discipline; `/tdd-plan` dispatches both adversaries and reports both in `Loop closed:`.
- **Anti-theater calibration** (§5a/§13): two new live scenarios — `band-aid-parallel-list` (plants a
  fix that adds to one of two disagreeing read-only lists; the agent MUST flag it) and
  `good-fix-single-source` (plants the unified fix; the agent must NOT false-positive), backed by a
  small `tools.py`/`audit.py` fixture that models the incident. The live suite grows **6 → 8**. The
  oracle is proven without model spend by stub-driven checks in `calibration/test_harness.py` (a
  rubber-stamp and a false-positive both BLOCKING-FAIL; a correct catch and a correct clean both PASS).
- Pinned by `test_agents.py::test_v18_doctrine` (+ planted-fixture); the agent roster is now **9**.
  SKILL description unchanged (958 chars, within budget).

## 1.7.1 — 2026-07-17

**Mutation-gate integrity — the two-axis vacuity guard** (origin: a vendored consumer's scoped
mutation gate had been false-greening *intermittently since before 2026-07* — the anti-gaming check
for every critical module was itself asleep). Two root causes downstream: a **RED/drifted baseline**
(a refactor left one test asserting on a return value that had moved) made `mutmut` print `failed to
collect stats / runner returned 1` and execute **zero** mutants while still **generating** them on
disk; and the gate **ran the tool but discarded its exit code**. Result: the exact false-green
signature `generated>0 / 0 survivors / exit 0` — generated > 0 satisfied the existing guard, the
survivor collector came back empty (empty both when all-killed AND when stats abort), and "0
survivors" read as a clean green.

The §4 vacuity guard was **single-axis** (it only caught a scope matching zero *generated* mutants —
a typo'd function name) and its own comment wrongly assumed a RED baseline yields 0 generated
mutants. That guard was **necessary but not sufficient**. This release extends it to **two axes**,
stack-agnostically (`mutmut`/`cosmic-ray`/`Stryker`/`pitest` all need a green baseline):

- **SKILL §4** — the guard now has a *scope* axis (existing) AND an *execution* axis: a mutation
  "green" is valid only when a positive count of mutants actually **EXECUTED against a GREEN
  baseline**. Three preconditions before trusting a pass — baseline GREEN, run-count > 0 from the
  tool's *run stats* (not the on-disk generated set), kill tests collected. The gate must **capture
  the tool's exit code / stats-abort markers**, never run-and-discard. Names the shared-baseline
  poisoning fact (one RED test disables every scoped gate at once) and a §13 tie-in: a deliberately-
  RED baseline must make the gate ABORT/FAIL. Two aphorisms are now load-bearing doctrine: **"0
  survivors ≠ pass, and generated > 0 ≠ measured"** and **"a discarded exit code is a discarded
  truth."** The "count from generated" line is reconciled, not blunted (it prevents the perfect-run
  false-*fail*; the new axis prevents the aborted-run false-*pass*).
- **`mutation-runner` agent + `/mutate` command** — carry the execution axis operationally (capture
  the exit/stats output; "cannot measure — gate RED" on an aborted run; confirm run-count > 0 before
  reading survivors).
- **New live calibration scenario** `red-baseline-false-green` (mutation-runner) — plants a RED
  baseline + the `generated>0 / 0 survivors / exit 0` report and requires the agent to refuse to
  certify green. The live suite grows **5 → 6** (re-baselines at 6/6 on the next run).
- Pinned by `test_agents.py::test_v171_doctrine` (+ planted-fixture) — the aphorisms are asserted
  verbatim so they can't be paraphrased out. SKILL description unchanged (958 chars, within budget).

## 1.7.0 — 2026-07-15

**The reachability release — closing the "toggle that ships dark" gap** (origin: a vendored
consumer shipped six user-facing config toggles that were built + wired + tested + registered
yet not user-reachable — they passed the anti-darkness coverage test through one inappropriate
exemption entry, which simultaneously kept them out of `/features` and out of the doctor's
dark-inventory; the human-judgment guard, the integration-adversary, was optional and skipped).
The Playbook already said "built ≠ wired ≠ usable," but had no mechanical forcing function for
the config-gated-feature case. Four stack-agnostic doctrine changes (the reachability/health
surfaces differ per repo, so the CONCEPT is pinned, never a pytest specific):

1. **Tripwire ACTIVATED/WIRED is now a TWO-surface reachability test for user-controllable
   (toggle-gated) deliverables** (SKILL §6, `/tripwire`, `tripwire-auditor`). Code that merely
   READS the flag is the route-exists trap; the bar is "a human other than the author can FIND
   and flip it." Where the repo has the surfaces, ACTIVATED must assert the switch is reachable
   through the canonical feature-control surface (the `/features`/settings equivalent) AND
   visible in the health/status surface (the doctor/dark-inventory equivalent) — absent from the
   first is dark-to-the-user, absent from the second is dark-to-the-operator.
2. **Exemption-as-darkness-vector named as an anti-pattern** (SKILL §6a, `/integration-audit`).
   A coverage/registration test's ignore/exempt/allow-list hatch is for NON-USER-FACING
   internals ONLY. Silencing it for a user-facing feature hides that feature from the very two
   surfaces (settings + health) the test exists to protect — one entry defeats every automated
   guard at once. Doctrine now demands a COMPANION test asserting user-facing / measured-rollout
   gates are registered, never exempted.
3. **The integration-adversary is MANDATORY, not optional, for any deliverable that adds a
   config gate or a user-facing capability** (SKILL §0, `integration-adversary`). That is exactly
   the author's blind spot; its brief now carries the explicit question — does every new
   gate/capability appear in the user-facing control surface AND the health/status surface, or is
   it dark-by-default / un-toggleable / health-invisible?
4. **New §6b "Onboard, don't hide"** — a default-OFF feature ships an onboarding contract or it
   doesn't ship default-OFF: (a) a named ONLINE metric that populates the moment it's on (not an
   offline eval someone must remember), (b) a turn-on-at-deploy step, (c) a scheduled keep/flip/
   kill review, (d) a kill condition, (e) a user-reachable toggle. Forcing rule: if a feature
   can't be measured online, it ships ON or it doesn't ship default-OFF. "A switch with no
   scheduled hand on it is a switch that will never be thrown."

Pinned by `test_agents.py::test_v17_doctrine` (+ its planted-fixture calibration) so the four
counter-rules can't silently regress. SKILL description left unchanged (958 chars, within
David's 1024 budget — the new concepts ride existing trigger vocab: Tripwire/ACTIVATED,
integration surface, darkness doctor).

## 1.6.3 — 2026-07-10

**SKILL description trimmed 1136 → 958 chars** (system-prompt tax, every session, every
surface) by removing ONLY the trailing "named pieces are…" list — a verbatim duplicate of
terms already present earlier in the description. Mechanically verified zero vocabulary
loss, so trigger coverage is unchanged. Live probe checklist for the next few sessions
(planted-trigger spirit): "run the tripwire", "grade that last cycle", "is X dead code?"
must each still fire the skill.

## 1.6.2 — 2026-07-10

**§10 CI integrity/determinism split** (from the "do we need GitHub Actions?" evaluation):
determinism comes from PINNING (SHA-pinned actions, pinned container images — hosted
runner images churn monthly), while the hosted vendor's unique contribution is THIRD-PARTY
INTEGRITY (results the working session can't edit) — weigh CI alternatives on those two
properties separately. And **workflow files ARE risky paths**: a diff touching
`.github/workflows/` or the pre-push hook can silently disable a blocking gate (H2 aimed
at the harness) — path-filter gate-file edits into the fast local gates and review them
like auth code. Three structural pins.

## 1.6.1 — 2026-07-10

**Doctrine hardening from downstream implementation** (cheliped's masker, red-first
tested there): the §4 informational string class exempts LITERAL STRING CONTENT only —
a logic mutant on a display line (True→False, and/or flip, dropped guard) and anything
inside an f-string `{expression}` is CODE and stays real/blocking. Mask the string's
characters, never the line it sits on. Carried in SKILL §4, mutation-runner, and /mutate,
with three structural pins.

## 1.6.0 — 2026-07-10

**The ROI release** — origin: downstream telemetry from a production repo (cheliped) showed
the Playbook's own drift modes: the TDD reminder firing TWICE per message (plugin + vendored
registration, version-skewed for weeks), a mutation roster crept to 44 modules against a
"critical only" doctrine, zero-survivor gates forcing verbatim prose-pin tests, and
auto-checkpoints entangling a mutation runner's transients. Same release adopts the
gate-quality patterns that repo built on its tamper-evident audit chain. Theme: **the honest
path must also be the cheap path — ceremony that outlives its justification is a tax, and
scoped gates need anti-vacuity teeth.**

### Added
- **§4 roster admission rule** — a module enters the mutation roster only with a one-line
  "a survivor here costs ___" justification (irreversible/security/money/data-integrity/
  loop-safety); rendering/presentation modules explicitly OUT; re-audit at feature end.
- **§4 string-mutant role classes** — DATA strings (SQL, keys, hash inputs, persisted
  audit/forensic content) stay zero-survivor; operator-facing DISPLAY prose is an
  informational class, never resolved by verbatim prose-pinning (named anti-pattern).
- **§4 function-scoped two-tier gating** — new/core work gates at zero real survivors on
  named functions; same-file pre-Playbook debt is tracked visibly, never diluted into or
  flattered by a whole-file floor.
- **§4 vacuity guard** — any scoped gate must fail loudly on a scope matching zero
  GENERATED mutants ("refusing a vacuous pass"); denominator from generated mutants, not
  the survivors report (a fully-killed scope looks empty there).
- **§4 audited equivalence ledger** — for equivalents the conservative filter can't
  classify: written proof per entry, exact-substitution matching, a can't-overmatch test
  per entry, text-not-location caution, keep-it-short smell rule.
- **§4 killing-suite visibility** — dedicated-suite tools (mutmut `tests_mutation/`) must
  provably collect the kill tests (shim/star-import + mechanical collision check).
- **§0 numeric ceremony thresholds** — path-criticality beats line count both ways;
  <~20 lines on non-roster/non-security paths + green targeted tests skips the independent
  verifier and full Tripwire; any roster/security diff gets full ceremony.
- **§11 concurrency-aware auto-checkpoints** — skip when a subagent holds the tree, exclude
  tool transients, session-id-tagged wip commits, mutation passes in an isolated worktree.
- **`intent_nudge` anti-tax rework** — runtime O_EXCL sentinel collapses duplicate
  registrations (plugin + vendored) to one reminder on any install topology; per-session
  time damping (default 30 min, `TDD_PLAYBOOK_NUDGE_INTERVAL`, `0`=off); meta-question
  exclusion ("should we…", "what do you think…"); all state fails OPEN.
- **`install_into_repo.py --doctor`** — loud version-skew check across canonical plugin,
  vendored copy (now stamped in `.claude/.tdd-playbook-version`), and the local plugin
  cache; skew exits 1 with the exact fix to run.
- **Calibration: `vacuous-mutation-scope` scenario** — a scoped gate whose scope matches
  nothing must be refused; harness stubs prove both directions deterministically.
- **20 structural doctrine pins** (`test_agents.py::test_v16_doctrine`) so the anti-tax
  rules can't silently regress out of SKILL.md / mutation-runner / /mutate.

### Fixed
- **`build_completion_reminder` macOS path bug** — session-edited-path intersection used
  `abspath` while macOS tempdirs resolve through `/var → /private/var`, silently emptying
  the intersection; the planted "source-only session" test slipped past on macOS. Now
  `realpath` on both sides.
- **TEST-LOCK dead on macOS symlinked project dirs (same class, worse consequence)** —
  `tdd_lock.py` keyed locks off `getcwd()` (always real) against a `CLAUDE_PROJECT_DIR`
  root (possibly symlinked), producing garbage relpath keys the guard could never match:
  the H2 blocking guard silently never fired. `realpath` on both sides in `tdd_lock.py`
  and `test_lock_guard.py`; the planted H2 tests (previously red on macOS) now block.

## 1.5.0 — 2026-07-09

**The integration release** — origin: a full-platform feature-wiring audit of a production
multi-surface agent system (11/11 confirmed findings; whole subsystems built well, tested
well, and never connected). Root cause, now doctrine: *every component shipped tests that wired the component up themselves, and nothing
continuously asserted the production assembly* — plus the meta-bug that health surfaces
reporting only on what RAN make dead features invisible by construction. Two principles run
through everything below: **no wiring claim counts unless proven through the production
composition root**, and **darkness must be an enumerable state, not an invisible one**.
(Roadmap note: WS5 was reserved as v1.5.0 in `docs/plans/implementation-plan-2026-07.md`;
this release was unplanned audit-driven work, so WS5 shifts to v1.6.0.)

### Added
- **Tripwire ACTIVATED leg (§6, /tripwire)** — deliverables now prove BUILT + WIRED +
  **ACTIVATED** + EXERCISED. Activated = on in the shipped default config, or off behind a
  NAMED user-reachable switch; "off with no on-switch" trips RED; a gate depending on another
  disabled gate must report itself dark, never silently no-op. The largest darkness class in
  the origin audit (a whole verify-oracle stack behind a switchless config gate, a delivery
  target shipping as "none") passed the old three-leg check.
- **Production composition root rule (§6, /tripwire)** — the WIRED proof must construct the
  REAL object graph (actual daemon/app factory, actual per-platform agent build), never a
  self-assembling test fixture; reachability checks must be SYMMETRIC (registered → reachable
  AND reachable → registered).
- **§6a Wiring liveness** — the standing (not per-plan) discipline: the **capability registry**
  (`capabilities.json`: surfaces, activation default + on-switch, `wired_by` production site,
  `exercised_by` assembly test, emits → named consumers, integration debt with owner + expiry;
  the registry only GROWS), the **assembly suite** (`@pytest.mark.assembly`, every CI push),
  **liveness canaries** (planted event through the production seam, scheduled) + **staleness
  sweep** (zero runs in N days), and **decide-or-park** (half-built-and-silent is the worst
  state).
- **`bin/capability_registry.py`** — stdlib-only mechanical gate for the registry:
  `validate` (R-DARK dark-with-no-switch · R-WRITE-ONLY emitter-without-consumer · R-DEBT
  expired/ownerless debt fails · R-DUP · R-SCHEMA, BLOCKING), `doctor` (the dark-feature
  inventory: built-but-off + on-switch, write-only emitters, debt aging, missing liveness,
  consumed-but-never-emitted), `init`. Planted-input calibrated in
  `tests/test_capability_registry.py` (21 checks).
- **Integration surface in the plan (§0, /tdd-plan)** — per deliverable: *consumes* (stated,
  never implied) · *emits → named consumer* (write-only loops become owned, dated integration
  debt) · *surface parity* (divergence stated, not discovered) · *reverse sweep* (existing
  features that should adopt the new capability) · *activation* (where's the on-switch).
  Islands are cheapest to catch at plan review.
- **`integration-adversary` agent** — fresh-context, refute-framed connectedness check of a
  plan ("assume it builds an island and prove it"): consumes gaps, write-only emitters,
  surface parity, reverse islands, dark shipping. `/tdd-plan` now closes its loop by
  dispatching it (`Loop closed:` contract, same teeth as /edge /mutate /probe).
- **`/integration-audit` command** — the codified "built but is it running?" sweep: enumerate
  from what SHOULD run (registry, else entry points — a missing registry is Finding #0), hunt
  the four darkness classes (broken wiring · dark-by-default · surface drift ·
  old-blind-to-new/write-only loops), §12 claims discipline with runtime probes and a
  fresh-context `claims-verifier` pass on every trap-category negative, findings ship with
  OWNER + EXPIRY and a decide-or-park verdict, and each finding names the standing mechanism
  (registry entry / assembly test / canary) that makes the next audit unnecessary.

### Changed
- `tests/test_agents.py` — contracts extended: 8 agents, `/tdd-plan` and `/integration-audit`
  join the loop-closing set, `/tripwire` must carry ACTIVATED + the registry gate + the
  composition-root rule.
- SKILL.md frontmatter, README, and the §Markers line (`assembly` added) reflect the new
  pieces.

## 1.4.0 — 2026-07-08

**The co-evolution release** — Workstreams 3–4 of the implementation plan: the answer to
the Verification Horizon problem ("no fixed gate stays effective as model capability
grows") is now mechanical, and §13's "grade from telemetry" has a real seam.

### Added
- **Generative plant corpus (`calibration/corpus/` + `calibration/author_plants.py`)** —
  each cycle an ADVERSARY agent (>= the doer's model tier) authors NEW planted-defect
  scenarios; mechanical validation (schema, edits-apply, oracle regexes) gates acceptance;
  human review moves proposed → approved; `run_calibration` includes approved plants and
  reports corpus size. **The corpus only grows** — plants record their authoring model so
  recall trends stay attributable. Pipeline planted-calibrated in `calibration/test_harness.py`.
- **Decay principle (§13 preamble)** — every gate is a decaying asset; the calibration
  schedule IS the product. `run_calibration` now prints a DECAY WARNING when
  `docs/HACK_CATALOG.md`'s refresh log is >100 days old (the quarterly ritual's mechanical
  reminder).
- **Verifier-strength policy (§13)** — calibration measures against the CURRENT doer model;
  plants authored at >= the doer's tier; a doer-model upgrade requires recalibration before
  its work is trusted.
- **`bin/grade_from_otel.py` + `docs/telemetry.md`** — /grade's telemetry seam: parses
  Claude Code OTel exports (lenient: flat-attribute JSONL AND OTLP/JSON; gen_ai.*
  conventions still unstable so no hard schema binding) into the §13 metrics — turns,
  tokens net of cache, file reads, greps, edits, tests-vs-source touched, cost. No
  recognizable records → exit 1 and /grade must label itself "narration-grade (telemetry
  unavailable)" — an estimate never wears a telemetry badge. `/grade` also now reads the
  TEST-LOCK journal (frequent/suspect unlock reasons cap the grade, H2).
- **Mutation v2 (§4, /mutate, mutation-runner)** — diff-scoped runs on PRs (Stryker
  `--incremental`/`--since`, pitest history, mutmut changed-files; repo-wide score is NOT a
  KPI), ACH-style targeted-mutant mode (mutation as test GENERATOR for the change's
  concern), and context hygiene: mutants stay OUT of the implementing agent's context — a
  visible verifier is a gameable verifier.
- **Doctrine wins** — §3: Schemathesis at the API boundary when a schema exists; §7:
  quarantine entries carry OWNER + EXPIRY (expired quarantine fails the suite); §10:
  affected-tests inner loop with the full suite at checkpoints/merge.

## 1.3.0 — 2026-07-08

**The integrity release** — Workstreams 0–2 of the implementation plan
(`docs/plans/implementation-plan-2026-07.md`): the Playbook now mechanically practices its
own doctrine, and the two top documented agent attack vectors (edit-the-test, over-mock)
are constrained by mechanism, not warning.

### Added
- **`docs/HACK_CATALOG.md`** — the versioned threat model (H1–H6: hardcode outputs ·
  edit/delete tests · over-mock · assertion-free coverage · harness exploitation ·
  architectural fakery), seeded from the 2026 research corpus. Guards cite entry IDs;
  the guard↔entry map makes open gaps diffable; quarterly refresh ritual included.
- **TEST-LOCK (§1, H2/H5)** — `bin/tdd_lock.py` (lock/unlock/status; unlock REFUSED
  without a ≥10-char reason; append-only journal read by `/grade`),
  `test_lock_guard.py` PreToolUse hook (BLOCKS edits to locked tests AND the verifier
  surface — conftest.py, pytest/jest/vitest configs — while a lock is active), and
  `/tdd-lock` + `/tdd-unlock` commands. The strongest validated anti-gaming defense
  (Beck; TDFlow/TDAD) made mechanical.
- **`bin/with_snapshot.py`** — mechanical revert safety (begin/verify/status; catches
  un-reverted plants, stray files, content drift, stray stashes). The four tree-touching
  agents (planted-error-probe, ux-probe-calibrator, mutation-runner, red-first-verifier)
  now REQUIRE worktree isolation or a begin/verify pair — a clean revert is proven, not
  narrated.
- **`overmock_guard.py` (H3, warn)** — flags net-new mocks in test edits (agents over-mock
  36% vs 26% for humans, MSR 2026); pairs with the new §1 rule: every new mock carries a
  one-line justification.
- **`snapshot_guard.py` (H5, block)** — blocks snapshot auto-update invocations
  (`jest -u`, `--update-snapshots`, `--snapshot-update`, env forms) and direct edits to
  `.snap`/`__snapshots__` files: snapshot diffs are human review artifacts.
- **Exit-call detection in the weakening guard (H5)** — `sys.exit`/`os._exit`/
  `process.exit` added to a test or `conftest.py` (verifier surface now in scope) is
  caught: exiting early fakes a passing suite (observed in production RL).
- **Agent calibration harness (`calibration/`)** — a fixture package + 4 planted scenarios
  (never-red test, unwired deliverable, false negative claim, missing boundary tests)
  driven headlessly against the real agents with DETERMINISTIC string oracles (no LLM
  judge); `--dry-run` validates free in CI; results append to `docs/calibration/history.md`.
  The harness itself is planted-calibrated with a stub binary (it can provably fail).
- **`tests/test_agents.py`** — structural contracts for all agents/commands (tool
  sanctions, forced verdict lines, revert-safety blocks, loop-closure lines).
- **LICENSE: Apache-2.0** (was UNLICENSED) — a universal floor needs a real license.

### Changed
- **Integrity hooks now default to BLOCK** (`test_weakening_guard`, `test_lock_guard`,
  `snapshot_guard`); advisory hooks stay warn. Demote per hook
  (`TDD_PLAYBOOK_HOOK_<NAME>=warn|off`) or globally (`TDD_PLAYBOOK_HOOK_MODE=warn`).
  Rationale: the 2025–2026 evidence is unambiguous that warnings do not stop test-gaming.
- **`/edge` `/mutate` `/probe` now close their loops** — each DISPATCHES its adversary
  agent (edge-case-adversary / planted-error-probe / ux-probe-calibrator) and ends with a
  mandatory `Loop closed: yes/no — why` line.
- **`flaky_guard` suppression tightened** — per-category suppressors: a `@pytest.fixture`
  or unrelated `monkeypatch` in the block no longer silences a wall-clock warning; only
  real clock control (freeze_time/fake timers/clock monkeypatch) does.
- **`verify_citations` quote quality** — short (<10 chars) or non-unique quotes are
  flagged `weak-quote` in the summary (gate unchanged; weak evidence is now visible).
- **`install_into_repo.py` reconciles instead of appending** — plugin-namespace hook
  groups are pruned and re-added from the current hooks.json, so removed/renamed hooks no
  longer accumulate downstream; user hooks outside `.claude/hooks/scripts/` untouched.
- **Stop-hook reminder is session-aware** — with a readable transcript it narrows to the
  session's own edits, so a pre-existing test change elsewhere no longer silences a
  source-only session; falls back to whole-tree.

## 1.2.1 — 2026-07-07

Two doctrine additions adapted from the Karpathy-inspired CLAUDE.md guidelines
(Think Before Coding / Surgical Changes) — the two that guard seams the Playbook
didn't: the integrity of the plan the tests are derived from, and the integrity
of the diff against that plan.

### Added
- **SKILL.md §0 — spec integrity** (once per plan, before the deliverables): assumptions
  stated explicitly; competing readings of the request presented, never picked silently;
  a materially simpler approach surfaced if one exists; genuine confusion raised as a
  question at plan review instead of planned around. Rationale: §§1–6 verify what the
  PLAN says — a wrong reading of the request passes every downstream gate. `/tdd-plan`
  now opens with this block.
- **SKILL.md §6 — the reverse check (diff → plan):** the Tripwire proves every deliverable
  is in the diff; the inverse is now also checked — every changed line traces to a plan
  deliverable. Non-tracing lines are scope creep / drive-by refactors / orphaned helpers:
  orphans the change created get removed; unrelated cleanup and dead code get mentioned,
  not done ("dead" is a negative claim — §12's exhaustive-sweep rule applies before acting).

## 1.2.0 — 2026-07-04

New doctrine: **UX probes** — intent-only agent probes that close the gap scripted journeys
structurally can't cover (a §5 journey's author already knows where the button is; a probe's
fresh agent has to find it). Backed by a code-level evaluation of the three candidate engines
(full source clones of alibaba/page-agent, browserbase/stagehand v3, browser-use v0.13, with
file:line citations — see `docs/evaluations/ux-probe-engine-evaluation-2026-07.md`).

### Added
- **SKILL.md §5a — UX probes** (`ux_probe` marker, non-blocking lane): a fresh LLM agent gets
  only the user's INTENT and must accomplish it through the real interface. Load-bearing rule:
  the **oracle split** — agent self-reported success is telemetry, NEVER a gate; blocking
  assertions are deterministic and harness-owned (DB effect, no-5xx from harness network
  capture, console budget); success rate/steps/cost/friction are tracked trend lines (§7
  zero-flake + §8 EVAL rules applied). Engine-agnostic OBSERVE/ACT/EVIDENCE/ORACLE contract
  with a per-interface driver table mirroring §5: web → Stagehand (TS; committed act-cache =
  probabilistic discovery, deterministic replay; UI drift = cache diff in PR) or browser-use
  (Python; `cdp_url` attach, HAR oracle, custom friction action; telemetry/judge off);
  Telegram mini-app → same engines + `Telegram.WebApp` shim (native chrome stubbed into the
  action space); TUI → tmux/PTY loop (screen is already text); Telegram bot → dispatcher/test
  DC; MCP → agent-SDK client. Planted-UX-defect calibration (§13's teeth), scheduled cadence
  with step/token caps, staging-only + injection hygiene, and the a11y "free win" note.
- **`docs/evaluations/ux-probe-engine-evaluation-2026-07.md`** — the engine evaluation
  (comparison matrix + three full code reviews) that grounds the §5a driver choices, including
  why page-agent was rejected for probe duty (SPA-only, synthetic `isTrusted:false` events,
  no replay) and why the harness attaches over CDP rather than driving through Playwright
  (both blessed engines left Playwright for their own CDP stacks).
- **`/probe` command** — the §5a runbook at the same altitude as `/mutate`: guardrails first
  (staging-only, critical journeys only, keys harness-side, caps set), driver selection from
  the §5a table by repo detection, goal-phrased intents sourced from the §0 plan (UI hints
  rejected — they defeat the probe), N≥3 runs, the oracle split applied verbatim, lying-UI
  detection flagged loudly, failed-goal transcripts filed as UX bugs, and first-run-in-repo
  setup (marker registration, testing-addendum note, calibration recommendation).
- **`ux-probe-calibrator` agent** — `planted-error-probe` one layer up: plants ONE
  user-meaningful UX defect the probe's perception channel can see (mislabel / lost
  accessible name / hidden required field / dead-ended CTA / lying success message), runs
  the probe 3×, verdicts `PROBE VERIFIED` (≥2/3 detections) or `BLOCKING GAP` classified as
  PERCEPTION / ORACLE / INTENT with the smallest fix, then reverts to a clean tree. Plant
  types rotate; the lying-success plant is periodically mandatory (it exercises the oracle
  split). Forced-recommendation discipline applies.
- `backups/SKILL.md.2026-07-04.pre-ux-probe.md` — pre-change snapshot (requested backstop).

### Changed
- Skill frontmatter + markers line register `ux_probe`; the Open-upgrade note now points at
  §5a as the mirror image of the pending agent-eval discipline (agents testing UXs vs evals
  testing agents), sharing the same oracle-split rule.

## 1.1.0 — 2026-06-25

Enforcement upgrades mined from a deep-dive of `mattpocock/skills` and `garrytan/gstack`,
filtered through a CTO/QA review (ported only what *raises* the bar; kept the plugin lean and
portable; did not import coverage-% theater or stateful telemetry that belongs in a host app).

### Added
- **`bin/verify_citations.py`** — the mechanical half of the §12 claims discipline. Resolves
  every `file:line` citation in a findings doc and checks quoted snippets against the real
  source (VERIFIED / UNRESOLVED / MISMATCH). Wired into `/claims` and the `claims-verifier`
  agent so "no claim before resolving evidence" is code, not an honor system. Planted-input
  calibrated (`tests/test_verify_citations.py`, 10/10).
- **`/debug` command** — feedback-loop-first debugging: a hard gate against theorizing before
  a reproduction loop exists, ranked loop menu, falsifiable hypotheses with predictions, a
  3-strike STOP→escalate, and a pinned regression test to finish.
- **Tripwire verification-mode taxonomy** (§6 + `/tripwire` + `tripwire-auditor`): for
  multi-deliverable plans, classify each deliverable DIFF-VERIFIABLE / CROSS-REPO /
  EXTERNAL-STATE / UNVERIFIABLE and name the probe; "code that handles a deliverable is not
  the deliverable."
- **E2E/EVAL decision matrix + regression IRON RULE** (§1, §8): pick the test layer
  deliberately; route prompt/tool-definition/agent-behavior changes to an `[→EVAL]` (outcome
  scoring, deterministic-oracle gate, LLM-judge as trend only); regression tests are
  non-negotiable, no approval prompt.
- **Forced-recommendation discipline** on `edge-case-adversary`, `claims-verifier`,
  `tripwire-auditor` — each ends with `Recommendation: <action> because <specific finding>`;
  generic justifications rejected.
- README "which command when" table.

### Changed
- Doctrine audit (mattpocock `writing-great-skills`): condensed §10 (CI hygiene) and the §9
  a11y note so the three new enforcement rules land with the always-on cost staying flat.

## 1.0.0 — 2026-06-24

Initial release: the universal TDD/QA doctrine as an auto-firing skill, 6 scaffolding commands
(`/tdd-plan` `/tripwire` `/edge` `/mutate` `/claims` `/grade`), 6 verification agents, and 4
warn-first enforcement hooks (test-weakening, flaky-pattern, build-intent nudge, Tripwire
reminder). Composes with each repo's own stack-specific testing on top. Public marketplace so
cloud/mobile sandboxes load it without auth.
