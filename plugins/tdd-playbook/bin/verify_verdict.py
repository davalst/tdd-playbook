#!/usr/bin/env python3
"""verify_verdict — the hub side of the CIVerd release gate (Playbook audit finding F4).

CIVerd is an independent CI engine on a VPS: it notices a commit, clones it at that SHA in a
sandbox the coding agent cannot reach, runs this plugin's gate, and publishes a SIGNED verdict
to `davalst/civerd-verdicts` (`verdicts.jsonl`, one memproof-2 bundle per line). This tool is
the VERIFY side — it runs anywhere (a public plugin, any repo) and answers ONE question:

    Is there a fresh, signed, GREEN *run* verdict for this exact commit, from a live engine?

Exit 0 ONLY when that is true. Every other answer — no verdict, forged claim, wrong SHA, stale,
silent engine, unreachable ledger, tampered bytes, missing crypto lib — is RED with its own
reason. Absence is never a silent pass: a release that ships during a verdict outage is exactly
the failure the engine exists to prevent.

WHY VENDOR, NOT IMPORT: the plugin is PUBLIC and vendors into sandboxes; CIVerd/memrebel are
PRIVATE. So this tool re-implements the memproof-2 verification (stdlib + `cryptography` for
Ed25519 — nothing else). Hand-rolling Ed25519 would fail *open* on a subtle bug (a verifier that
wrongly returns True passes everything), which is worse than no gate; `cryptography` is required
and its absence is RED, not a degraded pass. This is a release-time tool run where you can
`pip install`, not a per-commit hook.

TRUST MODEL: the adversary is the coding agent on this laptop, which cannot forge an Ed25519
signature. So signature + subject + freshness + `ok` is sufficient here; replaying the gate
predicate defends against a *compromised engine*, a different threat handled VPS-side. The
issuer's PUBLIC key is pinned below (it confirms a verdict, can never forge one).

USAGE:
    verify_verdict.py --sha <release sha> [--max-age-s 86400] [--ledger PATH]
Default: fetch `davalst/civerd-verdicts` into ~/.cache/civerd-verdicts (gh/git, ordinary GitHub
auth — a verdicts-READ credential, no write path to the engine) and read verdicts.jsonl.
`--ledger PATH` reads a local ledger instead (tests; no network). A failed fetch is its OWN red
reason (`ledger_unavailable`), never conflated with "no verdict found".

There is deliberately NO --force / --override: a bad release must be UNBUILDABLE, not discouraged
(the same property as `may_release` VPS-side). Exit 0 = release permitted. Exit 1 = RED (refused).
Exit 2 = bad invocation.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# --- The trust anchor. PUBLIC by design: confirms a verdict, can never forge one. Generated on
# the VPS, 0400 owned by civerd-signer, never left the box. Also at civerd:trust/issuer.pub.
# Embedded (not a separate trust/ file) because the installer vendors bin/ wholesale but not a
# new top-level dir — a separate file would silently fail to vendor, and a missing key fails
# closed, which looks identical to an engine outage. Single source, auto-vendored, format-tested.
PINNED_ISSUER_KEY = "08c6913d3c2db56d00a9507a13677bf8b6b243bca2e59bfe3b5c986f43ed4fda"

WIRE_VERSION = "memproof-2"      # signed domain-separation constant; NOT the product name
VERDICTS_REPO = "davalst/civerd-verdicts"

# memproof-2 domain-separation prefixes (SPEC.md §2). Using the wrong serialization under one of
# these silently fails the signature, so the two are kept distinct and documented at each use.
_P_RECORD = b"memproof-2/record-core\x00"
_P_ROOT = b"memproof-2/root\x00"
_P_SNAPSHOT = b"memproof-2/verdict-snapshot\x00"
_P_CLAIMED = b"memproof-2/claimed-verdict\x00"


class Refused(Exception):
    """A verification failed. `.reason` is the machine-stable RED reason string."""

    def __init__(self, reason, detail=""):
        super().__init__(reason if not detail else "{}: {}".format(reason, detail))
        self.reason = reason


# --------------------------------------------------------------------------- serializations
# canonical(): RFC 8785 JCS — keys sorted, compact separators, ensure_ascii=False, floats
# rejected. Used for record cores and the root statement. For the ASCII payloads CIVerd emits,
# JCS's UTF-16 key order coincides with Python's code-point sort_keys; floats are rejected
# explicitly because a float would hash differently across encoders.
def canonical(obj):
    _reject_floats(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


# stable_json(): sort_keys + compact separators. Used ONLY for `snapshot` and `claimed_report`.
def stable_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def _reject_floats(obj):
    if isinstance(obj, float):
        raise Refused("noncanonical", "float in signed core")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if not isinstance(k, str):
                raise Refused("noncanonical", "non-string key")
            _reject_floats(v)
    elif isinstance(obj, list):
        for v in obj:
            _reject_floats(v)


# --------------------------------------------------------------------------- crypto primitives
def _load_verifier():
    """Import Ed25519 lazily so `--help`/arg errors work without the lib, but any real
    verification without it is RED (cryptography_missing), never a degraded pass."""
    try:
        from cryptography.exceptions import InvalidSignature
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    except ImportError:
        raise Refused("cryptography_missing", "pip install cryptography (required to verify)")
    return Ed25519PublicKey, InvalidSignature


def _pubkey(hex_key):
    Ed25519PublicKey, _ = _load_verifier()
    try:
        raw = bytes.fromhex(hex_key.strip())
    except ValueError:
        raise Refused("issuer_key_mismatch", "pinned key is not hex")
    if len(raw) != 32:
        # A truncated paste makes every verify fail closed — call it out as key error, not outage.
        raise Refused("issuer_key_mismatch", "pinned key is not 32 bytes")
    try:
        return Ed25519PublicKey.from_public_bytes(raw)
    except Exception:
        raise Refused("issuer_key_mismatch", "pinned key is not a valid Ed25519 point")


def _verify(pk, sig_hex, prefixed_payload, reason):
    _, InvalidSignature = _load_verifier()
    try:
        sig = bytes.fromhex(sig_hex)
    except (ValueError, TypeError, AttributeError):
        raise Refused(reason, "signature not hex")
    try:
        pk.verify(sig, prefixed_payload)
    except InvalidSignature:
        raise Refused(reason, "signature does not verify")


# --------------------------------------------------------------------------- bundle verification
def _fold_merkle(records):
    """Bottom-up: leaf = sha256(0x00 + canonical(core)); node = sha256(0x01 + left + right),
    ordered by leaf_index. Recomputed from the records so a relaying party holding no key cannot
    swap in a different `merkle_root`."""
    leaves = [
        (r["leaf_index"], hashlib.sha256(b"\x00" + canonical(r["core"])).digest())
        for r in records
    ]
    level = [h for _, h in sorted(leaves, key=lambda t: t[0])]
    if not level:
        raise Refused("leaf_index_set_invalid", "no records")
    while len(level) > 1:
        nxt = []
        for i in range(0, len(level), 2):
            left = level[i]
            right = level[i + 1] if i + 1 < len(level) else level[i]  # duplicate the odd tail
            nxt.append(hashlib.sha256(b"\x01" + left + right).digest())
        level = nxt
    return level[0].hex()


def verify_bundle(bundle, expect_sha, now, max_age_s, pinned=PINNED_ISSUER_KEY):
    """Verify one memproof-2 bundle end to end. Returns a dict:
        {authentic, verdict_ok, kind, commit, reason}
    `authentic` ("this is genuinely our signed verdict") is reported SEPARATELY from `verdict_ok`
    ("the gate said yes") — conflating them ships red builds. Raises Refused on the first failure.
    """
    if not isinstance(bundle, dict):
        raise Refused("malformed", "bundle is not an object")

    # 1. version
    if bundle.get("version") != WIRE_VERSION:
        raise Refused("unsupported_version", str(bundle.get("version")))

    # 2. issuer key equals the vendored pin (case-insensitive, whitespace-stripped). Because we
    # ONLY ever verify against this pin (never a bundle-supplied key), a substituted small-order
    # key can't be used — pin-equality subsumes torsion rejection.
    issuer = str(bundle.get("issuer_public_key", "")).strip().lower()
    if issuer != pinned.strip().lower():
        raise Refused("issuer_key_mismatch", "bundle issuer != pinned")
    pk = _pubkey(pinned)

    records = bundle.get("records")
    if not isinstance(records, list) or not records:
        raise Refused("malformed", "no records")

    # 4. count == len(records) AND leaf_index set is exactly {0..count-1}. LOAD-BEARING: without
    # it a keyless relay could delete a record and duplicate another at its index and still verify.
    count = bundle.get("count")
    if count != len(records):
        raise Refused("leaf_index_set_invalid", "count != len(records)")
    try:
        idxs = sorted(int(r["leaf_index"]) for r in records)
    except (KeyError, TypeError, ValueError):
        raise Refused("leaf_index_set_invalid", "missing/bad leaf_index")
    if idxs != list(range(count)):
        raise Refused("leaf_index_set_invalid", "leaf_index set != {0..count-1}")

    # 3. every record signature verifies over the record core
    for r in records:
        _verify(pk, r.get("signature", ""), _P_RECORD + canonical(r["core"]), "record_sig_invalid")

    # 5. each leaf folds to merkle_root
    if _fold_merkle(records) != bundle.get("merkle_root"):
        raise Refused("merkle_root_mismatch", "records do not fold to merkle_root")

    # 6. root signature over {merkle_root, count, as_of}
    root_stmt = {
        "merkle_root": bundle.get("merkle_root"),
        "count": count,
        "as_of": bundle.get("as_of"),
    }
    _verify(pk, bundle.get("root_signature", ""), _P_ROOT + canonical(root_stmt), "root_sig_invalid")

    v = bundle.get("verdict")
    if not isinstance(v, dict):
        raise Refused("malformed", "no verdict section")
    snapshot = v.get("snapshot")
    claimed = v.get("claimed_report")
    if not isinstance(snapshot, dict) or not isinstance(claimed, dict):
        raise Refused("malformed", "verdict missing snapshot/claimed_report")

    # 7. verdict section signatures (stable_json, NOT canonical)
    _verify(pk, v.get("snapshot_signature", ""), _P_SNAPSHOT + stable_json(snapshot),
            "snapshot_sig_invalid")
    _verify(pk, v.get("claimed_report_signature", ""), _P_CLAIMED + stable_json(claimed),
            "claimed_report_sig_invalid")

    # --- bytes are authentic past this point. Now the SUBJECT/FRESHNESS/RESULT questions. ---
    kind = snapshot.get("kind")
    commit = snapshot.get("commit")

    # 9. fresh: as_of within window AND not future-dated (a future stamp must not extend validity)
    as_of = _parse_ts(bundle.get("as_of"))
    if as_of is None:
        raise Refused("stale", "unparseable as_of")
    age = (now - as_of).total_seconds()
    if age < 0:
        raise Refused("stale", "as_of is in the future")
    if age > max_age_s:
        raise Refused("stale", "older than max-age ({:.0f}s)".format(age))

    return {
        "authentic": True,
        "verdict_ok": bool(claimed.get("ok") is True),
        "kind": kind,
        "commit": commit,
        "reason": "ok",
    }


def _parse_ts(s):
    if not isinstance(s, str):
        return None
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


# --------------------------------------------------------------------------- ledger-level decision
def may_release(ledger_lines, expect_sha, now, max_age_s, pinned=PINNED_ISSUER_KEY):
    """Decide over a whole ledger. Returns (allowed: bool, reason: str).

    Requires BOTH (a) a fresh authentic GREEN *run* verdict whose commit == expect_sha, and
    (b) a live engine heartbeat. A quiet engine BLOCKS releases — if "engine down" let a release
    through, never publishing a verdict would be the cheapest attack. A heartbeat (commit 0x0*40)
    can never satisfy the run requirement: it fails the commit match and is not kind=="run"."""
    bundles = []
    for ln in ledger_lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            bundles.append(json.loads(ln))
        except ValueError:
            continue  # a malformed line is not a valid verdict; keep scanning

    engine_alive = False
    run_hit = None  # (allowed, reason) for the run verdict matching expect_sha, if any

    for b in bundles:
        snap = (b.get("verdict") or {}).get("snapshot") or {}
        kind = snap.get("kind")
        # Heartbeat: authentic + fresh (checks 1-9) => engine is alive.
        if kind == "heartbeat":
            try:
                verify_bundle(b, expect_sha=None, now=now, max_age_s=max_age_s, pinned=pinned)
                engine_alive = True
            except Refused:
                pass
            continue
        if kind != "run":
            continue
        # A run verdict: does it authenticate AND concern our SHA AND say ok?
        if snap.get("commit") != expect_sha:
            continue
        try:
            res = verify_bundle(b, expect_sha, now=now, max_age_s=max_age_s, pinned=pinned)
        except Refused as e:
            run_hit = (False, e.reason)
            continue
        if not res["verdict_ok"]:
            run_hit = (False, "verdict_not_ok")
        else:
            run_hit = (True, "ok")

    if run_hit is None:
        return (False, "no_verdict_for_commit")
    allowed, reason = run_hit
    if not allowed:
        return (False, reason)
    if not engine_alive:
        return (False, "engine_silent")
    return (True, "ok")


# --------------------------------------------------------------------------- ledger acquisition
def _cache_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "civerd-verdicts")


def fetch_ledger():
    """Clone/pull davalst/civerd-verdicts into the cache and return verdicts.jsonl lines.
    A failed fetch raises Refused('ledger_unavailable') — never silently 'no verdict', because
    a release must not slip through during an outage."""
    dest = _cache_dir()
    try:
        if os.path.isdir(os.path.join(dest, ".git")):
            subprocess.run(["git", "-C", dest, "pull", "--quiet", "--ff-only"],
                           check=True, capture_output=True, timeout=120)
        else:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            subprocess.run(["gh", "repo", "clone", VERDICTS_REPO, dest, "--", "-q"],
                           check=True, capture_output=True, timeout=120)
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        raise Refused("ledger_unavailable", str(e)[:120])
    path = os.path.join(dest, "verdicts.jsonl")
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.readlines()
    except OSError as e:
        raise Refused("ledger_unavailable", str(e)[:120])


# --------------------------------------------------------------------------- CLI
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="verify_verdict.py",
        description="Permit a release only for a fresh signed GREEN CIVerd verdict of this SHA.",
    )
    ap.add_argument("--sha", required=True, help="the exact release commit SHA to verify")
    ap.add_argument("--max-age-s", type=int, default=86400,
                    help="max verdict/heartbeat age in seconds (default 86400)")
    ap.add_argument("--ledger", default=None,
                    help="read this local verdicts.jsonl instead of fetching (tests/offline)")
    # NOTE: intentionally no --force / --override. A bad release is unbuildable, not discouraged.
    args = ap.parse_args(argv)

    now = datetime.now(timezone.utc)
    try:
        if args.ledger:
            with open(args.ledger, encoding="utf-8") as fh:
                lines = fh.readlines()
        else:
            lines = fetch_ledger()
        allowed, reason = may_release(lines, args.sha, now=now, max_age_s=args.max_age_s)
    except Refused as e:
        allowed, reason = False, e.reason
    except OSError as e:
        allowed, reason = False, "ledger_unavailable"
        reason = "ledger_unavailable"

    if allowed:
        print("RELEASE OK — signed GREEN verdict for {} (engine live)".format(args.sha[:12]))
        return 0
    print("RELEASE REFUSED [{}] — no releasable verdict for {}".format(reason, args.sha[:12]),
          file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
