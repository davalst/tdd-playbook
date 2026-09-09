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
    manifest = {
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
    material = {key: value for key, value in manifest.items()
                if key not in ("acknowledged_roster_sha256", "acknowledged_plan_sha256")}
    import hashlib
    manifest["acknowledged_plan_sha256"] = hashlib.sha256(
        json.dumps(material, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return manifest


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


def test_execution_manifest_digest_refuses_command_substitution():
    gp = _load("gate_plan")
    td, root = _repo()
    try:
        manifest = _manifest(gp.roster_digest(["test_one"], ["fixed"]))
        gp.full_plan(root, manifest)
        manifest["fixed_stages"][0]["argv"] = ["python3", "-c", "pass"]
        try:
            gp.full_plan(root, manifest)
        except gp.PlanError as exc:
            refused = "execution manifest digest" in str(exc).lower()
        else:
            refused = False
        check("manifest: PLANTED fixed-command substitution invalidates acknowledgement", refused)
    finally:
        td.cleanup()


def test_private_run_store_redacts_and_separates_concurrent_runs():
    gr = _load("gate_runner")
    td, root = _repo()
    try:
        common = os.path.join(root, ".git")
        first = gr.RunStore(common, "run-a", keep=5)
        second = gr.RunStore(common, "run-b", keep=5)
        raw = ("Authorization: Bearer secret-token\nAPI_KEY=sk-live-secret\n"
               "Authorization: Basic dXNlcjpzZWNyZXQ=\n"
               "ghp_abcdefghijklmnopqrstuvwxyz123456\n"
               "github_pat_abcdefghijklmnopqrstuvwxyz123456\n"
               "https://example.invalid/?token=url-secret-value\n"
               "FAIL url https://alice:really-secret@example.invalid/a\n")
        first.write_stage("one", raw)
        second.write_stage("one", "clean\n")
        body = open(os.path.join(first.path, "one.log")).read()
        mode_dir = stat.S_IMODE(os.stat(first.path).st_mode)
        mode_file = stat.S_IMODE(os.stat(os.path.join(first.path, "one.log")).st_mode)
        check("run store: secret-like values are absent", "secret-token" not in body and
              "sk-live-secret" not in body and "dXNlcjpzZWNyZXQ=" not in body and
              "ghp_" not in body and "github_pat_" not in body and
              "url-secret-value" not in body and "really-secret" not in body, body)
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


def test_retention_never_prunes_an_active_concurrent_run():
    gr = _load("gate_runner")
    td, root = _repo()
    try:
        common = os.path.join(root, ".git")
        first = gr.RunStore(common, "run-a", keep=1)
        second = gr.RunStore(common, "run-b", keep=1)
        first.write_stage("one", "PASS one\n")
        first.finalize({"schema_version": 1, "run_id": "run-a", "result": "GREEN"})
        check("retention: finalized run never deletes a concurrent active directory",
              os.path.isdir(second.path), second.path)
    finally:
        td.cleanup()


def test_compact_count_parser_supports_repository_result_form():
    gr = _load("gate_runner")
    check("reporter: Result N/N retains a denominator",
          gr._count_label("Result: 15/16 passed\n") == "16 checks")


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
                     "print('FAIL https://alice:console-secret@example.invalid/a')\n"
                     "print('token=top-secret')\n"
                     "[print('noise-%d' % i) for i in range(40)]\nsys.exit(1)\n")
        bad = subprocess.run(["sh", SHELL_GATE, d], cwd=REPO,
                             capture_output=True, text=True, timeout=30)
        check("compact runner: planted failure propagates with redacted detail",
              bad.returncode != 0 and "FAIL test_bad" in bad.stdout and
              "failure_signals=" in bad.stdout and
              "motivating failure" not in bad.stdout and
              "top-secret" not in bad.stdout + bad.stderr and
              "console-secret" not in bad.stdout + bad.stderr,
              (bad.returncode, bad.stdout, bad.stderr))


def test_failure_digest_names_the_failed_checks():
    """A gate that is red once and cannot say why (2026-09-09, run 18d8943b: test_hooks exit 1,
    373 lines, digest fail_signals=0). Two defects, both verified in source: the digest counted
    only lines STARTING with FAIL while every plugin suite prints '  FAIL - <name>' indented; and
    the redacted tail helper existed and was never emitted anywhere, so on failure the operator
    saw a hash. The fix persists and prints the failure-marked lines ONLY - redacted, bounded -
    which is what the existing store test already planted ('FAIL url ...really-secret...')."""
    gr = _load("gate_runner")
    raw = ("suite header\n  ok   - a check that passed\n"
           "  FAIL - capture: sha present in event  (None, None)\n"
           "  ok   - another\nFAIL unindented form\n"
           "  FAIL - token leak  Authorization: Bearer secret-token-value\n"
           "309 passed, 3 failed\n")
    digest = json.loads(gr._sanitized_diagnostic(raw))
    check("digest: counts INDENTED '  FAIL - ' markers (planted: 2 indented + 1 unindented)",
          digest["fail_signals"] == 3, digest)
    check("digest: counts indented '  ok   - ' as pass signals", digest["pass_signals"] == 2, digest)
    check("digest: persists the failed check NAMES",
          any("capture: sha present in event" in ln for ln in digest.get("failed_lines", [])), digest)
    check("digest: a failed line is REDACTED before it is persisted",
          all("secret-token-value" not in ln for ln in digest.get("failed_lines", []))
          and any("<redacted>" in ln for ln in digest.get("failed_lines", [])), digest)
    check("digest: non-failure lines never reach the digest",
          not any("a check that passed" in ln or "suite header" in ln
                  for ln in digest.get("failed_lines", [])), digest)
    # bounded: a pathological suite cannot turn the store into a transcript
    flood = "".join("  FAIL - c{}  {}\n".format(i, "x" * 5000) for i in range(500))
    big = json.loads(gr._sanitized_diagnostic(flood))
    check("digest: failed_lines are CAPPED in count", len(big.get("failed_lines", [])) <= gr.FAILED_LINES_MAX,
          len(big.get("failed_lines", [])))
    check("digest: each persisted line is TRUNCATED",
          all(len(ln) <= gr.FAILED_LINE_CHARS for ln in big.get("failed_lines", [])),
          max((len(ln) for ln in big.get("failed_lines", [])), default=0))
    check("digest: the cap is recorded so a reader knows lines were dropped",
          big.get("failed_lines_total") == 500, big.get("failed_lines_total"))
    # the console path: the operator must see the names at failure time, not a hash alone
    text = gr._failure_diagnostics(raw)
    check("console: failure diagnostics NAME the failed checks",
          "capture: sha present in event" in text and "secret-token-value" not in text, text)
    # the store: the same bounded, redacted lines land in the private log
    td, root = _repo()
    try:
        store = gr.RunStore(os.path.join(root, ".git"), "run-x", keep=5)
        store.write_stage("s", raw)
        body = open(os.path.join(store.path, "s.log")).read()
        check("store: the failed check name is readable after the run",
              "capture: sha present in event" in body and "secret-token-value" not in body, body)
    finally:
        td.cleanup()


def main():
    print("shared gate resolver/runner calibration")
    for fn in (test_full_plan_discovers_live_roster,
               test_affected_scope_includes_worktree_changes,
               test_affected_fail_full_matrix,
               test_roster_digest_refuses_silent_new_suite,
               test_execution_manifest_digest_refuses_command_substitution,
               test_private_run_store_redacts_and_separates_concurrent_runs,
               test_retention_never_prunes_an_active_concurrent_run,
               test_compact_count_parser_supports_repository_result_form,
               test_compact_runner_preserves_suite_directory_seam,
               test_failure_digest_names_the_failed_checks):
        try:
            fn()
        except Exception as exc:
            check(fn.__name__ + " executes", False, repr(exc))
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    assert not _results["fail"], "gate resolver/runner calibration failed"


if __name__ == "__main__":
    main()
