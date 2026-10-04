#!/usr/bin/env python3
"""Run labeled decision benchmarks against a real, explicitly configured Clef service."""

import argparse
import hashlib
import importlib.util
import json
import math
import os
import platform
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES_FILE = ROOT / "benchmarks" / "cases.json"
CLIENT_FILE = ROOT / "skills" / "cloudflare-clef" / "scripts" / "evaluate.py"
spec = importlib.util.spec_from_file_location("clef_client", CLIENT_FILE)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


def evaluate_case(case):
    return client.evaluate_clef(
        case["state"], case["type"], case["instructions"],
        case.get("choices"), levels=case.get("levels"),
    )


def matches(case, answer):
    if "error" in answer:
        return False
    if case["type"] == "noul":
        return (answer["noul"] >= 0.5) == case["expected"]
    if case["type"] == "choice":
        return answer["choice"] == case["expected"]
    return abs(answer["score"] - case["expected"]) <= 0.5


def latency_summary(values):
    if not values:
        return None
    ordered = sorted(values)
    # Nearest-rank percentiles: ceil(p * N), one-based.
    return {
        "mean": statistics.mean(ordered),
        "p50": ordered[math.ceil(0.50 * len(ordered)) - 1],
        "p95": ordered[math.ceil(0.95 * len(ordered)) - 1],
        "max": ordered[-1],
    }


def summarize(records, cases):
    lookup = {case["id"]: case for case in cases}
    valid = [record for record in records if "error" not in record["answer"]]
    matched = sum(record["matched"] for record in records)
    result = {
        "requests": len(records), "successful": len(valid), "errors": len(records) - len(valid),
        "matched": matched,
        "agreement_rate": matched / len(records) if records else None,
        "valid_answer_agreement_rate": matched / len(valid) if valid else None,
        "latency_ms": latency_summary([record["latency_ms"] for record in records]),
        "successful_latency_ms": latency_summary([record["latency_ms"] for record in valid]),
    }
    if valid and all(record["type"] == "noul" for record in valid):
        result["brier_score"] = statistics.mean(
            (record["answer"]["noul"] - int(lookup[record["case_id"]]["expected"])) ** 2 for record in valid
        )
        result["uncertain_answers"] = sum(0.2 < record["answer"]["noul"] < 0.8 for record in valid)
    elif valid and all(record["type"] == "choice" for record in valid):
        result["multiclass_brier_score"] = statistics.mean(
            sum((p - int(label == lookup[record["case_id"]]["expected"])) ** 2
                for label, p in record["answer"]["probabilities"].items()) for record in valid
        )
    elif valid and all(record["type"] == "score" for record in valid):
        result["mean_absolute_error"] = statistics.mean(
            abs(record["answer"]["score"] - lookup[record["case_id"]]["expected"]) for record in valid
        )
    return result


def run_benchmark(cases, repeats=3, warmup=3, transport_note="HTTP endpoint; network topology not recorded", cases_file=CASES_FILE):
    # Warm up one representative of each primitive; exclude these from metrics.
    representatives = list({case["type"]: case for case in cases}.values())
    if not representatives:
        raise ValueError("Benchmark requires at least one case")
    warmup_answers = [evaluate_case(representatives[i % len(representatives)]) for i in range(warmup)]
    records = []
    for repeat in range(1, repeats + 1):
        for case in cases:
            start = time.perf_counter()
            answer = evaluate_case(case)
            elapsed = (time.perf_counter() - start) * 1000
            records.append({
                "case_id": case["id"], "type": case["type"], "repeat": repeat,
                "expected": case["expected"], "answer": answer,
                "matched": matches(case, answer), "latency_ms": elapsed,
            })
        print(f"Completed repeat {repeat}/{repeats} ({len(records)} measured requests)", file=sys.stderr)
    return {
        "metadata": {
            "mode": "live-http", "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(), "client_platform": platform.platform(),
            "model": os.getenv("CLEF_MODEL", "clef"),
            "transport_note": transport_note,
            "timeout_seconds": os.getenv("CLEF_TIMEOUT", "10.0"),
            "max_retries": os.getenv("CLEF_MAX_RETRIES", "2"),
            "case_count": len(cases), "repeats": repeats,
            "warmup_requests": warmup, "warmup_errors": sum("error" in answer for answer in warmup_answers),
            "source_sha256": {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
                              for path in (cases_file, CLIENT_FILE, Path(__file__))},
            "dataset": str(cases_file.relative_to(ROOT)),
            "endpoint_recorded": False,
        },
        "summary": summarize(records, cases),
        "by_primitive": {kind: summarize([record for record in records if record["type"] == kind], cases)
                         for kind in ("noul", "choice", "score")},
        "records": records,
    }


