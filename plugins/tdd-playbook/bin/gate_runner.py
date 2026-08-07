#!/usr/bin/env python3
"""Compact executor for the single gate plan; local records never authorize release."""
from __future__ import annotations

import hashlib
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gate_plan  # noqa: E402


PLUGIN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(os.path.dirname(PLUGIN))
MANIFEST = os.path.join(REPO, "gate-manifest.json")
MAX_LOG_BYTES = 64 * 1024
TAIL_LINES = 20

_SECRET_PATTERNS = (
    re.compile(r"(?i)(authorization\s*:\s*(?:bearer|basic)\s+)[^\s]+"),
    re.compile(r"(?i)((?:api[_-]?key|token|secret|password)\s*[:=]\s*)[^\s]+"),
    re.compile(r"\b(?:sk|gh[opusr])-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
)


def redact(value: str) -> str:
    out = value
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub(lambda m: (m.group(1) if m.lastindex else "") + "<redacted>", out)
    return out


def _sanitized_diagnostic(raw: str) -> str:
    """Persist derived counts only; arbitrary subprocess text never reaches disk."""
    lines = raw.splitlines()
    summary = {
        "lines": len(lines),
        "pass_signals": sum(1 for line in lines if line.startswith("PASS")),
        "fail_signals": sum(1 for line in lines if line.startswith("FAIL")),
        "error_signals": sum(1 for line in lines if line.startswith(("ERROR", "Traceback"))),
    }
    return json.dumps(summary, sort_keys=True)


def _atomic_private(path: str, text: str) -> None:
    tmp = "{}.tmp-{}".format(path, uuid.uuid4().hex)
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


class RunStore:
    def __init__(self, common_dir: str, run_id: str, keep: int = 20):
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,80}", run_id) or run_id in (".", ".."):
            raise ValueError("run id must be a single safe path component")
        self.root = os.path.join(os.path.realpath(common_dir), "tdd-playbook", "gate-runs")
        os.makedirs(self.root, mode=0o700, exist_ok=True)
        os.chmod(self.root, 0o700)
        self.path = os.path.join(self.root, run_id)
        os.mkdir(self.path, 0o700)
        self.keep = max(1, int(keep))

    def write_stage(self, stage_id: str, raw: str) -> dict:
        safe_id = re.sub(r"[^A-Za-z0-9_.-]", "_", stage_id)
        encoded = raw.encode("utf-8", "replace")
        body = ("captured_output_sha256={}\nraw_bytes={}\n"
                "diagnostic_excerpt_begin\n{}\n"
                "diagnostic_excerpt_end\n").format(
                    hashlib.sha256(encoded).hexdigest(), len(encoded),
                    _sanitized_diagnostic(raw))
        path = os.path.join(self.path, safe_id + ".log")
        _atomic_private(path, body)
        return {"log": os.path.basename(path), "raw_bytes": len(encoded),
                "stored_bytes": len(body.encode("utf-8")),
                "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()}

    def finalize(self, metadata: dict) -> None:
        allowed = {key: metadata[key] for key in (
            "schema_version", "run_id", "mode", "authorizing", "commit", "dirty",
            "selected", "total", "started_at", "duration_ms", "result", "stages"
        ) if key in metadata}
        _atomic_private(os.path.join(self.path, "index.json"),
                        json.dumps(allowed, sort_keys=True, indent=2) + "\n")
        self.prune()

    def prune(self) -> None:
        lock_path = os.path.join(self.root, ".prune.lock")
        fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(fd, "r+") as lock:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            entries = []
            for name in os.listdir(self.root):
                path = os.path.join(self.root, name)
                if (path != self.path and os.path.isdir(path) and
                        not os.path.islink(path) and
                        os.path.isfile(os.path.join(path, "index.json"))):
                    entries.append((os.stat(path).st_mtime_ns, path))
            remove_count = max(0, len(entries) + 1 - self.keep)
            for _mtime, path in sorted(entries)[:remove_count]:
                if os.path.realpath(path).startswith(os.path.realpath(self.root) + os.sep):
                    shutil.rmtree(path)


def _git_text(*args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=REPO, capture_output=True, text=True, timeout=30)
    return proc.stdout.strip() if proc.returncode == 0 else "unavailable"


def _common_dir() -> str:
    value = _git_text("rev-parse", "--git-common-dir")
    if value == "unavailable":
        raise RuntimeError("not a Git checkout")
    return value if os.path.isabs(value) else os.path.realpath(os.path.join(REPO, value))


def _ledger_base() -> str:
    tag = _git_text("describe", "--tags", "--abbrev=0")
    if tag != "unavailable":
        return tag
    ledger = os.path.join(REPO, "docs", "calibration", "ledger.md")
    if os.path.isfile(ledger):
        match = re.search(r"^EPOCH:\s*([0-9a-f]{7,40})", open(ledger).read(), re.MULTILINE)
        if match:
            return match.group(1)
    raise gate_plan.PlanError("no ledger baseline (no tag and no EPOCH in ledger.md)")


def _resolved_argv(stage: gate_plan.Stage) -> list[str]:
    return [_ledger_base() if item == "{ledger_base}" else item for item in stage.argv]


def _count_label(output: str) -> str:
    matches = re.findall(r"(?m)^(\d+) passed, (\d+) failed\s*$", output)
    if matches:
        passed, failed = matches[-1]
        return "{} checks".format(int(passed) + int(failed))
    match = re.search(r"(?m)^ALL (\d+) checks passed", output)
    if match:
        return "{} checks".format(match.group(1))
    match = re.search(r"(?m)^Result:\s*(\d+)/(\d+) passed\s*$", output)
    if match:
        return "{} checks".format(match.group(2))
    return "checks reported in log"


def _tail(output: str) -> str:
    lines = redact(output).splitlines()
    return "\n".join(lines[-TAIL_LINES:])


def _failure_diagnostics(output: str) -> str:
    lines = redact(output).splitlines()
    signals = [line for line in lines
               if re.search(r"(?:^|\s)(?:FAIL|ERROR|AssertionError|Traceback)(?:\s|:|-|$)", line)]
    tail = lines[-TAIL_LINES:]
    combined = []
    for line in signals[:50] + tail:
        if line not in combined:
            combined.append(line)
    return "\n".join(combined)


def _run(plan: gate_plan.Plan) -> int:
    run_id = uuid.uuid4().hex
    started = time.time()
    try:
        store = RunStore(_common_dir(), run_id)
    except Exception as exc:
        store = None
        print("gate telemetry: unavailable ({}) — enforcement continues".format(exc),
              file=sys.stderr)
    rows = []
    failed = None
    for stage in plan.stages:
        before = time.monotonic()
        try:
            proc = subprocess.run(_resolved_argv(stage), cwd=REPO, capture_output=True,
                                  text=True, errors="replace", timeout=600)
            raw = proc.stdout + proc.stderr
            rc = proc.returncode
        except subprocess.TimeoutExpired as exc:
            raw = (exc.stdout or "") + (exc.stderr or "") + "\nTIMEOUT after 600s\n"
            rc = 124
        duration_ms = int((time.monotonic() - before) * 1000)
        log_meta = {}
        if store:
            try:
                log_meta = store.write_stage(stage.id, raw)
            except Exception as exc:
                print("gate telemetry: stage log unavailable for {} ({})".format(stage.id, exc),
                      file=sys.stderr)
        row = {"id": stage.id, "kind": stage.kind, "exit": rc,
               "duration_ms": duration_ms, **log_meta}
        rows.append(row)
        pointer = (os.path.join(store.path, log_meta["log"])
                   if store and log_meta.get("log") else "log unavailable")
        if rc == 0:
            print("PASS {} — {} — {:.2f}s — {}".format(
                stage.id, _count_label(raw), duration_ms / 1000.0, pointer))
        else:
            print("FAIL {} — exit {} — {:.2f}s — {}".format(
                stage.id, rc, duration_ms / 1000.0, pointer))
            diagnostics = _failure_diagnostics(raw)
            if diagnostics:
                print(diagnostics)
            failed = stage.id
            break
    result = "RED" if failed else "GREEN"
    metadata = {
        "schema_version": 1, "run_id": run_id, "mode": plan.mode,
        "authorizing": plan.authorizing, "commit": _git_text("rev-parse", "HEAD"),
        "dirty": bool(_git_text("status", "--porcelain")),
        "selected": len(plan.stages), "total": plan.total_stages,
        "started_at": int(started), "duration_ms": int((time.time() - started) * 1000),
        "result": result, "stages": rows,
    }
    if store:
        try:
            store.finalize(metadata)
        except Exception as exc:
            print("gate telemetry: index unavailable ({})".format(exc), file=sys.stderr)
    scope = "AUTHORIZING" if plan.authorizing else "NON-AUTHORIZING"
    telemetry = store.path if store else "unavailable"
    if failed:
        print("civerd_gate: RED — {} — selected {} of {} stages — failed {}".format(
            scope, len(plan.stages), plan.total_stages, failed) + " — telemetry=" + telemetry)
        return 1
    print("civerd_gate: GREEN — {} — selected {} of {} stages — {}".format(
        scope, len(plan.stages), plan.total_stages, "; ".join(plan.reasons)) +
          " — telemetry=" + telemetry)
    return 0


def _plan_json(plan: gate_plan.Plan) -> str:
    return json.dumps({"mode": plan.mode, "authorizing": plan.authorizing,
                       "selected": len(plan.stages), "total": plan.total_stages,
                       "stages": [s.id for s in plan.stages],
                       "reasons": list(plan.reasons),
                       "changed_paths": list(plan.changed_paths)}, sort_keys=True)


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        if argv and os.path.isdir(argv[0]):
            if len(argv) != 1:
                raise gate_plan.PlanError("suite-directory mode accepts exactly one argument")
            plan = gate_plan.suite_directory_plan(argv[0])
        else:
            manifest = gate_plan.load_manifest(MANIFEST)
            if not argv:
                plan = gate_plan.full_plan(REPO, manifest)
            elif argv[0] == "affected":
                base = None
                plan_only = False
                i = 1
                while i < len(argv):
                    if argv[i] == "--base" and i + 1 < len(argv):
                        base = argv[i + 1]
                        i += 2
                    elif argv[i] == "--plan-only":
                        plan_only = True
                        i += 1
                    else:
                        raise gate_plan.PlanError("unknown affected argument {!r}".format(argv[i]))
                if not base:
                    raise gate_plan.PlanError("affected requires --base <revision>")
                plan = gate_plan.affected_plan(REPO, manifest, base)
                if plan_only:
                    print(_plan_json(plan))
                    return 0
            else:
                raise gate_plan.PlanError("usage: civerd_gate.sh [affected --base REV [--plan-only] | suite_dir]")
    except (OSError, ValueError, gate_plan.PlanError) as exc:
        print("civerd_gate: REFUSED — {}".format(exc), file=sys.stderr)
        return 2
    return _run(plan)


if __name__ == "__main__":
    raise SystemExit(main())
