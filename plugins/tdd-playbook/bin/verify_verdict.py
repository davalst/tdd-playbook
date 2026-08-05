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
PRIVATE. So this tool re-implements the memproof-2 verification. It is STDLIB-ONLY — like every
other bin here — because the machine that watches this repo installs only `pytest`, so a
third-party import (`cryptography`) would make CIVerd emit a permanent RED for its only subject.
Ed25519 verification is provided by the sibling `_ed25519_verify` module (verification-only, no
signing/keygen). The one fear with a hand-written verifier is failing OPEN; that is neutralized by
RFC 8032 known-answer + negative vectors in tests/test_ed25519_verify.py (a `return True` mutant
must turn the suite RED). This is a release-time tool, not a per-commit hook.

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ed25519_verify  # noqa: E402  (sibling stdlib verifier, vendored alongside)

# --- The trust anchor. PUBLIC by design: confirms a verdict, can never forge one. Generated on
# the VPS, 0400 owned by civerd-signer, never left the box. Also at civerd:trust/issuer.pub.
# Embedded (not a separate trust/ file) because the installer vendors bin/ wholesale but not a
# new top-level dir — a separate file would silently fail to vendor, and a missing key fails
# closed, which looks identical to an engine outage. Single source, auto-vendored, format-tested.
PINNED_ISSUER_KEY = "08c6913d3c2db56d00a9507a13677bf8b6b243bca2e59bfe3b5c986f43ed4fda"

# ---- repo-side ROSTER PIN (2026-08-03 CIVerd hand-off; David's decisions same day) ----
# Verified engine-side: the verdict's `required` set is derived from what RAN — an echo,
# not a contract — so a check silently dropped from the engine's root config yields a
# GREEN verdict with a shorter checks[] that still verifies and still evaluates ok. This
# pin is the ONLY release-side defense against roster shrink. HARDCODED on purpose (no
# config file, no CLI/env override — same posture as no --force): changing it is a loud
# diff on exactly the surface the engine's integrity_globs should cover.
# EXPECTED_REQUIRED members must appear in BOTH the snapshot's `required` list and its
# checks[] (a check that ran but was demoted from required is also a shrink).
# EXPECTED_PRESENT members are pinned PRESENCE-ONLY (advisory checks never block on
# being red, but their silent DISAPPEARANCE is the absence-blind-monitor class §6c bans).
EXPECTED_REQUIRED = ("dataflow", "deps", "dryrun", "registry", "tests", "venv")
EXPECTED_PRESENT = ("staleness",)


# ---- probe/CI COLLISION (CIVerd engine finding, 2026-08-05) ----------------------------
# `planted_probe` writes ordinary kind:"run" ledger entries, so kind+commit cannot tell a
# probe verdict from a CI verdict. For ~5 hours a GREEN probe outranked a RED CI verdict at
# the same sha under a last-match-wins reducer. Identify release-deciding verdicts
# POSITIVELY instead: a CI entry's gate_cmd names the checks it actually ran (" && "
# separated); probe and cert entries structurally do not carry them. CI_CORE is deliberately
# MINIMAL — not the full roster — so that a genuine roster SHRINK still reaches roster_gaps()
# and fails loud and named, rather than silently ceasing to be a candidate.
CI_CORE = ("tests",)


def gate_cmd_checks(snapshot):
    """The check names an entry's gate_cmd claims to have run."""
    return {t.strip() for t in str(snapshot.get("gate_cmd") or "").split("&&") if t.strip()}


def is_ci_verdict(snapshot):
    """True only for release-deciding CI verdicts. A probe entry (gate_cmd
    'planted_probe') can never authorize a release, nor mask a CI verdict, nor trigger a
    spurious roster_shrink on one."""
    return set(CI_CORE).issubset(gate_cmd_checks(snapshot))


def roster_gaps(snapshot):
    """Sorted names missing from the snapshot vs the pin. Empty = roster intact.
    Engine-side EXTRA checks (integrity, integrity_baseline, ...) are always fine —
    the pin is a floor, never an exact-set match."""
    required = set(snapshot.get("required") or [])
    ran = {c.get("name") for c in snapshot.get("checks") or [] if isinstance(c, dict)}
    gaps = {n for n in EXPECTED_REQUIRED if n not in required or n not in ran}
    gaps.update(n for n in EXPECTED_PRESENT if n not in ran)
    return sorted(gaps)

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
# canonical(): RFC 8785 JCS. Keys sorted by UTF-16 CODE UNITS (NOT Python's code-point sort_keys —
# they agree on all ASCII and diverge only above the BMP, so real fixtures can't catch the bug; a
# wrong sort surfaces as a false RED on an honest non-ASCII verdict). Minimal escapes, literal
# UTF-8, floats rejected (a float would hash differently across encoders). Cross-validated against
# memrebel's golden canonical_vectors. Used for record cores and the root statement.
def canonical(obj):
    return _jcs(obj).encode("utf-8")