def markdown_report(result):
    metadata, summary = result["metadata"], result["summary"]
    lines = ["# Clef Decision Benchmark", "",
             f"UTC {metadata['timestamp_utc']} · `{metadata.get('dataset', 'benchmarks/cases.json')}` · "
             f"{metadata['case_count']} cases × {metadata['repeats']} repeats · {metadata['warmup_requests']} warmups excluded.", "",
             "| Primitive | Valid / requests | Matched / requests | p50 ms | p95 ms | Brier / MAE |",
             "| --- | --- | --- | --- | --- | --- |"]
    for kind, metrics in result["by_primitive"].items():
        if not metrics["requests"]:
            continue
        latency = metrics["successful_latency_ms"]
        statistic = metrics.get("brier_score", metrics.get("multiclass_brier_score", metrics.get("mean_absolute_error")))
        value = f"{statistic:.6f}" if statistic is not None else "N/A"
        p50 = f"{latency['p50']:.2f}" if latency else "N/A"
        p95 = f"{latency['p95']:.2f}" if latency else "N/A"
        lines.append(f"| {kind} | {metrics['successful']}/{metrics['requests']} | "
                     f"{metrics['matched']}/{metrics['requests']} | {p50} | {p95} | {value} |")
    lines += ["", f"Transport: {metadata['transport_note']}. Model: `{metadata['model']}`; "
              f"timeout {metadata['timeout_seconds']} s; retries {metadata['max_retries']}; errors {summary['errors']}.", "",
              "Successful-request latency includes HTTP, inference, retries and validation. Nearest-rank percentiles. "
              "Noul threshold 0.5; exact Choice labels; Score tolerance 0.5. "
              "Brier/MAE exclude errors; agreement includes errors. Repeats are not independent examples.", "",
              "Small selected subsets are diagnostic, not official leaderboard scores or calibration evidence. "
              "See [methodology](../../../METHODOLOGY.md) and [raw results](results.json)."]
    failures = [r for r in result["records"] if not r["matched"]]
    if failures:
        lines += ["", "Failures: " + ", ".join(dict.fromkeys(
            f"`{r['case_id']}` ({r['answer'].get('error', r['answer'].get(r['type']))})" for r in failures)) + "."]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=3)
    parser.add_argument("--cases", type=Path, default=CASES_FILE)
    parser.add_argument("--transport-note", default="HTTP endpoint; network topology not recorded")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "benchmarks" / "reports" / "latest")
    args = parser.parse_args()
    if not 1 <= args.repeats <= 100 or not 0 <= args.warmup <= 100:
        parser.error("repeats must be 1..100 and warmup must be 0..100")
    if not os.getenv("CLEF_BACKEND_URL"):
        parser.error("Set CLEF_BACKEND_URL explicitly before sending benchmark requests")
    cases_file = args.cases.resolve()
    cases = json.loads(cases_file.read_text(encoding="utf-8"))["cases"]
    result = run_benchmark(cases, args.repeats, args.warmup, args.transport_note, cases_file)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (args.output_dir / "report.md").write_text(markdown_report(result), encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    print(f"Reports saved to {args.output_dir}", file=sys.stderr)
    return 0 if result["summary"]["matched"] == result["summary"]["requests"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
