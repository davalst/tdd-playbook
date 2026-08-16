#!/usr/bin/env python3
"""Planted-input calibration for the TEST-LOCK (bin/tdd_lock.py + test_lock_guard.py).

The lock is the mechanical form of §1's iron rule (HACK_CATALOG H2/H5) — so the planted
attack here is the documented one: while a lock is active, an edit to the locked test (or
to conftest.py) must be BLOCKED (exit 2). Self-contained, no pytest. Run:
    python3 tests/test_tdd_lock.py
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCK_BIN = os.path.join(PLUGIN, "bin", "tdd_lock.py")
GUARD = os.path.join(PLUGIN, "hooks", "scripts", "test_lock_guard.py")

_results = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _results["pass"] += 1
        print("  ok   - {}".format(name))
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def clean_env(root):
    env = dict(os.environ)
    for k in list(env):
        if k.startswith("TDD_PLAYBOOK_"):
            del env[k]
    env["CLAUDE_PROJECT_DIR"] = root
    return env


def lock_cli(root, *args):
    return subprocess.run([sys.executable, LOCK_BIN, *args],
                          capture_output=True, text=True, cwd=root, env=clean_env(root),
                          timeout=30)


def guard(root, file_path, env_extra=None):
    env = clean_env(root)
    if env_extra:
        env.update(env_extra)
    event = {"tool_name": "Edit", "tool_input": {
        "file_path": file_path, "old_string": "a", "new_string": "b"}}
    return subprocess.run([sys.executable, GUARD], input=json.dumps(event),
                          capture_output=True, text=True, cwd=root, env=env, timeout=30)


def guard_bash(root, command):
    event = {"tool_name": "Bash", "tool_input": {"command": command}}
    return subprocess.run([sys.executable, GUARD], input=json.dumps(event),
                          capture_output=True, text=True, cwd=root, env=clean_env(root), timeout=30)


def main():
    print("TEST-LOCK calibration")
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "tests"))
        test_file = os.path.join(d, "tests", "test_pay.py")
        with open(test_file, "w") as fh:
            fh.write("def test_charge():\n    assert charge() == 10\n")
        with open(os.path.join(d, "conftest.py"), "w") as fh:
            fh.write("# fixtures\n")
        with open(os.path.join(d, "pay.py"), "w") as fh:
            fh.write("def charge():\n    return 10\n")

        # no lock -> guard is free and silent
        p = guard(d, test_file)
        check("no lock: edit passes (exit 0)", p.returncode == 0 and p.stderr == "",
              (p.returncode, p.stderr))

        # lock the test
        p = lock_cli(d, "lock", "tests/test_pay.py")
        check("lock records the file", p.returncode == 0 and "LOCKED 1" in p.stdout,
              (p.returncode, p.stdout, p.stderr))
        p = lock_cli(d, "status")
        check("status shows the active lock", "ACTIVE" in p.stdout and "test_pay.py" in p.stdout,
              p.stdout)

        # PLANTED (H2): editing the locked test must BLOCK
        p = guard(d, test_file)
        check("H2: edit to LOCKED test is BLOCKED (exit 2)",
              p.returncode == 2 and "TEST-LOCK" in p.stderr, (p.returncode, p.stderr))

        # relative path form is caught too
        p = guard(d, "tests/test_pay.py")
        check("H2: relative-path edit is BLOCKED", p.returncode == 2, (p.returncode, p.stderr))

        # PLANTED (H5): editing conftest.py during an active lock must BLOCK
        p = guard(d, os.path.join(d, "conftest.py"))
        check("H5: conftest edit during lock is BLOCKED",
              p.returncode == 2 and "verifier surface" in p.stderr, (p.returncode, p.stderr))

        # source edits stay free — the lock must never wedge implementation
        p = guard(d, os.path.join(d, "pay.py"))
        check("source edit stays free during lock", p.returncode == 0, (p.returncode, p.stderr))

        # unlock without a reason is REFUSED
        p = lock_cli(d, "unlock", "--reason", "meh", "--class", "phase")
        check("unlock without a real reason refused", p.returncode == 1 and "REFUSED" in p.stderr,
              (p.returncode, p.stderr))

        # unlock with a reason: journaled, lock lifted, guard free again
        p = lock_cli(d, "unlock", "--reason", "green — implementation complete",
                     "--class", "feature-end")
        check("reasoned unlock succeeds", p.returncode == 0, (p.returncode, p.stderr))
        journal = os.path.join(d, ".claude", "tdd-lock-journal.jsonl")
        entries = [json.loads(ln) for ln in open(journal)]
        check("journal holds lock + unlock with the reason",
              [e["event"] for e in entries] == ["lock", "unlock"]
              and entries[1]["reason"].startswith("green"), entries)
        p = guard(d, test_file)
        check("after unlock: edit passes again", p.returncode == 0, (p.returncode, p.stderr))

        # mode demotion works (warn)
        lock_cli(d, "lock", "tests/test_pay.py")
        p = guard(d, test_file, {"TDD_PLAYBOOK_HOOK_TESTLOCK": "warn"})
        check("TESTLOCK=warn demotes to exit 1", p.returncode == 1, (p.returncode, p.stderr))

    test_reason_class()
    test_reason_class_reaches_the_rollup()
    test_out_of_root_jurisdiction()
    test_cross_session_recovery()
    test_force_unlock()
    test_version_skew_guard()

    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    sys.exit(1 if _results["fail"] else 0)


def test_out_of_root_jurisdiction():
    """cheliped field report (plugin v1.36.0, 2026-08-15): while a lock is active, a write to an
    OUT-OF-ROOT path (memory ~/.claude/projects, plan-mode ~/.claude/plans, scratchpad) was
    BLOCKED — edit_findings converted policy_decision's 'target escapes repository root'
    ContractError into a block, a cross-session DoS that also broke plan-mode (whose only write is
    the out-of-root plan file). The bug fires ONLY in a real git repo, where resolve_repository
    succeeds and policy_decision is reached — the non-git scratch path never hits the buggy branch
    (which is why the fixture MUST git-init, verified red-first against the pre-fix guard).
    Two-directional §13 fixture: in-root locked test still BLOCKS, out-of-root write ALLOWS."""
    print("\n[TEST-LOCK out-of-root jurisdiction — cheliped DoS]")
    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
        os.makedirs(os.path.join(d, "tests"))
        with open(os.path.join(d, "tests", "test_x.py"), "w") as fh:
            fh.write("def test_x():\n    assert x() == 1\n")
        gid = ["-c", "user.email=t@t", "-c", "user.name=t"]
        for args in (["init", "-q"], [*gid, "add", "-A"], [*gid, "commit", "-qm", "seed"]):
            subprocess.run(["git", "-C", d, *args], check=True, capture_output=True)
        lock_cli(d, "lock", "tests/test_x.py")
        # in-root locked test still BLOCKS via the git/policy_decision path (the other direction)
        p = guard(d, os.path.join(d, "tests", "test_x.py"))
        check("git repo: in-root locked test still BLOCKS (exit 2)", p.returncode == 2,
              (p.returncode, p.stderr))
        # out-of-root write PASSES — pre-fix this BLOCKED (exit 2), the cross-session DoS
        p = guard(d, os.path.join(outside, "memory.md"))
        check("cheliped DoS: out-of-root write PASSES while a lock is active (jurisdiction)",
              p.returncode == 0, (p.returncode, p.stderr))
        # cheliped secondary: an UNDECIDABLE write (variable path) while locked still fails closed,
        # but with the HONEST message — NOT one naming the locked test it may not even touch.
        p = guard_bash(d, "python3 -c \"open(vv, 'w')\"")
        check("cheliped: undecidable write while locked blocks with an HONEST message (not the test)",
              p.returncode == 2 and "cannot resolve" in p.stderr and "test_x.py" not in p.stderr,
              (p.returncode, p.stderr))


def test_cross_session_recovery():
    """cheliped field report (2026-08-16, SECOND live repro): an auto-lock the GUARD imported was
    stamped with the fallback owner 'claude-hook' (test_lock_guard.py), which the unlock CLI's
    ownership check can NEVER match — its fallback is 'local-worktree-<hash>' — so clear_lock
    REFUSED for every session and the only escape was `rm .git/tdd-playbook/active-lock.json`.
    §13 replay of the exact wedged-lock shape (guard-imported legacy lock, foreign owner).
    D1: the guard's import now routes through the SAME shared host_contract.session_id() the CLI
    uses, so an imported lock is releasable by any same-worktree session."""
    print("\n[TEST-LOCK cross-session recovery — cheliped deadlock]")
    gid = ["-c", "user.email=t@t", "-c", "user.name=t"]

    # D1: a guard-IMPORTED legacy lock must be releasable by a plain (same-worktree) unlock.
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "tests"))
        tf = os.path.join(d, "tests", "test_x.py")
        open(tf, "w").write("def test_x():\n    assert x() == 1\n")
        for args in (["init", "-q"], [*gid, "add", "-A"], [*gid, "commit", "-qm", "seed"]):
            subprocess.run(["git", "-C", d, *args], check=True, capture_output=True)
        digest = hashlib.sha256(open(tf, "rb").read()).hexdigest()
        os.makedirs(os.path.join(d, ".claude"))
        with open(os.path.join(d, ".claude", "tdd-lock.json"), "w") as fh:
            json.dump({"files": {"tests/test_x.py": digest},
                       "session_id": "whatever", "locked_at": "2026-08-16T11:02:46Z"}, fh)
        # a write touches the guard -> it imports the legacy lock into the canonical authority
        guard(d, tf)
        active = os.path.join(d, ".git", "tdd-playbook", "active-lock.json")
        check("D1: guard imported the legacy lock into the canonical authority",
              os.path.isfile(active), active)
        owner = json.load(open(active))["session_id"]
        check("D1: the imported lock is NOT owned by the unreleasable 'claude-hook'",
              owner != "claude-hook", owner)
        p = lock_cli(d, "unlock", "--reason", "green — recovered the imported lock",
                     "--class", "feature-end")
        check("D1: a same-worktree plain unlock RELEASES the imported lock (deadlock gone)",
              p.returncode == 0, (p.returncode, p.stdout, p.stderr))

    # ALREADY-WEDGED (the live incident): a lock left on disk owned by 'claude-hook' by the old
    # 1.30.0 guard must be releasable by a plain env-less unlock — ownership falls to worktree_id,
    # which still matches. This is the root fix reaching BACK, not just forward (integ. Finding 4).
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "tests"))
        tf = os.path.join(d, "tests", "test_w.py")
        open(tf, "w").write("def test_w():\n    assert w() == 1\n")
        for args in (["init", "-q"], [*gid, "add", "-A"], [*gid, "commit", "-qm", "seed"]):
            subprocess.run(["git", "-C", d, *args], check=True, capture_output=True)
        lock_cli(d, "lock", "tests/test_w.py")           # a valid lock (correct worktree_id)
        active = os.path.join(d, ".git", "tdd-playbook", "active-lock.json")
        rec = json.load(open(active))
        rec["session_id"] = "claude-hook"                 # simulate the old wedging guard's stamp
        with open(active, "w") as fh:
            json.dump(rec, fh)
        p = lock_cli(d, "unlock", "--reason", "recovering a claude-hook-wedged lock in place",
                     "--class", "feature-end")
        check("root-fix reaches BACK: an on-disk 'claude-hook' lock is released by a plain unlock",
              p.returncode == 0 and not os.path.isfile(active), (p.returncode, p.stderr))


def test_force_unlock():
    """The LEGAL recovery that retires `rm .git/tdd-playbook/active-lock.json`: a lock owned by a
    DIFFERENT real session (env-present cross-session) or a CORRUPT/schema-mismatched lock that
    clear_lock cannot even read is releasable by `unlock --force --reason`, journaled forced:true
    and surfaced to the yield instrument. BOTH families covered so no `rm` escape survives; --force
    still COMPOSES with the reason/class gate (recovery is audited, not a bypass), and the
    cross-session refusal POINTS at --force so nobody reaches into .git."""
    print("\n[TEST-LOCK --force recovery]")
    gid = ["-c", "user.email=t@t", "-c", "user.name=t"]

    def mkrepo(d, name):
        os.makedirs(os.path.join(d, "tests"))
        p = os.path.join(d, "tests", name)
        open(p, "w").write("def t():\n    assert f() == 1\n")
        for a in (["init", "-q"], [*gid, "add", "-A"], [*gid, "commit", "-qm", "seed"]):
            subprocess.run(["git", "-C", d, *a], check=True, capture_output=True)
        return p

    def cli(d, sess, *args):
        env = clean_env(d)
        if sess:
            env["TDD_PLAYBOOK_SESSION_ID"] = sess
        return subprocess.run([sys.executable, LOCK_BIN, *args], cwd=d, env=env,
                              capture_output=True, text=True, timeout=30)

    active_of = lambda d: os.path.join(d, ".git", "tdd-playbook", "active-lock.json")

    # (a) env-present cross-session: A locks with a real token; B needs --force
    with tempfile.TemporaryDirectory() as d:
        mkrepo(d, "test_a.py")
        cli(d, "sess-A", "lock", "tests/test_a.py")
        p = cli(d, "sess-B", "unlock", "--reason", "recover A's lock please", "--class", "feature-end")
        check("--force NEEDED: session B's plain unlock of A's real-session lock is REFUSED",
              p.returncode == 1 and "another session" in p.stderr, (p.returncode, p.stderr))
        check("discoverable: the cross-session refusal NAMES --force (not rm)", "--force" in p.stderr,
              p.stderr)
        p = cli(d, "sess-B", "unlock", "--force", "--reason",
                "recovering an orphaned lock from a dead session A", "--class", "feature-end")
        check("--force RELEASES a foreign real-session lock", p.returncode == 0 and
              not os.path.isfile(active_of(d)), (p.returncode, p.stderr))

    # (b) a CORRUPT/schema-mismatched lock clear_lock cannot even read
    with tempfile.TemporaryDirectory() as d:
        mkrepo(d, "test_b.py")
        cli(d, None, "lock", "tests/test_b.py")
        rec = json.load(open(active_of(d))); rec["schema_version"] = 999
        with open(active_of(d), "w") as fh:
            json.dump(rec, fh)
        p = cli(d, None, "unlock", "--reason", "cannot read this lock", "--class", "feature-end")
        check("validation-fail: a plain unlock of a schema-mismatched lock is REFUSED",
              p.returncode == 1, (p.returncode, p.stderr))
        p = cli(d, None, "unlock", "--force", "--reason",
                "force-clearing a schema-mismatched lock from a version skew", "--class", "feature-end")
        check("--force clears a schema-mismatched lock too (rm retired for this family)",
              p.returncode == 0 and not os.path.isfile(active_of(d)), (p.returncode, p.stderr))

    # (c) --force COMPOSES with the reason gate (auditability not bypassed)
    with tempfile.TemporaryDirectory() as d:
        mkrepo(d, "test_c.py")
        cli(d, "sess-A", "lock", "tests/test_c.py")
        p = cli(d, "sess-B", "unlock", "--force", "--reason", "short", "--class", "feature-end")
        check("--force still needs a real reason (>=10 chars) — recovery is audited, not a bypass",
              p.returncode == 1 and "REFUSED" in p.stderr, (p.returncode, p.stderr))

    # (d) forced:true reaches a CONSUMER — the journal /grade reads carries it (not write-only)
    with tempfile.TemporaryDirectory() as d:
        mkrepo(d, "test_d.py")
        cli(d, "sess-A", "lock", "tests/test_d.py")
        cli(d, "sess-B", "unlock", "--force", "--reason", "recovering the orphaned lock now",
            "--class", "feature-end")
        events = os.path.join(d, ".git", "tdd-playbook", "events.jsonl")
        rows = [json.loads(ln) for ln in open(events)] if os.path.isfile(events) else []
        unlocks = [r for r in rows if r.get("event") == "unlock"]
        check("consumer: the forced unlock's journal entry (what /grade reads) carries forced=true",
              any(r.get("forced") is True for r in unlocks), unlocks)

    # (e) HARDENING (security-adversary): the ONE new release path — an env-less same-worktree
    # unlock clearing a REAL-token owner's lock — journals session_downgrade:true for /grade.
    with tempfile.TemporaryDirectory() as d:
        mkrepo(d, "test_e.py")
        cli(d, "sess-A", "lock", "tests/test_e.py")            # real env-token owner
        p = cli(d, None, "unlock", "--reason", "same-worktree env-less release of A's lock",
                "--class", "feature-end")                       # env-less -> worktree governs
        check("hardening: env-less same-worktree unlock of a real-token lock SUCCEEDS", p.returncode == 0,
              (p.returncode, p.stderr))
        events = os.path.join(d, ".git", "tdd-playbook", "events.jsonl")
        rows = [json.loads(ln) for ln in open(events)] if os.path.isfile(events) else []
        check("hardening: it journals session_downgrade=true (the one new path, visible to /grade)",
              any(r.get("event") == "unlock" and r.get("session_downgrade") is True for r in rows),
              rows)


def test_version_skew_guard():
    """cheliped Defect C residual: under version skew (an older vendored guard reading a lock a
    newer CLI wrote), active_lock sets _contract_error and main() fails closed on EVERY write —
    including OUT-OF-ROOT ones, the same cross-session DoS the v1.37.0 edit_findings fix closed but
    which this earlier main() branch re-opened. D4: out-of-root passes even in the repair state, and
    the in-root block names the actual remedy (update + reload), not an opaque 'authority repaired'."""
    print("\n[TEST-LOCK version-skew guard — Defect C residual]")
    gid = ["-c", "user.email=t@t", "-c", "user.name=t"]
    with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as outside:
        os.makedirs(os.path.join(d, "tests"))
        tf = os.path.join(d, "tests", "test_v.py")
        open(tf, "w").write("def test_v():\n    assert v() == 1\n")
        for a in (["init", "-q"], [*gid, "add", "-A"], [*gid, "commit", "-qm", "seed"]):
            subprocess.run(["git", "-C", d, *a], check=True, capture_output=True)
        lock_cli(d, "lock", "tests/test_v.py")
        active = os.path.join(d, ".git", "tdd-playbook", "active-lock.json")
        rec = json.load(open(active)); rec["schema_version"] = 999   # a newer CLI wrote it
        with open(active, "w") as fh:
            json.dump(rec, fh)
        # OUT-OF-ROOT write during the version-skew repair state must PASS (not the DoS)
        p = guard(d, os.path.join(outside, "memory.md"))
        check("D4: out-of-root write PASSES under a version-skew _contract_error (no residual DoS)",
              p.returncode == 0, (p.returncode, p.stderr))
        # IN-ROOT write fails closed, but names the ACTIONABLE remedy (update + reload)
        p = guard(d, tf)
        check("D4: in-root write under version skew names the remedy (update + reload)",
              p.returncode == 2 and "version mismatch" in p.stderr and "reload" in p.stderr,
              (p.returncode, p.stderr))


def _fresh(d, name="tests/test_pay.py"):
    """A scratch project with one locked test file; returns its abs path."""
    os.makedirs(os.path.join(d, "tests"), exist_ok=True)
    p = os.path.join(d, name)
    if not os.path.isfile(p):
        # a real assertion, not a tautology: this string is fixture CONTENT, but the
        # weakening guard reads it as source and is right to — keep fixtures honest too
        open(p, "w").write("def test_pay_totals():\n    assert pay(100, 0.2) == 80\n")
    lock_cli(d, "lock", name)
    return p


def test_reason_class():
    """PLANTED (v1.27, pre-fix sha 119e2de): every journaled unlock was reported to the yield
    instrument as a block adjudicated a false positive, so the normal red-first rhythm drove
    `RETIREMENT CANDIDATE: testlock`. `--class` names WHY the lock was released; only
    `gate-wrong` adjudicates.

    The self-grading hazard is the point of the refusals below: the agent picking the class
    is the agent that wants out, so the one class that moves the needle is the one hardest to
    claim, and a phase-shaped reason claiming it is FLAGGED — never silently rewritten."""
    print("\n[unlock reason-class (v1.27)]")
    journal = lambda d: [json.loads(ln) for ln in
                         open(os.path.join(d, ".claude", "tdd-lock-journal.jsonl"))]

    with tempfile.TemporaryDirectory() as d:
        _fresh(d)
        p = lock_cli(d, "unlock", "--reason", "phase boundary — green, re-locking after",
                     "--class", "phase")
        check("unlock --class phase succeeds and is journaled as stated",
              p.returncode == 0 and journal(d)[-1]["reason_class"] == "phase",
              (p.returncode, p.stderr))

    with tempfile.TemporaryDirectory() as d:
        _fresh(d)
        # PLANTED: the exculpatory class claimed on a thin reason
        p = lock_cli(d, "unlock", "--reason", "gate was wrong", "--class", "gate-wrong")
        check("PLANTED thin gate-wrong is REFUSED (exit 1)",
              p.returncode == 1 and "REFUSED" in p.stderr, (p.returncode, p.stderr))
        check("PLANTED thin gate-wrong: lock NOT lifted, nothing journaled",
              os.path.isfile(os.path.join(d, ".claude", "tdd-lock.json"))
              and [e["event"] for e in journal(d)] == ["lock"], journal(d))
        # CONTROL: the same class over the bar is accepted
        p = lock_cli(d, "unlock", "--class", "gate-wrong", "--reason",
                     "the testlock guard blocked an edit to a file that was never locked")
        check("CONTROL: gate-wrong over the bar succeeds",
              p.returncode == 0 and journal(d)[-1]["reason_class"] == "gate-wrong",
              (p.returncode, p.stderr))

    with tempfile.TemporaryDirectory() as d:
        _fresh(d)
        # PLANTED: an invented class must not open a new bucket
        p = lock_cli(d, "unlock", "--reason", "a perfectly fine reason here",
                     "--class", "made-up")
        check("PLANTED invented class rejected by the closed vocabulary (exit 2)",
              p.returncode == 2, (p.returncode, p.stderr))
        check("PLANTED invented class: lock survives",
              os.path.isfile(os.path.join(d, ".claude", "tdd-lock.json")))
        for k in ("phase", "feature-end", "test-wrong", "gate-wrong"):
            reason = ("the gate blocked work it should not have, here is which one and why"
                      if k == "gate-wrong" else "a perfectly fine reason here")
            _fresh(d)
            p = lock_cli(d, "unlock", "--reason", reason, "--class", k)
            check("CONTROL: vocabulary member {} accepted".format(k), p.returncode == 0,
                  (k, p.returncode, p.stderr))

    with tempfile.TemporaryDirectory() as d:
        _fresh(d)
        # PLANTED (self-grading): phase-shaped prose claiming the adjudicating class
        p = lock_cli(d, "unlock", "--class", "gate-wrong", "--reason",
                     "implemented to green and will re-lock once the next batch lands")
        e = journal(d)[-1]
        check("PLANTED phase-shaped gate-wrong is FLAGGED as a mismatch",
              p.returncode == 0 and "MISMATCH" in p.stderr and e.get("class_mismatch") is True,
              (p.returncode, p.stderr, e))
        check("mismatch NEVER rewrites the stated class (no silent fabrication)",
              e["reason_class"] == "gate-wrong", e)

    with tempfile.TemporaryDirectory() as d:
        _fresh(d)
        # CONTROL: the same prose with the honest class draws no flag
        p = lock_cli(d, "unlock", "--class", "phase", "--reason",
                     "implemented to green and will re-lock once the next batch lands")
        check("CONTROL: phase-shaped prose classed phase -> no mismatch flag",
              p.returncode == 0 and "MISMATCH" not in p.stderr
              and "class_mismatch" not in journal(d)[-1], (p.stderr, journal(d)[-1]))

    with tempfile.TemporaryDirectory() as d:
        _fresh(d)
        # v1.32.0 INVERTED (was: no --class succeeds and records UNCLASSIFIED). An
        # unclassified unlock measures nothing, and this repo's journal is 22 of 26 rows with
        # no class at all — which left the retirement instrument with nothing to compute from,
        # so a reader fell back to counting `overrides` and concluded TEST-LOCK had 20 false
        # positives when the measured number is 0. The cheapest fix to that whole class is to
        # stop producing unmeasured rows. Strictly stronger than the assertion it replaces:
        # the old one accepted an unmeasured record, this one refuses it.
        p = lock_cli(d, "unlock", "--reason", "old caller with no class flag")
        check("v1.32.0: --class is REQUIRED — an unmeasured unlock is refused, not recorded",
              p.returncode == 2 and journal(d)[-1]["event"] == "lock",
              (p.returncode, p.stderr[:80], journal(d)[-1]))
        check("the refusal TEACHES the four classes rather than just failing",
              all(k in p.stderr for k in ("phase", "feature-end", "test-wrong", "gate-wrong")),
              p.stderr[:200])
        check("the refusal names gate-wrong as the only false-positive class",
              "false positive" in p.stderr and "gate-wrong" in p.stderr, p.stderr[:200])
        # and the sanctioned path still works
        p = lock_cli(d, "unlock", "--reason", "old caller, now classified",
                     "--class", "feature-end")
        check("classified unlock still succeeds and records the class",
              p.returncode == 0 and journal(d)[-1]["reason_class"] == "feature-end",
              (p.returncode, journal(d)[-1]))


def test_reason_class_reaches_the_rollup():
    """SEAM (§1 v1.26 — test at the seam you don't own): the writer names the field
    `reason_class` and the reader looks for `reason_class`. Every other test here reads only
    what tdd_lock itself wrote, so both sides could be self-consistently wrong and stay green.
    This drives the REAL gate_yield.py rollup and asserts the committed `fp` cell."""
    print("\n[seam: unlock class -> real gate_yield rollup]")
    gy = os.path.join(PLUGIN, "bin", "gate_yield.py")
    for klass, want_fp in (("gate-wrong", 1), ("phase", 0)):
        with tempfile.TemporaryDirectory() as d:
            _fresh(d)
            log = os.path.join(d, "yield.jsonl")
            md = os.path.join(d, "gate_yield.md")
            # clean_env strips TDD_PLAYBOOK_*, so the log MUST be set explicitly here or the
            # unlock drains the developer's real yield log (the 2026-07-28 G5 incident).
            env = clean_env(d)
            env["TDD_PLAYBOOK_YIELD_LOG"] = log
            subprocess.run([sys.executable, LOCK_BIN, "unlock", "--class", klass, "--reason",
                            "the gate blocked work it should not have, naming which and why"],
                           capture_output=True, text=True, env=env, cwd=d, timeout=60)
            check("seam: unlock({}) wrote a raw override row".format(klass),
                  os.path.isfile(log) and '"reason_class"' in open(log).read(),
                  open(log).read() if os.path.isfile(log) else "no log")
            subprocess.run([sys.executable, gy, "rollup", "--log", log, "--md", md,
                            "--date", "2026-09-09"], capture_output=True, text=True,
                           env=env, timeout=60)
            body = open(md).read() if os.path.isfile(md) else ""
            check("seam: real rollup records fp={} for --class {}".format(want_fp, klass),
                  "| 2026-09-09 | testlock | 0 | 0 | 1 | 0 | {} |".format(want_fp) in body,
                  body)


if __name__ == "__main__":
    main()
