#!/usr/bin/env python3
"""_ed25519_verify — a pure-stdlib Ed25519 signature VERIFIER (no signing, no key generation).

Why this exists: the TDD Playbook plugin is stdlib-only by invariant — every bin runs in any
Claude Code sandbox / vendored repo with just `python3`, no pip. CIVerd's release-gate verifier
(`verify_verdict.py`) needs Ed25519 verification, and the one machine that watches this repo
installs only `pytest` — so a `cryptography` import would make the engine emit a permanent RED
for its only subject. Hence a self-contained verifier.

SCOPE IS DELIBERATELY NARROW. This module ONLY verifies. It generates no keys and produces no
signatures, so it has no nonce generation and no secret-dependent timing — the genuinely
dangerous parts of Ed25519 are all on the SIGNING side, which lives on the VPS behind
`cryptography`. The one fear with a hand-written verifier is that it fails OPEN (wrongly returns
True). That is neutralized by the test suite in tests/test_ed25519_verify.py:
  - RFC 8032 §7.1 known-answer vectors must all VERIFY;
  - tampered message / signature / public key, and a small-order key, must all be REJECTED;
  - non-canonical S (S >= L) must be REJECTED (the one forgeability-adjacent omission);
  - a mutant that `return True`s unconditionally must turn the suite RED.

Reference: RFC 8032 §5.1 (Ed25519), affine Edwards arithmetic for readability over speed. This is
a release-time tool verifying a handful of signatures, so per-add modular inversion is fine.
"""
import hashlib

# Curve25519 / edwards25519 constants (RFC 8032 §5.1).
_P = 2 ** 255 - 19
_L = 2 ** 252 + 27742317777372353535851937790883648493   # prime order of the base-point subgroup
_D = (-121665 * pow(121666, _P - 2, _P)) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)                       # sqrt(-1) mod p
_IDENTITY = (0, 1)


def _inv(x):
    return pow(x, _P - 2, _P)


def _xrecover(y):
    """Recover x from y on the curve, or None if y is not a valid coordinate."""
    xx = (y * y - 1) * _inv(_D * y * y + 1) % _P
    x = pow(xx, (_P + 3) // 8, _P)
    if (x * x - xx) % _P != 0:
        x = (x * _SQRT_M1) % _P
    if (x * x - xx) % _P != 0:
        return None
    if x % 2 != 0:
        x = _P - x
    return x


_BY = 4 * _inv(5) % _P
_BX = _xrecover(_BY)
_B = (_BX % _P, _BY % _P)


def _on_curve(pt):
    x, y = pt
    return (-x * x + y * y - 1 - _D * x * x * y * y) % _P == 0


def _add(pt1, pt2):
    x1, y1 = pt1
    x2, y2 = pt2
    dd = _D * x1 * x2 * y1 * y2
    x3 = (x1 * y2 + x2 * y1) * _inv(1 + dd) % _P
    y3 = (y1 * y2 + x1 * x2) * _inv(1 - dd) % _P
    return (x3 % _P, y3 % _P)


def _scalarmult(pt, e):
    """Constant-set double-and-add. Not constant-TIME, but this verifier touches only public
    values (public key, signature, message) — there is no secret to leak."""
    result = _IDENTITY
    addend = pt
    while e > 0:
        if e & 1:
            result = _add(result, addend)
        addend = _add(addend, addend)
        e >>= 1
    return result


def _decode_point(s):
    """Decode a 32-byte compressed point. Returns None for any invalid/non-canonical encoding."""
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    if y >= _P:                       # non-canonical y coordinate
        return None
    x = _xrecover(y)
    if x is None:
        return None
    if (x & 1) != sign:
        x = _P - x
    pt = (x % _P, y % _P)
    if not _on_curve(pt):
        return None
    return pt


def _is_small_order(pt):
    """True if the point's order divides the cofactor 8 (i.e. it is a small-order point). Such
    a public key must be rejected: it is forgeability-adjacent and never a legitimate signer."""
    return _scalarmult(pt, 8) == _IDENTITY


def valid_pubkey(public_key):
    """True iff `public_key` (32 bytes) decodes to a valid, NON-small-order curve point — i.e. a
    key a legitimate signer could hold. Used to reject a malformed or small-order *issuer* key
    up front, distinctly from a signature-verification failure."""
    if not isinstance(public_key, (bytes, bytearray)) or len(public_key) != 32:
        return False
    pt = _decode_point(bytes(public_key))
    if pt is None:
        return False
    return not _is_small_order(pt)


def verify(public_key, message, signature):
    """Return True iff `signature` is a valid Ed25519 signature of `message` under `public_key`.
    All three are bytes. Fails CLOSED (returns False) on any malformation — never raises."""
    if not isinstance(public_key, (bytes, bytearray)) or len(public_key) != 32:
        return False
    if not isinstance(signature, (bytes, bytearray)) or len(signature) != 64:
        return False
    if not isinstance(message, (bytes, bytearray)):
        return False

    r_bytes = bytes(signature[:32])
    s = int.from_bytes(signature[32:], "little")
    if s >= _L:                        # canonical-S check — reject malleable/oversized S
        return False

    a_pt = _decode_point(bytes(public_key))
    if a_pt is None:
        return False
    if _is_small_order(a_pt):
        return False

    r_pt = _decode_point(r_bytes)
    if r_pt is None:
        return False

    h = int.from_bytes(hashlib.sha512(r_bytes + bytes(public_key) + bytes(message)).digest(),
                       "little") % _L

    # RFC 8032 §5.1.7 cofactorless equation: [S]B == R + [h]A
    lhs = _scalarmult(_B, s)
    rhs = _add(r_pt, _scalarmult(a_pt, h))
    return lhs == rhs
