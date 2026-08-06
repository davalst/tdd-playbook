#!/usr/bin/env python3
"""PreToolUse(Edit|MultiEdit|Write + Bash) — enforce the TEST-LOCK (HACK_CATALOG H2 + H5).

While .claude/tdd-lock.json is active this guard defends four surfaces against BOTH the
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

NAME = "testlock"

_VERIFIER_BASENAMES = {
    "conftest.py", "pytest.ini", "tox.ini", "setup.cfg",
    "jest.config.js", "jest.config.ts", "jest.config.mjs", "jest.config.cjs",
    "vitest.config.js", "vitest.config.ts", "vitest.config.mts",
    "playwright.config.js", "playwright.config.ts",
    ".mocharc.yml", ".mocharc.json", "karma.conf.js",
}
# F2 — the lock's own state; never legitimately hand-edited (tdd_lock.py owns them).
_LOCK_STATE_BASENAMES = {
    "tdd-lock.json", "tdd-lock-journal.jsonl", "tdd-pending-red.json",
}
# F1-extension — disabling the enforcement is editing the test by another name.
_GUARD_BASENAMES = {
    "test_lock_guard.py", "snapshot_guard.py", "test_weakening_guard.py",
    "flaky_guard.py", "overmock_guard.py", "red_lock.py", "_common.py",
    "hooks.json", "settings.json", "settings.local.json",
}

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
    return os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()


def active_lock(root):
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
              "tdd_lock.py unlock --reason \"why\" (reviewed by /grade) — do NOT write around "
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
    return ["TEST-LOCK active: '{}' is enforcement (a guard hook / settings) — disabling "
            "the guard is the quietest test-weakening (§10 risky path).".format(name), unlock]


def edit_findings(event, lock, root):
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
        if not _WRITE_MODE.search(mode):
            continue
        if path is None:
            return True                                      # unresolvable -> fail closed
        if path == needle or os.path.basename(path) == needle or path.endswith("/" + needle):
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
    for needle, kind in _needles(lock):
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


def main():
    event = read_event()
    root = project_root()
    lock = active_lock(root)
    if not lock:
        sys.exit(0)
    if event.get("tool_name") == "Bash":
        cmd = (event.get("tool_input", {}) or {}).get("command", "")
        emit(NAME, bash_findings(cmd, lock, root))
    else:
        emit(NAME, edit_findings(event, lock, root))


if __name__ == "__main__":
    main()
