# Telemetry recipe — making /grade mechanical

§13 says "grade from telemetry, never self-narration." Claude Code exports OpenTelemetry
natively; this recipe captures it to a local file and feeds it to
`bin/grade_from_otel.py`, so `/grade` pastes measured numbers instead of estimating.

## Quick local capture (console exporter → file)

```bash
export CLAUDE_CODE_ENABLE_TELEMETRY=1
export OTEL_LOGS_EXPORTER=console
export OTEL_METRICS_EXPORTER=console
claude 2>>~/.claude/otel-session.jsonl   # console exporter writes to stderr
# ... work ...
python3 <plugin>/bin/grade_from_otel.py ~/.claude/otel-session.jsonl
```

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
