# Measurement protocol

## Decision datasets

- Smoke: 18 synthetic cases covering risk gates, routing and ordinal review.
- BoolQ: 24 public validation cases, balanced 12/12. First rows per label, no truncation.
- BANKING77: 24 public test utterances, 2 per 12 selected intents. **12-way adaptation**;
  the deployed service permits at most 64 candidates, so this is not the original 77-way benchmark.
- Three serial repetitions, three unmeasured warmups per suite. No tuning against these examples.
- Noul threshold `>= 0.5`; Choice exact label; Score absolute error `<= 0.5`.
- Errors count as incorrect. Brier and MAE include valid answers only. Multiclass Brier
  sums squared probability errors over all labels, without class-count normalization.
- Latency is `perf_counter` wall time around the Python client: HTTP, inference, retries,
  parsing and validation included; process startup and model load excluded.
- p50/p95 use nearest rank `ceil(p*N)`. Repetitions measure latency variation, not independent accuracy samples.
- No private endpoint, credentials or source code are recorded. Hardware/load are not independently measured.

Run each suite with an explicit endpoint:

```bash
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --cases benchmarks/datasets/boolq.json \
  --repeats 3 --warmup 3 --output-dir benchmarks/reports/live/boolq
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --cases benchmarks/datasets/banking77.json \
  --repeats 3 --warmup 3 --output-dir benchmarks/reports/live/banking77
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --output-dir benchmarks/reports/live/smoke
```

Generate the concise combined report after all suites and the four normalized browser trials:

```bash
python3 benchmarks/report.py
```

The generator rejects differing URL/text hashes or browser-driver versions.
See [dataset attribution](NOTICE.md). These diagnostic subsets do not estimate official
leaderboard scores, production accuracy, probability calibration or training-data contamination.

## Live browser pilot: X application triage

Task: search `jev typesafe` on X Latest, inspect the first eight loaded posts,
judge which describe concrete Jev applications. Same browser page, session, search URL,
600-character budget per post, relevance instruction and 0.5 Clef threshold.
DOM clones exclude Immersive Translate's appended translation nodes; whitespace and NFC
are normalized before truncation. The live DOM is not modified.

Both arms use the same three ego-browser calls: `goto`, condition-based
`waitForFunction`, DOM extraction with `evaluate`. Navigation is deterministic;
this test measures replacing the **post-reading judgment turn**, not autonomous DOM navigation.

- **Agent arm:** current Codex session reads the extracted evidence and submits eight boolean
  judgments in the next tool invocation. Decision time spans observation to submitted labels,
  including LLM reasoning, tool transport and the second ego-browser invocation.
  Exact base model ID, inference-only time and token counts are unavailable.
- **Clef arm:** one native HTTP request evaluates all eight Noul questions in one batch,
  then returns judgments within the same browser invocation. No agent turn during triage;
  no retry. HTTP time and returned usage are recorded.
- Final order A–B–B–A, two trials per arm, recorded as `normalized-*`. Earlier pilot
  records remain available, including the OOM failure and the input-translation mismatch;
  they are excluded from the controlled comparison. Search and agent familiarity were
  already warm. Start clocks inside the
  browser script; initial tool launch is excluded. End clocks after labels are available.
- No editing or unrelated tools occur between an agent-arm observation and its submitted labels.
- Live inputs may change. Compare URL **and** text hash across trials before computing
  paired judgment agreement; different inputs invalidate an identical-corpus comparison.
- Agent judgments are a reference, not independent ground truth. Post claims and performance
  numbers are not externally validated. Classification speed is not reading comprehension proof.
- Raw published records contain only URLs, hashes and labels; private scratch files contain
  bounded public snippets. Do not publish account snapshots or scratch files.

Reproduce inside `ego-browser nodejs` using one task space for the whole experiment:

```javascript
const task = await taskSpace("Clef X triage pilot"); // create once; reuse its numeric ID
const bench = await import("file:///absolute/path/skills-cloudflare-clef/benchmarks/browser.mjs");
console.log(await bench.begin(task.page("p1"), "agent", "normalized-agent-1"));
// Next invocation: read the eight posts, then call bench.finish("normalized-agent-1", eightBooleans).
// Clef arm (full endpoint passed explicitly because browser runtimes may not inherit shell env):
console.log(await bench.runClef(task.page("p1"), "normalized-clef-1", "http://127.0.0.1:8000/v1/systemone"));
// Run normalized-clef-2 then normalized-agent-2; finish the task space once after the experiment.
```

This is a warm-session, four-trial harness pilot. It does not establish statistical
significance, cold-start performance, benefits for all browser tasks, or a complete
research workflow including opening sources, verifying claims and writing a report.
Exact selectors and fixed actions should remain ordinary code; use Clef where semantic judgment is needed.
