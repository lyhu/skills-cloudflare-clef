import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "cloudflare-clef" / "scripts" / "evaluate.py"
spec = importlib.util.spec_from_file_location("evaluate", SCRIPT)
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)


def response(answer):
    return {"model": "clef", "answers": {"verdict": answer}, "usage": {"input_tokens": 20, "output_tokens": 0}}


NOUL = {"type": "noul", "noul": 0.93}
CHOICE = {
    "type": "choice", "choice": "technical", "confidence": 0.9,
    "probabilities": {"technical": 0.9, "review": 0.1},
}
SCORE = {
    "type": "score", "score": 1.6, "confidence": 0.7,
    "legend": {"0": "none", "1": "some", "2": "complete"},
    "probabilities": {"0": 0.1, "1": 0.2, "2": 0.7},
}


class ClientTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.replies = []
        test = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = self.rfile.read(int(self.headers["Content-Length"]))
                test.requests.append({"path": self.path, "headers": dict(self.headers), "body": json.loads(body)})
                status, value, headers, delay = test.replies.pop(0)
                if delay:
                    time.sleep(delay)
                data = value if isinstance(value, bytes) else json.dumps(value).encode()
                self.send_response(status)
                for key, value in headers.items():
                    self.send_header(key, value)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def log_message(self, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        self.thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01})
        self.thread.start()
        self.environment = patch.dict(os.environ, {
            "CLEF_BACKEND_URL": f"http://127.0.0.1:{self.server.server_port}/v1/systemone",
            "CLEF_MODEL": "clef", "CLEF_TIMEOUT": "0.3", "CLEF_MAX_RETRIES": "0",
            "CLEF_API_KEY": "", "NO_PROXY": "127.0.0.1",
            "CLEF_LOG_ENABLED": "0",
        })
        self.environment.start()

    def tearDown(self):
        self.environment.stop()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()

    def queue(self, answer=None, status=200, *, raw=None, headers=None, delay=0):
        value = raw if raw is not None else response(NOUL if answer is None else answer)
        self.replies.append((status, value, headers or {}, delay))

    def evaluate(self, kind="noul", **kwargs):
        return client.evaluate_clef("状态：结账报错", kind, "Evaluate the specified condition", **kwargs)

    def assert_failure(self, result, code):
        self.assertEqual(result["error"], code)
        self.assertIs(result["fallback_used"], True)
        self.assertNotIn("noul", result)
        self.assertNotIn("choice", result)
        self.assertNotIn("score", result)

    def test_noul_payload_and_native_answer(self):
        self.queue()
        self.assertEqual(self.evaluate(), NOUL)
        request = self.requests[0]
        self.assertEqual(request["path"], "/v1/systemone")
        self.assertEqual(request["body"], {
            "model": "clef", "state": "状态：结账报错",
            "questions": {"verdict": {"type": "noul", "instructions": "Evaluate the specified condition"}},
        })
        self.assertNotIn("Authorization", request["headers"])

    def test_choice_labels_become_named_criteria(self):
        self.queue(CHOICE)
        self.assertEqual(self.evaluate("choice", choices=["technical", "review"]), CHOICE)
        question = self.requests[0]["body"]["questions"]["verdict"]
        self.assertEqual(question["criteria"], {"technical": "technical", "review": "review"})
        self.assertNotIn("choices", question)

    def test_choice_descriptions_and_json_state(self):
        self.queue(CHOICE)
        choices = {"technical": {"definition": "Software outage"}, "review": "Unknown"}
        state = {"issue": "中文", "tests_passed": False}
        result = client.evaluate_clef(state, "choice", "Which handler?", choices)
        self.assertEqual(result, CHOICE)
        self.assertEqual(self.requests[0]["body"]["state"], state)
        self.assertEqual(self.requests[0]["body"]["questions"]["verdict"]["criteria"], choices)

    def test_score_uses_zero_based_ordered_levels(self):
        self.queue(SCORE)
        result = self.evaluate("score", levels=["none", "some", "complete"])
        self.assertEqual(result, SCORE)
        self.assertGreater(result["score"], 1)
        self.assertEqual(self.requests[0]["body"]["questions"]["verdict"]["criteria"], ["none", "some", "complete"])

    def test_optional_bearer_key_and_model(self):
        self.queue()
        with patch.dict(os.environ, {"CLEF_API_KEY": "test-key", "CLEF_MODEL": "Cloudflare/clef"}):
            self.assertEqual(self.evaluate(), NOUL)
        self.assertEqual(self.requests[0]["headers"]["Authorization"], "Bearer test-key")
        self.assertEqual(self.requests[0]["body"]["model"], "Cloudflare/clef")

    def test_invalid_input_never_sends_request(self):
        cases = [
            ("unknown", {}), ("choice", {}), ("choice", {"choices": []}),
            ("choice", {"choices": ["a", "a"]}), ("choice", {"choices": [True]}),
            ("choice", {"choices": [" "]}), ("choice", {"choices": [str(i) for i in range(65)]}),
            ("choice", {"choices": {"": "description"}}), ("score", {}),
            ("score", {"levels": []}), ("score", {"levels": ["level"] * 17}),
            ("noul", {"choices": ["a"]}), ("noul", {"levels": ["a"]}),
        ]
        for kind, kwargs in cases:
            with self.subTest(kind=kind, kwargs=kwargs):
                self.assert_failure(self.evaluate(kind, **kwargs), "CLEF_INVALID_INPUT")
        for state, instruction in [(float("nan"), "Question?"), ({1, 2}, "Question?"), ("state", " "), ("state", {})]:
            self.assert_failure(client.evaluate_clef(state, "noul", instruction), "CLEF_INVALID_INPUT")
        self.assertEqual(self.requests, [])

    def test_invalid_configuration_never_sends_request(self):
        cases = [
            ("CLEF_TIMEOUT", "NaN"), ("CLEF_TIMEOUT", "inf"), ("CLEF_TIMEOUT", "0"),
            ("CLEF_TIMEOUT", "bad"), ("CLEF_MAX_RETRIES", "-1"), ("CLEF_MAX_RETRIES", "6"),
            ("CLEF_MAX_RETRIES", "1.5"), ("CLEF_BACKEND_URL", "file:///etc/passwd"),
            ("CLEF_BACKEND_URL", "http://user:secret@localhost/"),
            ("CLEF_BACKEND_URL", "http:///missing-host"), ("CLEF_MODEL", "invented-alias"),
            ("CLEF_API_KEY", "key\nInjected: header"),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value), patch.dict(os.environ, {key: value}):
                self.assert_failure(self.evaluate(), "CLEF_INVALID_CONFIG")
        self.assertEqual(self.requests, [])

    def test_transient_status_retries_then_succeeds(self):
        for status in client.RETRYABLE_STATUSES:
            with self.subTest(status=status):
                self.queue(status=status)
                self.queue()
                with patch.dict(os.environ, {"CLEF_MAX_RETRIES": "2"}), patch.object(client.time, "sleep") as sleep:
                    self.assertEqual(self.evaluate(), NOUL)
                    sleep.assert_called_once_with(0.5)

    def test_exhausted_retries_fail_closed_with_status(self):
        for _ in range(3):
            self.queue(status=429)
        with patch.dict(os.environ, {"CLEF_MAX_RETRIES": "2"}), patch.object(client.time, "sleep") as sleep:
            result = self.evaluate()
        self.assert_failure(result, "CLEF_SERVICE_UNAVAILABLE")
        self.assertEqual(result["http_status"], 429)
        self.assertEqual(len(self.requests), 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.5, 1.0])

    def test_permanent_status_is_not_retried(self):
        for status in [400, 401, 403, 404, 413, 422]:
            with self.subTest(status=status):
                self.queue(status=status)
                with patch.dict(os.environ, {"CLEF_MAX_RETRIES": "2"}), patch.object(client.time, "sleep") as sleep:
                    result = self.evaluate()
                self.assert_failure(result, "CLEF_HTTP_ERROR")
                self.assertEqual(result["http_status"], status)
                sleep.assert_not_called()
        self.assertEqual(len(self.requests), 6)

    def test_connection_failure_and_timeout_retry_are_bounded(self):
        for exception in [urllib.error.URLError("connection refused"), TimeoutError("timeout")]:
            with self.subTest(exception=type(exception).__name__):
                with patch.dict(os.environ, {"CLEF_MAX_RETRIES": "2"}), patch.object(client.time, "sleep") as sleep:
                    with patch.object(urllib.request.OpenerDirector, "open", side_effect=exception) as request:
                        result = self.evaluate()
                self.assert_failure(result, "CLEF_SERVICE_UNAVAILABLE")
                self.assertEqual(request.call_count, 3)
                self.assertEqual(request.call_args.kwargs["timeout"], 0.3)
                self.assertEqual(sleep.call_count, 2)

    def test_real_socket_timeout_returns_error(self):
        self.queue(delay=0.1)
        with patch.dict(os.environ, {"CLEF_TIMEOUT": "0.01"}):
            self.assert_failure(self.evaluate(), "CLEF_SERVICE_UNAVAILABLE")

    def test_redirect_does_not_forward_context_or_credentials(self):
        self.queue(status=307, headers={"Location": "/other-endpoint"})
        with patch.dict(os.environ, {"CLEF_API_KEY": "test-key"}):
            result = self.evaluate()
        self.assert_failure(result, "CLEF_HTTP_ERROR")
        self.assertEqual(result["http_status"], 307)
        self.assertEqual(len(self.requests), 1)

    def test_malformed_envelopes_and_json_are_not_retried(self):
        for raw in [b"not JSON", b"\xff", b"null", b"[]", b"{}", b'{"answers": []}',
                    b'{"error":"upstream failure","answers":{"verdict":{"type":"noul","noul":0.9}}}',
                    b'{"result":{"answers":{"verdict":{"type":"noul","noul":0.9}}}}']:
            with self.subTest(raw=raw):
                self.queue(raw=raw)
                with patch.dict(os.environ, {"CLEF_MAX_RETRIES": "2"}), patch.object(client.time, "sleep") as sleep:
                    self.assert_failure(self.evaluate(), "CLEF_INVALID_RESPONSE")
                    sleep.assert_not_called()

    def test_invalid_noul_never_becomes_an_allow_verdict(self):
        for answer in [True, 0.9, {}, {"type": "score", "score": 1},
                       {"type": "noul", "noul": True}, {"type": "noul", "noul": "0.9"},
                       {"type": "noul", "noul": -0.1}, {"type": "noul", "noul": 1.1},
                       {"type": "noul", "noul": float("nan")}, {"type": "noul", "noul": float("inf")},
                       {"type": "noul", "noul": 0.9, "error": "upstream-error"},
                       {"type": "noul", "noul": 0.9, "allow": True}]:
            with self.subTest(answer=answer):
                self.queue(answer)
                self.assert_failure(self.evaluate(), "CLEF_INVALID_RESPONSE")

    def test_invalid_choice_distribution_or_selection_is_rejected(self):
        cases = [
            {"choice": "other"}, {"choice": ["technical"]}, {"choice": "review"},
            {"probabilities": {"technical": 0.9}}, {"probabilities": {"technical": 0.9, "other": 0.1}},
            {"probabilities": {"technical": 0.8, "review": 0.1}},
            {"probabilities": {"technical": 1.1, "review": -0.1}},
            {"probabilities": {"technical": True, "review": 0}},
            {"confidence": float("nan")}, {"confidence": 1.1}, {"confidence": None}, {"confidence": 0.5},
        ]
        for change in cases:
            with self.subTest(change=change):
                self.queue({**CHOICE, **change})
                self.assert_failure(self.evaluate("choice", choices=["technical", "review"]), "CLEF_INVALID_RESPONSE")

    def test_invalid_score_or_legend_is_rejected(self):
        for change in [{"score": True}, {"score": -1}, {"score": 2.1}, {"score": 0.2},
                       {"legend": {"0": "wrong", "1": "some", "2": "complete"}},
                       {"legend": None}, {"probabilities": {"0": 0.3, "1": 0.7}}]:
            with self.subTest(change=change):
                self.queue({**SCORE, **change})
                self.assert_failure(self.evaluate("score", levels=["none", "some", "complete"]), "CLEF_INVALID_RESPONSE")

    def test_native_rounding_and_maximum_criteria_are_accepted(self):
        choices = [str(i) for i in range(64)]
        self.queue({"type": "choice", "choice": "0", "confidence": 0.0156,
                    "probabilities": dict.fromkeys(choices, 0.0156)})
        self.assertNotIn("error", self.evaluate("choice", choices=choices))
        levels = [f"level {i}" for i in range(16)]
        self.queue({"type": "score", "score": 7.5, "confidence": 0.0625,
                    "legend": dict(enumerate(levels)),
                    "probabilities": {str(i): 0.0625 for i in range(16)}})
        self.assertNotIn("error", self.evaluate("score", levels=levels))

    def test_cli_success_errors_and_no_site_packages(self):
        self.queue()
        args = [sys.executable, "-S", str(SCRIPT), "--state", "中文上下文", "--type", "noul", "--instructions", "Risk?"]
        completed = subprocess.run(args, capture_output=True, text=True, timeout=5)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), NOUL)
        self.assertEqual(completed.stderr, "")
        invalid = subprocess.run(args[:-4] + ["--type", "choice", "--instructions", "Route?"], capture_output=True, text=True, timeout=5)
        self.assertEqual(invalid.returncode, 1)
        self.assert_failure(json.loads(invalid.stdout), "CLEF_INVALID_INPUT")
        self.assertEqual(invalid.stderr, "")
        usage = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, timeout=5)
        self.assertEqual(usage.returncode, 2)
        self.assertEqual(usage.stdout, "")

    def test_python_template_works_when_copied_to_application(self):
        self.queue({**CHOICE, "probabilities": {"technical": 0.9, "billing": 0.0, "review": 0.1}})
        with tempfile.TemporaryDirectory() as directory:
            shutil.copy(SCRIPT, Path(directory) / "evaluate.py")
            shutil.copy(ROOT / "skills/cloudflare-clef/templates/client.py", Path(directory) / "client.py")
            completed = subprocess.run([sys.executable, "client.py"], cwd=directory, capture_output=True, text=True, timeout=5)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["choice"], "technical")

    def test_typescript_template_uses_validated_cli(self):
        node = shutil.which("node")
        if not node or int(subprocess.check_output([node, "-p", "process.versions.node.split('.')[0]"]).strip()) < 24:
            self.skipTest("Node 24 is needed for the TypeScript template integration test")
        module = (ROOT / "skills/cloudflare-clef/templates/client.ts").as_uri()
        # No shell expansion: state is sent literally, even with shell metacharacters.
        state = "--literal state $(touch UNEXPECTED_FILE) `id` 中文"
        code = f'''import {{ evaluateClef }} from {json.dumps(module)};
const result = await evaluateClef({json.dumps(str(SCRIPT))}, {json.dumps(state)},
  {{type: "noul", instructions: "Risk?"}});
console.log(JSON.stringify(result));'''
        self.queue()
        completed = subprocess.run([node, "--input-type=module", "-e", code], capture_output=True, text=True, timeout=5)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout), NOUL)
        self.assertEqual(self.requests[0]["body"]["state"], state)
        self.assertFalse((ROOT / "UNEXPECTED_FILE").exists())
        self.queue(status=503)
        failed = subprocess.run([node, "--input-type=module", "-e", code], capture_output=True, text=True, timeout=5)
        self.assert_failure(json.loads(failed.stdout), "CLEF_SERVICE_UNAVAILABLE")

    def test_cloudflare_official_api_envelope_and_errors(self):
        # 1. 验证 Cloudflare Client v4 API 标准响应信封: {"result": {...}, "success": true}
        cf_envelope = {
            "result": {
                "model": "@cf/cloudflare/clef",
                "answers": {"verdict": NOUL},
                "usage": {"input_tokens": 15, "output_tokens": 0},
            },
            "success": True,
            "errors": [],
            "messages": [],
        }
        self.queue(raw=json.dumps(cf_envelope).encode())
        with patch.dict(os.environ, {"CLEF_MODEL": "@cf/cloudflare/clef"}):
            self.assertEqual(self.evaluate(), NOUL)

        # 2. 验证 Cloudflare API 错误响应: {"success": false, "errors": [...]}
        cf_error = {
            "result": None,
            "success": False,
            "errors": [{"code": 1000, "message": "Authentication error"}],
            "messages": [],
        }
        self.queue(raw=json.dumps(cf_error).encode())
        result = self.evaluate()
        self.assert_failure(result, "CLEF_HTTP_ERROR")
        self.assertIn("Authentication error", result["message"])

    def test_logs_retry_usage_correlation_and_no_sensitive_content(self):
        self.queue(status=503)
        self.queue({"type": "choice", "choice": "PRIVATE_OPTION", "confidence": 0.9,
            "probabilities": {"PRIVATE_OPTION": 0.9, "OTHER_PRIVATE_OPTION": 0.1}})
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "logs/events.jsonl"
            with patch.dict(os.environ, {"CLEF_LOG_ENABLED": "1", "CLEF_LOG_PATH": str(log),
                "CLEF_LOG_SOURCE": "ego-clef", "CLEF_MAX_RETRIES": "1", "CLEF_API_KEY": "PRIVATE_KEY",
                "CLEF_RUN_ID": "00000000-0000-4000-8000-000000000001",
                "CLEF_CALL_ID": "00000000-0000-4000-8000-000000000002"}), patch.object(client.time, "sleep"):
                result = client.evaluate_clef("PRIVATE_STATE", "choice", "PRIVATE_INSTRUCTIONS",
                    ["PRIVATE_OPTION", "OTHER_PRIVATE_OPTION"])
            self.assertNotIn("error", result)
            text = log.read_text()
            events = [json.loads(line) for line in text.splitlines()]
            self.assertNotIn("PRIVATE", text)
            self.assertNotIn(str(self.server.server_port), text)
            self.assertEqual([e["event"] for e in events], ["attempt", "attempt", "call"])
            self.assertEqual([e["http_status"] for e in events], [503, 200, 200])
            self.assertEqual({e["call_id"] for e in events}, {"00000000-0000-4000-8000-000000000002"})
            self.assertTrue(all(e["source"] == "ego-clef" and e["run_id"].endswith("0001") for e in events))
            call = events[-1]
            self.assertEqual((call["attempt_count"], call["retry_count"]), (2, 1))
            self.assertEqual((call["input_tokens"], call["output_tokens"]), (20, 0))
            self.assertEqual(call["confidence"], 0.9)
            self.assertGreater(call["request_bytes"], 0)
            self.assertGreaterEqual(call["duration_ms"], events[1]["duration_ms"])
            self.assertEqual(log.stat().st_mode & 0o777, 0o600)

    def test_logs_local_failures_without_claiming_http_attempts(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "events.jsonl"
            with patch.dict(os.environ, {"CLEF_LOG_ENABLED": "1", "CLEF_LOG_PATH": str(log)}):
                self.assert_failure(self.evaluate("choice"), "CLEF_INVALID_INPUT")
                with patch.dict(os.environ, {"CLEF_MODEL": "PRIVATE_INVALID_MODEL"}):
                    self.assert_failure(self.evaluate(), "CLEF_INVALID_CONFIG")
            events = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(len(events), 2)
            self.assertTrue(all(e["event"] == "call" and e["attempt_count"] == 0 and e["fallback_used"] for e in events))
            self.assertNotIn("PRIVATE", log.read_text())
            self.assertEqual(self.requests, [])

    def test_logs_http_failure_and_tolerates_disabled_or_unwritable_sink(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "events.jsonl"
            self.queue(status=401)
            with patch.dict(os.environ, {"CLEF_LOG_ENABLED": "1", "CLEF_LOG_PATH": str(log)}):
                self.assert_failure(self.evaluate(), "CLEF_HTTP_ERROR")
            events = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertTrue(all(e["error_code"] == "CLEF_HTTP_ERROR" and e["http_status"] == 401 for e in events))
            self.queue()
            with patch.dict(os.environ, {"CLEF_LOG_ENABLED": "1", "CLEF_LOG_PATH": directory}):
                self.assertEqual(self.evaluate(), NOUL)
            self.queue()
            absent = Path(directory) / "disabled.jsonl"
            with patch.dict(os.environ, {"CLEF_LOG_ENABLED": "0", "CLEF_LOG_PATH": str(absent)}):
                self.assertEqual(self.evaluate(), NOUL)
            self.assertFalse(absent.exists())

    def test_usage_validation_and_cloudflare_envelope_logging(self):
        self.queue(raw=json.dumps({"success": True, "result": {"answers": {"verdict": NOUL},
            "model": {"private": "not a model"}, "usage": {"input_tokens": True, "output_tokens": -2,
                "total_tokens": "PRIVATE_USAGE", "prompt": "PRIVATE_PROMPT"}}}).encode())
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "events.jsonl"
            with patch.dict(os.environ, {"CLEF_LOG_ENABLED": "1", "CLEF_LOG_PATH": str(log)}):
                self.assertEqual(self.evaluate(), NOUL)
            text = log.read_text()
            self.assertNotIn("PRIVATE", text)
            call = json.loads(text.splitlines()[-1])
            self.assertNotIn("input_tokens", call)
            self.assertNotIn("output_tokens", call)
            self.assertNotIn("served_model", call)

    def test_concurrent_calls_append_complete_records(self):
        from concurrent.futures import ThreadPoolExecutor
        for _ in range(12):
            self.queue()
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "events.jsonl"
            with patch.dict(os.environ, {"CLEF_LOG_ENABLED": "1", "CLEF_LOG_PATH": str(log)}):
                with ThreadPoolExecutor(max_workers=4) as pool:
                    results = list(pool.map(lambda _: self.evaluate(), range(12)))
            self.assertTrue(all(result == NOUL for result in results))
            events = [json.loads(line) for line in log.read_text().splitlines()]
            self.assertEqual(len(events), 24)
            calls = [e for e in events if e["event"] == "call"]
            self.assertEqual(len({e["call_id"] for e in calls}), 12)


if __name__ == "__main__":
    unittest.main()
