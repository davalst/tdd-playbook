#!/usr/bin/env python3
"""Planted calibration-runner contract for Claude and Codex host isolation."""
import importlib
import os
import stat
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
CALIBRATION = os.path.join(REPO, "calibration")
sys.path.insert(0, CALIBRATION)

_results = {"pass": 0, "fail": 0}


def check(name, condition, detail=""):
    if condition:
        _results["pass"] += 1
        print("  ok   - " + name)
    else:
        _results["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def _stub(root):
    path = os.path.join(root, "host-stub")
    with open(path, "w") as fh:
        fh.write("#!/bin/sh\n"
                 "if [ \"${1:-}\" = --version ]; then echo 'host-stub 9.8.7'; exit 0; fi\n"
                 "printf '%s\\n' \"$@\" > \"$HOST_ARGS_DUMP\"\n"
                 "if [ \"${1:-}\" = exec ]; then\n"
                 "  printf '%s\\n' '{\"type\":\"thread.started\",\"thread_id\":\"thr-1\"}'\n"
                 "  printf '%s\\n' '{\"type\":\"item.completed\",\"item\":{\"type\":\"agent_message\",\"text\":\"Codex verdict line\"}}'\n"
                 "else\n"
                 "  echo 'Claude verdict line'\n"
                 "fi\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
    return path


def test_runner_invocations():
    runner = importlib.import_module("host_runner")
    with tempfile.TemporaryDirectory() as d:
        binary = _stub(d)
        dump = os.path.join(d, "args.txt")
        env = dict(os.environ)
        env["HOST_ARGS_DUMP"] = dump
        claude = runner.invoke("claude", binary, "PROMPT", "model-c", d,
                               max_turns="7", timeout=30, env=env)
        claude_args = open(dump).read().splitlines()
        check("runner: Claude invocation remains backward-compatible",
              claude.status == "ok" and claude.output.strip() == "Claude verdict line"
              and claude_args == ["-p", "PROMPT", "--model", "model-c", "--max-turns", "7"],
              (claude, claude_args))

        codex = runner.invoke("codex", binary, "PROMPT", "model-x", d,
                              max_turns="7", timeout=30, env=env)
        codex_args = open(dump).read().splitlines()
        check("runner: Codex invocation normalizes prompt/model/cwd and JSONL output",
              codex.status == "ok" and codex.output == "Codex verdict line"
              and codex.transcript_id == "thr-1" and codex_args[0] == "exec"
              and "--json" in codex_args and "model-x" in codex_args
              and codex_args[-1] == "PROMPT", (codex, codex_args))
        check("runner: host identities and histories stay separate",
              runner.model_identity("claude", "same") == "same"
              and runner.model_identity("codex", "same") == "codex:same"
              and runner.default_history("claude").endswith("history.md")
              and runner.default_history("codex").endswith("history-codex.md"))
        check("runner: capability probe records the actual binary version",
              runner.probe_version(binary, timeout=30) == "host-stub 9.8.7")


def test_runner_failures_are_typed():
    runner = importlib.import_module("host_runner")
    with tempfile.TemporaryDirectory() as d:
        path = os.path.join(d, "refusal")
        with open(path, "w") as fh:
            fh.write("#!/bin/sh\necho 'refused' >&2\nexit 23\n")
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        result = runner.invoke("claude", path, "P", "M", d, timeout=30,
                               env=dict(os.environ))
        check("runner: non-execution is typed at the subprocess seam",
              result.status == "env_failure" and result.returncode == 23
              and "refused" in result.output, result)
        try:
            runner.invoke("unknown", path, "P", "M", d, timeout=30,
                          env=dict(os.environ))
        except runner.RunnerError:
            refused = True
        else:
            refused = False
        check("runner: unknown hosts fail closed", refused)


def main():
    print("portable calibration host-runner calibration")
    for fn in (test_runner_invocations, test_runner_failures_are_typed):
        try:
            fn()
        except Exception as exc:
            check(fn.__name__ + " executes", False, repr(exc))
    print("\n{} passed, {} failed".format(_results["pass"], _results["fail"]))
    assert not _results["fail"], "host runner calibration failed"


if __name__ == "__main__":
    main()
