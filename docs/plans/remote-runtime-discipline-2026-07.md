# Remote-runtime & operational-surface discipline — comprehensive plan (A–D)

*Provenance: CIVerd's `PLAYBOOK_CAPABILITY_GAPS.md` (2026-07-27), written from the CIVerd/memrebel
VPS build, plus this session's CTO review. Sequenced per David's call: **A first (v1.14.0), then B,
C, D** as follow-ups; one deferred item (Gap 2.1) recorded as owned debt. Written to preserve the
full reasoning so no part of the CIVerd feedback is lost between releases.*

---

## 1. Root-cause diagnosis — the two reported gaps are ONE gap

The Playbook's two working mechanical oracles — **Tripwire wiring-liveness** (§6/§6a) and
**planted-error calibration** (§13) — are scoped to *code in the repo you are sitting in*. The
moment a deliverable **runs somewhere else** — a VPS, a daemon, or a **vendored `.claude/` in
another repo** — there is no mechanical oracle, so verification silently falls back to *reading
output*. And per the report's sharpest line:

> *"Where the only signal was reading output, I did not [catch it] — because I had already
> concluded it was green, and I was reading to confirm."*

Over-confidence lives exactly where the mechanical oracle ends. Every one of the report's three
most-consequential misses (six-commit deploy drift; a `verify_install.sh` that said "ALL CONTROLS
HOLD" three times over a broken engine; a signer crash-looping while the check inspected timers) was
in an **operational / remote surface the Playbook's calibration does not reach**.

**This implicates our own architecture, not just CIVerd.** CIVerd is a remote runtime; every
Cheliped/MemStruct vendored copy is a remote runtime that can drift from this repo's HEAD. The
six-commit drift is the same failure mode a stale vendored plugin has (the reason `install_into_repo
--doctor` exists). So closing this hardens the Playbook we ship, not only CIVerd.

## 2. What already worked — extend, do not rewrite (honor the report)

The additions must land *in proportion*. These are confirmed strengths; the plan builds on them:

- **Planted-error calibration caught every defect it was pointed at** (12/14 plants killed
  immediately; the 2 survivors were real test weaknesses). §13 is the right tool — just scoped to
  code.
- **The Tripwire's ast-based "defined and not skip-marked" check** (§6 EXERCISED) is genuinely
  non-vacuous — it caught a skip a grep would have accepted.
- **The claims discipline (§12)** produced the F4 correction; the founding plans were cited and the
  contradiction was visible.
- **Cross-session adversarial review was the highest-yield control of the day** — the "will this run
  in Cheliped?" catch (this session) stopped a public-plugin/private-dependency error that would
  have bricked CIVerd's only watched repo on day one. Two independent reasoners converged on the
  wrong answer; a third-party question caught it.

**Design principle for this plan:** bias to MECHANISM over prose (the F5 lesson applied to our own
doctrine), and resist roster-creep. Nine proposals consolidate to four deliverables + one deferred.

---

## 3. Deliverable A — §6 RUNNING leg + version-echo + registry `deploy_surface` (v1.14.0)

**The mechanical core, and the root-cause fix.** Absorbs report proposals 1.3 (version-echo) and 1.4
(Tripwire RUNNING leg). Reuses patterns we already ship: `verify_verdict.py` asserts `commit == SHA`;
`install_into_repo.py --doctor` detects vendor-stamp skew. A remote deliverable's "the deployed
version is the intended version" is the same assertion.

### A.1 — Doctrine: a fifth Tripwire leg, RUNNING (§6)
- Extend §6 from **BUILT + WIRED + ACTIVATED + EXERCISED** to add **RUNNING** *for remote
  deliverables only* (a deliverable whose execution host is not the session's repo/process): the
  deployed instance reports the sha/version it is executing, and a probe asserts it equals the
  intended sha. This sharpens the existing §6 `EXTERNAL-STATE (…deployed endpoint…)` proof category
  (SKILL.md ~L414) from "cite where + how you checked" into a named, probeable leg.
- State the failure it closes verbatim from the report: *"all four legs passed on a system running
  code from 97 minutes earlier."* A local checkout can satisfy BUILT/WIRED/ACTIVATED/EXERCISED while
  the deployed system runs different code; RUNNING is the leg that cannot be answered "about the
  laptop."
- Report line: `Tripwire: N/N (+ RUNNING M/M for remote deliverables)`.

### A.2 — Version-echo convention (mechanical)
- Convention: every deployed/remote component exposes the sha/version it is running (an endpoint, a
  `--version`, a heartbeat field, a stamp file). CIVerd already does this — its verdict carries
  `engine_version` + `commit`; `install_into_repo` writes a vendor stamp. Name the convention and
  point at those as the reference implementations.
- Optional small helper `plugins/tdd-playbook/bin/version_echo.py` (stdlib): given an
  expected sha and a command/file/URL that echoes the running sha, exit 0 iff they match, with
  distinct RED reasons (`no_echo`, `drift`, `unreachable`). Decide during A whether this earns a bin
  or stays a documented pattern (lean: document the pattern + let each repo's probe assert it, to
  avoid a bin that only wraps a string compare — but a shared helper is justified if ≥2 repos need
  it). Either way, `install_into_repo --doctor`'s existing skew check is cited as the in-tree example.

### A.3 — Registry: a `deploy_surface` field (§6a, mechanical)
- Extend `capabilities.json` schema with an optional `deploy_surface` per capability whose host is
  remote: `{runs_on, gets_there_by, running_version_probe, divergence}` (mirrors the report's four
  mandatory answers, §3.1). `capability_registry.py validate` requires: if a capability declares a
  remote surface, it MUST carry a `running_version_probe` string (else violation) — so "no way to
  tell if it's the right version" is a hard failure, not an omission.
- `doctor` prints remote capabilities whose probe is stale/absent alongside the dark-feature
  inventory. This is the §6a darkness doctrine extended from "dark features" to "drifted deployments."

### A.4 — Tests (red-first, planted-input)
- `test_capability_registry.py`: a planted capability with a remote `deploy_surface` but NO
  `running_version_probe` must FAIL `validate` (a schema that can't reject the omission is theater).
- `version_echo` helper (if built): planted drift (echo != expected) → RED `drift`; matching → 0;
  unreachable echo → `unreachable`, never a silent pass (mirrors `verify_verdict`'s
  `ledger_unavailable` discipline).
- `test_agents.py` doctrine pin: §6 contains the RUNNING leg + the "97 minutes" origin string;
  planted-fixture check (stripping RUNNING from §6 must be detected).
- **SKILL description budget:** the description names the Tripwire as "BUILT + WIRED + ACTIVATED +
  EXERCISED". Adding RUNNING ideally updates it (~+10 chars; 958/1024 today → headroom exists but
  MUST be re-measured and deduped, per the standing description-budget rule). If it won't fit,
  RUNNING stays body-only and the description keeps the four — flag to David, never silently exceed.

### A.5 — Integration & deploy surface (A eats its own dogfood)
- Consumes: the existing `deploy_surface`-shaped data CIVerd/vendored copies already emit.
- Emits → consumer: `deploy_surface` entries consumed by `capability_registry validate/doctor` and by
  the release-gate spec sent to CIVerd (the `staleness`/`parity` checks gain a `running_version`
  sibling). Register CIVerd itself (`civerd-release-gate` capability) with a real `deploy_surface`:
  `runs_on: srv1621832`, `gets_there_by: update.sh`, `running_version_probe: the verdict's
  engine_version/commit vs HEAD`, so we are our own first RUNNING-leg example.

---

## 4. Deliverable B — §0 "deploy surface" block (doctrine)

Absorbs report proposals 1.1 (deploy-surface plan block) and 1.2 (deploy path is deliverable #1).

- Add to §0's reviewable plan, alongside the **integration surface**, a **deploy surface** required
  whenever any deliverable runs where the session does not control it (VPS, server, daemon, installed
  plugin, vendored copy). Four mandatory answers:
  - **Runs where** — the actual host/process, named.
  - **Gets there how** — the specific mechanism. *If the answer is "I'll paste files," that is a
    finding, not a plan* (quote the report; the base64-blob hand-patching produced a box no checkout
    matched).
  - **Verified how** — how a session proves the RUNNING version matches the intended one (ties to
    A's version-echo).
  - **Divergence** — what happens when they differ, and who notices.
- **Deploy path = deliverable #1**, before any feature — same logic as red-first (build the thing
  that proves the state before the thing that changes it). Concretely for CIVerd that was
  `update.sh` + `verify_install.sh` in the first hour; instead they were committed *after* the damage.
- Pin: `test_agents.py` §0 doctrine needle ("deploy surface" + "Runs where"/"Verified how") +
  planted-fixture.

## 5. Deliverable C — `script-adversary` agent + calibration scenario

Absorbs report proposal 2.2. Follows the `architecture-adversary` precedent exactly (frontmatter
`model: opus` per F3, a verdict format, a worked example, a KNOWN_AGENTS + AGENT_CONTRACTS + calibration
registration).

- **New agent `plugins/tdd-playbook/agents/script-adversary.md`** — reviews operator-facing scripts
  (health checks, probes, deploy/verify scripts) for the failure modes ordinary code review misses.
  The load-bearing lens, one rule that would have caught all four CIVerd hit:
  > **A probe must take its target as an argument, never touch stdin, never write, and must
  > distinguish "refused" from "failed for any other reason."**
  Plus the four named modes: *blocks on stdin* (`tee`/`read`/`cat -`), *destructive probe* (`tee
  FILE` truncating the very allowlist it checks), *passes for the wrong reason* (any non-zero read as
  "refused"), *guessed diagnostics* (a handler printing a hypothesis while the real error sits one
  line above). Verdict: `SCRIPT-SAFE / UNSAFE(n) / MIXED(n)`.
- **Wire it** (or it ships dark — §6a on ourselves): reference from §5/§5a and/or the `/probe`
  command; add to `author_plants.py` KNOWN_AGENTS and `test_agents.py` AGENT_CONTRACTS (both were
  caught lagging before — the old-blind-to-new trap in our own tooling).
- **Calibration scenario** `script-unsafe-probe` (calibration/scenarios.json + fixture): plant a
  probe that reads Ctrl+C/any-nonzero as "refused" (the real CIVerd defect — three security controls
  reported PASS having tested nothing). The agent must flag it UNSAFE. Deterministic regex oracle,
  mirrors existing scenarios. Raises the live suite by one scenario.
- Pin + planted-fixture in `test_agents.py`; `model: opus` asserted by the F3 `test_verifier_model_pins`
  (add script-adversary to the PINNED set — it is a judgment verifier).

## 6. Deliverable D — doctrine sharpening (§1, §12, §13)

Absorbs report proposals 2.3, 1.5, 2.4. Small, high-leverage, mostly one-liners.

- **§1 — "assert the outcome, not the proxy," extended to CHECKS.** Current §1 wording ("test
  BEHAVIOR/OUTCOMES, not 'the route fired'") is about *tests*; every CIVerd miss was a *CHECK* (a
  systemd unit inspected instead of a service exercised; a config read instead of a remote queried;
  source text grepped instead of parsed). Add one sentence generalizing the rule to any verification,
  test or check: *exercise the effect, don't inspect the proxy.* Cite the `RuntimeMaxSec`-ignored-for-
  `Type=oneshot` example (systemd said so in the journal; both scrolled past for hours).
- **§12 — remote "done" is a claim needing evidence.** One line: *"Fixed"/"done"/"working" about a
  remote runtime requires a probe / log line / echoed version — never a commit sha; and if a human
  must run something for it to land, that instruction ships in the SAME message as the fix.* (The
  six-commit drift, and "how have you fixed things if you didn't give me something to paste?")
- **§13 — grade "who caught it."** Add a learning-loop dimension: self-caught (mechanical) vs
  accidental (red on good code) vs human-caught vs cross-session-caught. The report's own ratio (3
  self / 3 accidental / 3 human / 1 peer) shows the human-caught ones were the most consequential and
  all were places already declared "green" — a loop tracking that ratio flags over-confidence hours
  earlier. Wire into `/grade` (telemetry seam) as a reported dimension, not just prose.
- Pins: §1/§12/§13 doctrine needles + planted-fixtures in `test_agents.py`.

## 7. Deferred (owned debt, NOT half-built) — Gap 2.1: operational planted-error calibration

The report's proposal 2.1 — *plant a defect in the deployed system (stop a service, corrupt a config,
revert a file) and require the operational verifier to catch it* — is powerful and correct, but needs
a **live deployed target to plant into**, which our calibration harness does not have. Half-building
it would violate the very "assert the outcome" rule D adds. It wants its own design pass, most likely
a `deployment-probe-calibrator` agent mirroring `ux-probe-calibrator` (plant a known outage → require
the health check to flag it → restore). **Record as capability `integration_debt`** (owner: david,
dated expiry) so completeness is a loan, not a silent deferral — the §6a discipline applied to this
plan itself.

## 8. Cross-cutting / release plumbing (every deliverable)

- Every mechanical change ships a **planted-input test** (repo release discipline); every doctrine
  edit ships a **needle pin + planted-fixture** in `test_agents.py`.
- SKILL **description budget ≤1024** re-measured on any description touch (only A may need it, for
  RUNNING); dedupe first, flag David if it won't fit, never silently exceed.
- Version bumps update `plugin.json` + `marketplace.json` + `CHANGELOG.md` + the version-marker
  memory, together. **Each release now goes through the F4 tag-gate** (`scripts/release_verify.py`
  `--wait-s`) — A is v1.14.0, the first release *planned* under the tag-gate from the outset.
- Release gate per deliverable: all suites green + `run_calibration.py --dry-run` (+ a live
  re-baseline when C adds a scenario, David-run) + `capability_registry validate` + scratch-install
  parity + `check_staleness --warn-only`.
- The CIVerd `repos.yml` gate spec (tests/dryrun/registry/staleness) is handed to David separately;
  A's `deploy_surface`/version-echo makes a future `running_version` CIVerd check possible.

## 9. Sequencing

1. **A → v1.14.0** (RUNNING leg + version-echo + `deploy_surface`) — root-cause fix, most mechanical,
   immediately useful to CIVerd + vendored copies. **Build first.**
2. **B → v1.15.0** (§0 deploy-surface block) — cheap doctrine, can ride with A if the diff stays
   reviewable; otherwise its own bump.
3. **C → v1.16.0** (`script-adversary` agent + calibration scenario) — self-contained agent add;
   needs a live calibration re-baseline.
4. **D → folded into A/B or its own patch** (§1/§12/§13 one-liners) — smallest; sequence for a clean
   diff.
5. **Deferred 2.1** — owned debt, revisited when a `deployment-probe-calibrator` is scoped.

## 10. Reuse / patterns to follow (don't reinvent)

- RUNNING leg / version-echo: copy the shape of `verify_verdict.py` (`commit == SHA`) and
  `install_into_repo.py --doctor` (vendor-stamp skew) — both already do "running == intended."
- `deploy_surface` field: mirror the existing `integration_debt`/`liveness` optional-field pattern in
  `capabilities.json` + `capability_registry.py`.
- `script-adversary`: mirror `architecture-adversary.md` end-to-end (frontmatter, verdict grammar,
  worked example) + its calibration scenario + KNOWN_AGENTS/AGENT_CONTRACTS/PINNED registration.
- Doctrine pins: mirror `test_agents.py::test_v1x_doctrine` + `_planted_fixtures`.
- Keep it stack-agnostic: state the invariant (running == intended; a probe exercises the effect),
  cite CIVerd/systemd as the origin examples, never bake in a specific stack.
```
