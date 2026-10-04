**English** | [简体中文](logging_zh.md)

# Clef Telemetry & Observability Specification

`evaluate_clef` logs structured metadata to `~/.local/state/clef/events.jsonl` by default across Python module invocations, the CLI, and sub-processes. Standard output, return dictionaries, and exit codes remain strictly compliant with the core protocol, operating transparently to callers.

---

## 1. Event Model & Telemetry Metrics

| Event Type (`event`) | Trigger | Primary Statistical Purpose |
| :--- | :--- | :--- |
| **`call`** | Client invocation completed (including validation/configuration errors) | Total call count, success rate, primitive distribution, source tag, end-to-end duration, token usage |
| **`attempt`** | Single HTTP network attempt finished (including retries) | HTTP attempt volume, status code distribution, per-attempt round-trip latency |
| **`run`** *(Optional)* | Host workflow completion/handoff record | High-level task status tracking (not counted as raw model inference) |

### Correlation & Data Contract
- **`call_id`**: Uniquely identifies a client invocation and groups its underlying HTTP `attempt` records.
- **`run_id`**: Optional UUID correlating multiple calls within the same workflow task.
- **Record Schema**: Includes `schema_version: 1`, UTC timestamp, `source` tag, `primitive`, requested model alias, server-reported model alias, duration, retry count, status codes, and output probabilities or scores.
- **Strict Privacy & Redaction**: **Never records** `--state`, `--instructions`, candidate text, full URLs, API keys, response bodies, or raw exception traces.

### Token Usage Accounting
- The fields `input_tokens`, `output_tokens`, and `total_tokens` record only non-negative integers explicitly reported by the backend; missing values are never fabricated or estimated.
- Usage accumulation sums only over `call` events, avoiding duplicate counting across retries.
- `usage_reported_calls` tracks token reporting coverage; omitted records denote missing metrics, not zero consumption.

---

## 2. Natural Language & CLI Queries

### Natural Language Query Mapping
Agents support querying local telemetry directly using natural language prompts without requiring users to type shell commands:

| Natural Language Query | CLI Flags | Scope & Description |
| :--- | :--- | :--- |
| "Show Clef log statistics" / "查看 Clef 日志统计" | `--today --json` | Current local calendar day, all sources |
| "Show today's ego-clef calls" / "查看今天 ego-clef 的调用" | `--today --source ego-clef --json` | Current day, filtered by `ego-clef` source |
| "Show Clef calls for the last 7 days" | `--since <7-days-ago ISO> --json` | Summary over the past 7 days |
| "Check ego-clef task status" | `--today --source ego-clef --file ... --file ...` | Reads both generic call logs and browser workflow logs |

### CLI Usage Examples

```bash
# 1. Summary for today (local timezone)
python3 <skill-dir>/scripts/log_stats.py --today

# 2. Filter by source and start date
python3 <skill-dir>/scripts/log_stats.py --source ego-clef --since 2026-10-01

# 3. Output structured JSON (for automation or reporting)
python3 <skill-dir>/scripts/log_stats.py --today --json

# 4. Joint analysis of generic call logs and browser workflow logs
python3 <skill-dir>/scripts/log_stats.py --today --json \
  --file ~/.local/state/clef/events.jsonl \
  --file ~/.local/state/clef-browser/events.jsonl
```

### Metric Definitions
- **Latency**: Client `duration_ms` is measured using monotonic clocks, covering network transfer, validation, backoff, and file append overhead (not raw GPU kernel time).
- **Percentiles**: p50 and p95 use the Nearest-Rank method (`ceil(p * N)`).
- **Deduplication & Fault Tolerance**: Deduplicates repeated `call_id`, `attempt`, and `run` records; skips malformed lines and reports corrupted line counts; returns empty stats when log files do not exist.

---

## 3. Environment Variables Reference

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `CLEF_LOG_ENABLED` | `1` | Set to `0` to disable logging; decision logic is unaffected |
| `CLEF_LOG_PATH` | `~/.local/state/clef/events.jsonl` | Target JSONL file path (useful for test isolation) |
| `CLEF_LOG_SOURCE` | `cloudflare-clef` | Caller identity tag (1–48 chars: lowercase alphanumeric, `-`, `_`) |
| `CLEF_RUN_ID` | *(Empty)* | Optional workflow task UUID |
| `CLEF_CALL_ID` | Auto-generated | UUID for a single call; never reuse across multiple calls |

### File Security & Lifecycle
- Log files append with `0600` permissions (parent directories created with `0700`).
- Log write failures (e.g. read-only disk) fail silently and never disrupt decisions or pollute stdout/stderr.
- File rotation is managed by the host OS or supervisor; this tool does not truncate history.


