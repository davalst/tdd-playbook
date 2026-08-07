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


def test_lock_transaction_and_binding():
    """PLANTED: concurrent agents cannot replace each other's protected-file authority."""
    core = _core()
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        with open(os.path.join(root, "tests", "test_other.py"), "w") as fh:
            fh.write("def test_other():\n    assert True\n")
        ident = core.resolve_repository(root)
        first = core.new_lock_record(ident, ["tests/test_pay.py"], "session-a")
        second = core.new_lock_record(ident, ["tests/test_other.py"], "session-b")
        barrier = threading.Barrier(2)
        outcomes = []

        def contender(record):
            barrier.wait()
            try:
                core.merge_lock(ident, record)
                outcomes.append("won:" + record["session_id"])
            except core.ContractError as exc:
                outcomes.append("refused:" + str(exc))

        threads = [threading.Thread(target=contender, args=(record,))
                   for record in (first, second)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        active = core.read_lock(ident)
        check("lock transaction: one competing session wins and one is named/refused",
              len([row for row in outcomes if row.startswith("won:")]) == 1
              and len([row for row in outcomes if "competing" in row]) == 1, outcomes)
        check("lock transaction: the winning protection is never replaced by the loser",
              len(active["files"]) == 1, active)

        missing = ("tests/test_pay.py" if "tests/test_pay.py" not in active["files"]
                   else "tests/test_other.py")
        same_session = core.new_lock_record(ident, [missing], active["session_id"])
        merged = core.merge_lock(ident, same_session)
        check("lock transaction: the same run can extend its lock without a lost update",
              set(merged["files"]) == {"tests/test_pay.py", "tests/test_other.py"}, merged)
        try:
            core.clear_lock(ident, expected_generation=active["generation"])
        except core.ContractError:
            stale_clear_refused = True
        else:
            stale_clear_refused = False
        check("lock transaction: stale unlock cannot clear a newer lock generation",
              stale_clear_refused and core.read_lock(ident) is not None)

        current = core.read_lock(ident)
        try:
            core.clear_lock(ident, expected_generation=current["generation"],
                            expected_lock_id=current["lock_id"],
                            expected_session_id="not-the-owner")
        except core.ContractError:
            nonowner_refused = True
        else:
            nonowner_refused = False
        check("lock transaction: a non-owner cannot unlock an active run", nonowner_refused)

        core.clear_lock(ident, expected_generation=current["generation"],
                        expected_lock_id=current["lock_id"],
                        expected_session_id=current["session_id"])
        replacement = core.new_lock_record(ident, ["tests/test_pay.py"], "replacement")
        core.merge_lock(ident, replacement)
        try:
            core.clear_lock(ident, expected_generation=current["generation"],
                            expected_lock_id=current["lock_id"],
                            expected_session_id=current["session_id"])
        except core.ContractError:
            aba_refused = True
        else:
            aba_refused = False
        check("lock transaction: stale ABA clear cannot delete a replacement generation-1 lock",
              aba_refused and core.read_lock(ident)["session_id"] == "replacement")

        core.clear_lock(ident, expected_generation=1,
                        expected_lock_id=replacement["lock_id"],
                        expected_session_id="replacement")
        side = os.path.join(d, "side")
        _git(root, "worktree", "add", "-qb", "side-owner", side)
        main_ident = core.resolve_repository(root)
        side_ident = core.resolve_repository(side)
        main_record = core.new_lock_record(main_ident, ["tests/test_pay.py"], "shared-session")
        core.merge_lock(main_ident, main_record)
        side_record = core.new_lock_record(side_ident, ["tests/test_pay.py"], "shared-session")
        try:
            core.merge_lock(side_ident, side_record)
        except core.ContractError:
            worktree_collision_refused = True
        else:
            worktree_collision_refused = False
        check("lock transaction: same session text in another worktree is a competing owner",
              worktree_collision_refused
              and core.read_lock(main_ident)["source_worktree_id"] == main_ident["worktree_id"])
        try:
            core.clear_lock(side_ident, expected_generation=1,
                            expected_lock_id=main_record["lock_id"],
                            expected_session_id="shared-session",
                            expected_worktree_id=side_ident["worktree_id"])
        except core.ContractError:
            cross_worktree_clear_refused = True
        else:
            cross_worktree_clear_refused = False
        check("lock transaction: same session text cannot unlock from another worktree",
              cross_worktree_clear_refused and core.read_lock(main_ident) is not None)

        core.clear_lock(main_ident, expected_generation=1,
                        expected_lock_id=main_record["lock_id"],
                        expected_session_id="shared-session",
                        expected_worktree_id=main_ident["worktree_id"])
        try:
            core.clear_lock(main_ident, expected_generation=1,
                            expected_lock_id=main_record["lock_id"],
                            expected_session_id="shared-session",
                            expected_worktree_id=main_ident["worktree_id"])
        except core.ContractError:
            disappeared_clear_refused = True
        else:
            disappeared_clear_refused = False
        check("lock transaction: clear-after-read disappearance cannot report success",
              disappeared_clear_refused)
        merged = core.merge_lock(ident, current)
        binding = core.lock_binding(ident, merged)
        check("lock binding: current source revision is explicit", binding == "current", binding)
        with open(os.path.join(root, "pay.py"), "a") as fh:
            fh.write("y = 2\n")
        _git(root, "add", "pay.py")
        _git(root, "commit", "-qm", "advance")
        advanced = core.resolve_repository(root)
        check("lock binding: a HEAD advance is stale evidence, not silently current",
              core.lock_binding(advanced, merged) == "stale_revision")


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
               test_concurrent_journal, test_lock_transaction_and_binding,
               test_assurance_contract):
        try:
            fn()
        except Exception as exc:
            check(fn.__name__ + " executes", False, repr(exc))
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    assert not _results["fail"], "portable core calibration failed"


if __name__ == "__main__":
    main()
