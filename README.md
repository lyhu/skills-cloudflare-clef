**English** | [简体中文](README_zh.md)

# Cloudflare Clef Agent Skill

A strongly-typed System One decision skill for AI coding agents such as Claude Code, Codex CLI, Google Antigravity, Grok Build, Pi, and DeepSeek Harness. Powered by locally or privately hosted **Cloudflare Clef (Qwen3.8-27B)**, providing instant structured verdicts (`noul`, `choice`, `score`) and calibrated probabilities.

Adheres to the [Agent Skills Specification](https://agentskills.io/specification) and [typesafe-ai/skills](https://github.com/typesafe-ai/skills) directory structure standards. This is an independent open-source project and is not an official release by Cloudflare or TypeSafe.

---

## Skill Architecture

This repository distributes two decoupled, standalone skills that can be installed independently or together:

| Skill | Primary Role | Runtime Dependencies |
| :--- | :--- | :--- |
| **[cloudflare-clef](skills/cloudflare-clef/SKILL.md)** | Generic typed decision engine: semantic routing, high-risk action gating, candidate selection, ordinal scoring | Python 3.9+ standard library, Clef endpoint |
| **[ego-clef](skills/ego-clef/SKILL.md)** | Semantic browser decision layer for `ego-browser`: element interaction, link navigation, execution observability | cloudflare-clef, ego-browser, Node.js 22+ |

- `cloudflare-clef` can be used standalone by any agent or backend service without browser dependencies.
- `ego-clef` delegates inference to the generic client while leaving browser execution and completion verification to the host browser skill.

---

## Key Features

- ⚡️ **Single-Forward Instant Decisions**: Built on a non-autoregressive architecture, eliminating the token overhead and latency of generating free-form text, returning structured verdicts and calibrated probabilities directly.
- 🎯 **Three Typed Decision Primitives**:
  - `noul`: Single proposition probability (`[0, 1]`), quantifying risk and prerequisite validity.
  - `choice`: Multi-class semantic routing (1–64 candidates), dispatching directly to business handlers.
  - `score`: Ordinal gradient scoring (0-based weighted expectation `sum(i * p)`), evaluating code quality and test completeness.
- 🪶 **Zero External Client Dependencies**: Requires only the **Python 3.9+ standard library**. The client downloads no model weights and requires no heavy inference frameworks.
- 🛡️ **Strict Isolation & Resilience**:
  - **Prompt Injection Defense**: Physical separation of business context data (`--state`) and criteria questions (`--instructions`).
  - **Fail-Closed Semantics**: High-risk operations are strictly blocked when services are unavailable or decisions exhibit high uncertainty.
  - **Bounded Exponential Backoff**: Automatic retry protection against transient network failures with strict redirect isolation to protect credentials.
- 🔌 **Native Multi-Agent Ecosystem Support**: Ready out-of-the-box for Claude Code, Codex CLI, Google Antigravity, Grok Build, Pi, and DeepSeek Harness (dsh).

---

## Measured Performance & Gains

In a live "search result inspection and scenario triage" benchmark, offloading semantic evaluation from the main agent to local Clef:
**End-to-end task latency dropped from 9.04s to 4.02s — a 2.25× speedup (55.6% time reduction).**

| Benchmark Phase | Main Agent Direct Reasoning | Clef Batch Inference | Performance Improvement |
| :--- | :--- | :--- | :--- |
| **End-to-End Task Duration** | 9.04 s | 4.02 s | **2.25x Speedup (-55.6%)** |
| Page Navigation & DOM Extraction | 2.94 s | 2.81 s | Comparable |
| **Semantic Judgment Stage** | 6.10 s | 1.21 s | **80.2% Latency Reduction** |
| Context & Token Overhead | 1 long reasoning turn with full context | 1 lightweight HTTP call (8 parallel propositions) | Substantial token savings |

### Accuracy & Agreement Verification
- **BANKING77 12-Class Adaptation** (24 samples × 3 repeats): **95.8%** agreement rate.
- **BoolQ Validation Subset** (24 full passage-question samples × 3 repeats): **91.7%** agreement rate.
- For complete benchmark methodology and raw datasets, see the [Benchmark Report](benchmarks/REPORT.md) and [Methodology Specification](benchmarks/METHODOLOGY.md).

---

## Quick Start

### 1. Configure Endpoint and Run

```bash
# 1. Clone the repository
git clone https://github.com/lyhu/skills-cloudflare-clef.git
cd skills-cloudflare-clef

# 2. Configure Clef service endpoint (local or private GPU)
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"

# 3. Execute a semantic routing evaluation
python3 skills/cloudflare-clef/scripts/evaluate.py \
  --state 'Checkout requests return HTTP 500 and customers cannot place orders.' \
  --type choice \
  --instructions 'Which handler should investigate?' \
  --choices technical billing review
```

### 2. Output Schema

The CLI outputs schema-validated JSON to stdout (exit code `0` on success):

```json
{
  "type": "choice",
  "choice": "technical",
  "confidence": 0.92,
  "probabilities": {
    "technical": 0.92,
    "billing": 0.03,
    "review": 0.05
  }
}
```

> **Private Network Tip**: If your Clef inference service is on a remote private server, forward the port via SSH:
> ```bash
> ssh -N -L 8000:127.0.0.1:8000 user@clef-host
> ```

---

## Decision Primitives & Scenarios

| Primitive | Definition | CLI Parameters | Output Schema |
| :--- | :--- | :--- | :--- |
| **`noul`** | Probability of a single proposition being true | No candidates required | `noul`: float in `[0, 1]` (values near 0.5 denote high uncertainty) |
| **`choice`** | Single selection from a discrete set of candidates | `--choices` (1–64 unique labels) | `choice`, `confidence`, `probabilities` |
| **`score`** | Weighted score across an ordered ordinal gradient | `--levels` (1–16 ascending labels) | `score` (expected value `sum(i * p)` based on 0..N-1), `confidence`, `legend`, `probabilities` |

### Scenario 1: Pre-Execution Safety Gating (Noul)
Assess whether a destructive shell command risks destroying unexpected data:

```bash
python3 skills/cloudflare-clef/scripts/evaluate.py \
  --state 'command: rm -rf ./build; cwd: /work/project; scope: generated build files only' \
  --type noul \
  --instructions 'Could this command destroy valuable data outside the generated build directory?'
```
> **Safety Directive**: This evaluation does not constitute execution authorization. If the service is unreachable or the score indicates high uncertainty, the host system must halt automation and fail-closed to manual review.

### Scenario 2: Workflow Semantic Routing (Choice)
Replace prompt-based classification by dispatching tickets or user requests directly to handlers:

```bash
python3 skills/cloudflare-clef/scripts/evaluate.py \
  --state 'Customer reports being charged twice for subscription renewal.' \
  --type choice \
  --instructions 'Which department should handle this ticket?' \
  --choices billing tech_support fraud review
```

### Scenario 3: Automated Code Review Grading (Score)
Quantify quality or test completeness across focused diffs:

```bash
python3 skills/cloudflare-clef/scripts/evaluate.py \
  --state 'Diff adds retry handling. Tests cover timeout and success, but omit HTTP 429.' \
  --type score \
  --instructions 'How complete is test coverage for retry behavior?' \
  --levels 'No relevant tests' 'Some retry cases tested' 'All specified retry cases tested'
```

---

## Installation & Platform Setup

### 💬 Agent Conversation Setup Prompts (Recommended)

Copy and send any of the following natural-language prompts directly to your coding agent (Claude Code, Codex, Antigravity, etc.) to automate installation and verification:

#### Standard Local Installation
> **📋 Copy & paste to your Agent**:
>
> "Please install and configure the `cloudflare-clef` decision skill in this project:
> 1. Run `npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef` to install the skill.
> 2. Verify that Python 3.9+ is available locally.
> 3. Set the backend service endpoint: `export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"`.
> 4. Run a quick Noul evaluation test to verify connectivity and output."

#### Remote / Private GPU Server Setup
> **📋 Copy & paste to your Agent**:
>
> "Please connect to our private Clef decision service and configure the skill:
> 1. Install the skill: `npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef`.
> 2. Establish SSH port forwarding: `ssh -N -L 8000:127.0.0.1:8000 <user>@<clef-host>`.
> 3. Set the endpoint variable: `export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"`.
> 4. Run an evaluation test to confirm connectivity and verdict parsing."

#### Cloudflare Official Workers AI Hosted Setup
> **📋 Copy & paste to your Agent**:
>
> "Please connect `cloudflare-clef` to Cloudflare official Workers AI:
> 1. Install the skill: `npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef`.
> 2. Set the official endpoint: `export CLEF_BACKEND_URL="https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/ai/run/@cf/cloudflare/clef"`.
> 3. Set the authentication token: `export CLEF_API_KEY="<CLOUDFLARE_AUTH_TOKEN>"`.
> 4. Run a test Noul query to confirm successful communication."

---

### Command-Line Installation

Install via the official [skills CLI](https://github.com/vercel-labs/skills):

```bash
# Global installation (available across all workspaces)
npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -g

# Local installation (current project only)
npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef
```

### Platform Compatibility Matrix

| Platform | Install Command / Target Path | Notes |
| :--- | :--- | :--- |
| **Claude Code** | `npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -a claude-code`<br>or symlink to `.claude/skills/cloudflare-clef` | Automatically discovers project-level skills |
| **Codex CLI** | `npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -a codex`<br>or symlink to `.agents/skills/cloudflare-clef` | Supports `$cloudflare-clef` invocations and intent routing |
| **Google Antigravity** | `npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -a antigravity` | Installed to workspace `.agents/skills/` |
| **Grok Build** | `npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -a grok` | Mapped to `.grok/skills/` |
| **Pi Coding Agent** | `pi install git:github.com/lyhu/skills-cloudflare-clef` | Native package management and `/skill:cloudflare-clef` |
| **DeepSeek Harness (dsh)** | Copy to `~/.agents/skills/cloudflare-clef` | Automatic discovery via filesystem skill provider |

### Local Development or Git Submodule
```bash
# Direct local path installation
npx skills add /path/to/skills-cloudflare-clef --skill cloudflare-clef

# Or add as a Git Submodule
git submodule add https://github.com/lyhu/skills-cloudflare-clef.git .vendor/skills-cloudflare-clef
mkdir -p .agents/skills
ln -s "$PWD/.vendor/skills-cloudflare-clef/skills/cloudflare-clef" .agents/skills/cloudflare-clef
```

---

## Protocol Contract & Configuration

The client features a unified adapter layer supporting both **self-hosted System One endpoints** and **Cloudflare official Workers AI**, automatically unboxing and aligning response structures.

### Dual-Mode Setup

#### Mode A: Self-Hosted / Private GPU Deployment (Default)
Optimized for ultra-low latency, strict privacy, and zero external dependency:
```bash
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"
export CLEF_MODEL="clef"
```

#### Mode B: Cloudflare Workers AI Managed Service
Optimized for zero-maintenance, global edge availability:
```bash
export CLEF_BACKEND_URL="https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/ai/run/@cf/cloudflare/clef"
export CLEF_API_KEY="<CLOUDFLARE_AUTH_TOKEN>"
export CLEF_MODEL="clef"  # Also supports @cf/cloudflare/clef or clef-flash
```

---

### Self-Hosted vs Official Workers AI Comparison

| Dimension | Self-Hosted Deployment (System One) | Workers AI Cloud Service | Client Compatibility Layer |
| :--- | :--- | :--- | :--- |
| **Endpoint** | `http://<ip>:<port>/v1/systemone` | `https://api.cloudflare.com/client/v4/accounts/{id}/ai/run/@cf/cloudflare/clef` | Seamlessly switched via `CLEF_BACKEND_URL` |
| **Authentication** | Default unauthenticated; supports Bearer tokens | Requires Cloudflare API Token | Injected automatically via `CLEF_API_KEY` |
| **Payload Schema** | `{"model": "...", "state": ..., "questions": {...}}` | `{"model": "...", "state": ..., "questions": {...}}` | **Identical** underlying decision schema |
| **Envelope** | Direct `{"answers": {...}, "usage": {...}}` | Envelope `{"result": {...}, "success": true}` | **Auto-unboxed**: extracts `result.answers` |
| **Error Format** | HTTP status + structured JSON error | `errors: [{"code": ..., "message": ...}]` | Normalized into standard client errors |
| **Context Limit** | Defaults to **4,096 tokens** | Up to **65,536 tokens** | Monitored to prevent silent context drops |
| **Context Overflow** | **Strict Fail-closed**: HTTP 413, **no silent truncation** | Silently truncates long text | Local mode guarantees risk assessment fidelity |
| **Candidate Budget** | Choice 1–64; Score 1–16 levels | Choice 2–255; Score 2–10 levels | Fully covers operational needs |
| **Multimodal** | Client focuses on text-only subsets | Supports `images` parameter (up to 4 base64/data URLs) | Extensible for upcoming image features |

---

### Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `CLEF_BACKEND_URL` | `http://127.0.0.1:8000/v1/systemone` | Full HTTP(S) endpoint URL (local or Cloudflare v4) |
| `CLEF_MODEL` | `clef` | Model alias (`clef`, `clef-flash`, `@cf/cloudflare/clef`, etc.) |
| `CLEF_API_KEY` | *(Empty)* | Optional Bearer token or Cloudflare API auth token |
| `CLEF_TIMEOUT` | `10.0` | Socket connect and read timeout in seconds |
| `CLEF_MAX_RETRIES` | `2` | Max retries for transient network failures (0–5, backoff 0.5s/1.0s) |

### Error Handling & Fail-Closed Contract

On failure, the CLI outputs structured JSON errors and exits with non-zero exit code (`1`):
```json
{
  "error": "CLEF_SERVICE_UNAVAILABLE",
  "message": "Connection failed or timed out after retries",
  "fallback_used": true
}
```

- **Error Codes**: `CLEF_INVALID_INPUT`, `CLEF_INVALID_CONFIG`, `CLEF_HTTP_ERROR`, `CLEF_INVALID_RESPONSE`, `CLEF_SERVICE_UNAVAILABLE`.
- **Retry Scope**: Only transient socket errors, timeouts, and HTTP 429/500/502/503/504 trigger retries; 400/401/403/413 fail immediately.

---

## Integration Examples

### 1. Local Logging & Statistics

Metadata telemetry is enabled by default for CLI calls, Python/TypeScript templates, and `ego-clef`. Model logs are stored at `~/.local/state/clef/events.jsonl`, and browser workflow logs at `~/.local/state/clef-browser/events.jsonl`.

Ask your Agent: **"Show Clef log statistics"** or **"Show today's ego-clef calls"** to get a summary without running commands manually. Alternatively, inspect via CLI:

```bash
# View summary for all calls today
python3 skills/cloudflare-clef/scripts/log_stats.py --today

# Filter by ego-clef source and output JSON
python3 skills/cloudflare-clef/scripts/log_stats.py --today --source ego-clef --json
```

Logs record sanitized metadata only (no raw prompts, text snippets, or credentials). See [Logging Specification](skills/cloudflare-clef/references/logging.md) ([中文版](skills/cloudflare-clef/references/logging_zh.md)).

---

### 2. ego-clef: Semantic Browser Decision Layer

Provides site-agnostic next-step semantic decision making (navigation, search, menus, filters, known-value filling, dropdowns, and scrolling) inside existing `ego-browser` sessions without launching redundant browser instances.

```bash
# Install both skills
npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef
npx skills add lyhu/skills-cloudflare-clef --skill ego-clef

# Run one-time setup
python3 skills/ego-clef/scripts/install-browser.py --endpoint "http://127.0.0.1:8000/v1/systemone"
```

**Architecture & Roles**:
- **Clef Engine**: Selects the next action from visible DOM elements (up to 24 candidates).
- **ego-browser**: Handles CDP execution, page rendering, and DOM events.
- **Host Agent**: Enforces action whitelists (`allowAction`), provides exact known input values, and performs independent goal verification (`verify`).
- High-risk operations (logins, payments, publishing, file downloads) immediately hand off to standard `ego-browser` workflows.
- See the [Browser Integration Guide](skills/ego-clef/references/browser.md) ([中文版](skills/ego-clef/references/browser_zh.md)) and [Semantic Browser Evaluation](benchmarks/SEMANTIC_BROWSER_REPORT.md).

---

### 3. Python Integration
Using the bundled [Python template](skills/cloudflare-clef/templates/client.py):

```python
from client import route_issue

# Evaluate semantic routing
result = route_issue("Checkout requests fail with HTTP 500.")

# Extract verdict or apply fallback
handler = "review" if "error" in result else result["choice"]
print(f"Assigning to: {handler}")
```

### 4. TypeScript / Node.js Integration
Using the bundled [TypeScript template](skills/cloudflare-clef/templates/client.ts) (zero npm dependencies, safe process invocation):

```typescript
import { evaluateClef } from "./client.ts";

const result = await evaluateClef(
  "/path/to/skills/cloudflare-clef/scripts/evaluate.py",
  "Checkout service throws 500.",
  {
    type: "choice",
    instructions: "Which handler should investigate?",
    choices: ["technical", "billing", "review"],
  }
);

const handler = "error" in result ? "review" : result.choice;
console.log(`Handler: ${handler}`);
```

---

## Local Development & Validation

```bash
# Install dev dependencies (used only for schema and packaging validation)
python3 -m pip install -r requirements-dev.txt

# 1. Metadata, packaging, schema, and syntax validation
python3 scripts/validate.py

# 2. Run unit tests (covering protocol, retry backoff, and security boundaries)
python3 -m unittest discover -s tests -v

# 3. Run decision benchmark suite
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --repeats 3 --warmup 3
```

---

## References & License

- **Model Weights & Documentation**: [Cloudflare Clef on HuggingFace](https://huggingface.co/Cloudflare/clef)
- **Specifications**: [Agent Skills Specification](https://agentskills.io/specification) | [TypeSafe Decision Primitives](https://docs.typesafe.ai/primitives/noul)
- **License**: Code in this repository is licensed under [Apache-2.0](LICENSE). Benchmark datasets retain their original licenses as detailed in [NOTICE](benchmarks/NOTICE.md).


