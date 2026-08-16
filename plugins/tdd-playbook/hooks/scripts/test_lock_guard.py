#!/usr/bin/env python3
"""PreToolUse(Edit|MultiEdit|Write + Bash) — enforce the TEST-LOCK (HACK_CATALOG H2 + H5).

While the canonical Git-common-dir lock is active this guard defends four surfaces against BOTH the
structured-edit channel AND the shell channel (audit finding F1: the Edit-only guard was
blind to `sed -i` / `> file` / `git checkout -- test` / inline-python writes — the shell IS
the bypass a capable model reaches for):
  - LOCKED test files (H2: edit/weaken/delete the failing test);
  - the VERIFIER SURFACE — conftest.py, pytest/jest/vitest configs (H5: patch the harness
    instead of the test);
  - the LOCK'S OWN STATE — tdd-lock.json / its journal / tdd-pending-red.json (F2: deleting
    the lock file is a silent unlock that skips the journaled reason);
  - the ENFORCEMENT itself — the guard scripts, hooks.json, settings.json (disabling the hook
    is the quietest possible test-weakening; §10 "workflow files are risky paths").
Reads are always fine (you MUST be able to run the locked tests) — only WRITE-shaped
operations are blocked. No lock -> exit 0, zero cost. Default mode: BLOCK (integrity hook).
The one sanctioned exit is a journaled reason: bin/tdd_lock.py unlock --reason "...". This
guard is heuristic on the shell side (it catches the common write verbs, not every possible
command) — that is honest, and the deeper backstop is the independent verifier (memrebel/
CIVerd), not a perfect shell parser.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _common import read_event, emit, file_path_of  # noqa: E402
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "..", "..", "bin")))
from host_contract import (ContractError, GUARD_BASENAMES, import_legacy_lock,
                           LOCK_STATE_BASENAMES, policy_decision, read_lock,
                           record_capability_observation, resolve_repository,
                           VERIFIER_BASENAMES)  # noqa: E402

NAME = "testlock"

# U1 (2026-08-15): these rosters have ONE owner — host_contract. They used to be re-typed
# here and diverged live (the local copy omitted TRANSACTION_FILENAME, the canonical copy
# omitted PENDING_FILENAME), so each channel slipped a different lock-state file. Aliased
# to the internal names so the classifier/needle call sites are unchanged; parity is pinned
# by test_hooks.test_basename_roster_parity.
_VERIFIER_BASENAMES = VERIFIER_BASENAMES
_LOCK_STATE_BASENAMES = LOCK_STATE_BASENAMES
_GUARD_BASENAMES = GUARD_BASENAMES

# write-shaped shell signals (reads are intentionally excluded).
#
# v1.28 — CALIBRATED IN BOTH DIRECTIONS. The block direction was always tested; the ALLOW
# direction never was, and three false-positive classes grew in the gap, each contradicting
# this module's own docstring ("Reads are always fine"). All three are frozen as fixtures in
# test_hooks.py with the dates they bit:
#   FP1 the verb matched ANYWHERE, so a python loop variable named `ln` read as the `ln`
#       command and blocked a journal READ  -> verbs must now appear in COMMAND POSITION;
#   FP2 `needle in cmd and <any inline write>` fired when the write targeted an unrelated
#       file        -> the open() TARGET is now resolved and compared;
#   FP3 no cwd awareness, so `cd /tmp/scratch && git checkout .` read as a repo revert
#                   -> segments now carry a cwd and anything outside the project is skipped.
# Narrowing is not amnesty: every documented bypass still blocks, pinned alongside.
_WRITE_HEAD = re.compile(r"^(?:sed|perl|rm|rmdir|mv|cp|tee|truncate|install|ln|dd|shred)$")
_INPLACE_FLAG = re.compile(r"^-i\S*$")
_GIT_REVERT_SUB = re.compile(r"^(?:checkout|restore)$")
_REDIRECT = r"(?:>>?|>\|)\s*['\"]?[^\s'\";|&]*"
_OPEN_CALL = re.compile(r"open\s*\(\s*(?:(['\"])([^'\"]+)\1|([A-Za-z_][A-Za-z_0-9]*))\s*,"
                        r"\s*['\"]([rwaxb+]+)['\"]")
_ASSIGN = r"""{}\s*=\s*['"]([^'"]+)['"]"""
_WRITE_MODE = re.compile(r"[wax]|r\+")
# shell wrappers that precede the real command word
_WRAPPERS = {"sudo", "env", "time", "nohup", "xargs", "command", "builtin", "exec"}
_SEG_SPLIT = re.compile(r"\|\||&&|[;&|\n]")
_CD = re.compile(r"^cd\s+(?:-\S+\s+)*(['\"]?)([^'\";|&\s]+)\1\s*$")


def project_root():
    return os.path.realpath(os.environ.get("TDD_PLAYBOOK_PROJECT_ROOT")
                            or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())


def active_lock(root):
    try:
        identity = resolve_repository(root)
    except ContractError:
        identity = None
    if identity:
        try:
            import_legacy_lock(
                identity,
                os.environ.get("TDD_PLAYBOOK_SESSION_ID")
                or os.environ.get("CLAUDE_SESSION_ID") or "claude-hook")
            return read_lock(identity)
        except ContractError as exc:
            # A malformed authority must not turn the strongest guard off.  The main path
            # emits a block explaining the state needs repair; it never fabricates a lock.
            return {"files": {}, "_contract_error": str(exc)}
    path = os.path.join(root, ".claude", "tdd-lock.json")
    if not os.path.isfile(path):
        return None
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        return None


def _classify_path(path, lock, root):
    """(kind, rel) for a path that touches a protected surface, else (None, None)."""
    if not path:
        return None, None
    ap = os.path.realpath(path if os.path.isabs(path) else os.path.join(root, path))
    rel = os.path.relpath(ap, os.path.realpath(root))
    base = os.path.basename(ap)
    if rel in lock.get("files", {}):
        return "locked", rel
    if base in _LOCK_STATE_BASENAMES:
        return "lockstate", rel
    if base in _VERIFIER_BASENAMES:
        return "verifier", rel
    if base in _GUARD_BASENAMES:
        return "guard", rel
    return None, None


def _msg(kind, name):
    unlock = ("your ONE sanctioned exit is a journaled reason: python3 <plugin>/bin/"
              "tdd_lock.py unlock --reason \"why\" --class phase|feature-end|test-wrong|"
              "gate-wrong (--class is REQUIRED since v1.32.0; only gate-wrong claims the "
              "gate was wrong) — do NOT write around "
              "the guard")
    if kind == "locked":
        return ["TEST-LOCK: '{}' is a locked red test — read-only during implementation "
                "(H2). Running it is fine; MODIFYING it is the move the lock exists to "
                "stop.".format(name), unlock]
    if kind == "lockstate":
        return ["TEST-LOCK: '{}' is the lock's own STATE (F2) — editing/deleting it is a "
                "silent unlock that skips the journaled reason.".format(name), unlock]
    if kind == "verifier":
        return ["TEST-LOCK active: '{}' is verifier surface (conftest/runner config) — "
                "patching the harness while tests are locked equals editing the locked "
                "test (H5).".format(name), unlock]
    if kind == "undecidable":
        # cheliped secondary observation: fail-closed-on-undecidable is BY DESIGN, but the message
        # must say so — not name a specific locked test the write may not even touch.
        return ["TEST-LOCK active: this command has a WRITE whose target the guard cannot resolve "
                "(a variable path such as `open($X, 'w')`, or a heredoc writer). While a lock is "
                "held the guard fails CLOSED — it cannot prove the write misses the locked tests. "
                "This is NOT a specific locked-file violation: use a literal path the guard can "
                "check, or the journaled unlock below.", unlock]
    return ["TEST-LOCK active: '{}' is enforcement (a guard hook / settings) — disabling "
            "the guard is the quietest test-weakening (§10 risky path).".format(name), unlock]


def edit_findings(event, lock, root):
    # An out-of-root target (memory ~/.claude/projects, plan-mode ~/.claude/plans, scratchpad) is
    # OUT OF THE LOCK'S JURISDICTION, not a policy violation — a TEST-LOCK governs THIS repo's
    # tests, never every file the session touches. policy_decision RAISES "target escapes
    # repository root" for such paths, and converting that ContractError into a block was a
    # cross-session DoS: any lock held anywhere froze every session's memory/plan/scratchpad
    # writes (and broke plan-mode, whose only permitted write is the out-of-root plan file).
    # Field report: cheliped, plugin v1.36.0, 2026-08-15. Fixed by pre-checking containment with
    # the same `_inside` the Bash leg already uses for cwd — only in-root targets are policy-eval'd.
    if not _inside(root, file_path_of(event)):
        return []
    try:
        identity = resolve_repository(root)
    except ContractError:
        identity = None
    if identity and not lock.get("_contract_error"):
        try:
            result = policy_decision(identity, lock, {
                "kind": "write", "targets": [file_path_of(event)]})
        except ContractError as exc:
            return ["TEST-LOCK state/policy mismatch — refusing a write while the canonical "
                    "authority is repaired: {}".format(exc)]
        if result["decision"] == "block":
            return _msg(result["surface"], result["target"])
        return []
    kind, rel = _classify_path(file_path_of(event), lock, root)
    return _msg(kind, rel) if kind else []


def _inside(root, path):
    """Is `path` inside the project? FP3: a scratch clone under /tmp is not this repo."""
    try:
        rp = os.path.realpath(root)
        ap = os.path.realpath(path)
    except OSError:
        return True                      # unresolvable -> assume ours (fail closed)
    return ap == rp or ap.startswith(rp + os.sep)


def segments(cmd, root):
    """[(segment, cwd)] — shell segments with the cwd in force, tracking `cd`. Segments
    whose cwd left the project are the caller's to skip (FP3)."""
    cwd, out = root, []
    for seg in _SEG_SPLIT.split(cmd):
        st = seg.strip()
        if not st:
            continue
        m = _CD.match(st)
        if m:
            target = m.group(2)
            cwd = target if os.path.isabs(target) else os.path.join(cwd, target)
            continue
        out.append((st, cwd))
    return out


