#!/usr/bin/env python3
"""with_snapshot — mechanical revert safety for tree-touching agents.

The Playbook's calibration agents (planted-error-probe, ux-probe-calibrator,
mutation-runner) and red-first-verifier temporarily mutate or stash the working tree and
promise to restore it. A prose promise is an honor system — the exact seam this plugin
exists to close (§13: "make the honest path the cheap path and the dishonest path visible").
This tool makes the promise a checked invariant:

    with_snapshot.py preflight # REFUSE (loud exit 1) if uncommitted TRACKED changes exist —
                               #   a revert-based (git checkout) pass would clobber them
    with_snapshot.py begin    # record the tree's state BEFORE touching anything
    ... plant / stash / mutate / revert ...
    with_snapshot.py verify   # exit 0 iff the tree is EXACTLY as recorded; loud exit 1 if not
    with_snapshot.py status   # show the recorded snapshot, if any

`preflight` is for the REVERT-VIA-CHECKOUT pattern (a hand-rolled targeted-mutant script that
`git checkout`s to restore source): a bare checkout silently destroys uncommitted work, so gate
the script on `preflight` and it fails loudly instead. `begin`/`verify` is the OTHER pattern — it
RECORDS a dirty tree and restores it, so it does not need a clean tree (origin: a targeted-mutant
script git-checkout'd away uncommitted work mid-pass; detect-after-the-fact is worse than
refuse-before).

State is kept in .git/tdd_playbook_snapshot.json (never committed, per-repo, survives the
agent's process). `verify` deletes the snapshot on success so a stale snapshot can't mask a
later run; on failure it KEEPS it (the evidence) and prints exactly what diverged.

Exit codes: 0 ok · 1 divergence (verify) or no snapshot to verify · 2 usage/not-a-repo.
"""
import hashlib
import json
import os
import subprocess
import sys

SNAP_REL = "tdd_playbook_snapshot.json"


def _git(*args, **kw):
    return subprocess.run(["git", *args], capture_output=True, text=True, timeout=30, **kw)


def _git_dir():
    out = _git("rev-parse", "--git-dir")
    if out.returncode != 0:
        sys.stderr.write("with_snapshot: not a git repository\n")
        sys.exit(2)
    return out.stdout.strip()


def capture():
    """The tree's identity: HEAD + porcelain status + a hash of the full diff vs HEAD."""
    head = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain", "--untracked-files=all")
    diff = _git("diff", "HEAD")
    if status.returncode != 0:
        sys.stderr.write("with_snapshot: git status failed: {}\n".format(status.stderr.strip()))
        sys.exit(2)
    stash_list = _git("stash", "list")
    return {
        "head": head.stdout.strip() if head.returncode == 0 else "(no commits)",
        "status": status.stdout,
        "diff_sha256": hashlib.sha256(diff.stdout.encode("utf-8", "replace")).hexdigest(),
        "stash_count": len([ln for ln in stash_list.stdout.splitlines() if ln.strip()]),
    }


def snap_path():
    return os.path.join(_git_dir(), SNAP_REL)


def cmd_begin():
    state = capture()
    with open(snap_path(), "w") as fh:
        json.dump(state, fh, indent=2)
    print("with_snapshot: recorded (HEAD {} · {} changed path(s) · {} stash(es))".format(
        state["head"][:12], len(state["status"].splitlines()), state["stash_count"]))
    return 0


def cmd_verify():
    path = snap_path()
    if not os.path.isfile(path):
        sys.stderr.write("with_snapshot: NO SNAPSHOT to verify — `begin` was never run "
                         "(or a previous verify already consumed it)\n")
        return 1
    with open(path) as fh:
        want = json.load(fh)
    have = capture()
    problems = []
    if have["head"] != want["head"]:
        problems.append("HEAD moved: {} -> {}".format(want["head"][:12], have["head"][:12]))
    if have["status"] != want["status"]:
        w, h = set(want["status"].splitlines()), set(have["status"].splitlines())
        for ln in sorted(h - w):
            problems.append("NEW change left behind: {}".format(ln.strip()))
        for ln in sorted(w - h):
            problems.append("pre-existing change GONE (overwritten?): {}".format(ln.strip()))
    elif have["diff_sha256"] != want["diff_sha256"]:
        problems.append("same paths changed but CONTENT differs from the recorded state")
    if have["stash_count"] != want["stash_count"]:
        problems.append("stash count changed: {} -> {} (a stray stash was left or dropped)".format(
            want["stash_count"], have["stash_count"]))
    if problems:
        sys.stderr.write("with_snapshot: TREE NOT RESTORED — the revert promise failed:\n")
        for p in problems:
            sys.stderr.write("  - {}\n".format(p))
        sys.stderr.write("Snapshot kept at {} for forensics. Restore the tree, then re-verify.\n"
                         .format(path))
        return 1
    os.remove(path)
    print("with_snapshot: clean — tree exactly as recorded")
    return 0


def cmd_preflight():
    """Refuse a REVERT-BASED pass (git checkout/stash-pop to restore source) when the tree has
    uncommitted changes to TRACKED files — a bare checkout would clobber that work. Untracked
    files survive a checkout, so they don't block. Commit/stash first, run in a `git worktree`,
    or use begin/verify (which RECORDS and restores the dirty state) instead of a bare checkout."""
    status = _git("status", "--porcelain")
    if status.returncode != 0:
        sys.stderr.write("with_snapshot: git status failed: {}\n".format(status.stderr.strip()))
        return 2
    dirty = [ln for ln in status.stdout.splitlines() if ln.strip() and not ln.startswith("??")]
    if dirty:
        sys.stderr.write("with_snapshot: REFUSING — {} uncommitted tracked change(s); a "
                         "revert-based (git checkout) pass will CLOBBER them:\n".format(len(dirty)))
        for ln in dirty:
            sys.stderr.write("  - {}\n".format(ln.strip()))
        sys.stderr.write("Commit or stash first, run in a `git worktree`, or use "
                         "`with_snapshot.py begin`/`verify` (records + restores the dirty state).\n")
        return 1
    print("with_snapshot: preflight clean — no uncommitted tracked changes; safe for a "
          "revert-based pass")
    return 0


def cmd_status():
    path = snap_path()
    if not os.path.isfile(path):
        print("with_snapshot: no active snapshot")
        return 0
    with open(path) as fh:
        want = json.load(fh)
    print("with_snapshot: active snapshot (HEAD {} · {} changed path(s))".format(
        want["head"][:12], len(want["status"].splitlines())))
    return 0


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1 or argv[0] not in ("preflight", "begin", "verify", "status"):
        sys.stderr.write("usage: with_snapshot.py preflight|begin|verify|status\n")
        return 2
    return {"preflight": cmd_preflight, "begin": cmd_begin, "verify": cmd_verify,
            "status": cmd_status}[argv[0]]()


if __name__ == "__main__":
    sys.exit(main())
