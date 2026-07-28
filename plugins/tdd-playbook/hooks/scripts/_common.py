"""Shared helpers for TDD Playbook hooks.

Hooks run on the Claude Code HOST (macOS or the cloud Linux sandbox), driven by a
JSON event on stdin. They are warn-first by default: a finding is surfaced but does
NOT block, so false positives never wedge a session. Promote a hook to blocking by
setting its mode to "block" (see resolve_mode).

Exit-code contract (Claude Code):
  0  -> success, nothing surfaced
  2  -> BLOCKING; stderr is fed back to Claude
  1  -> non-blocking; first line of stderr is shown to the user  (our "warn")
"""
import datetime
import json
import os
import sys

# Global default + per-hook override.
#   TDD_PLAYBOOK_HOOK_MODE=warn|block         (global default)
#   TDD_PLAYBOOK_HOOK_<NAME>=warn|block|off   (per-hook, wins over global)
# Most hooks ship as "warn" (advisory nudges must never wedge a session). INTEGRITY hooks —
# the ones defending the documented agent attack vectors (HACK_CATALOG H2/H3/H5: weaken the
# test, lock bypass, snapshot re-approval) — ship as "block": the research is unambiguous
# that warnings do not stop test-gaming; mechanical constraints do. Demote with the env vars.
_GLOBAL_ENV = "TDD_PLAYBOOK_HOOK_MODE"
_DEFAULT_MODES = {
    "testweaken": "block",
    "testlock": "block",
    "snapshotguard": "block",
}


def read_event():
    """Read and parse the hook's stdin JSON. Returns {} on any problem."""
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def resolve_mode(name):
    """Resolve a hook's mode: 'off' | 'warn' | 'block'.

    Default is per-hook (_DEFAULT_MODES, integrity hooks 'block'), else 'warn'.
    Precedence: per-hook env > global env > per-hook default > 'warn'.
    """
    per_hook = os.environ.get("TDD_PLAYBOOK_HOOK_" + name.upper())
    if per_hook:
        val = per_hook.strip().lower()
        if val in ("off", "warn", "block"):
            return val
    glob = os.environ.get(_GLOBAL_ENV, "").strip().lower()
    if glob in ("warn", "block"):
        return glob
    return _DEFAULT_MODES.get(name.lower(), "warn")


def project_root():
    """realpath: getcwd() resolves symlinks while CLAUDE_PROJECT_DIR may not (macOS
    /var -> /private/var); mismatched roots produce garbage relative paths."""
    return os.path.realpath(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def heartbeat_file(root=None):
    return os.environ.get("TDD_PLAYBOOK_HEARTBEAT") or os.path.join(
        root or project_root(), ".claude", "playbook-guards-heartbeat")


def write_heartbeat():
    """H8 (live incident 2026-07-28): plugin enablement is USER-scope — one mis-click in
    any repo darkens the guard layer in EVERY repo, silently and persistently. Committed !=
    deployed != RUNNING applies to the guards themselves, so a hook that fires on every
    user prompt leaves this heartbeat; dark-detection (installer doctor, run_calibration)
    compares it against repo activity. MUST never raise. Honest limit: local-only and
    forgeable by touching the file — this detects the accidental outage, not a determined
    adversary (that residue is the engine's guard_env/diff-integrity territory)."""
    try:
        path = heartbeat_file()
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "w") as fh:
            fh.write(datetime.datetime.now(datetime.timezone.utc)
                     .isoformat(timespec="seconds") + "\n")
    except Exception:
        pass


def guards_dark(root):
    """(status, detail): 'dark' if the repo's latest commit postdates the last heartbeat
    (work happened while no guard hook fired), 'live' if the heartbeat is current,
    'unknown' when there is no heartbeat or no git history (fresh clones must never
    false-RED)."""
    import subprocess
    hb = heartbeat_file(root)
    if not os.path.isfile(hb):
        return "unknown", "no heartbeat recorded (fresh clone, or guards never fired here)"
    try:
        p = subprocess.run(["git", "-C", root, "log", "-1", "--format=%ct"],
                           capture_output=True, text=True, timeout=30)
        commit_ts = int(p.stdout.strip())
    except (ValueError, OSError, subprocess.SubprocessError):
        return "unknown", "no git history to compare against"
    hb_ts = os.path.getmtime(hb)
    if commit_ts > hb_ts + 3600:
        days = (commit_ts - hb_ts) / 86400.0
        return "dark", ("latest commit postdates the last guard heartbeat by {:.1f} day(s) "
                        "— work was committed while NO guard hook fired (plugin disabled? "
                        "hooks unloaded?)".format(days))
    return "live", "heartbeat current relative to the latest commit"


