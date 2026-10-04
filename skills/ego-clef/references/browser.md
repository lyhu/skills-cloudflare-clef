**English** | [简体中文](browser_zh.md)

# Clef-Browser Integration Guide

This guide explains how to integrate and use the Clef semantic decision layer within `ego-browser` for strongly-typed next-action evaluation during browser automation.

---

## 1. Natural Language Task Interaction

Once configured, users can describe browser tasks in everyday conversations without referencing Clef, underlying functions, or thresholds:

- "Search for `pathlib` in the current documentation site and locate core usage patterns."
- "Expand the top navigation menu, filter by the Tools category, and apply."
- "Fill in the known account name on the form and navigate to settings."

**Interaction Conventions**:
- Decision inference occurs internally within the Agent; under normal conditions, only final task results and citations are presented.
- Step-by-step decision trajectories and probability distributions are surfaced only when the user explicitly requests troubleshooting or benchmark evaluations.

---

## 2. State Verification & Observability

Browser execution logs are written to `~/.local/state/clef-browser/events.jsonl` with `0600` permissions (excluded from version control).

### Live Telemetry Streaming
```bash
tail -f ~/.local/state/clef-browser/events.jsonl
```

### Core Event Types
- **`event: decision`** (`transport: http`, `outcome: success`): Indicates Clef successfully returned and validated an action decision. Contains selected action kind, probability, inference latency, and model identifier.
- **`event: run`** (`status: completed`, `reason: verified`): Interaction loop completed successfully and passed the independent `verify` predicate.
- **`status: handoff`**: Control yielded back to the primary agent. Reasons include missing configuration, insufficient confidence (< 0.6), no-progress loop protection, or service timeouts.

### Telemetry Correlation & Statistics
Underlying model calls are simultaneously logged to `~/.local/state/clef/events.jsonl` (`source: ego-clef`), correlated via `call_id` and `run_id`:

```bash
# Query today's ego-clef decision statistics
python3 <cloudflare-clef-dir>/scripts/log_stats.py --today --source ego-clef

# Jointly analyze model calls and browser workflows without double counting
python3 <cloudflare-clef-dir>/scripts/log_stats.py --today --json \
  --file ~/.local/state/clef/events.jsonl \
  --file ~/.local/state/clef-browser/events.jsonl
```

---

## 3. One-Time Installation & Environment Setup

Install prerequisites: `cloudflare-clef`, `ego-clef`, and `ego-browser`.

### Initialization Script
```bash
python3 <skill-dir>/scripts/install-browser.py --endpoint "http://127.0.0.1:8000/v1/systemone"
```

**Configuration Notes**:
- Writes configuration to `~/.config/clef-browser/config.json` (`{"endpoint": "...", "enabled": true}`).
- Automatically backs up existing `~/.agents/skills/ego-browser/SKILL.md` and injects routing hints towards `ego-clef`. Fully idempotent.
- Precedence: Runtime `CLEF_BACKEND_URL` overrides the config file; disable automatic routing by setting `"enabled": false` in the configuration.

---

## 4. Control Interaction Mode (Interact)

Within an existing `ego-browser` page, drive multi-step UI control interactions via `interact`:

### Native Capabilities Matrix
| Action Type | Clef Role | Policy Requirements |
| :--- | :--- | :--- |
| **Link Navigation** | Selects optimal link target from extracted anchors | Default strictly same-origin; constrain to read-only paths |
| **Menu / Filter / Button** | Selects semantically relevant `click` or `hover` | Target selector must be explicitly whitelisted in `allowAction` |
| **Text Input** | Selects key from provided `values` dict; runtime injects verbatim | Supply only known, non-sensitive values; never let models fabricate credentials |
| **Select Dropdown** | Selects matching `<option>` present in DOM | Custom non-native selects handled via click sequences |
| **Deep Page Exploration** | Emits `scroll` action to trigger scrolling | DOM is re-captured after scroll for subsequent evaluation |
| **High-Risk Operations** | Auth/login, payments, delete/publish, Canvas, modals | Immediately yields back to primary agent for native handling |

### Code Example

```javascript
import { interact } from '/path/to/ego-clef/scripts/browser.mjs';

const permittedSelectors = new Set(['#search-query', '#category-select', '#submit-btn']);

const result = await interact(page, userGoal, {
  // Inject only known exact values and usage hints
  values: {
    search: { value: 'pathlib', hint: 'Documentation search keyword' }
  },
  // Strict action and element whitelist
  allowAction: action => permittedSelectors.has(action.selector) &&
    ['fill', 'select', 'click', 'press'].includes(action.kind),
  // Independent verification predicate; does not rely on model's DONE signal
  verify: async (state, p) => p.evaluate(() =>
    document.querySelector('#search-results')?.dataset.loaded === 'true'),
  maxSteps: 6,
  maxSeconds: 60,
});
```

---

## 5. Hyperlink Navigation Mode (Navigate)

For scenarios restricted to navigating between hyperlinks, use `runClefBrowser`. This mode extracts visible links from the DOM and delegates single-step URL selection to Clef.

### Code Example

```javascript
import { runClefBrowser } from '/path/to/ego-clef/scripts/browser.mjs';

const result = await runClefBrowser(page, {
  goal: 'Open the CONTRIBUTING.md file in the repository.',
  // Read-only origin and path whitelist
  allowNavigation: url => url.origin === 'https://github.com' && !url.search &&
    (url.pathname === '/owner/repo' || /^\/owner\/repo\/(blob|tree)\/main\//.test(url.pathname)),
  // Independent goal verification
  verify: state => new URL(state.url).pathname === '/owner/repo/blob/main/CONTRIBUTING.md',
  maxSteps: 5,
  maxSeconds: 45,
  threshold: 0.6,
  // Dynamic SPA wait condition
  waitForPage: p => p.waitForFunction(() => !document.querySelector('.loading-spinner'), { timeout: 8000 }),
});
```

### Safety & Guardrail Contracts
- **Candidate Budget**: Up to 24 deduplicated links per evaluation (filtering out current and visited URLs).
- **Independent Verification**: Status is marked as `completed` only when independent `verify` returns `true`. If the model outputs `DONE` without verification passing, control is yielded back.
- **Fail-Closed**: Step budget exceeded, repeated lack of progress, low confidence (< 0.6), or unexpected redirects trigger immediate handoff to the primary agent without unauthorized retries.
