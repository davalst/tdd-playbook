#!/usr/bin/env python3
"""_debt.py — the ONE house debt-date implementation (stdlib-only, vendored alongside).

The `{what, owner, expires}` debt shape appears in capabilities.json integration_debt and
in §6c sweep exemptions (dataflow_sweeps.py). Both consumers share THIS date logic so the
semantics can never drift: `expires` is ISO YYYY-MM-DD, and expiry is STRICTLY AFTER —
expires == today is "due", not expired (pinned by test_capability_registry's boundary
tests and test_dataflow_sweeps' --as-of pair).

extracted from capability_registry.py (v1.24, arch-adversary finding #2: a fourth dated-
exemption shape with no expiry teeth — reuse, don't sibling).
"""
import datetime as _dt

DEBT_FIELDS = ("what", "owner", "expires")


def parse_date(s):
    """ISO YYYY-MM-DD -> datetime.date, or None on anything else (never raises)."""
    try:
        return _dt.date.fromisoformat(s)
    except (TypeError, ValueError):
        return None


def is_expired(expires, today):
    """STRICTLY-AFTER expiry: True only when today is past the expires date.

    Unparsable dates are NOT expired — callers must treat parse_date(expires) is None
    as its own (malformed) violation, never fold it into expiry.
    """
    exp = parse_date(expires)
    return exp is not None and exp < today


def debt_problems(entry, today, label):
    """Validate one {what, owner, expires} entry. Returns a list of problem strings
    (empty = clean), formatted '<label>: <detail>' — rule-prefixing is the caller's."""
    missing = [f for f in DEBT_FIELDS if not (entry or {}).get(f)]
    if missing:
        return ["%s: missing %s" % (label, "/".join(missing))]
    if parse_date(entry["expires"]) is None:
        return ["%s: expires '%s' is not YYYY-MM-DD" % (label, entry["expires"])]
    if is_expired(entry["expires"], today):
        return ["%s: EXPIRED %s (owner: %s) — '%s'; pay it down, re-date it with a "
                "reason, or park the capability loudly"
                % (label, entry["expires"], entry["owner"], entry["what"])]
    return []
