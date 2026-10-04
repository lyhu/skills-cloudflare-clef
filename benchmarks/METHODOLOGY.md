**English** | [简体中文](METHODOLOGY_zh.md)

# Benchmark Methodology & Evaluation Protocols

This specification defines the metrics, evaluation protocols, and replication procedures for decision model benchmarks and live browser experiments.

---

## 1. Structured Decision Evaluation Protocol

### Dataset Design & Slices
- **Smoke (Smoke Suite)**: 18 original synthetic cases covering high-risk guardrail moderation (`noul`), routing categorization (`choice`), and code review evaluation (`score`).
- **BoolQ Subset**: 24 balanced samples (12 true / 12 false) drawn from the first 100 lines of the public validation set, preserving original passages and questions without text truncation.
- **BANKING77 Adapted Suite**: 12 representative intent classes with 2 test cases each (24 cases total). Adapted to a 12-class task to fit the single-request 64-candidate constraint; does not directly equate to the 77-class global benchmark.

### Metrics & Statistical Standards
- **Execution Protocol**: Each case is evaluated across 3 serial repeats, preceded by 3 unmeasured warmup requests per suite. No prompt engineering or fine-tuning was performed on evaluation samples.
- **Agreement Criteria**:
  - `noul`: Probability `>= 0.5` is considered positive.
  - `choice`: Exact string match between output key and ground-truth label.
  - `score`: Absolute difference between predicted score and ground-truth level `<= 0.5`.
- **Error Metrics**:
  - Backend errors count as disagreement. Brier scores and MAE are computed exclusively over valid non-error responses.
  - Multiclass Brier score computes the unnormalized mean sum of squared probability errors across all candidate categories.
- **Latency Measurement**:
  - Measured via Python client monotonic clock (`time.perf_counter`), capturing HTTP round-trip, model inference, retry backoff, JSON deserialization, and schema validation; excludes interpreter boot and cold model initialization.
  - p50 / p95 percentiles computed using Nearest-Rank (`ceil(p * N)`). Repeats measure latency variance, not independent samples.

### Replication Guide

```bash
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"

# 1. Run BoolQ evaluation
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --cases benchmarks/datasets/boolq.json \
  --repeats 3 --warmup 3 --output-dir benchmarks/reports/live/boolq

# 2. Run BANKING77 evaluation
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --cases benchmarks/datasets/banking77.json \
  --repeats 3 --warmup 3 --output-dir benchmarks/reports/live/banking77

# 3. Run Smoke evaluation
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --output-dir benchmarks/reports/live/smoke

# 4. Generate consolidated summary report
python3 benchmarks/report.py
```

> **Evaluation Caveats**: These subsets serve engineering validation of client protocols and inference latencies; they do not represent global leaderboard standings, universal production accuracy, global calibration, or contamination-audited scores.

---

## 2. In-Browser Live Comparison Experiment: X Platform Application Triage

### Experimental Task & Controlled Environment
- **Task Goal**: Search live X for `jev typesafe`, scrape and evaluate the first 8 loaded public tweets to determine which describe concrete Jev deployment use cases.
- **Controlled Variables**: Identical browser session, page context, search query URL, 600-character per-tweet text budget, triage prompt, and 0.5 Clef decision threshold.
- **DOM Sanitization**: Clones DOM nodes and strips injected third-party translation artifacts; normalizes whitespace and Unicode NFC prior to truncation, avoiding live DOM mutation.
- **Deterministic Navigation**: Both arms share the exact same underlying CDP operations: `goto` navigation, `waitForFunction` condition check, and `evaluate` extraction. This experiment strictly isolates and benchmarks **reading extracted text and rendering semantic verdicts**, not DOM pathfinding.

### Controlled Design (A-B-B-A Crossover)
- **Agent Baseline (Codex session)**: Reads extracted text evidence and submits 8 boolean decisions across an extra tool call round. Latency captures LLM inference, tool RPC overhead, and subsequent browser round-trips.
- **Clef Arm**: Dispatches a single lightweight HTTP request evaluating all 8 Noul propositions in batch, returning verdicts within the same browser tool execution without intermediate Agent round-trips.
- **Execution Order**: A-B-B-A alternation (2 runs per arm, labeled `normalized-*`) to eliminate one-way bias from caching or session warmup.

### Code Replication

Within the `ego-browser nodejs` environment, all runs share a single TaskSpace:

```javascript
const task = await taskSpace("Clef X triage pilot");
const bench = await import("file:///path/to/skills-cloudflare-clef/benchmarks/browser.mjs");

// 1. Run Agent Baseline Run 1
console.log(await bench.begin(task.page("p1"), "agent", "normalized-agent-1"));
// (Agent reads 8 tweets, then calls bench.finish("normalized-agent-1", eightBooleans))

// 2. Run Clef Arm Run 1
console.log(await bench.runClef(task.page("p1"), "normalized-clef-1", "http://127.0.0.1:8000/v1/systemone"));

// 3. Sequentially run normalized-clef-2 and normalized-agent-2; dispose TaskSpace upon completion
```

> **Methodological Scope**: This trial is a 4-run benchmark probe under controlled settings, designed to quantify round-trip and latency savings when offloading simple semantic verdicts to specialized decision models. It excludes deep open-ended investigation (e.g., following external links, deep fact-checking, or drafting). Static selectors and programmatic operations should remain native code; Clef is reserved for ambiguous semantic branches.
