import importlib.util
import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("benchmark", ROOT / "benchmarks/run.py")
benchmark = importlib.util.module_from_spec(spec)
spec.loader.exec_module(benchmark)
CASES = json.loads((ROOT / "benchmarks/cases.json").read_text())["cases"]


def fixture_answer(case):
    """Reference fixture for testing the harness; never report as model output."""
    if case["type"] == "noul":
        return {"type": "noul", "noul": 0.9 if case["expected"] else 0.1}
    if case["type"] == "choice":
        return {"type": "choice", "choice": case["expected"], "confidence": 1.0,
                "probabilities": {label: float(label == case["expected"]) for label in case["choices"]}}
    return {"type": "score", "score": float(case["expected"]), "confidence": 1.0,
            "legend": {str(i): level for i, level in enumerate(case["levels"])},
            "probabilities": {str(i): float(i == case["expected"]) for i in range(len(case["levels"]))}}


class BenchmarkTests(unittest.TestCase):
    def test_classic_subsets_and_single_primitive_warmup(self):
        for name, kind in (("boolq", "noul"), ("banking77", "choice")):
            path = ROOT / f"benchmarks/datasets/{name}.json"
            dataset = json.loads(path.read_text())
            cases = dataset["cases"]
            self.assertEqual(len(cases), 24)
            self.assertEqual(len({case["id"] for case in cases}), 24)
            self.assertTrue(dataset["dataset"]["license"].startswith("CC-BY"))
            for case in cases:
                self.assertEqual(case["type"], kind)
                answer = fixture_answer(case)
                question = {"type": kind}
                if kind == "choice":
                    question["criteria"] = case["choices"]
                self.assertNotIn("error", benchmark.client._validate_answer(answer, question))
            if kind == "noul":
                self.assertEqual(sum(case["expected"] for case in cases), 12)
            else:
                self.assertEqual(len(cases[0]["choices"]), 12)
                self.assertEqual(len({case["expected"] for case in cases}), 12)
            with patch.object(benchmark, "evaluate_case", side_effect=fixture_answer) as evaluate:
                result = benchmark.run_benchmark(cases, repeats=1, warmup=3, cases_file=path)
            self.assertEqual(evaluate.call_count, 27)
            self.assertEqual(result["summary"]["matched"], 24)
            self.assertIn(str(path.relative_to(ROOT)), result["metadata"]["source_sha256"])

    def test_cases_have_unique_ids_valid_contracts_and_labels(self):
        self.assertEqual(len(CASES), 18)
        self.assertEqual(len({case["id"] for case in CASES}), len(CASES))
        schema = json.loads((ROOT / "skills/cloudflare-clef/references/primitives.json").read_text())
        validator = Draft202012Validator(schema)
        answer_schema = {**schema, "$ref": "#/$defs/answer"}
        for case in CASES:
            with self.subTest(case=case["id"]):
                question = {"type": case["type"], "instructions": case["instructions"]}
                if case["type"] == "choice":
                    question["criteria"] = case["choices"]
                    self.assertIn(case["expected"], case["choices"])
                elif case["type"] == "score":
                    question["criteria"] = case["levels"]
                    self.assertIs(type(case["expected"]), int)
                    self.assertTrue(0 <= case["expected"] < len(case["levels"]))
                else:
                    self.assertIs(type(case["expected"]), bool)
                validator.validate({"model": "clef", "state": case["state"], "questions": {"verdict": question}})
                Draft202012Validator(answer_schema).validate(fixture_answer(case))

    def test_nearest_rank_percentiles_and_empty_group(self):
        latency = benchmark.latency_summary([1001, 1000, 10, 20])
        self.assertEqual(latency["p50"], 20)
        self.assertEqual(latency["p95"], 1001)
        self.assertEqual(latency["mean"], 507.75)
        self.assertIsNone(benchmark.latency_summary([]))

    def test_failures_count_against_agreement_and_not_brier(self):
        case = CASES[0]
        records = [
            {"case_id": case["id"], "type": "noul", "latency_ms": 10, "matched": True,
             "answer": {"type": "noul", "noul": 0.8}},
            {"case_id": case["id"], "type": "noul", "latency_ms": 100, "matched": False,
             "answer": {"error": "CLEF_SERVICE_UNAVAILABLE"}},
        ]
        metrics = benchmark.summarize(records, [case])
        self.assertEqual(metrics["agreement_rate"], 0.5)
        self.assertEqual(metrics["valid_answer_agreement_rate"], 1)
        self.assertEqual(metrics["errors"], 1)
        self.assertAlmostEqual(metrics["brier_score"], 0.04)
        self.assertEqual(metrics["latency_ms"]["p95"], 100)
        self.assertEqual(metrics["successful_latency_ms"]["p95"], 10)

    def test_multiclass_brier_and_score_mae(self):
        choice_case = {"id": "route", "expected": "a"}
        choice = [{"case_id": "route", "type": "choice", "latency_ms": 1, "matched": True,
                   "answer": {"probabilities": {"a": 0.8, "b": 0.2}}}]
        self.assertAlmostEqual(benchmark.summarize(choice, [choice_case])["multiclass_brier_score"], 0.08)
        score_case = {"id": "grade", "type": "score", "expected": 2}
        score = [{"case_id": "grade", "type": "score", "latency_ms": 1, "matched": True,
                  "answer": {"score": 1.8}}]
        self.assertAlmostEqual(benchmark.summarize(score, [score_case])["mean_absolute_error"], 0.2)

    def test_scoring_boundaries_and_errors(self):
        self.assertTrue(benchmark.matches({"type": "noul", "expected": True}, {"noul": 0.5}))
        self.assertFalse(benchmark.matches({"type": "noul", "expected": False}, {"noul": 0.5}))
        self.assertTrue(benchmark.matches({"type": "score", "expected": 2}, {"score": 1.5}))
        self.assertFalse(benchmark.matches({"type": "score", "expected": 2}, {"score": 1.49}))
        self.assertFalse(benchmark.matches(CASES[0], {"error": "CLEF_INVALID_RESPONSE"}))

    def test_warmup_excluded_and_credentials_not_recorded(self):
        cases = [next(case for case in CASES if case["type"] == kind) for kind in ("noul", "choice", "score")]
        with patch.object(benchmark, "evaluate_case", side_effect=fixture_answer) as evaluate:
            with patch.dict(os.environ, {"CLEF_API_KEY": "DO_NOT_RECORD_SECRET", "CLEF_BACKEND_URL": "http://private-host.invalid/v1/systemone"}):
                result = benchmark.run_benchmark(cases, repeats=2, warmup=3)
        self.assertEqual(evaluate.call_count, 9)
        self.assertEqual(result["summary"]["requests"], 6)
        self.assertEqual(result["summary"]["matched"], 6)
        self.assertEqual(result["metadata"]["warmup_requests"], 3)
        serialized = json.dumps(result) + benchmark.markdown_report(result)
        self.assertNotIn("DO_NOT_RECORD_SECRET", serialized)
        self.assertNotIn("private-host", serialized)

    def test_error_only_report_is_renderable(self):
        with patch.object(benchmark, "evaluate_case", return_value={"error": "CLEF_SERVICE_UNAVAILABLE", "fallback_used": True}):
            result = benchmark.run_benchmark(CASES, repeats=1, warmup=0)
        self.assertIsNone(result["summary"]["valid_answer_agreement_rate"])
        report = benchmark.markdown_report(result)
        self.assertIn("N/A", report)
        self.assertIn("CLEF_SERVICE_UNAVAILABLE", report)
        self.assertEqual(result["summary"]["errors"], 18)

    def test_cli_requires_explicit_endpoint_before_requests(self):
        environment = {key: value for key, value in os.environ.items() if key != "CLEF_BACKEND_URL"}
        completed = subprocess.run([sys.executable, str(ROOT / "benchmarks/run.py")], env=environment,
                                   capture_output=True, text=True, timeout=5)
        self.assertEqual(completed.returncode, 2)
        self.assertIn("Set CLEF_BACKEND_URL explicitly", completed.stderr)


if __name__ == "__main__":
    unittest.main()
