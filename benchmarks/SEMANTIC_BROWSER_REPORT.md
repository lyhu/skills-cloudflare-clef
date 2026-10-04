**English** | [简体中文](SEMANTIC_BROWSER_REPORT_zh.md)

# Ego Clef Semantic Web Interaction Validation Report

Validation Date: 2026-10-04 · Environment: Live `ego-browser` + Local Clef HTTP Service · Decision Threshold: 0.6.

This report documents the functional validation of extending Clef to site-agnostic semantic DOM control decisions. Across controlled HTML fixtures and live Python documentation sites, typical interactions such as menu expansion, form filling, native dropdown selection, button clicking, and Enter key submission were evaluated. All task completions are independently verified via DOM/URL state assertions in code; relying solely on model probability as proof of completion is strictly forbidden.

---

## 1. Interactive Task Benchmark Performance

| Task Scenario | Action Sequence | Effective Decisions | End-to-End Loop Latency | Verification Verdict |
| :--- | :--- | :---: | :---: | :---: |
| **Expand Navigation Menu** (Controlled Fixture) | `click` | 1 | 0.60 s | Verified |
| **Form Filling & Submission** (Controlled Fixture) | `fill` → `click` | 2 | 2.31 s | Verified |
| **Category Selection & Filtering** (Controlled Fixture) | `click` → `select` → `click` | 3 | 1.94 s | Verified |
| **Docs Search & Enter Submission** (Public Site) | `fill` → `press` | 2 | 1.96 s | Verified |

> **Note**: Loop latency encompasses page observation capture, Python client bridge, HTTP round-trip, browser CDP action execution, DOM mutation wait, and final verification check; initial page navigation is excluded. Every task correlates directly with local event logs via `run_id`.

---

## 2. Key Engineering Challenges & Mitigations

Prototype debugging surfaced three typical engineering issues, which were systematically resolved:
1. **Full-Page DOM Candidates Exceeding Context Limits**:
   - *Issue*: Directly serializing all DOM nodes easily exceeded the 4,096-token service limit.
   - *Solution*: Pruned candidate extraction to only include interactive, visible elements with semantic roles (capped at 24 candidates per step).
2. **Premature Form Submission Before Input Population**:
   - *Issue*: Models exhibited a tendency to click Submit before input fields were filled.
   - *Solution*: Primary agent policies inject pre-condition constraints (e.g., target input must hold a non-empty value before submit actions become eligible).
3. **SPA Wait Conditions & Rendering Race Conditions**:
   - *Issue*: Conflating ARIA landmarks with raw HTML tags led to triggering completion checks before results finished rendering.
   - *Solution*: Bound checks to container-specific readiness anchors (e.g., `dataset.ready === 'true'`).

Early debugging traces are preserved in [development-findings.json](reports/semantic-browser/development-findings.json).

---

## 3. Boundaries & Reproduction Guide

- **Scope & Limitations**: This validation confirms the viability of site-agnostic semantic DOM decisions. Screenshots/Canvas, complex drag-and-drop, iframe/Shadow DOM isolation, file downloads, authentication/login, payments, and modal dialogs are strictly handled by the primary agent.
- **Raw Data**: [results.json](reports/semantic-browser/results.json).

### Local Reproduction Steps

```bash
# 1. Start local controlled fixture server
python3 -m http.server 8878 --bind 127.0.0.1 --directory benchmarks/fixtures
```

In an `ego-browser nodejs` environment configured with endpoint credentials:
```javascript
const bench = await import("/path/to/benchmarks/semantic-browser.mjs");
const task = await taskSpace("Semantic Browser Test");
const page = task.page("p1");

// Run controlled fixture trials (index: 0, 1, 2)
await bench.trial(page, "http://127.0.0.1:8878/semantic.html", 0);

// Run live documentation search trial
await bench.pythonSearchTrial(page);

await task.finish({ keep: [] });
```
