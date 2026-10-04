#!/usr/bin/env python3
"""Summarize Clef JSONL calls, HTTP attempts and optional correlated workflow logs."""
import argparse
import json
import math
import os
import re
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def label(value):
    return value if isinstance(value, str) and re.fullmatch(r"[\w@./-]{1,64}", value) else "unknown"


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def metrics(calls):
    durations = sorted(c["duration_ms"] for c in calls if number(c.get("duration_ms")))
    success = sum(c.get("outcome") == "success" for c in calls)
    return {"calls": len(calls), "success": success, "errors": len(calls) - success,
        "success_rate": round(success / len(calls), 4) if calls else None,
        "retries": sum(c.get("retry_count", 0) for c in calls if number(c.get("retry_count", 0))),
        "p50_ms": durations[math.ceil(len(durations) * .5) - 1] if durations else None,
        "p95_ms": durations[math.ceil(len(durations) * .95) - 1] if durations else None,
        "usage_reported_calls": sum(type(c.get("input_tokens")) is int for c in calls),
        "input_tokens": sum(c["input_tokens"] for c in calls if type(c.get("input_tokens")) is int and c["input_tokens"] >= 0),
        "output_tokens": sum(c["output_tokens"] for c in calls if type(c.get("output_tokens")) is int and c["output_tokens"] >= 0)}


def summarize(files, *, since=None, source=None):
    calls, runs = [], []
    groups = {key: defaultdict(list) for key in ("source", "primitive", "model")}
    attempts, invalid, duplicates = 0, 0, 0
    statuses, errors, reasons = Counter(), Counter(), Counter()
    seen, run_ids = set(), set()
    for path in dict.fromkeys(Path(file).expanduser() for file in files):
        if not path.exists():
            continue
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                    if not isinstance(event, dict):
                        raise ValueError("Expected an object")
                    timestamp = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                    if timestamp.tzinfo is None:
                        raise ValueError("Expected a timezone")
                except (ValueError, TypeError, KeyError, AttributeError):
                    invalid += 1
                    continue
                if since and timestamp < since:
                    continue
                event_source = label(event.get("source"))
                if source and event_source != source:
                    continue
                kind = event.get("event")
                if kind not in ("call", "attempt", "run"):
                    continue  # Frontend decision records never count as extra model calls.
                identifier = event.get("run_id" if kind == "run" else "call_id")
                if not isinstance(identifier, str) or not identifier:
                    invalid += 1
                    continue
                identity = (kind, identifier, event.get("attempt") if kind == "attempt" else None)
                if type(identity[2]) not in (int, type(None)):
                    invalid += 1
                    continue
                if identity in seen:
                    duplicates += 1
                    continue
                seen.add(identity)
                if kind == "call":
                    calls.append(event)
                    for key, group in groups.items():
                        group[label(event.get(key))].append(event)
                    if isinstance(event.get("run_id"), str):
                        run_ids.add(event["run_id"])
                    if event.get("outcome") != "success":
                        errors[label(event.get("error_code"))] += 1
                elif kind == "attempt":
                    attempts += 1
                    if type(event.get("http_status")) is int:
                        statuses[str(event["http_status"])] += 1
                else:
                    runs.append(event)
                    reasons[label(event.get("reason"))] += 1
    return {"summary": {**metrics(calls), "http_attempts": attempts, "correlated_runs": len(run_ids)},
        **{"by_" + key: {name: metrics(items) for name, items in sorted(group.items())} for key, group in groups.items()},
        "errors": dict(errors), "http_statuses": dict(statuses),
        "workflow_runs": {"total": len(runs), "completed": sum(r.get("status") == "completed" for r in runs),
            "handoff": sum(r.get("status") == "handoff" for r in runs), "reasons": dict(reasons)},
        "invalid_lines": invalid, "duplicate_events": duplicates}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", action="append", help="JSONL path; repeat to include a workflow log")
    parser.add_argument("--source", help="Filter by source, e.g. ego-clef")
    parser.add_argument("--since", help="ISO date/time; no timezone means local time")
    parser.add_argument("--today", action="store_true", help="Since local midnight")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON")
    args = parser.parse_args()
    if args.today and args.since:
        parser.error("Choose --today or --since")
    try:
        since = datetime.fromisoformat(args.since.replace("Z", "+00:00")).astimezone() if args.since else None
        if args.today:
            since = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).astimezone()
        files = args.file or [os.getenv("CLEF_LOG_PATH", str(Path.home() / ".local/state/clef/events.jsonl"))]
        report = summarize(files, since=since, source=args.source)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    report["since"] = since.isoformat() if since else None
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
    else:
        summary = report["summary"]
        print(f"Calls {summary['calls']} | success {summary['success']} | errors {summary['errors']} | "
            f"HTTP attempts {summary['http_attempts']} | retries {summary['retries']}")
        print("Source                    Calls  Success  Errors   p50 ms   p95 ms  Input tokens")
        for name, item in report["by_source"].items():
            p50 = f"{item['p50_ms']:.1f}" if item['p50_ms'] is not None else "-"
            p95 = f"{item['p95_ms']:.1f}" if item['p95_ms'] is not None else "-"
            print(f"{name:<25} {item['calls']:>5}  {item['success']:>7}  {item['errors']:>6}  {p50:>7}  {p95:>7}  {item['input_tokens']:>12}")
        print(f"Usage reported: {summary['usage_reported_calls']}/{summary['calls']} calls; "
            f"correlated runs: {summary['correlated_runs']}")
        workflow = report["workflow_runs"]
        if workflow["total"]:
            print(f"Workflow runs {workflow['total']} | completed {workflow['completed']} | handoff {workflow['handoff']}")
        if report["invalid_lines"] or report["duplicate_events"]:
            print(f"Skipped invalid lines {report['invalid_lines']} | duplicate events {report['duplicate_events']}")


if __name__ == "__main__":
    main()
