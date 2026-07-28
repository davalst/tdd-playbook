#!/usr/bin/env python3
"""Planted-input calibration for bin/_ed25519_verify.py — the stdlib Ed25519 verifier.

The one fear with a hand-written verifier is that it fails OPEN: wrongly returns True, so the
release gate always passes. This suite exists to make that impossible to ship (per §13, the check
must be able to FAIL):
  - RFC 8032 §7.1 known-answer vectors must all VERIFY (positive control);
  - tampered message / signature / public key, non-canonical S (S >= L), and a small-order key
    must all be REJECTED (negative controls — the forgeability-adjacent ones CIVerd flagged);
  - a `return True` MUTANT verifier must turn this suite RED. If it doesn't, the vectors aren't
    doing their job.
Self-contained, stdlib only. Run:  python3 tests/test_ed25519_verify.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "bin"))
import _ed25519_verify as ed  # noqa: E402

FIX = os.path.join(HERE, "fixtures", "rfc8032_ed25519.json")
_L = 2 ** 252 + 27742317777372353535851937790883648493

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def _load_kat():
    with open(FIX) as fh:
        return json.load(fh)["vectors"]


def _positive_vector():
    v = _load_kat()[1]  # TEST 2: short non-empty message
    return bytes.fromhex(v["public_key"]), bytes.fromhex(v["message"]), bytes.fromhex(v["signature"])


def run_positive(verify):
    """Return True iff every KAT verifies under `verify`. Used both for the real verifier (must be
    True) and to reason about mutants."""
    return all(
        verify(bytes.fromhex(v["public_key"]), bytes.fromhex(v["message"]),
               bytes.fromhex(v["signature"]))
        for v in _load_kat()
    )


def run_negatives(verify):
    """Return the list of negative cases that WRONGLY verified under `verify` (should be empty)."""
    pk, msg, sig = _positive_vector()
    leaks = []
    if verify(pk, msg + b"\x00", sig):
        leaks.append("tampered_message")
    bad = bytearray(sig); bad[0] ^= 1
    if verify(pk, msg, bytes(bad)):
        leaks.append("tampered_signature")
    bad = bytearray(pk); bad[0] ^= 1
    if verify(bytes(bad), msg, sig):
        leaks.append("wrong_key")
    s = int.from_bytes(sig[32:], "little")
    nc = (s + _L).to_bytes(32, "little") if (s + _L) < 2 ** 256 else None
    if nc is not None and verify(pk, msg, sig[:32] + nc):
        leaks.append("noncanonical_S")
    if verify(b"\x01" + b"\x00" * 31, msg, sig):  # identity / small-order key
        leaks.append("small_order_key")
    return leaks


def main():
    print("test_ed25519_verify — RFC 8032 KAT + negative controls + fail-open mutant")

    # positive: every RFC vector verifies
    for v in _load_kat():
        ok = ed.verify(bytes.fromhex(v["public_key"]), bytes.fromhex(v["message"]),
                       bytes.fromhex(v["signature"]))
        check("KAT verifies: {}".format(v["name"]), ok is True)

    # negatives: each must be rejected
    leaks = run_negatives(ed.verify)
    for case in ("tampered_message", "tampered_signature", "wrong_key",
                 "noncanonical_S", "small_order_key"):
        check("rejects {}".format(case), case not in leaks, leaks)

    # valid_pubkey helper
    good = _load_kat()[0]["public_key"]
    check("valid_pubkey accepts a real key", ed.valid_pubkey(bytes.fromhex(good)) is True)
    check("valid_pubkey rejects small-order key",
          ed.valid_pubkey(b"\x01" + b"\x00" * 31) is False)
    check("valid_pubkey rejects wrong length", ed.valid_pubkey(b"\x00" * 31) is False)

    # THE ANTI-FAIL-OPEN MUTANT: a verifier that returns True unconditionally must be caught by
    # the negative controls (they would all wrongly "verify"). If run_negatives came back empty
    # for such a mutant, the vectors would be theater.
    fail_open = lambda pk, msg, sig: True  # noqa: E731
    mutant_leaks = run_negatives(fail_open)
    check("return-True mutant is caught (negatives leak)", len(mutant_leaks) >= 4, mutant_leaks)
    # and a mutant that ignores the message entirely is caught by the tampered_message negative
    ignore_msg = lambda pk, msg, sig: ed.verify(pk, _positive_vector()[1], sig)  # noqa: E731
    check("ignore-message mutant is caught", "tampered_message" in run_negatives(ignore_msg))

    # ---- probe-gap (CIVerd run 2, 2026-07-28): flip_boolop survived on the input guards.
    # Triage found the REAL difference: under the mutant, non-bytes inputs RAISE TypeError
    # (len(None)) where the contract says fail CLOSED — return False, never raise. The
    # negatives below were verified to FAIL under each or->and mutant before shipping.
    for bad in (None, 5, 3.14, ["k"], {"k": 1}, "not-bytes"):
        try:
            check("probe-gap: valid_pubkey({}) fails closed".format(type(bad).__name__),
                  ed.valid_pubkey(bad) is False)
        except Exception as e:
            check("probe-gap: valid_pubkey({}) fails closed".format(type(bad).__name__),
                  False, "RAISED {}".format(type(e).__name__))
    pk, msg, sig = _positive_vector()
    for bad_pk in (None, 7, "x" * 32):
        try:
            check("probe-gap: verify(non-bytes pk: {}) fails closed".format(
                      type(bad_pk).__name__),
                  ed.verify(bad_pk, msg, sig) is False)
        except Exception as e:
            check("probe-gap: verify(non-bytes pk: {}) fails closed".format(
                      type(bad_pk).__name__), False, "RAISED {}".format(type(e).__name__))
    for bad_sig in (None, 7, "x" * 64):
        try:
            check("probe-gap: verify(non-bytes sig: {}) fails closed".format(
                      type(bad_sig).__name__),
                  ed.verify(pk, msg, bad_sig) is False)
        except Exception as e:
            check("probe-gap: verify(non-bytes sig: {}) fails closed".format(
                      type(bad_sig).__name__), False, "RAISED {}".format(type(e).__name__))
    # length sweep: every wrong length fails closed (defense-in-depth stays observable)
    length_ok = True
    try:
        for n in list(range(0, 40)) + [64]:
            if n != 32 and ed.valid_pubkey(b"\x00" * n) is not False:
                length_ok = False
        for n in (0, 1, 32, 63, 65, 128):
            if ed.verify(pk, msg, b"\x00" * n) is not False:
                length_ok = False
    except Exception as e:
        length_ok = "RAISED {}".format(type(e).__name__)
    check("probe-gap: all wrong lengths fail closed, never raise", length_ok is True,
          length_ok)

    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


if __name__ == "__main__":
    main()
