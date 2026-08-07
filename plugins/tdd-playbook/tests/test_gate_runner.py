#!/usr/bin/env python3
"""Planted contracts for the shared full/affected gate plan and compact runner."""
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile


HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(PLUGIN))
BIN = os.path.join(PLUGIN, "bin")
MANIFEST = os.path.join(REPO, "gate-manifest.json")
SHELL_GATE = os.path.join(REPO, "scripts", "civerd_gate.sh")

_results = {"pass": 0, "fail": 0}


def check(name, condition, detail=""):
    if condition:
        _results["pass"] += 1
        print("  ok   - " + name)
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def _load(name):
    path = os.path.join(BIN, name + ".py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True,
                          capture_output=True, text=True)


def _repo():
    td = tempfile.TemporaryDirectory()
    root = td.name
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Gate Test")
    os.makedirs(os.path.join(root, "plugins", "tdd", "tests"))
    with open(os.path.join(root, "plugins", "tdd", "tests", "test_one.py"), "w") as fh:
        fh.write("print('1 passed, 0 failed')\n")
    with open(os.path.join(root, "source.py"), "w") as fh:
        fh.write("VALUE = 1\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "base")
    return td, root


def _manifest(roster_digest):
    return {
        "schema_version": 1,
        "suite_glob": "plugins/tdd/tests/test_*.py",
        "acknowledged_roster_sha256": roster_digest,
        "fixed_stages": [
            {"id": "fixed", "argv": ["python3", "fixed.py"]}
        ],
        "force_full": ["gate-manifest.json", "scripts/**"],
        "safe_rules": [
            {"patterns": ["source.py"], "suites": ["test_one"]}
        ]
    }


def test_full_plan_discovers_live_roster():
    gp = _load("gate_plan")
    manifest = gp.load_manifest(MANIFEST)
    plan = gp.full_plan(REPO, manifest)
    live = sorted(os.path.basename(p)[:-3] for p in
                  __import__("glob").glob(os.path.join(
                      REPO, "plugins", "tdd-playbook", "tests", "test_*.py")))
    planned = sorted(s.id for s in plan.stages if s.kind == "suite")
    fixed = [s.id for s in plan.stages if s.kind == "fixed"]
    check("full plan: live suite roster is exact", planned == live,
          {"planned": planned, "live": live})
    check("full plan: existing four fixed stages are declared once",
          fixed == ["calibration", "dataflow", "ledger", "plant-forms"], fixed)
    check("full plan: no-arg remains authorizing full mode",
          plan.mode == "full" and plan.authorizing is True, plan)


def test_affected_scope_includes_worktree_changes():
    gp = _load("gate_plan")
    td, root = _repo()
    try:
        manifest = _manifest(gp.roster_digest(["test_one"], ["fixed"]))
        with open(os.path.join(root, "source.py"), "a") as fh:
            fh.write("VALUE = 2\n")
        with open(os.path.join(root, "new.txt"), "w") as fh:
            fh.write("untracked\n")
        scope = gp.collect_changed_paths(root, "HEAD")
        check("affected scope: unstaged tracked path included",
              "source.py" in scope.paths, scope)
        check("affected scope: untracked path included",
              "new.txt" in scope.paths, scope)
        plan = gp.affected_plan(root, manifest, "HEAD")
        check("affected scope: unknown untracked path forces full",
              plan.mode == "full" and "unmapped" in " ".join(plan.reasons).lower(),
              plan.reasons)

        os.unlink(os.path.join(root, "new.txt"))
        _git(root, "add", "source.py")
        plan = gp.affected_plan(root, manifest, "HEAD")
        check("affected scope: staged mapped path narrows safely",
              plan.mode == "affected" and
              [s.id for s in plan.stages if s.kind == "suite"] == ["test_one"], plan)
        check("affected scope: narrowed result is non-authorizing",
              plan.authorizing is False, plan)
    finally:
        td.cleanup()


def test_affected_fail_full_matrix():
    gp = _load("gate_plan")
    td, root = _repo()
    try:
        manifest = _manifest(gp.roster_digest(["test_one"], ["fixed"]))
        missing = gp.affected_plan(root, manifest, "does-not-exist")
        check("affected: invalid base forces full", missing.mode == "full", missing)

        os.makedirs(os.path.join(root, "scripts"))
        with open(os.path.join(root, "scripts", "gate.py"), "w") as fh:
            fh.write("# gate surface\n")
        forced = gp.affected_plan(root, manifest, "HEAD")
        check("affected: dirty gate surface forces full",
              forced.mode == "full" and "gate surface" in " ".join(forced.reasons),
              forced.reasons)

        os.unlink(os.path.join(root, "scripts", "gate.py"))
        _git(root, "mv", "source.py", "renamed.py")
        renamed = gp.affected_plan(root, manifest, "HEAD")
        check("affected: rename with unmapped destination forces full",
              renamed.mode == "full" and
              {"source.py", "renamed.py"}.issubset(set(renamed.changed_paths)), renamed)
    finally:
        td.cleanup()


def test_roster_digest_refuses_silent_new_suite():
    gp = _load("gate_plan")
    td, root = _repo()
    try:
        manifest = _manifest(gp.roster_digest(["test_one"], ["fixed"]))
        gp.full_plan(root, manifest)
        with open(os.path.join(root, "plugins", "tdd", "tests", "test_two.py"), "w") as fh:
            fh.write("print('1 passed, 0 failed')\n")
        try:
            gp.full_plan(root, manifest)
        except gp.PlanError as exc:
            refused = "roster digest" in str(exc).lower()
        else:
            refused = False
        check("roster: a newly discovered suite invalidates acknowledgement", refused)
    finally:
        td.cleanup()


def test_private_run_store_redacts_and_separates_concurrent_runs():
    gr = _load("gate_runner")
    td, root = _repo()
    try:
        common = os.path.join(root, ".git")
        first = gr.RunStore(common, "run-a", keep=5)
        second = gr.RunStore(common, "run-b", keep=5)
        raw = "Authorization: Bearer secret-token\nAPI_KEY=sk-live-secret\n"
        first.write_stage("one", raw)
        second.write_stage("one", "clean\n")
        body = open(os.path.join(first.path, "one.log")).read()
        mode_dir = stat.S_IMODE(os.stat(first.path).st_mode)
        mode_file = stat.S_IMODE(os.stat(os.path.join(first.path, "one.log")).st_mode)
        check("run store: secret-like values are absent", "secret-token" not in body and
              "sk-live-secret" not in body, body)
        check("run store: concurrent run ids get distinct paths", first.path != second.path)
        check("run store: private permissions are enforced",
              mode_dir == 0o700 and mode_file == 0o600, (oct(mode_dir), oct(mode_file)))
        try:
            gr.RunStore(common, "../escape", keep=5)
        except ValueError:
            traversal_refused = True
        else:
            traversal_refused = False
        check("run store: PLANTED traversal-shaped run id is refused", traversal_refused)
    finally:
        td.cleanup()


def test_compact_runner_preserves_suite_directory_seam():
    with tempfile.TemporaryDirectory() as d:
        with open(os.path.join(d, "test_ok.py"), "w") as fh:
            fh.write("print('7 passed, 0 failed')\n")
        good = subprocess.run(["sh", SHELL_GATE, d], cwd=REPO,
                              capture_output=True, text=True, timeout=30)
        check("compact runner: planted suite-dir success remains reachable",
              good.returncode == 0 and "PASS test_ok" in good.stdout and
              len(good.stdout.splitlines()) <= 3, (good.returncode, good.stdout, good.stderr))
        with open(os.path.join(d, "test_bad.py"), "w") as fh:
            fh.write("import sys\nprint('FAIL - motivating failure')\n"
                     "print('token=top-secret')\n"
                     "[print('noise-%d' % i) for i in range(40)]\nsys.exit(1)\n")
        bad = subprocess.run(["sh", SHELL_GATE, d], cwd=REPO,
                             capture_output=True, text=True, timeout=30)
        check("compact runner: planted failure propagates with redacted detail",
              bad.returncode != 0 and "FAIL test_bad" in bad.stdout and
              "motivating failure" in bad.stdout and
              "top-secret" not in bad.stdout + bad.stderr,
              (bad.returncode, bad.stdout, bad.stderr))


def main():
    print("shared gate resolver/runner calibration")
    for fn in (test_full_plan_discovers_live_roster,
               test_affected_scope_includes_worktree_changes,
               test_affected_fail_full_matrix,
               test_roster_digest_refuses_silent_new_suite,
               test_private_run_store_redacts_and_separates_concurrent_runs,
               test_compact_runner_preserves_suite_directory_seam):
        try:
            fn()
        except Exception as exc:
            check(fn.__name__ + " executes", False, repr(exc))
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    assert not _results["fail"], "gate resolver/runner calibration failed"


if __name__ == "__main__":
    main()
