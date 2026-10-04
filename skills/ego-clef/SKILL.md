---
name: ego-clef
description: Provides strongly-typed semantic decision support for ego-browser. Evaluates and selects browser actions (navigation, search, menus, filters, form filling, native selects, scrolling) via Clef while reusing existing browser sessions; depends on ego-browser and cloudflare-clef.
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: "Open Source Contributor"
---

**English** | [简体中文](SKILL_zh.md)

# Ego Clef Browser Semantic Decision Skill

This skill serves as an optional semantic decision-making layer for `ego-browser`. It invokes the underlying `cloudflare-clef` client to provide structured next-step evaluation within the browser interaction loop. The skill does not bundle model weights and does not launch redundant browser instances.

---

## 1. Runtime Requirements & Path Resolution

- **Environment**: Node.js 22+, Python 3.9+, and an accessible Clef service endpoint.
- **Dependencies**: Requires prior installation of `ego-browser` and `cloudflare-clef`.
- **Path Resolution**: Checks the `CLEF_SKILL_DIR` environment variable first; automatically falls back to sibling `cloudflare-clef`, `~/.agents/skills/cloudflare-clef`, or `~/.codex/skills/cloudflare-clef`. If the shared client is missing, control is yielded back to the primary agent.

---

## 2. Interaction Patterns & Core Interfaces

Within the same TaskSpace / Page, deterministic actions are executed directly. For scenarios requiring real-time page semantic inference, use the following interfaces:

- **`navigate(page, goal, options)`**: Multi-step hyperlink navigation, selecting the optimal path toward the goal from visible links.
- **`interact(page, goal, options)`**: Rich interactive controls supporting menu expansion, filter application, keyword search, known-value filling, and page scrolling.
- **Dynamic Policy Constraints**: The primary agent supplies `allowAction` (action and selector whitelist) and `verify` (independent post-action verification) per task. Default policies only allow same-origin navigation and scrolling; click, input, and submit operations must be strictly scoped.
- **Input Safety Standards**: `values` only passes predetermined, non-sensitive input dictionaries (e.g., search keywords). Clef only performs key selection, and the runtime injects the mapped value verbatim. Generating credentials, passwords, or CAPTCHA answers via model inference is strictly prohibited.

---

## 3. Architectural Division & Safety Boundaries

| Role | Core Responsibilities |
| :--- | :--- |
| **Clef Engine** | Evaluates current page observations (up to 24 candidates) and outputs a strongly-typed next action, `DONE`, or `HANDOFF`. |
| **ego-browser** | Manages underlying CDP sessions, DOM events, page rendering, and scrolling execution. |
| **Primary Agent** | Controls high-level task planning, permission gating, input value provision, independent verification, and fallback handling. |

### Handoff & Fallback Contract
The loop terminates immediately with a `handoff` back to the primary agent within the existing browser session under the following conditions:
- Missing configuration, network failure, or single-step confidence below threshold (default `0.6`).
- No substantive progress detected across steps (infinite loop guard) or budget exceeded (default 6 steps, maximum 20).
- Highly sensitive contexts encountered: authentication/login, payment transactions, content publication/deletion, file downloads, Canvas/drag-and-drop, or native modal dialogs.

---

## 4. Observability & References

- **Telemetry Logs**: Browser interaction streams are recorded to `~/.local/state/clef-browser/events.jsonl`, and underlying model calls are recorded to `~/.local/state/clef/events.jsonl` (`source: ego-clef`), correlated via `call_id` and `run_id`.
- **Detailed Reference**: For full API signatures, action schemas, and setup instructions, see [references/browser.md](references/browser.md) (or [references/browser_zh.md](references/browser_zh.md)).
