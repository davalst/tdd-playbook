#!/usr/bin/env python3
"""grade_from_otel — the mechanical half of §13 ("grade from telemetry, never self-narration").

/grade's rules demand tool-log truth: files actually read, greps actually run, tokens net of
cache, turns, tests-added vs source-changed. Without a seam that EMITS those numbers, the
grade is narration with a colon in it. This is the seam: point it at a Claude Code
OpenTelemetry export (see docs/telemetry.md) and it computes the §13 metrics from the
records — /grade PASTES this output instead of estimating.

Accepted input (lenient by design — gen_ai.* conventions are still unstable, so we parse
attributes wherever they appear rather than hard-binding a schema):
  - JSONL where each line is a log/event record with an `attributes` dict or OTLP-style
    `attributes: [{key, value:{stringValue|intValue|...}}]` list;
  - full OTLP/JSON export bodies (resourceLogs -> scopeLogs -> logRecords).

Usage: grade_from_otel.py EXPORT.jsonl [--json]
Exit 0 with a summary block; exit 1 if no recognizable records (telemetry unavailable —
/grade must then SAY "narration-grade" instead of pretending).
"""
import argparse
import json
import os
import sys

TOOL_EVENT_NAMES = {"claude_code.tool_result", "claude_code.tool_decision", "tool_result",
                    "tool_decision"}
API_EVENT_NAMES = {"claude_code.api_request", "api_request"}
READ_TOOLS = {"Read"}
SEARCH_TOOLS = {"Grep", "Glob"}
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}


def _flatten_otlp_attrs(attrs):
    """OTLP [{key, value:{stringValue:...}}] -> plain dict."""
    out = {}
    for a in attrs:
        if not isinstance(a, dict) or "key" not in a:
            continue
        v = a.get("value")
        if isinstance(v, dict):
            for k in ("stringValue", "intValue", "doubleValue", "boolValue"):
                if k in v:
                    v = v[k]
                    break
        out[a["key"]] = v
    return out


def iter_records(obj):
    """Yield flat attribute dicts for every record found anywhere in obj."""
    stack = [obj]
    while stack:
        cur = stack.pop()
        if isinstance(cur, dict):
            attrs = cur.get("attributes")
            flat = None
            if isinstance(attrs, dict):
                flat = dict(attrs)
            elif isinstance(attrs, list):
                flat = _flatten_otlp_attrs(attrs)
            if flat is not None:
                # event name may live beside the attributes rather than inside them
                for k in ("event.name", "event_name", "name"):
                    if k not in flat and isinstance(cur.get(k), str):
                        flat[k] = cur[k]
                if isinstance(cur.get("body"), (str,)) and "event.name" not in flat:
                    flat.setdefault("event.name", cur["body"])
                yield flat
            stack.extend(cur.values())
        elif isinstance(cur, list):
            stack.extend(cur)


def _int(v):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return 0


def _event_name(rec):
    for k in ("event.name", "event_name", "name"):
        v = rec.get(k)
        if isinstance(v, str):
            return v
    return ""


def _is_test_path(path):
    p = (path or "").replace("\\", "/").lower()
    base = p.rsplit("/", 1)[-1]
    return ("/tests/" in p or "/test/" in p or "/__tests__/" in p or "/spec/" in p
            or base.startswith("test_") or ".test." in base or ".spec." in base
            or base.endswith("_test.py") or base.endswith("_test.go"))


def analyze(lines):
    m = {
        "records": 0, "api_requests": 0,
        "input_tokens": 0, "output_tokens": 0, "cache_read_tokens": 0,
        "files_read": 0, "searches": 0, "edits": 0, "bash": 0,
        "test_files_touched": set(), "source_files_touched": set(),
        "cost_usd": 0.0,
    }
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        for rec in iter_records(obj):
            name = _event_name(rec)
            tool = rec.get("tool_name") or rec.get("tool") or ""
            if name in API_EVENT_NAMES:
                m["records"] += 1
                m["api_requests"] += 1
                m["input_tokens"] += _int(rec.get("input_tokens"))
                m["output_tokens"] += _int(rec.get("output_tokens"))
                m["cache_read_tokens"] += _int(rec.get("cache_read_tokens"))
                try:
                    m["cost_usd"] += float(rec.get("cost_usd") or 0)
                except (TypeError, ValueError):
                    pass
            elif name in TOOL_EVENT_NAMES or tool:
                m["records"] += 1
                fp = rec.get("file_path") or ""
                if tool in READ_TOOLS:
                    m["files_read"] += 1
                elif tool in SEARCH_TOOLS:
                    m["searches"] += 1
                elif tool in EDIT_TOOLS:
                    m["edits"] += 1
                    if fp:
                        (m["test_files_touched"] if _is_test_path(fp)
                         else m["source_files_touched"]).add(fp)
                elif tool == "Bash":
                    m["bash"] += 1
    return m


def main(argv=None):
    ap = argparse.ArgumentParser(description="Compute §13 grade metrics from an OTel export.")
    ap.add_argument("export", help="OTel export file (JSONL or OTLP/JSON)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    args = ap.parse_args(argv)
    if not os.path.isfile(args.export):
        sys.stderr.write("grade_from_otel: no such file: {}\n".format(args.export))
        return 1
    with open(args.export, errors="replace") as fh:
        m = analyze(fh)
    if m["records"] == 0:
        sys.stderr.write(
            "grade_from_otel: no recognizable telemetry records — /grade must report "
            "'narration-grade (telemetry unavailable)' rather than estimating.\n")
        return 1
    net = m["input_tokens"] - m["cache_read_tokens"]
    tests_n, src_n = len(m["test_files_touched"]), len(m["source_files_touched"])
    if args.json:
        out = dict(m)
        out["test_files_touched"] = sorted(m["test_files_touched"])
        out["source_files_touched"] = sorted(m["source_files_touched"])
        out["input_tokens_net_of_cache"] = net
        print(json.dumps(out, indent=2))
        return 0
    print("GRADE TELEMETRY (mechanical — the seam emits the count)")
    print("  api requests (≈turns): {}".format(m["api_requests"]))
    print("  tokens: in {} · out {} · cache-read {} · in NET of cache {}".format(
        m["input_tokens"], m["output_tokens"], m["cache_read_tokens"], net))
    if m["cost_usd"]:
        print("  cost: ${:.4f}".format(m["cost_usd"]))
    print("  evidence gathering: {} file reads · {} greps/globs · {} bash".format(
        m["files_read"], m["searches"], m["bash"]))
    print("  edits: {} tool calls · {} test file(s) vs {} source file(s) touched".format(
        m["edits"], tests_n, src_n))
    if src_n and not tests_n:
        print("  ⚠ source touched with NO test files — §1/§6 smell, grade accordingly")
    return 0


if __name__ == "__main__":
    sys.exit(main())
