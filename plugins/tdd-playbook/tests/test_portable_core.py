#!/usr/bin/env python3
"""Planted calibration for the host-neutral identity, lock, and policy seam.

This suite intentionally imports a module that does not exist in the red commit.  It is the
first portability slice: prove one lock authority across linked worktrees without moving
Claude's live transport yet.  Self-contained, no pytest-only fixtures.
"""
import importlib
import json
import os
import subprocess
import sys
import tempfile
import threading

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(PLUGIN, "bin")
sys.path.insert(0, BIN)

_results = {"pass": 0, "fail": 0}


def check(name, condition, detail=""):
    if condition:
        _results["pass"] += 1
        print("  ok   - " + name)
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True,
                          timeout=30, check=True)


def _repo(base):
    root = os.path.join(base, "main repo")
    os.makedirs(root)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Portable Core Test")
    with open(os.path.join(root, "pay.py"), "w") as fh:
        fh.write("def pay():\n    return 1\n")
    os.makedirs(os.path.join(root, "tests"))
    with open(os.path.join(root, "tests", "test_pay.py"), "w") as fh:
        fh.write("def test_pay():\n    assert pay() == 2\n")
    _git(root, "add", "pay.py", "tests/test_pay.py")
    _git(root, "commit", "-qm", "fixture")
    return root


def _core():
    return importlib.import_module("host_contract")


def test_worktree_state_identity():
    """PLANTED: the old CLAUDE_PROJECT_DIR/.claude path gives linked worktrees two locks."""
    core = _core()
    with tempfile.TemporaryDirectory() as d:
        main = _repo(d)
        side = os.path.join(d, "side worktree")
        _git(main, "worktree", "add", "-qb", "side", side)
        a = core.resolve_repository(main)
        b = core.resolve_repository(side)
        check("identity: linked worktrees share one canonical state directory",
              a["state_dir"] == b["state_dir"], (a, b))
        check("identity: linked worktrees retain distinct worktree identities",
              a["worktree_git_dir"] != b["worktree_git_dir"], (a, b))
        check("identity: repo id is stable across linked worktrees",
              a["repo_id"] == b["repo_id"], (a, b))
        check("identity: roots are canonical and distinct",
              a["root"] == os.path.realpath(main)
              and b["root"] == os.path.realpath(side) and a["root"] != b["root"], (a, b))


def test_lock_policy():
    """Pure normalized policy blocks protected writes and rejects containment escapes."""
    core = _core()
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        ident = core.resolve_repository(root)
        record = core.new_lock_record(
            ident, [os.path.join(root, "tests", "test_pay.py")],
            session_id="run-1", now="2026-08-07T12:00:00+00:00")
        blocked = core.policy_decision(
            ident, record, {"kind": "write", "targets": ["tests/test_pay.py"]})
        allowed = core.policy_decision(
            ident, record, {"kind": "write", "targets": ["pay.py"]})
        verifier = core.policy_decision(
            ident, record, {"kind": "write", "targets": ["pytest.ini"]})
        check("policy: planted locked-test write is blocked",
              blocked["decision"] == "block" and blocked["surface"] == "locked", blocked)
        check("policy: clean source write remains allowed", allowed["decision"] == "allow", allowed)
        check("policy: verifier surface is blocked while a lock is active",
              verifier["decision"] == "block" and verifier["surface"] == "verifier", verifier)
        try:
            core.normalize_target(ident, "../escape.py")
        except core.ContractError:
            escaped = True
        else:
            escaped = False
        check("policy: planted traversal is rejected, never normalized into scope", escaped)

        outside = os.path.join(d, "outside.py")
        with open(outside, "w") as fh:
            fh.write("secret\n")
        link = os.path.join(root, "tests", "linked.py")
        os.symlink(outside, link)
        try:
            core.normalize_target(ident, link)
        except core.ContractError:
            symlink_escaped = True
        else:
            symlink_escaped = False
        check("policy: planted symlink escape is rejected", symlink_escaped)


def test_single_legacy_import():
    """A one-shot importer prevents the permanent dual-read split-brain seam."""
    core = _core()
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        ident = core.resolve_repository(root)
        legacy_dir = os.path.join(root, ".claude")
        os.makedirs(legacy_dir)
        legacy = os.path.join(legacy_dir, "tdd-lock.json")
        with open(legacy, "w") as fh:
            json.dump({"locked_at": "2026-08-07T12:00:00+00:00",
                       "files": {"tests/test_pay.py": "abc"}}, fh)
        first = core.import_legacy_lock(ident, session_id="legacy-session")
        second = core.import_legacy_lock(ident, session_id="legacy-session")
        record = core.read_lock(ident)
        check("legacy: first import creates the canonical versioned lock", first == "imported", first)
        check("legacy: imported record is readable from canonical state only",
              record["schema_version"] == 1
              and "tests/test_pay.py" in record["files"], record)
        check("legacy: source is consumed so no dual read remains",
              not os.path.exists(legacy) and os.path.exists(legacy + ".migrated"), legacy)
        check("legacy: repeated importer is a no-op", second == "already-canonical", second)


def test_concurrent_journal():
    """PLANTED: append-only evidence must not lose rows when two agents write together."""
    core = _core()
    with tempfile.TemporaryDirectory() as d:
        ident = core.resolve_repository(_repo(d))
        errors = []

        def writer(i):
            try:
                core.append_event(ident, {"schema_version": 1, "event": "probe", "seq": i})
            except Exception as exc:
                errors.append(repr(exc))

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        rows = core.read_events(ident)
        check("journal: concurrent writers all complete", not errors, errors)
        check("journal: no rows are lost or duplicated",
              sorted(row["seq"] for row in rows) == list(range(12)), rows)


def test_assurance_contract():
    core = _core()
    check("contract: assurance vocabulary is closed and trust-ordered",
          core.ASSURANCE_LEVELS == (
              "unmeasured", "local_claim", "host_observed", "host_prevented",
              "ci_verified", "civerd_signed"), core.ASSURANCE_LEVELS)
    check("contract: only CIVerd-signed evidence is release-authorizing",
          core.release_authorizing("civerd_signed") is True
          and all(not core.release_authorizing(level)
                  for level in core.ASSURANCE_LEVELS[:-1]))


def main():
    print("portable host core calibration")
    # Keep every predicate-bearing function explicitly invoked: this repo's script-style
    # suites otherwise create a green function that never ran.
    for fn in (test_worktree_state_identity, test_lock_policy, test_single_legacy_import,
               test_concurrent_journal, test_assurance_contract):
        try:
            fn()
        except Exception as exc:
            check(fn.__name__ + " executes", False, repr(exc))
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    assert not _results["fail"], "portable core calibration failed"


if __name__ == "__main__":
    main()
