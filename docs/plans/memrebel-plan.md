# memrebel — a tiny open standard for signed, replayable verdicts (founding plan)

**Status:** approved-for-build · 2026-07-27 · lives in the hub; copy into the new `memrebel`
repo as its founding spec.
**What it is:** the proof kernel extracted from MemStruct (`memproof-2` format) as a
standalone, frozen, open library + specification: canonical serialization, Ed25519
sign/verify, offline **bit-for-bit replayable** verification of a signed verdict bundle.
**Why it exists:** three products share one verification-trust DNA — the TDD Playbook
(methodology), CIVerd (CI verdicts), MemStruct (memory/decision verdicts). The
universal piece is not any app; it is the PROOF FORMAT. Whoever publishes the format owns the
category conversation ("the trust layer for agent-era work products"). An open, one-sitting-
auditable kernel with two working reference implementations is a stronger claim than either
app alone — and it is the piece platform incumbents are structurally conflicted about
absorbing (they sell the agent; a neutral proof format needs independence).

## 1. Scope — and the HARD ceiling (read before adding anything)

IN: the envelope format (in-toto Statement-shaped: standard envelope, domain-owned predicate
payload) · canonical JSON serialization rules · Ed25519 sign/verify · bundle
assembly/parsing · offline replay verification · golden test vectors · `SPEC.md` (normative)
· a ~50-line CLI (`memrebel verify <bundle>`, `memrebel sign` for testing).

OUT — **permanently, this is what "standard" means**: no network, no storage, no key custody
(consumers own keys), no transparency log, no registries, no domain schemas (CIVerd owns
its verdict predicate; MemStruct owns its belief predicates), no server, no framework.
**Ceiling: ~500 lines of library code, ONE dependency (`cryptography`).** A standard's value
is inverse to its growth rate; when it works, it FREEZES (changes = new spec version with
explicit rules, never in-place drift).

## 1a. Naming — product vs wire format (CRITICAL: do not conflate)

The **product / library / repo / standard** is **memrebel** (renamed 2026-07-27 for trademark).
The **on-disk wire-format identifier stays `memproof-2`** and MUST NOT be renamed — it is a
**signed cryptographic domain-separation constant** (verified 2026-07-27 in MemStruct's
`app/proof_verify.py`: `"memproof-2/root\x00"`, `"memproof-2/verdict-snapshot\x00"`,
`"memproof-2/record-core\x00"`, `"memproof-2/claimed-verdict\x00"`). These strings are part of
the signed bytes: renaming them changes every signature, breaks every existing MemStruct bundle,
and voids the §3 golden vectors. **memrebel v1 IS the memproof-2 wire format, adopted verbatim.**
Future breaking format versions continue the `memproof-N` lineage (memproof-3, …) regardless of
product name; a product-branded re-tag would be a deliberate, compat-breaking future decision,
never this rename. Build session: treat every `memproof-2*` literal as a frozen protocol constant.

## 2. Extraction sources (verified by inspection 2026-07-27)

From `~/Documents/GitHub/MemStruct` (≈400 lines total, sole crypto dep
`cryptography>=41.0.7` / `Ed25519PublicKey`):
- `app/gate_eval.py` (253 ln) — the deterministic verdict evaluation + canonicalization side
  (extract only the format/canonicalization pieces; app-specific verdict LOGIC stays behind).
- `app/proof_replay.py` (92 ln) — offline replay of a signed bundle.
- `scripts/verify_proof.py` (55 ln) — outsider verification with only the issuer pubkey.
- Also referenced: `app/proof_verify.py`, `app/assurance.py` — the build session maps the
  actual import graph and takes the MINIMAL closure (§12 rule: read before cherry-picking).

**Interim divergence guard (do FIRST, in MemStruct's repo):** add one line to MemStruct's
`CLAUDE.md`: *"proof kernel (gate_eval/proof_replay/proof_verify/verify_proof) FROZEN pending
memrebel extraction — see tdd-playbook/docs/plans/memrebel-plan.md"* — so agent sessions
there don't evolve the dialect while the standard hardens.

## 3. The compatibility contract (the acceptance criterion that makes this safe)

**Golden vectors:** capture real `memproof-2` bundles produced by TODAY's MemStruct and
commit them to `memrebel/testdata/golden/`. `memrebel-core` MUST verify them byte-for-byte.
This guarantees the later MemStruct retrofit is *swap-the-import*, not *migrate-the-data* —
and it is the planted-test bedrock:
- golden bundle verifies → PASS required;
- ONE flipped byte anywhere (payload, signature, envelope) → verification MUST fail;
- signature from a different key → MUST fail;
- truncated / reordered-keys / re-serialized-non-canonically → MUST fail (canonicalization is
  part of the contract, not a courtesy);
- a bundle claiming spec version `memproof-3` → REFUSED by a `memproof-2` verifier (never
  "best effort").
A verifier that cannot be made to fail is theater (Playbook §13 — same rule, same teeth).

## 4. Deliverables

| # | Deliverable | Notes |
|---|---|---|
| 1 | `memrebel/` library (≤500 ln) | `envelope.py` · `canonical.py` · `sign.py` · `verify.py` · `replay.py` |
| 2 | `SPEC.md` (normative) | Envelope fields, canonicalization rules, signature scheme, replay semantics, versioning policy (memproof-2 baseline; how a future memproof-3 would happen), key-custody GUIDANCE (non-normative appendix). |
| 3 | Golden vectors + planted suite | §3 above; zero-model, stdlib test runner in the Playbook's planted-input style. |
| 4 | CLI (~50 ln) | `verify` / `sign` (testing only) — the outsider's one-command check. |
| 5 | README + positioning | "A proof format for agent-era work products"; names the two reference implementations; Apache-2.0 (patent grant; matches family licensing). |

## 5. Build order & consumers

1. **memrebel repo** (this plan) — extraction + golden vectors green.
2. **CIVerd P1** consumes it (first NEW reference implementation; its verdicts are
   memrebel bundles — see `civerd-plan.md` §3 rule 2).
3. **Playbook hub** vendors the verify side (`verify_verdict.py`) when CIVerd P2 lands.
4. **MemStruct retrofit LAST** (David's sequencing, agreed): after civerd + memrebel are
   proven on the VPS, MemStruct swaps its embedded kernel for the library — golden vectors
   guarantee the swap. MemStruct also relocates to the VPS per its own roadmap (independence:
   a tamper-evident ledger on the agent's laptop is theater).

## 6. Open questions for David

1. Name check: "memrebel" collision/trademark sweep at repo creation (5 minutes, before the
   README goes public).
2. Public from day one, or private until CIVerd proves it? (Lean: private until golden
   vectors + one reference implementation are green, then public with the positioning README —
   an open standard with zero working consumers is a press release, not a standard.)
3. Does `memproof-2`'s envelope already carry a spec-version field? (Build session verifies;
   if not, that's the ONE permitted format addition, done as memproof-2.1 with MemStruct's
   agreement since it defines the dialect today.)