def _command_word(seg):
    """The first real command word of a segment, skipping env assignments and wrappers.
    FP1: `python3 -c "for ln in open(...)"` has command word `python3`, never `ln`."""
    for tok in seg.split():
        if "=" in tok and not tok.startswith("-") and "/" not in tok.split("=", 1)[0]:
            continue                                     # FOO=bar prefix
        if os.path.basename(tok) in _WRAPPERS:
            continue
        return os.path.basename(tok), seg.split()
    return "", []


def _open_targets(seg):
    """[(path_or_None, mode)] for python open() calls; a variable target is resolved from
    an assignment in the same segment when one exists (FP2: compare the TARGET, not the
    mere co-occurrence of a protected name somewhere in the command)."""
    out = []
    for m in _OPEN_CALL.finditer(seg):
        literal, var, mode = m.group(2), m.group(3), m.group(4)
        path = literal
        if path is None and var:
            a = re.search(_ASSIGN.format(re.escape(var)), seg)
            path = a.group(1) if a else None
        out.append((path, mode))
    return out


def _seg_writes(seg, needle):
    if re.search(_REDIRECT + re.escape(needle), seg):        # redirection target
        return True
    head, toks = _command_word(seg)
    if head and needle in seg:
        if _WRITE_HEAD.match(head):
            # sed/perl only rewrite in place with -i; without it they are readers
            if head in ("sed", "perl") and not any(_INPLACE_FLAG.match(t) for t in toks):
                pass
            else:
                return True
        if head == "git":
            after = [t for t in toks if not os.path.basename(t) == "git"]
            if after and _GIT_REVERT_SUB.match(after[0]):
                return True
    for path, mode in _open_targets(seg):                    # python open(path, 'w')
        if not _WRITE_MODE.search(mode) or path is None:
            continue                                         # undecidable handled separately
        if path == needle or os.path.basename(path) == needle or path.endswith("/" + needle):
            return True
    return False


