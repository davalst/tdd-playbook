# Gate Engine — independent CI verdicts for the TDD Playbook (build plan)

**Status:** approved-for-build plan · 2026-07-27 · lives here in the hub; copy into the new
`gate-engine` repo as its founding spec.
**Deployment target:** David's Hostinger VPS (cohabiting with idle Hermes) · Tailscale for
admin only · no public inbound.
**Origin:** Playbook audit finding F4 — every release-gate "green" is currently self-attested
by the same agent session that wrote the code. §10 doctrine: the one property a third party
uniquely provides is *results the working session cannot edit*. GitHub Actions was rejected as
hub-shaped (its own UI/status model/YAML, doesn't report back into our flow); this engine is
the satellite architecture: **the Playbook hub owns the protocol; runners are dumb muscles.**

---

## 1. Threat model — read this first, it drives every decision

- **Defended against:** the coding agent (Claude) running on David's laptop with David's user
  privileges. Documented attack classes (HACK_CATALOG H2/H5): weaken the gate, fake the green,
  tamper with the checker. Assume a top-tier model that reads this spec.
- **NOT the primary threat:** internet attackers. Tailscale + no public ports handles that
  cheaply. Do not let network hardening substitute for trust-flow hardening.
- **Consequences:**
  1. **The laptop is the untrusted zone.** It gets NO write path to the engine — no SSH key
     on the laptop that can touch engine code/config/ledger/keys. Tailscale SSH is David's
     human admin plane only. (The agent inherits every credential the laptop holds.)
  2. **Verdict authenticity = cryptography, not network position.** Being "on the tailnet"
     authorizes nothing.
  3. **Gate execution is hostile-code execution.** The tests the engine runs were pushed by
     the very party we defend against. The process that runs them must not be able to reach
     the signing key or the ledger.
  4. **Absence of evidence = RED.** If "engine down" lets a release proceed, the agent's
     cheapest move is to never wait for a verdict. Fail closed, always.

## 2. Non-goals

No public webhooks · no inbound HTTP · no GitHub Actions · no matrix builds · no test
orchestration logic (repos define their own gate command) · no pip dependencies (stdlib +
git + ssh-keygen only) · not a general CI platform — it watches the Playbook repo family only.

## 3. Architecture

```
                    (poll, read-only deploy key)
   GitHub remotes  <──────────────────────────────  [gate-runner user]
   (watched repos)                                   fresh clone per SHA
        │                                            run configured gate cmd
        │ push verdicts / commit statuses            capture exit+output digest
        ▼                                            write result → /var/spool/gate/
   gate-verdicts repo  ◄──────────────────────────  [gate-signer user]
   + commit statuses (statuses:write PAT)            validate spool entry
        │                                            ssh-keygen -Y sign → append ledger
        ▼                                            push ledger + post status
   David's laptop / agent sessions                   daily heartbeat verdict
   READ verdicts via git/gh like anyone else
   (verify signature with vendored pubkey)

   Tailscale: ADMIN PLANE ONLY (David → sshd bound to tailnet interface)
```

**The trust rules (load-bearing, in order):**
1. Laptop→engine: no data-plane write path exists. Period.
2. Verdicts are signed on-box (`ssh-keygen -Y sign`, ed25519). Private key: owned by
   `gate-signer`, mode 0400, generated on the VPS, never leaves it. Public key: vendored
   into the Playbook (`allowed_signers`), so any session can VERIFY but none can FORGE.
3. `gate-runner` cannot read the key or write the ledger. `gate-signer` never executes repo
   code. The spool directory is the only shared surface (runner: write-only; signer:
   read+delete; validated schema, size-capped).
4. A verdict binds `{repo, sha, branch, gate_cmd, exit, stdout_digest, started, duration,
   engine_version}` — signature over the canonical JSON line. Wrong SHA / unsigned /
   tampered ⇒ the Playbook-side verifier REFUSES (RED).
5. Engine config (`repos.yml`, units, keys) changes only via David's admin SSH — never
   derived from watched-repo contents. (A repo cannot reconfigure its own judge.)
6. Heartbeat: one signed `heartbeat` verdict daily. Playbook staleness sweep flags a silent
   engine; "no fresh heartbeat" = engine considered DOWN = releases blocked (fail closed).

## 4. Components (all stdlib; target sizes are ceilings)

| Component | User | ~Size | Responsibility |
|---|---|---|---|
| `poller.py` | gate-runner | 120 ln | Every 60s: `git ls-remote` watched repos; new SHA on a watched branch → enqueue job. |
| `runner.py` | gate-runner | 150 ln | Fresh `git clone --depth 1` at SHA into throwaway dir; run the repo's configured gate command with timeout + resource caps; write result JSON to spool; scrub workdir. |
| `signer.py` | gate-signer | 150 ln | Validate spool entry against schema; canonicalize; `ssh-keygen -Y sign`; append to `verdicts.jsonl`; commit+push to `gate-verdicts` repo; POST commit status; delete spool entry. |
| `heartbeat` | gate-signer | 30 ln | Daily signed heartbeat verdict (cron/systemd timer). |
| `repos.yml` | root-owned | — | Allowlist: repo URL, branches, gate command, timeout. Nothing else is ever watched. |
| systemd units ×2 | root | — | Hardening: `NoNewPrivileges`, `ProtectSystem=strict`, `PrivateTmp`, `ProtectHome`, `MemoryMax`, `RuntimeMaxSec` per run; runner unit additionally `IPAddressAllow` = GitHub only. |

**Initial `repos.yml`:** `tdd-playbook` (gate: the release-gate suite commands) — grow to the
vendored-consumer repos (cheliped, memstruct) once stable. Gate command per repo TODAY is the
explicit suite list; when the Playbook ships `release_gate.py` (single vendored entrypoint),
configs collapse to that one line. Engine stays dumb either way.

## 5. Playbook-side integration (separate release in the hub repo)

- `bin/verify_verdict.py --sha <sha>`: pulls `gate-verdicts`, finds the newest verdict for the
  SHA, verifies signature against the vendored `allowed_signers`, checks freshness + exit==0.
  Exit 0 only on a valid signed green. **This joins the release gate:** no version bump ships
  without a signed engine verdict for the release SHA (absence/stale/tampered/wrong-sha = RED).
- Session flow: after push, `Monitor` the `gate-verdicts` remote (or `gh api` the commit
  status) — the return comes INTO our flow; nobody reads a foreign CI tab.
- Optional, zero-GHA enforcement: branch protection requiring the engine's status context.

## 6. Failure modes → responses

| Failure | Response |
|---|---|
| Engine down / VPS dead | No fresh heartbeat → releases blocked (fail closed). Admin fixes via Tailscale. |
| Clone or gate command errors | Verdict with `exit != 0` + error class — a RED verdict, never silence. |
| Gate hangs | `RuntimeMaxSec` kills it → RED verdict `timeout`. |
| Tampered ledger line | Signature verification fails Playbook-side → RED + loud "tamper evidence" message. |
| Forged verdict attempt | No key off-box; forging requires VPS privilege escalation via… what path? None exists from the laptop. |
| Key loss (VPS dies) | Rotate: new key on rebuilt box; David commits the new pubkey to the Playbook (human-signed trust anchor). Ledger history survives in git. |
| Replay (old green re-presented) | Verdicts bind SHA + timestamp; verifier requires the RELEASE SHA and freshness window. |

## 7. Calibration — the engine eats the Playbook's own dogfood (§13)

Suite (planted-input, runs in the engine repo's CI-less test suite):
- forged signature → verifier REFUSES; tampered byte in a ledger line → REFUSES;
- verdict for the wrong SHA → REFUSES; stale heartbeat → staleness check RED;
- runner spool entry with schema violations → signer rejects (never signs garbage);
- a gate command that exits nonzero → RED verdict emitted (never swallowed).

Live probe (scheduled, monthly): push a known-RED commit to a scratch branch of a watched
repo; the engine must publish a RED verdict for it. An engine that never fails a plant is
theater — same rule as every other gate in the system.

## 8. VPS prerequisites (David checks before build)

- [ ] `python3 --version` ≥ 3.9; `git --version`; `ssh-keygen -Y sign` available (OpenSSH ≥ 8.2p1)
- [ ] Disk ≥ 2 GB free (clones are shallow + scrubbed); RAM headroom with Hermes idle (engine needs ~100 MB peak)
- [ ] systemd available; can create `gate-runner`/`gate-signer` users
- [ ] Tailscale up; sshd bound to tailnet interface only; public inbound closed
- [ ] GitHub: read-only deploy key (or fine-grained PAT, contents:read) + statuses:write PAT — created by David, stored only on the VPS, never on the laptop
- [ ] New empty `gate-verdicts` repo + new `gate-engine` repo

## 9. Build phases & acceptance

- **P1 — Engine MVP:** poller + runner + signer + heartbeat + units + planted suite. Accept:
  a push to `tdd-playbook` produces a signed verdict in `gate-verdicts` within ~2 min; every
  planted-suite check green; laptop demonstrably cannot write engine state (documented probe).
- **P2 — Hub integration (tdd-playbook release):** `verify_verdict.py` + vendored pubkey +
  release-discipline line ("no bump without a signed verdict") + Monitor flow. Accept: a
  release attempt without a fresh signed verdict fails RED in this repo's own release gate.
- **P3 — Rollout + probes:** add consumer repos to `repos.yml`; monthly known-red live probe
  scheduled; optional branch-protection status contexts.

## 10. Prior art (swept 2026-07-27 — build justified, two borrowings)

Five-search sweep across four facets before committing to build. Conclusion: **the two halves
exist separately — validating this design — but no product/OSS combines them.**
- **Buildkite** independently validates the satellite pattern (agents poll outward over HTTPS,
  no inbound, compute stays yours) — but its SaaS is the truth store: unsigned verdicts in
  their DB/UI. Borrow the pattern, not the product.
- **Laminar CI / Woodpecker / Gitea-Forgejo Actions / sourcehut builds**: minimal runners
  exist, but all are execution-only or hub-shaped (webhooks/forge/their UI), none sign
  verdicts, none have the runner/signer privilege split. Laminar could replace `runner.py`
  only by adding a C++ daemon dependency — rejected.
- **Sigstore/cosign/Rekor + in-toto**: mature signed-attestation machinery, built for
  supply-chain artifact provenance (keyless OIDC, public logs) — heavier than our need.
  **Borrowing:** shape the verdict JSON as an in-toto Statement envelope (field-naming only,
  ~zero cost) for future interop.
- **Agent-sandbox industry (E2B/Modal/Northflank/Docker, 2026)**: solves the INVERSE problem
  (protect the world from agent code), not ours (protect the verdict from the agent). The
  agent-adversarial, fail-closed verdict gate appears unserved.
- §12 bound: "doesn't exist" is bounded by this sweep. If the build session's own dive finds
  real prior art matching the threat model, ADOPT it — this plan prefers not-invented-here
  losing to a genuine fit.

## 11. Relationship to MemStruct (decided 2026-07-27: share primitives, never the trust chain)

MemStruct already ships the engine's DNA in production form: Ed25519-signed offline-replayable
proof bundles (`memproof-2`), hash-chained tamper-evident ledgers, deterministic zero-model-call
verdicts, fail-closed refusal, planted-error non-vacuity. Consolidation was considered and
REJECTED on trust grounds:
- **The judge can't live inside a defendant.** MemStruct is actively agent-developed and is a
  repo this engine should WATCH; merging means every agent-written MemStruct deploy redeploys
  the judge (violates trust rule #5).
- **Trust chains must be boring.** The engine is ~450 frozen stdlib lines; MemStruct is a living
  product (FastAPI/Docker/migrations/pgvector/MCP) — its whole dependency + deploy surface would
  join the verdict trust chain, and its churn would block releases (fail-closed cuts both ways).
What we DO take:
1. **Same VPS**, separate unix users + systemd units (Hermes pattern).
2. **Primitives, if they extract cleanly:** prefer MemStruct's proven Ed25519 sign/verify +
   replay core over `ssh-keygen -Y` IF it vendors as a small frozen no-dependency module
   (build-time call in the engine repo; the stdlib-only rule is the bar).
3. **MemStruct as downstream CONSUMER:** verdicts ingested READ-ONLY into MemStruct as governed
   records ("was release SHA X verified — prove it, point-in-time"), feeding its audit-budget
   story without entering the trust chain. Git ledger remains the source of truth.
Family framing for productization: Playbook (methodology) · Gate Engine (CI verdicts) ·
MemStruct (memory/decision verdicts) — one verification-trust DNA, three surfaces.

## 12. Open questions for David

1. VPS specs / OS version (sizes the resource caps).
2. Watch `main` only, or feature branches too? (main-only is the cheap start.)
3. Freshness window for verdicts at release time (proposal: 24 h, and always same-SHA).
4. Container isolation (podman) as P4 hardening, or is the two-user + systemd tier enough
   for the current threat level? (Proposal: two-user now; containers if collaborators join.)
