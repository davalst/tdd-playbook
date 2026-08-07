#!/usr/bin/env python3
"""Planted checks for advisory host evidence and `tdd doctor` assurance reporting."""
import importlib
import json
import os
import subprocess
import sys
import tempfile

PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN = os.path.join(PLUGIN, "bin")
DOCTOR = os.path.join(BIN, "tdd.py")
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
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                          text=True, timeout=30)


def _repo(base):
    root = os.path.join(base, "repo")
    os.makedirs(root)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Doctor Test")
    with open(os.path.join(root, "app.py"), "w") as fh:
        fh.write("x = 1\n")
    _git(root, "add", "app.py")
    _git(root, "commit", "-qm", "fixture")
    return root


def test_local_evidence_schema():
    core = importlib.import_module("host_contract")
    with tempfile.TemporaryDirectory() as d:
        identity = core.resolve_repository(_repo(d))
        event = core.new_local_evidence_event(
            identity, host="claude", host_version="1.2.3", adapter_version="1.31.0",
            run_id="probe-1", event="capability_probe", decision="block",
            assurance="host_prevented", scope="structured_edit",
            details={"capability": "test-lock", "route": "structured_edit",
                     "outcome": "blocked", "redactions": 0},
            now="2026-08-07T12:00:00+00:00")
        required = {"schema_version", "host", "host_version", "adapter_version", "repo_id",
                    "worktree_id", "sha", "ts", "run_id", "event", "decision",
                    "assurance", "scope", "details", "trust"}
        check("evidence: normalized event carries every contract field",
              set(event) == required and event["trust"] == "local_unverified", event)
        check("evidence: exact SHA and worktree identity bind the observation",
              event["sha"] == identity["head"]
              and event["worktree_id"] == identity["worktree_id"], event)
        try:
            core.new_local_evidence_event(
                identity, host="claude", host_version="1", adapter_version="1",
                run_id="bad", event="capability_probe", decision="block",
                assurance="civerd_signed", scope="shell", details={},
                now="2026-08-07T12:00:00+00:00")
        except core.ContractError:
            forged = True
        else:
            forged = False
        check("evidence: local writer cannot forge CIVerd-signed assurance", forged)
        try:
            core.new_local_evidence_event(
                identity, host="claude", host_version="1", adapter_version="1",
                run_id="secret", event="capability_probe", decision="block",
                assurance="host_prevented", scope="shell",
                details={"command": "TOKEN=secret pytest"},
                now="2026-08-07T12:00:00+00:00")
        except core.ContractError:
            secret_refused = True
        else:
            secret_refused = False
        check("evidence: raw command/prompt fields are refused by the allowlist", secret_refused)


def _doctor(root, *args, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([sys.executable, DOCTOR, "doctor", "--json", *args], cwd=root,
                          env=env, capture_output=True, text=True, timeout=30)


def test_doctor_assurance():
    core = importlib.import_module("host_contract")
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        empty = _doctor(root, "--as-of", "2026-08-07")
        report = json.loads(empty.stdout) if empty.returncode == 0 else {}
        claude = (report.get("hosts") or {}).get("claude", {})
        check("doctor: declared capability without a live probe is unmeasured",
              claude.get("capabilities", {}).get("test-lock", {}).get("assurance")
              == "unmeasured", (empty.returncode, empty.stderr, report))

        identity = core.resolve_repository(root)
        event = core.new_local_evidence_event(
            identity, host="claude", host_version="1.2.3", adapter_version="1.30.0",
            run_id="probe-live", event="capability_probe", decision="block",
            assurance="host_prevented", scope="structured_edit",
            details={"capability": "test-lock", "route": "structured_edit",
                     "outcome": "blocked", "redactions": 0},
            now="2026-08-07T10:00:00+00:00")
        core.append_event(identity, event)
        measured = _doctor(root, "--as-of", "2026-08-07")
        measured_report = json.loads(measured.stdout) if measured.returncode == 0 else {}
        value = measured_report["hosts"]["claude"]["capabilities"]["test-lock"]
        check("doctor: observed route reports measured local assurance",
              value["assurance"] == "host_prevented"
              and value["trust"] == "local_unverified", value)

        stale = _doctor(root, "--as-of", "2026-09-01")
        stale_report = json.loads(stale.stdout) if stale.returncode == 0 else {}
        stale_value = stale_report["hosts"]["claude"]["capabilities"]["test-lock"]
        check("doctor: stale probe decays back to unmeasured",
              stale_value["assurance"] == "unmeasured" and stale_value["stale"] is True,
              stale_value)


def test_doctor_invalid_state_fails_closed():
    core = importlib.import_module("host_contract")
    with tempfile.TemporaryDirectory() as d:
        root = _repo(d)
        identity = core.resolve_repository(root)
        os.makedirs(identity["state_dir"])
        with open(core.lock_path(identity), "w") as fh:
            fh.write("not-json\n")
        result = _doctor(root, "--as-of", "2026-08-07")
        check("doctor: planted malformed canonical lock exits nonzero and names state",
              result.returncode == 1 and "canonical lock" in result.stderr.lower(),
              (result.returncode, result.stdout, result.stderr))


def main():
    print("host doctor/evidence calibration")
    for fn in (test_local_evidence_schema, test_doctor_assurance,
               test_doctor_invalid_state_fails_closed):
        try:
            fn()
        except Exception as exc:
            check(fn.__name__ + " executes", False, repr(exc))
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    assert not _results["fail"], "host doctor/evidence calibration failed"


if __name__ == "__main__":
    main()
