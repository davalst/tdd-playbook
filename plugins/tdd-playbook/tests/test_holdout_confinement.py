#!/usr/bin/env python3
"""Suite-level regression tests for the holdout answer-key confinement (Part 2, 2026-08-15).

These live in the BLESSED suite (not only calibration/test_harness.py) because they pin the
security-adversary's confirmed findings on the diff that built the holdout controller — chiefly
F1, the critical one: `git clone` writes `.git/` beside `bodies/`, and denying only the
`bodies/` leaf left `git show HEAD:bodies/*.json` able to reconstruct the entire answer key from
the object store. The fix denies the whole clone TREE. A critical security regression belongs in
the first-class suite that runs every gate, and it is the closure evidence for the P1 finding in
docs/reviews/2026-08-15-two-tier-calibration-part2-controller.json.

Raw `assert` (H5): an assert cannot fake a passing suite, an exit call can. main() sums failures.
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
# dirname^3: tests -> tdd-playbook -> plugins -> REPO ROOT.
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, os.path.join(REPO, "calibration"))

import confine  # noqa: E402
import child_env as ce  # noqa: E402
import holdout  # noqa: E402
import run_calibration as rc  # noqa: E402


def test_holdout_deny_read_prefers_clone_root():
    """F1: the deny target is the whole clone ROOT (covers .git), not the bodies leaf."""
    keep_dir = os.environ.get(rc.HOLDOUT_DIR_ENV)
    keep_deny = os.environ.get(rc.HOLDOUT_DENY_ENV)
    try:
        os.environ[rc.HOLDOUT_DIR_ENV] = "/clone/vault/bodies"
        os.environ[rc.HOLDOUT_DENY_ENV] = "/clone"
        assert rc.holdout_deny_read() == ["/clone"], rc.holdout_deny_read()
        # and with no env at all, a dev run is never confined
        os.environ.pop(rc.HOLDOUT_DIR_ENV, None)
        os.environ.pop(rc.HOLDOUT_DENY_ENV, None)
        assert rc.holdout_deny_read() is None
    finally:
        for k, v in ((rc.HOLDOUT_DIR_ENV, keep_dir), (rc.HOLDOUT_DENY_ENV, keep_deny)):
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def test_run_holdout_denies_whole_clone_tree():
    """F1 end-to-end: run_holdout sets the deny env to a root that contains BOTH bodies/ and the
    .git sibling `git show` would reconstruct the key from. Offline (a local git vault clone)."""
    git_id = ["-c", "user.email=t@t", "-c", "user.name=t"]
    with tempfile.TemporaryDirectory() as vault:
        bodies = os.path.join(vault, "bodies")
        os.makedirs(bodies)
        with open(os.path.join(bodies, "b.json"), "w") as fh:
            json.dump({"id": "hc-body", "agent": "claims-verifier", "plant": "p",
                       "edits": [], "task": "t", "must_match": ["a"], "must_not_match": ["b"]}, fh)
        for c in (["git", "-C", vault, "init", "-q"],
                  ["git", "-C", vault, *git_id, "add", "-A"],
                  ["git", "-C", vault, *git_id, "commit", "-q", "-m", "seed"]):
            subprocess.run(c, check=True, capture_output=True, text=True)
        seen = {}

        def runner(argv, env, bodies_dir):
            deny = env.get(rc.HOLDOUT_DENY_ENV)
            git_sibling = os.path.join(os.path.dirname(bodies_dir), ".git")
            seen["ok"] = (bool(deny)
                          and holdout.dest_is_inside_tree(bodies_dir, deny)
                          and holdout.dest_is_inside_tree(git_sibling, deny)
                          and "--form" in argv and "holdout" in argv)
            return 0

        code = holdout.run_holdout(vault, ["--dry-run"], runner=runner)
        assert code == 0
        assert seen.get("ok"), seen


def test_child_env_strips_holdout_location():
    """F2: the answer-key location never reaches a nested model's env; capture stays off."""
    keep_a = os.environ.get(rc.HOLDOUT_DIR_ENV)
    keep_b = os.environ.get(rc.HOLDOUT_DENY_ENV)
    try:
        os.environ[rc.HOLDOUT_DIR_ENV] = "/clone/vault/bodies"
        os.environ[rc.HOLDOUT_DENY_ENV] = "/clone"
        env = ce.child_env()
        assert rc.HOLDOUT_DIR_ENV not in env and rc.HOLDOUT_DENY_ENV not in env, \
            [k for k in env if "HOLDOUT" in k]
        assert env.get("TDD_PLAYBOOK_HOOK_CAPTURE") == "off"
    finally:
        for k, v in ((rc.HOLDOUT_DIR_ENV, keep_a), (rc.HOLDOUT_DENY_ENV, keep_b)):
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v


def test_confine_denies_git_sibling_under_root():
    """F1 at the OS layer (macOS): denying the clone ROOT blocks the .git sibling; a MUST-FAIL
    with only the bodies leaf denied leaves it readable. Skips cleanly without sandbox-exec."""
    if not confine.sandbox_exec_available():
        return
    with tempfile.TemporaryDirectory() as d:
        root = os.path.realpath(os.path.join(d, "vault"))
        bodies = os.path.join(root, "bodies")
        gitobj = os.path.join(root, ".git")
        ws = os.path.realpath(os.path.join(d, "ws"))
        for p in (bodies, gitobj, ws):
            os.makedirs(p)
        with open(os.path.join(gitobj, "answer"), "w") as fh:
            fh.write("ANSWER-KEY")
        probe = os.path.join(ws, "p.sh")
        with open(probe, "w") as fh:
            fh.write('#!/bin/sh\ncat "%s/answer" >/dev/null 2>&1 && echo READ || echo BLOCK\n'
                     % gitobj)
        os.chmod(probe, 0o755)
        blocked = subprocess.run(confine.confined_argv(["/bin/sh", probe], ws, deny_read=[root]),
                                 capture_output=True, text=True, timeout=30).stdout
        assert "BLOCK" in blocked, blocked
        leaked = subprocess.run(confine.confined_argv(["/bin/sh", probe], ws, deny_read=[bodies]),
                                capture_output=True, text=True, timeout=30).stdout
        assert "READ" in leaked, leaked  # the original bug, proving the test can distinguish


def main():
    failures = []
    for fn in (test_holdout_deny_read_prefers_clone_root,
               test_run_holdout_denies_whole_clone_tree,
               test_child_env_strips_holdout_location,
               test_confine_denies_git_sibling_under_root):
        try:
            fn()
            print("  ok   - " + fn.__name__)
        except AssertionError as e:
            failures.append("{}: {}".format(fn.__name__, e))
            print("  FAIL - " + fn.__name__)
    assert not failures, "\n".join(failures)
    print("holdout-confinement suite green")


if __name__ == "__main__":
    main()
