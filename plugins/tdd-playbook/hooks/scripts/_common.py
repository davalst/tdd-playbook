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
    # KEPT BLOCKING — each on evidence, not sentiment.
    #   testweaken:    4 blocks, 0 adjudicated false positives. The one unambiguous winner.
    #   testlock:      16 blocks, 20 journaled unlocks, of which ZERO are `gate-wrong`. The
    #                  overrides column is not a false-positive count (v1.27); reading it as
    #                  one is the documented error that once recommended retiring the
    #                  strongest anti-gaming defense there is, across four cycles in which no
    #                  gate was ever wrong. Measured false positives: 0.
    #   snapshotguard: covers the other cheap route to faking a pass.
    #   tagguard:      reserving the release tag for the owner is the whole compensating
    #                  control for deleting the CIVerd wall. A warning reserves nothing.
    "testweaken": "block",
    "testlock": "block",
    "snapshotguard": "block",
    "tagguard": "block",
    # RETIRED TO OPT-IN (v1.32.0) — 31 warnings and ZERO blocks across all recorded history
    # (docs/calibration/gate_yield.md: exitcode 0/24, overmock 0/3, exhaustive 0/2, flaky
    # 0/1, redlock 0/1). §13's decay principle runs in BOTH directions: a gate can decay by
    # becoming more expensive than the risk it retires, not only by becoming weaker than the
    # threat. Retirement is never silent deletion — the scripts stay, the per-hook knob turns
    # each back on (`TDD_PLAYBOOK_HOOK_<NAME>=warn`), and gate_yield keeps accruing rows for
    # anyone who opts in. Absent yield data is UNMEASURED, never zero; these five are the
    # only guards for which the data is present and reads zero.
    "exitcode": "off",
    "overmock": "off",
    "exhaustive": "off",
    "flaky": "off",
    "redlock": "off",
    # WARN by default (A, 2026-08-15) — a real, rare signal, not a block. Fires only when an
    # EXPECTED ANSWER in a test-data file is rewritten or a case removed (fixture_guard);
    # adding cases / editing non-answer fields is silent. Promote to block, or retire, on
    # committed yield evidence (the dated trigger on the fixture-data-guard capability).
    "fixtureguard": "warn",
}


HOOK_EVENT_SINK_ENV = "TDD_PLAYBOOK_HOOK_EVENT_SINK"


def note_hook_fired(marker="hook"):
    """B1 isolation liveness (EFFECT-proof). When TDD_PLAYBOOK_HOOK_EVENT_SINK names a file, append
    a marker line — proof that a PLAYBOOK HOOK PROCESS ACTUALLY RAN. The baseline-isolation runner
    sets this per calibration run: a no-playbook run's sink MUST stay empty (plugin disabled → this
    module never loads → nothing appended); a non-empty sink means the plugin was still active, so
    that run is recorded INVALID, never a clean isolated number. This is an effect (a hook that
    cannot run cannot write), not a config-read proxy. Best-effort, MUST never raise (same contract
    as write_heartbeat). Honest limit: forgeable like the heartbeat — it catches ACCIDENTAL
    non-isolation (the real failure), not an owner-vs-owner adversary (out of scope, holdout custody
    note). Called from read_event (every PreToolUse/PostToolUse/Stop guard — structurally
    unavoidable, so any future guard auto-registers) plus the UserPromptSubmit heartbeat path (the
    once-per-run hook). NOT from emit(), which sys.exit(0)s before logging, so a clean guard would
    never mark and a no-playbook run would look falsely isolated."""
    sink = os.environ.get(HOOK_EVENT_SINK_ENV)
    if not sink:
        return
    try:
        with open(sink, "a") as fh:
            fh.write(marker + "\n")
    except Exception:
        pass


def read_event():
    """Read and parse the hook's stdin JSON. Returns {} on any problem."""
    note_hook_fired("read_event")
    try:
        raw = sys.stdin.read()
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


# Every env var that can weaken the guard layer. Exported so the ONE owner of the env
# contract also owns the list, and install_into_repo.py --doctor can import it instead of
# guessing with a `startswith("TDD_PLAYBOOK_HOOK")` prefix — which was blind to break-glass,
# a strictly WIDER switch than the per-hook demotions the doctor was written to catch.
def is_guard_control_var(key):
    return key == "TDD_PLAYBOOK_BREAK_GLASS" or key.startswith("TDD_PLAYBOOK_HOOK")


