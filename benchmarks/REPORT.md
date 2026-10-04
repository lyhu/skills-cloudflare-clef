**English** | [简体中文](REPORT_zh.md)

# Clef Benchmark Report · 2026-10-04

**Live X (Twitter) search result extraction & semantic triage: Average task latency 9.04s → 4.02s, 2.25× speedup, 55.6% latency reduction.**

---

## 1. Browser Controlled Experiment

`jev typesafe` · X Latest · 8 public tweets (URL and text hash parity) · ego-browser · A–B–B–A crossover · 2 runs per arm.

| Arm | Mean Task Latency | Browser Scraping Latency | Semantic Triage Latency | Decision Turn Overhead |
| :--- | :--- | :--- | :--- | :--- |
| **Codex Baseline** | 9.04 s | 2.94 s | 6.10 s | 1 long-token inference round-trip |
| **Clef Arm** | 4.02 s | 2.81 s | 1.21 s | 1 HTTP request (8 concurrent Noul) |

- **Agreement**: Clef decisions matched Agent ground-truth labels across **16/16 trials** (8 unique test tweets across 2 runs).
- **Attribution**: Latency reduction stems from eliminating primary Agent LLM thinking and tool turn-taking; static URL navigation and DOM extraction remain programmatic.
- **Boundaries**: Controlled warm-session test. Agent latency captures model reasoning and tool RPC; pure GPU execution was not isolated. Excludes external link traversal, fact checking, and report drafting.

---

## 2. Live HTTP Decision Benchmarks

| Suite | Unique Cases | Valid Response Rate | Agreement Rate | Latency p50 | Latency p95 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [Smoke Suite](reports/live/smoke/report.md) | 18 | 54/54 | 54/54 | 375.7 ms | 521.1 ms |
| [BoolQ Subset](reports/live/boolq/report.md) | 24 | 72/72 | 66/72 | 386.4 ms | 538.4 ms |
| [BANKING77 (12-class adapted)](reports/live/banking77/report.md) | 24 | 72/72 | 69/72 | 415.8 ms | 555.9 ms |

- **Configuration**: 3 serial repeats per case, 3 warmup requests per suite, 0 retries; routed through Nginx to dedicated A800 GPU 7.
- **Sampling Notes**: Repeats evaluate latency variance without expanding unique cases; BANKING77 is adapted to 12 classes and does not reflect official 77-class results.
- **Operations Incident**: Initial batch requests encountered CUDA OOM due to active gradient tracking; patched with `@torch.inference_mode()` under authorization and retested. Full [Incident Post-Mortem](reports/live/service-incident.md) archived.

---

## 3. Related Documentation

- [Methodology & Protocols](METHODOLOGY.md) (Chinese: [METHODOLOGY_zh.md](METHODOLOGY_zh.md))
- [Data Attribution & Licensing](NOTICE.md) (Chinese: [NOTICE_zh.md](NOTICE_zh.md))
- [Per-Run Browser Traces](reports/live/browser/)
- [X Platform Deployment Evidence](X-APPLICATIONS.md) (Chinese: [X-APPLICATIONS_zh.md](X-APPLICATIONS_zh.md))
- [Validation & Verification Log](reports/live/validation.md)