def _jcs(o):
    if o is True:
        return "true"
    if o is False:
        return "false"
    if o is None:
        return "null"
    if isinstance(o, float):
        raise Refused("noncanonical", "float in signed core")
    if isinstance(o, int):
        return str(o)
    if isinstance(o, str):
        return json.dumps(o, ensure_ascii=False)
    if isinstance(o, list):
        return "[" + ",".join(_jcs(x) for x in o) + "]"
    if isinstance(o, dict):
        for k in o:
            if not isinstance(k, str):
                raise Refused("noncanonical", "non-string key")
        items = sorted(o.items(), key=lambda kv: kv[0].encode("utf-16-be"))
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + _jcs(v)
                              for k, v in items) + "}"
    raise Refused("noncanonical", "unserializable type")


# stable_json(): sort_keys (code point) + compact separators. Used ONLY for `snapshot` and
# `claimed_report`, whose keys are ASCII. Unlike canonical() it does NOT reject floats.
# Cross-validated against memrebel's golden stable_json_vectors.
def stable_json(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


# --------------------------------------------------------------------------- crypto primitives
def _pubkey(hex_key):
    """Validate and return the 32 raw bytes of the pinned issuer key. A non-hex/non-32-byte or
    small-order key is `bad_issuer_key` — distinct from `issuer_key_mismatch` (a well-formed key
    that just isn't ours). A truncated paste fails closed, so name it a key error, not an outage."""
    try:
        raw = bytes.fromhex(hex_key.strip())
    except (ValueError, AttributeError):
        raise Refused("bad_issuer_key", "pinned key is not hex")
    if not _ed25519_verify.valid_pubkey(raw):
        raise Refused("bad_issuer_key", "pinned key is not a valid non-small-order Ed25519 key")
    return raw


def _verify(pk_bytes, sig_hex, prefixed_payload, reason):
    try:
        sig = bytes.fromhex(sig_hex)
    except (ValueError, TypeError, AttributeError):
        raise Refused(reason, "signature not hex")
    if not _ed25519_verify.verify(pk_bytes, prefixed_payload, sig):
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


def verify_facts(bundle, pinned=PINNED_ISSUER_KEY):
    """Verify the FACTS layer of one memproof-2 bundle: version, issuer, every signature, the
    count/leaf_index set, and the Merkle fold. This is the crypto/structure half — it is
    time-independent and subject-independent, so it exactly mirrors memrebel's own facts check
    (cross-validated against its golden bundle_cases, reason strings included). Returns
        {kind, commit, verdict_ok}
    on success — where `verdict_ok` ("the gate said yes") is deliberately SEPARATE from the fact
    that the bundle is authentic; conflating them ships red builds. Raises Refused(reason) on the
    first failure, with memrebel's exact reason string. Freshness/commit-match/engine-liveness are
    the RELEASE-decision layer and live in may_release(), not here."""
    if not isinstance(bundle, dict):
        raise Refused("malformed", "bundle is not an object")

    # version
    if bundle.get("version") != WIRE_VERSION:
        raise Refused("unsupported_version", str(bundle.get("version")))

    # issuer must equal the vendored pin (case-insensitive, whitespace-stripped); then the pinned
    # key itself must be a valid non-small-order point. mismatch vs bad-key are distinct reasons.
    issuer = str(bundle.get("issuer_public_key", "")).strip().lower()
    if issuer != pinned.strip().lower():
        raise Refused("issuer_key_mismatch", "bundle issuer != pinned")
    pk = _pubkey(pinned)

    records = bundle.get("records")
    if not isinstance(records, list) or not records:
        raise Refused("malformed", "no records")

    # count == len(records), THEN leaf_index set is exactly {0..count-1}. LOAD-BEARING: without the
    # set rule a keyless relay could delete a record and duplicate another at its index and verify.
    count = bundle.get("count")
    if count != len(records):
        raise Refused("count_mismatch", "count != len(records)")
    try:
        idxs = sorted(int(r["leaf_index"]) for r in records)
    except (KeyError, TypeError, ValueError):
        raise Refused("leaf_index_set_invalid", "missing/bad leaf_index")
    if idxs != list(range(count)):
        raise Refused("leaf_index_set_invalid", "leaf_index set != {0..count-1}")

    # every record signature verifies over the record core
    for r in records:
        _verify(pk, r.get("signature", ""), _P_RECORD + canonical(r["core"]),
                "record_signature_invalid")

    # each leaf folds to merkle_root
    if _fold_merkle(records) != bundle.get("merkle_root"):
        raise Refused("merkle_root_mismatch", "records do not fold to merkle_root")

    # root signature over {merkle_root, count, as_of} — a tampered as_of surfaces HERE (the reason
    # is root_signature_invalid), never as a fake "stale", because as_of is inside the signed root.
    root_stmt = {
        "merkle_root": bundle.get("merkle_root"),
        "count": count,
        "as_of": bundle.get("as_of"),
    }
    _verify(pk, bundle.get("root_signature", ""), _P_ROOT + canonical(root_stmt),
            "root_signature_invalid")

    v = bundle.get("verdict")
    if not isinstance(v, dict):
        raise Refused("malformed", "no verdict section")
    snapshot = v.get("snapshot")
    claimed = v.get("claimed_report")
    if not isinstance(snapshot, dict) or not isinstance(claimed, dict):
        raise Refused("malformed", "verdict missing snapshot/claimed_report")

    # verdict-section signatures (stable_json, NOT canonical)
    _verify(pk, v.get("snapshot_signature", ""), _P_SNAPSHOT + stable_json(snapshot),
            "snapshot_signature_invalid")
    _verify(pk, v.get("claimed_report_signature", ""), _P_CLAIMED + stable_json(claimed),
            "claimed_report_signature_invalid")

    return {
        "kind": snapshot.get("kind"),
        "commit": snapshot.get("commit"),
        "verdict_ok": bool(claimed.get("ok") is True),
    }


def _fresh(bundle, now, max_age_s):
    """Freshness gate (release-decision layer). Raises Refused('stale') if as_of is unparseable,
    future-dated (a future stamp must not extend its own validity), or older than max_age_s."""
    as_of = _parse_ts(bundle.get("as_of"))
    if as_of is None:
        raise Refused("stale", "unparseable as_of")
    age = (now - as_of).total_seconds()
    if age < 0:
        raise Refused("stale", "as_of is in the future")
    if age > max_age_s:
        raise Refused("stale", "older than max-age ({:.0f}s)".format(age))


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
    run_hit = None  # (allowed, reason) for the CI verdict matching expect_sha, if any

    # Decide on the LATEST CI judgment of this sha, not on ledger file order: a re-run
    # after an infrastructure failure is legitimate, and "whichever line came last" is not
    # a decision rule. Undated entries sort first so a dated verdict always outranks them.
    bundles.sort(key=lambda x: (_parse_ts(x.get("as_of"))
                                or datetime.min.replace(tzinfo=timezone.utc)))

    for b in bundles:
        snap = (b.get("verdict") or {}).get("snapshot") or {}
        kind = snap.get("kind")
        # Heartbeat: authentic facts + fresh => engine is alive.
        if kind == "heartbeat":
            try:
                verify_facts(b, pinned=pinned)
                _fresh(b, now, max_age_s)
                engine_alive = True
            except Refused:
                pass
            continue
        if kind != "run":
            continue
        # A run verdict: does it authenticate AND concern our SHA AND is fresh AND say ok?
        if snap.get("commit") != expect_sha:
            continue
        # ...and is it a CI verdict at all? A probe entry is kind:"run" at our sha too.
        if not is_ci_verdict(snap):
            continue
        try:
            res = verify_facts(b, pinned=pinned)
            _fresh(b, now, max_age_s)
        except Refused as e:
            run_hit = (False, e.reason)
            continue
        if not res["verdict_ok"]:
            run_hit = (False, "verdict_not_ok")
        else:
            gaps = roster_gaps(snap)
            if gaps:
                # roster shrink fails LOUD and NAMED on an otherwise-valid verdict —
                # never "no verdict", never a pass
                run_hit = (False, "roster_shrink:" + ",".join(gaps))
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