def log_yield_event(gate, event, extra=None, source="hook"):
    """One line of gate-yield exhaust (R4): {ts, source, gate, event, ...} appended to
    $TDD_PLAYBOOK_YIELD_LOG or <project>/.claude/playbook-yield.jsonl. This is the SINGLE
    write path for the yield instrument — every guard flows through emit(), so no guard can
    silently drop out of the record and read as zero-yield. MUST never raise: telemetry
    failing must never change enforcement."""
    try:
        path = os.environ.get("TDD_PLAYBOOK_YIELD_LOG") or os.path.join(
            project_root(), ".claude", "playbook-yield.jsonl")
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        row = {"ts": datetime.datetime.now(datetime.timezone.utc)
                                     .isoformat(timespec="seconds"),
               "source": source, "gate": gate, "event": event}
        row.update(extra or {})
        with open(path, "a") as fh:
            fh.write(json.dumps(row) + "\n")
    except Exception:
        pass


def emit(name, lines):
    """Surface findings per the hook's mode, then exit with the right code.

    `lines` is a list of human-readable finding strings (empty -> clean exit 0).
    """
    mode = resolve_mode(name)
    if not lines:
        sys.exit(0)
    if mode == "off":
        # A demoted gate must never be a SILENT kill switch: findings that fire while the
        # gate is off leave a 'suppressed' trace, so the yield record can distinguish a
        # muzzled gate from a quiet one (and gate_yield surfaces it loudly).
        log_yield_event(name, "suppressed", {"findings": len(lines)})
        sys.exit(0)
    log_yield_event(name, mode, {"findings": len(lines)})
    header = "⚠️  TDD Playbook · {}".format(name)
    body = "\n".join("   - " + ln for ln in lines)
    if mode == "block":
        tail = ("   (BLOCKING; set TDD_PLAYBOOK_HOOK_{0}=warn to demote or =off to "
                "silence)".format(name.upper()))
    else:
        tail = ("   (warn-only; set TDD_PLAYBOOK_HOOK_{0}=off to silence, "
                "=block to enforce)".format(name.upper()))
    sys.stderr.write(header + "\n" + body + "\n" + tail + "\n")
    sys.exit(2 if mode == "block" else 1)


def is_test_file(path):
    """Language-agnostic test-file heuristic (pytest, unittest, jest, vitest, go, rust)."""
    if not path:
        return False
    p = path.replace("\\", "/").lower()
    base = p.rsplit("/", 1)[-1]
    if "/tests/" in p or "/test/" in p or "/__tests__/" in p or "/spec/" in p:
        return True
    return (
        base.startswith("test_")
        or base.endswith("_test.py")
        or base.endswith("_test.go")
        or ".test." in base
        or ".spec." in base
        or base.endswith("test.rs")
    )


def edit_pairs(event):
    """Yield (old, new) text pairs from an Edit / MultiEdit event.

    Write events have no `old` to compare against, so weakening can't be diffed;
    callers handle Write separately. Returns a list of (old, new) tuples.
    """
    ti = event.get("tool_input", {}) or {}
    if "edits" in ti and isinstance(ti["edits"], list):  # MultiEdit
        return [(e.get("old_string", ""), e.get("new_string", "")) for e in ti["edits"]]
    if "old_string" in ti or "new_string" in ti:  # Edit
        return [(ti.get("old_string", ""), ti.get("new_string", ""))]
    return []


def file_path_of(event):
    ti = event.get("tool_input", {}) or {}
    return ti.get("file_path") or ti.get("path") or ""
