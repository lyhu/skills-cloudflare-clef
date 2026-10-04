import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "skills/cloudflare-clef/scripts/log_stats.py"
spec = importlib.util.spec_from_file_location("log_stats", SCRIPT)
stats = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stats)


def event(kind, call_id="call-a", **fields):
    return {"timestamp": "2026-10-04T12:00:00+00:00", "event": kind,
        "call_id": call_id, "source": "cloudflare-clef", "primitive": "noul", "model": "clef", **fields}


class LogStatsTests(unittest.TestCase):
    def test_counts_calls_attempts_usage_and_workflows_without_double_counting(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "events.jsonl"
            rows = [event("attempt", attempt=1, http_status=503),
                event("attempt", attempt=2, http_status=200, input_tokens=100),
                event("call", outcome="success", duration_ms=200, retry_count=1, input_tokens=100,
                    output_tokens=0, run_id="run-a"),
                event("attempt", "call-b", attempt=1, source="ego-clef", http_status=401),
                event("call", "call-b", source="ego-clef", outcome="error", error_code="CLEF_HTTP_ERROR", duration_ms=20),
                event("call", "call-c", outcome="error", error_code="CLEF_INVALID_INPUT", duration_ms=1),
                event("decision", outcome="success", input_tokens=100, duration_ms=200),
                event("run", run_id="run-a", status="completed", reason="verified"),
                event("run", source="ego-clef", run_id="run-b", status="handoff", reason="decision_error")]
            file.write_text("\n".join(json.dumps(row) for row in rows)+"\n")
            report = stats.summarize([file, file])
            summary = report["summary"]
            self.assertEqual((summary["calls"], summary["success"], summary["errors"]), (3, 1, 2))
            self.assertEqual((summary["http_attempts"], summary["retries"]), (3, 1))
            self.assertEqual((summary["input_tokens"], summary["usage_reported_calls"]), (100, 1))
            self.assertEqual((summary["p50_ms"], summary["p95_ms"]), (20, 200))
            self.assertEqual(report["by_source"]["ego-clef"]["calls"], 1)
            self.assertEqual(report["workflow_runs"]["completed"], 1)
            self.assertEqual(report["workflow_runs"]["handoff"], 1)
            self.assertEqual(report["http_statuses"], {"503": 1, "200": 1, "401": 1})
            filtered = stats.summarize([file], source="ego-clef")
            self.assertEqual(filtered["summary"]["calls"], 1)
            self.assertEqual(filtered["summary"]["http_attempts"], 1)

    def test_duplicate_records_partial_lines_and_date_filters(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "events.jsonl"
            row = event("call", outcome="success", duration_ms=50)
            file.write_text(json.dumps(row)+"\n"+json.dumps(row)+"\n{unfinished\n[]\n")
            report = stats.summarize([file])
            self.assertEqual(report["summary"]["calls"], 1)
            self.assertEqual(report["invalid_lines"], 2)
            self.assertEqual(report["duplicate_events"], 1)
            self.assertEqual(stats.summarize([file], since=datetime(2026, 10, 5, tzinfo=timezone.utc))["summary"]["calls"], 0)

    def test_missing_logs_and_missing_usage_do_not_invent_observations(self):
        with tempfile.TemporaryDirectory() as directory:
            report = stats.summarize([Path(directory) / "missing"])
            self.assertEqual(report["summary"]["calls"], 0)
            self.assertIsNone(report["summary"]["success_rate"])
            self.assertIsNone(report["summary"]["p95_ms"])
            file = Path(directory) / "events.jsonl"
            file.write_text(json.dumps(event("call", outcome="success", duration_ms=float("nan")))+"\n")
            report = stats.summarize([file])
            self.assertIsNone(report["summary"]["p50_ms"])
            self.assertEqual(report["summary"]["usage_reported_calls"], 0)

    def test_cli_runs_without_site_packages_and_preserves_json_interface(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / "events.jsonl"
            file.write_text(json.dumps(event("call", outcome="success", duration_ms=50))+"\n")
            result = subprocess.run([sys.executable, "-S", str(SCRIPT), "--file", str(file), "--json",
                "--since", "2026-10-04T00:00:00+00:00"], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["summary"]["calls"], 1)
            result = subprocess.run([sys.executable, str(SCRIPT), "--today", "--since", "2026-10-04"], capture_output=True)
            self.assertEqual(result.returncode, 2)