def _parse_mode(raw, source, allow_off=True):
    """'off'|'warn'|'block' from an operator-set value, or None — LOUDLY.

    The v1.32.0 defect this fixes: `TDD_PLAYBOOK_HOOK_MODE=off` was silently ignored,
    because the read was a membership test against ("warn","block") and anything else just
    fell through to the default. The operator believes they turned the layer off; it is
    still on; nothing says so. A first attempt at this shipped a THIRD env var beside the
    broken one instead of fixing the swallow — adding a knob is not fixing a knob. Now every
    operator-set value is either honoured or reported; nothing is swallowed.
    """
    if raw is None:
        return None
    val = raw.strip().lower()
    if not val:
        return None
    if val == "off" and not allow_off:
        # A GLOBAL off would silence every gate at once, integrity ones included — the
        # H-class kill switch by definition. It is refused rather than honoured, and refused
        # LOUDLY rather than swallowed: the old code just fell through, so the operator
        # believed the layer was off while it was fully armed. The sanctioned wide switch is
        # break-glass, which demotes to warn, demands a reason, and leaves a record.
        sys.stderr.write(
            "⚠️  TDD Playbook · {}=off is REFUSED — a global off silences every gate at once, "
            "integrity gates included.\n"
            "   The guard layer is STILL ARMED. Use TDD_PLAYBOOK_BREAK_GLASS=\"<reason>\" to "
            "demote blocking gates to warn (reason required, recorded), or "
            "TDD_PLAYBOOK_HOOK_<NAME>=off for one specific gate.\n".format(source))
        return None
    if val in ("off", "warn", "block"):
        return val
    sys.stderr.write(
        "⚠️  TDD Playbook · {} is set to {!r}, which is not off|warn|block — IGNORED.\n"
        "   The guard layer is running at its normal strength. If you meant to demote "
        "everything for this session, use TDD_PLAYBOOK_BREAK_GLASS=\"<reason>\".\n"
        .format(source, raw))
    return None


def break_glass_reason():
    """The one obvious switch: TDD_PLAYBOOK_BREAK_GLASS="<reason>" demotes every BLOCKING
    gate to warn for this session.

    Why it exists (v1.32.0, owner-control): the per-hook knob already worked, but it demands
    you already know WHICH of eleven guards is in your way — exactly what you do not know at
    the moment you are blocked.

    The REASON is required, not decorative. An empty or whitespace value does not demote.
    This is the difference between an emergency and a habit.
    """
    return (os.environ.get("TDD_PLAYBOOK_BREAK_GLASS") or "").strip()


def resolve_mode(name):
    """Resolve a hook's mode: 'off' | 'warn' | 'block'.

    Base precedence: per-hook env > global env > per-hook default > 'warn'.
    Break-glass is then applied as a CLAMP over that fully-resolved base.

    The clamp is the whole design, and the first version got it wrong in a way worth
    recording: it returned `_DEFAULT_MODES.get(name)` directly, which SKIPPED the global-env
    layer and landed on the v1.32.0 `off` defaults — so breaking glass SILENCED the five
    opt-in guards outright, and did so even for an operator who had globally escalated
    everything to `block`. The docstring said "it cannot silence a gate"; the code silenced
    five. Written as a clamp over the resolved base, the invariant is structural rather than
    asserted: break-glass can only ever turn `block` into `warn`, never into `off`, because
    that is the only transition the expression can express.

    An explicit per-hook setting still wins — a specific instruction beats a blanket one, so
    `TDD_PLAYBOOK_HOOK_TESTWEAKEN=block` still blocks during an incident.
    """
    per_hook = _parse_mode(os.environ.get("TDD_PLAYBOOK_HOOK_" + name.upper()),
                           "TDD_PLAYBOOK_HOOK_" + name.upper())
    if per_hook:
        return per_hook
    glob = _parse_mode(os.environ.get(_GLOBAL_ENV), _GLOBAL_ENV, allow_off=False)
    base = glob or _DEFAULT_MODES.get(name.lower(), "warn")
    if break_glass_reason() and base == "block":
        return "warn"
    return base


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


