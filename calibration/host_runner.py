#!/usr/bin/env python3
"""Host invocation seam for live verifier and plant-author calibration.

The runner normalizes process lifecycle and model-visible output only.  It does not pretend
Claude and Codex have the same CLI or transcript format, and it never merges their history
files or score denominators.
"""
from __future__ import annotations

import dataclasses
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)


class RunnerError(ValueError):
    pass


@dataclasses.dataclass(frozen=True)
class Result:
    host: str
    status: str
    output: str
    returncode: int | None
    transcript_id: str | None = None


def model_identity(host, model):
    if host == "claude":
        return model
    if host == "codex":
        return "codex:" + model
    raise RunnerError("unknown host: {}".format(host))


def default_history(host):
    if host == "claude":
        name = "history.md"
    elif host == "codex":
        name = "history-codex.md"
    else:
        raise RunnerError("unknown host: {}".format(host))
    return os.path.join(REPO, "docs", "calibration", name)


def command_for(host, binary, prompt, model, max_turns=None, extra_args=None, settings=None):
    extra = list(extra_args or [])
    if host == "claude":
        command = [binary, "-p", prompt, "--model", model]
        if max_turns is not None:
            command += ["--max-turns", str(max_turns)]
        if settings:  # B1: a settings file that disables the tdd-playbook plugin (no-playbook run)
            command += ["--settings", settings]
        return command + extra
    if host == "codex":
        # JSONL is a stable machine-facing stream; `--ephemeral` prevents calibration turns
        # entering the operator's history.  Host-specific sandbox/trust flags may be supplied
        # through the existing TDD_PLAYBOOK_CALIBRATION_ARGS escape hatch.
        if settings:
            raise RunnerError(
                "no-playbook isolation is not applicable on the codex host — there is no "
                "--settings plugin-disable analog; record not-applicable, never a fabricated "
                "isolated number")
        return ([binary, "exec", "--json", "--ephemeral", "--ignore-rules",
                 "-m", model] + extra + [prompt])
    raise RunnerError("unknown host: {}".format(host))


def _codex_output(stdout):
    messages = []
    transcript_id = None
    for line in (stdout or "").splitlines():
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("type") == "thread.started":
            transcript_id = row.get("thread_id")
        item = row.get("item") if row.get("type") == "item.completed" else None
        if isinstance(item, dict) and item.get("type") == "agent_message" \
                and isinstance(item.get("text"), str):
            messages.append(item["text"])
    return ("\n".join(messages) if messages else (stdout or "")), transcript_id


def _maybe_confine(command, cwd, deny_read):
    """Wrap the agent command in OS confinement when `deny_read` is set (a holdout run — the
    answer-key dir must be unreadable to the untrusted agent). FAIL-CLOSED: if confinement is
    unavailable we RAISE rather than run the agent unconfined with the answer key on disk.
    `deny_read` empty/None → the command is unchanged (normal dev run)."""
    if not deny_read:
        return command
    import confine
    if not confine.sandbox_exec_available():
        raise RunnerError(
            "holdout run requires OS confinement (sandbox-exec) but it is unavailable on this "
            "host — refusing to run the agent unconfined with holdout bodies on disk")
    return confine.confined_argv(command, cwd, deny_read=deny_read)


def invoke(host, binary, prompt, model, cwd, max_turns=None, timeout=600, env=None,
           extra_args=None, confine_deny_read=None, settings=None):
    command = _maybe_confine(
        command_for(host, binary, prompt, model, max_turns, extra_args, settings=settings),
        cwd, confine_deny_read)
    try:
        process = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                                 timeout=timeout, env=env)
    except subprocess.TimeoutExpired:
        return Result(host, "timeout", "[TIMEOUT after {}s]".format(timeout), None)
    if host == "codex":
        output, transcript_id = _codex_output(process.stdout)
    else:
        output, transcript_id = process.stdout or "", None
    if process.returncode != 0 and not (process.stdout or "").strip():
        return Result(host, "env_failure",
                      "[env failure rc={}]\n{}".format(
                          process.returncode, (process.stderr or "")[-800:]),
                      process.returncode, transcript_id)
    if process.returncode != 0 and process.stderr:
        output += "\n[stderr]\n" + process.stderr
    return Result(host, "ok", output, process.returncode, transcript_id)


def probe_version(binary, timeout=15):
    try:
        process = subprocess.run([binary, "--version"], capture_output=True, text=True,
                                 timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return None
    value = (process.stdout or process.stderr or "").strip().splitlines()
    return value[0] if process.returncode == 0 and value else None
