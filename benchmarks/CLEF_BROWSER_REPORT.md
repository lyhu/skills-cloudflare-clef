**English** | [简体中文](CLEF_BROWSER_REPORT_zh.md)

# Clef-Browser Navigation Feasibility Report

**Core Finding**: Across constrained read-only hyperlink navigation scenarios, the Clef decision prototype demonstrated rock-solid reliability: 3 target tasks evaluated across 3 trials each **completed successfully (9/9 passed)**. Fully autonomous general browser agents remain an area requiring further engineering.

---

## 1. Experimental Design & Measured Telemetry

Evaluation Date: 2026-10-04 · Deployment: Live private Clef HTTP backend + `ego-browser` active session.
Experimental Design: 3 deterministic navigation tasks executed across 3 independent cycles (order: ABC / CBA / BAC). Single steps leveraged the `choice` primitive with a 0.6 confidence threshold and a budget of 5 steps / 45 seconds per run. Completion required both the model's `DONE` emission and independent goal URL verification.

| Target Navigation Task | Success Rate | Median End-to-End Latency | Median Cumulative Decision Latency | Requests per Task |
| :--- | :---: | :---: | :---: | :---: |
| **GitHub Repo → CONTRIBUTING.md** | 3/3 | 4.82 s | 2.18 s | 2 |
| **GitHub Repo → src/cli.ts** | 3/3 | 6.41 s | 3.20 s | 3 |
| **X Search → Specific Jev Case Tweet** | 3/3 | 5.42 s | 2.05 s | 2 |

- **Latency Breakdown**: End-to-end latency includes initial page navigation, DOM extraction, HTTP decision RPCs, CDP navigation dispatches, and async render waits; cumulative decision latency accounts for Python CLI invocation and network round-trips (median step latency range: 0.57s ~ 1.62s).
- **Candidate Scaling**: Evaluating 19 link candidates took ~1.6s; lightweight completion checks took ~0.6s.

---

## 2. Key Engineering Challenges & Discoveries

During initial X platform trials, the model accurately picked the target tweet anchor, but because tweet text rendered asynchronously, verification fired prematurely and triggered a `HANDOFF`. Introducing explicit readiness predicates (`waitForFunction`) resolved the issue, and all subsequent repeated trials passed with 100% success.
- Pre-readiness traces archived: [x-browser-before-readiness.json](reports/clef-browser/x-browser-before-readiness.json)
- Final verified runs and harness hashes: [results.json](reports/clef-browser/results.json)

---

## 3. Engineering Complexity & Scope Assessment

| Maturity Tier | Complexity | Status & Core Engineering Demands |
| :--- | :---: | :--- |
| **Current Prototype (Read-only Navigation)** | **Moderate (Shipped)** | Reuses existing browser session; runtime code enforces candidate whitelisting, deduplication, cycle detection, and independent assertions. |
| **Extended Controls (Forms/Menus/Selects)** | **Medium-High (Verified)** | Relies on robust DOM element extraction, deterministic known-value injection, explicit render predicates, and post-action assertions. |
| **Autonomous General Agent** | **Very High (Ongoing)** | Requires global task planning, visual layout understanding, multi-factor authentication, side-effect safety gates, and self-healing. |

> **Methodological Caveat**: This experiment isolated deterministic link navigation without an autoregressive LLM baseline; it is not presented as an end-to-end speedup comparison.

---

## 4. Default Routing Verification

Following internal Agent routing patterns, `scripts/install-browser.py` writes local configuration and injects routing hints into `ego-browser`. With explicit environment variables cleared, two Chinese natural language tasks completed smoothly:
- **Contributing Guide Navigation**: Loop latency 3.16s
- **X Original Tweet Discovery**: Loop latency 3.38s

Detailed execution traces: [default-routing.json](reports/clef-browser/default-routing.json).