def _has_undecidable_write(seg):
    """A write whose TARGET the guard cannot resolve (a python open() with a non-literal path).
    While a lock is active this fails CLOSED — the guard cannot prove the write misses the locked
    tests — but it is NOT a specific locked-file hit, so bash_findings gives it the honest
    'undecidable' message instead of naming a locked test it may miss (cheliped 2026-08-15)."""
    for path, mode in _open_targets(seg):
        if _WRITE_MODE.search(mode) and path is None:
            return True
    return False


def _needles(lock):
    out = []
    for rel in lock.get("files", {}):
        out.append((rel, "locked"))
        b = os.path.basename(rel)
        if b != rel:
            out.append((b, "locked"))
    for b in sorted(_LOCK_STATE_BASENAMES):
        out.append((b, "lockstate"))
    for b in sorted(_VERIFIER_BASENAMES):
        out.append((b, "verifier"))
    for b in sorted(_GUARD_BASENAMES):
        out.append((b, "guard"))
    return out


def bash_findings(cmd, lock, root):
    if not cmd:
        return []
    live = [(seg, cwd) for seg, cwd in segments(cmd, root) if _inside(root, cwd)]
    needles = _needles(lock)
    if needles:
        # An UNDECIDABLE write while a lock is active fails closed — but with an HONEST message,
        # not one misnaming a locked test it may not touch (cheliped secondary observation).
        for seg, _cwd in live:
            if _has_undecidable_write(seg):
                return _msg("undecidable", "")
    for needle, kind in needles:
        for seg, _cwd in live:
            if _seg_writes(seg, needle):
                return _msg(kind, needle)
    if lock.get("files"):
        for seg, _cwd in live:                  # `git checkout .` reverts locked tests
            head, toks = _command_word(seg)
            after = [t for t in toks if os.path.basename(t) != "git"]
            if head == "git" and after and _GIT_REVERT_SUB.match(after[0]) \
                    and any(t == "." for t in after):
                return _msg("locked", "<all tracked files: git revert>")
    return []


