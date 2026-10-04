# Clef Decision Benchmark

UTC 2026-10-04T07:43:52.958992+00:00 · `benchmarks/datasets/boolq.json` · 24 cases × 3 repeats · 3 warmups excluded.

| Primitive | Valid / requests | Matched / requests | p50 ms | p95 ms | Brier / MAE |
| --- | --- | --- | --- | --- | --- |
| noul | 0/72 | 0/72 | N/A | N/A | N/A |

Transport: Direct LAN HTTP to user-provided service; no SSH tunnel; server hardware/load unverified. Model: `clef`; timeout 10.0 s; retries 0; errors 72.

Successful-request latency includes HTTP, inference, retries and validation. Nearest-rank percentiles. Noul threshold 0.5; exact Choice labels; Score tolerance 0.5. Brier/MAE exclude errors; agreement includes errors. Repeats are not independent examples.

Small selected subsets are diagnostic, not official leaderboard scores or calibration evidence. See [methodology](../../../METHODOLOGY.md) and [raw results](results.json).

Failures: `boolq-validation-0` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-1` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-2` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-3` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-4` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-5` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-6` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-7` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-8` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-9` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-10` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-11` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-12` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-13` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-14` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-20` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-27` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-32` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-36` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-38` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-39` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-41` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-43` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-52` (CLEF_SERVICE_UNAVAILABLE).