def runtime_host():
    """Which host runtime invoked this process — from HOST-RUNTIME-PROVIDED signals only
    (v1.34.0 D5). CLAUDE_PROJECT_DIR is set by the Claude Code runtime itself when it
    invokes hooks and bins; the Codex adapter sets TDD_PLAYBOOK_PROJECT_ROOT
    (adapters/codex/pre_tool_test_lock.py). Not cwd, not a source path, not user config —
    those label the TREE, not the runtime. Unrecognised contexts are `unknown`, and the
    row is STILL LOGGED with that label: silent non-logging on an unclassified context is
    the fatal-flaw shape the readable-surface re-review removed, and this module's own
    invariant is that no producer silently drops out of the record. Scope stated (§12):
    this labels by invoking runtime; it does not defend against a deliberately exported
    variable, any more than the log file defends against an editor."""
    if os.environ.get("CLAUDE_PROJECT_DIR"):
        return "claude"
    if os.environ.get("TDD_PLAYBOOK_PROJECT_ROOT"):
        return "codex"
    return "unknown"


def log_yield_event(gate, event, extra=None, source="hook"):
    """One line of gate-yield exhaust (R4): {ts, source, host, gate, event, ...} appended
    to $TDD_PLAYBOOK_YIELD_LOG or <project>/.claude/playbook-yield.jsonl. This is the
    SINGLE write path for the yield instrument — every guard flows through emit(), so no
    guard can silently drop out of the record and read as zero-yield. MUST never raise:
    telemetry failing must never change enforcement."""
    try:
        path = os.environ.get("TDD_PLAYBOOK_YIELD_LOG") or os.path.join(
            project_root(), ".claude", "playbook-yield.jsonl")
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        row = {"ts": datetime.datetime.now(datetime.timezone.utc)
                                     .isoformat(timespec="seconds"),
               "source": source, "host": runtime_host(), "gate": gate, "event": event}
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
    glass = break_glass_reason()
    # Log the FACT (a block fired) separately from the OUTCOME (it was demoted). Logging the
    # demoted mode instead erases the block from gate_yield's `blocks` column — and
    # guard_response.md, the one instrument built to tell "complied with the block" apart
    # from "routed around the block", counts exactly that column. Measured: two identical
    # sessions differing only by break-glass produced 2 blocks + 2 loud UNACCOUNTED rows
    # versus a file that was never written at all. The record read cleanest precisely in the
    # session where every block was bypassed, which is the inverse of what it is for.
    would_have = _DEFAULT_MODES.get(name.lower(), "warn") if not glass else None
    logged_event = mode
    payload = {"findings": len(lines)}
    if glass and mode == "warn" and _DEFAULT_MODES.get(name.lower(), "warn") == "block":
        logged_event = "block"
        payload["demoted_by"] = "break-glass"
        payload["break_glass"] = glass
    log_yield_event(name, logged_event, payload)
    header = "⚠️  TDD Playbook · {}".format(name)
    body = "\n".join("   - " + ln for ln in lines)
    if mode == "block":
        # Name BOTH exits at the moment of need. The per-hook knob demands you already know
        # WHICH of eleven guards is in your way, which is exactly what you do not know while
        # reading your first block — so the blanket switch has to be discoverable HERE, not
        # only in a README the blocked reader is not currently looking at.
        tail = ("   (BLOCKING; TDD_PLAYBOOK_HOOK_{0}=warn demotes just this one, or "
                "TDD_PLAYBOOK_BREAK_GLASS=\"<reason>\" demotes every blocking gate for the "
                "session — the reason is required and recorded)".format(name.upper()))
    else:
        tail = ("   (warn-only; set TDD_PLAYBOOK_HOOK_{0}=off to silence, "
                "=block to enforce)".format(name.upper()))
    if glass and logged_event == "block":
        # Only claim "would normally BLOCK" when that is true — an advisory gate that merely
        # warns must not print it, or the banner is a proxy for the switch being set rather
        # than a statement about this gate.
        tail = ("   *** BREAK-GLASS ACTIVE — this gate would normally BLOCK. Reason: {} ***\n"
                "   (recorded as a BLOCK with demoted_by=break-glass, so the yield record "
                "still shows it fired; unset TDD_PLAYBOOK_BREAK_GLASS to restore)"
                .format(glass))
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
