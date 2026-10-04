# Clef Decision Benchmark

UTC 2026-10-04T07:53:40.436745+00:00 · `benchmarks/cases.json` · 18 cases × 3 repeats · 3 warmups excluded.

| Primitive | Valid / requests | Matched / requests | p50 ms | p95 ms | Brier / MAE |
| --- | --- | --- | --- | --- | --- |
| noul | 18/18 | 18/18 | 397.02 | 932.94 | 0.000092 |
| choice | 18/18 | 18/18 | 366.49 | 471.28 | 0.001053 |
| score | 18/18 | 18/18 | 366.67 | 645.82 | 0.042267 |

Transport: LAN HTTP via Nginx to A800 GPU 7; inference_mode patch applied; no concurrent benchmark requests. Model: `clef`; timeout 10.0 s; retries 0; errors 0.

Successful-request latency includes HTTP, inference, retries and validation. Nearest-rank percentiles. Noul threshold 0.5; exact Choice labels; Score tolerance 0.5. Brier/MAE exclude errors; agreement includes errors. Repeats are not independent examples.

Small selected subsets are diagnostic, not official leaderboard scores or calibration evidence. See [methodology](../../../METHODOLOGY.md) and [raw results](results.json).
