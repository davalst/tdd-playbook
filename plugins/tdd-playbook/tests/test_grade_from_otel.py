#!/usr/bin/env python3
"""Planted-input calibration for bin/grade_from_otel.py (the §13 telemetry seam).

Planted fixtures in BOTH accepted shapes (flat-attribute JSONL and OTLP/JSON) must yield
exact known counts; an empty/garbage export must exit 1 loudly (never a silent zero-grade —
"narration with a telemetry badge" is the failure mode). Self-contained, no pytest. Run:
    python3 tests/test_grade_from_otel.py
"""
import json
import os
import subprocess
import sys
import tempfile

BIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "bin", "grade_from_otel.py")
_r = {"pass": 0, "fail": 0}


def check(name, cond, detail=""):
    if cond:
        _r["pass"] += 1
        print("  ok   - " + name)
    else:
        _r["fail"] += 1
        print("  FAIL - {}  {}".format(name, detail))


def run(lines, *extra):
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False) as fh:
        fh.write("\n".join(lines) + "\n")
        path = fh.name
    try:
        p = subprocess.run([sys.executable, BIN, path, *extra],
                           capture_output=True, text=True, timeout=30)
        return p.returncode, p.stdout, p.stderr
    finally:
        os.unlink(path)


def flat(event, **attrs):
    return json.dumps({"event.name": event, "attributes": attrs})


def otlp(event, **attrs):
    kv = [{"key": "event.name", "value": {"stringValue": event}}]
    for k, v in attrs.items():
        val = {"intValue": str(v)} if isinstance(v, int) else {"stringValue": v}
        kv.append({"key": k, "value": val})
    return json.dumps({"resourceLogs": [{"scopeLogs": [{"logRecords": [{"attributes": kv}]}]}]})


def main():
    print("grade_from_otel calibration")

    # flat JSONL shape: known counts in -> exact numbers out
    lines = [
        flat("claude_code.api_request", input_tokens=1000, output_tokens=200,
             cache_read_tokens=600),
        flat("claude_code.api_request", input_tokens=500, output_tokens=100,
             cache_read_tokens=0),
        flat("claude_code.tool_result", tool_name="Read", file_path="/r/src/app.py"),
        flat("claude_code.tool_result", tool_name="Grep"),
        flat("claude_code.tool_result", tool_name="Bash"),
        flat("claude_code.tool_result", tool_name="Edit", file_path="/r/src/app.py"),
        flat("claude_code.tool_result", tool_name="Edit", file_path="/r/tests/test_app.py"),
        "not json at all",  # garbage line tolerated
    ]
    rc, out, _e = run(lines, "--json")
    check("flat shape parses (exit 0)", rc == 0, (rc, _e))
    m = json.loads(out) if rc == 0 else {}
    check("api requests counted", m.get("api_requests") == 2, m.get("api_requests"))
    check("tokens net of cache computed", m.get("input_tokens_net_of_cache") == 900,
          m.get("input_tokens_net_of_cache"))
    check("reads/searches/bash counted",
          (m.get("files_read"), m.get("searches"), m.get("bash")) == (1, 1, 1), m)
    check("test-vs-source split correct",
          m.get("test_files_touched") == ["/r/tests/test_app.py"]
          and m.get("source_files_touched") == ["/r/src/app.py"], m)

    # OTLP/JSON shape yields the same accounting
    rc, out, _e = run([
        otlp("claude_code.api_request", input_tokens=100, output_tokens=10,
             cache_read_tokens=40),
        otlp("claude_code.tool_result", tool_name="Read", file_path="/x/y.py"),
    ], "--json")
    m = json.loads(out) if rc == 0 else {}
    check("OTLP shape parses to same accounting",
          rc == 0 and m.get("api_requests") == 1 and m.get("files_read") == 1
          and m.get("input_tokens_net_of_cache") == 60, (rc, m))

    # human block prints the smell line when source moved without tests
    rc, out, _e = run([
        flat("claude_code.tool_result", tool_name="Edit", file_path="/r/src/only.py"),
    ])
    check("source-without-tests smell surfaced", rc == 0 and "NO test files" in out, out)

    # PLANTED: garbage/empty export must exit 1 loudly, never a silent zero-grade
    rc, _out, e = run(["{}", "not json", ""])
    check("no recognizable records -> exit 1 + narration-grade warning",
          rc == 1 and "narration-grade" in e, (rc, e))
    rc, _out, e = run([""])
    check("empty export -> exit 1", rc == 1, (rc, e))

    print("\n{} passed, {} failed".format(_r["pass"], _r["fail"]))
    sys.exit(1 if _r["fail"] else 0)


if __name__ == "__main__":
    main()