def record_observation(root, lock, event, route, findings):
    """Best-effort Claude host-boundary observation; never weakens a block on I/O failure."""
    if lock.get("_contract_error"):
        return
    try:
        identity = resolve_repository(root)
        manifest = os.path.realpath(os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "..", "adapters",
            "claude", "adapter.json"))
        with open(manifest) as fh:
            version = json.load(fh)["adapter_version"]
        record_capability_observation(
            identity, host="claude",
            host_version=(event.get("host_version")
                          or os.environ.get("TDD_PLAYBOOK_HOST_VERSION") or "unreported"),
            adapter_version=version, run_id=lock["session_id"], route=route,
            outcome="blocked" if findings else "allowed")
    except (ContractError, OSError, ValueError, KeyError):
        pass


def main():
    event = read_event()
    root = project_root()
    lock = active_lock(root)
    if not lock:
        sys.exit(0)
    if lock.get("_contract_error"):
        emit(NAME, ["TEST-LOCK canonical state is invalid — failing closed instead of "
                    "silently disabling protection: {}".format(lock["_contract_error"])])
    if event.get("tool_name") == "Bash":
        cmd = (event.get("tool_input", {}) or {}).get("command", "")
        findings = bash_findings(cmd, lock, root)
        record_observation(root, lock, event, "shell", findings)
        emit(NAME, findings)
    else:
        findings = edit_findings(event, lock, root)
        record_observation(root, lock, event, "structured_edit", findings)
        emit(NAME, findings)


if __name__ == "__main__":
    main()
