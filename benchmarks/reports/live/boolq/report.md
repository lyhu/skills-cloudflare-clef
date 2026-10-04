# Clef Decision Benchmark

UTC 2026-10-04T07:54:11.830373+00:00 · `benchmarks/datasets/boolq.json` · 24 cases × 3 repeats · 3 warmups excluded.

| Primitive | Valid / requests | Matched / requests | p50 ms | p95 ms | Brier / MAE |
| --- | --- | --- | --- | --- | --- |
| noul | 72/72 | 66/72 | 386.35 | 538.36 | 0.061580 |

Transport: LAN HTTP via Nginx to A800 GPU 7; inference_mode patch applied; no concurrent benchmark requests. Model: `clef`; timeout 10.0 s; retries 0; errors 0.

Successful-request latency includes HTTP, inference, retries and validation. Nearest-rank percentiles. Noul threshold 0.5; exact Choice labels; Score tolerance 0.5. Brier/MAE exclude errors; agreement includes errors. Repeats are not independent examples.

Small selected subsets are diagnostic, not official leaderboard scores or calibration evidence. See [methodology](../../../METHODOLOGY.md) and [raw results](results.json).

Failures: `boolq-validation-12` (0.0138), `boolq-validation-27` (0.5742).
