# Telemetry recipe — making /grade mechanical

§13 says "grade from telemetry, never self-narration." Claude Code exports OpenTelemetry
natively; this recipe captures it to a local file and feeds it to
`bin/grade_from_otel.py`, so `/grade` pastes measured numbers instead of estimating.

## Quick local capture (console exporter → file)

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_LOGS_EXPORTER=console
export OTEL_METRICS_EXPORTER=console
claude >>~/.claude/otel-session.log        # console exporter writes to STDOUT, not stderr
```

**The console exporter is for eyeballing, NOT for `grade_from_otel.py`.** Verified 2026-08-17
on Claude Code 2.1.234: it emits pretty-printed, multi-line JS-object notation with UNQUOTED
keys (`tool_name: "Read"`), which is not JSON and not JSONL. Pointed at such a file the parser
recognises nothing and exits 1 with "telemetry unavailable" — correct behaviour (it fails
closed rather than inventing a zero-grade), but it means the quick path never fed the grader.
Two claims in this recipe were wrong until that capture was actually run: the stream, and the
implied machine-readability. Use the OTLP path below for anything mechanical.

**Event and attribute names, VERIFIED against real captures** (2026-08-17, Claude Code
2.1.234) rather than assumed from the semantic conventions:

| Fact | Event | Attribute |
|---|---|---|
| a tool was invoked | `claude_code.tool_decision` | `tool_name`, `decision` |
| a tool returned | `claude_code.tool_result` | `tool_name`, `success` |
| **a subagent was dispatched** | `claude_code.tool_decision` | **`tool_name: "Agent"`** |

Two traps that cost nothing to avoid and everything to discover late:
- the dispatch tool is **`Agent`**, NOT `Task`. `grade_from_otel.py` was specified against
  `Task` and would have counted zero dispatches forever while its own fixtures passed.
- ONE dispatch emits BOTH a `tool_decision` and a `tool_result`, so counting every
  `Agent`-bearing record double-counts. Count decisions.
- there is **no `subagent_type` attribute** in either capture, so a per-agent-type breakdown
  has no supplier. `grade_from_otel.py` reports the total only, and says `unmeasured` — never
  `0` — when an export contains no tool events at all, because a zero and a blind spot are
  different facts.

## Proper capture (OTLP → collector → file)

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_LOGS_EXPORTER=otlp
export OTEL_EXPORTER_OTLP_PROTOCOL=http/json
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4318
```

Minimal collector config (file exporter):

```yaml
receivers:
  otlp: { protocols: { http: { endpoint: 0.0.0.0:4318 } } }
exporters:
  file: { path: /var/log/claude-otel.jsonl }
service:
  pipelines:
    logs: { receivers: [otlp], exporters: [file] }
```

Then: `python3 <plugin>/bin/grade_from_otel.py /var/log/claude-otel.jsonl`

## Notes

- The parser is deliberately LENIENT (accepts flat-attribute JSONL and OTLP/JSON bodies) —
  the OTel GenAI semantic conventions are still marked unstable, so we don't hard-bind a
  schema. If a Claude Code release changes event names, extend the accepted names in
  `grade_from_otel.py` (and add a planted fixture line to its test).
- **No telemetry ≠ silent fallback.** When the script finds nothing it exits 1, and `/grade`
  must SAY "narration-grade (telemetry unavailable)". An estimated number wearing a
  telemetry badge is the exact failure §12/§13 exist to prevent.
- `/grade` also reads `.claude/tdd-lock-journal.jsonl` (TEST-LOCK unlock reasons): frequent
  unlocks or "adjusted test to match output" reasons are honor-system breaches (H2).
