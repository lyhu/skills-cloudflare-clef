/** Local metadata-only JSONL log. Logging failures never change navigation behavior. */
import { appendFile, mkdir } from "node:fs/promises";
import { homedir } from "node:os";
import { dirname, join } from "node:path";

export const browserLogFile = join(homedir(), ".local/state/clef-browser/events.jsonl");
const fields = ["event", "run_id", "site", "transport", "outcome", "action", "confidence",
  "duration_ms", "model", "status", "reason", "decision_attempts", "successful_decisions",
  "error_code", "http_status"];

export async function appendBrowserEvent(event, file = browserLogFile) {
  const entry = { timestamp: new Date().toISOString() };
  for (const key of fields) if (event[key] !== undefined) entry[key] = event[key];
  try {
    await mkdir(dirname(file), { recursive: true, mode: 0o700 });
    await appendFile(file, JSON.stringify(entry) + "\n", { mode: 0o600 });
    return true;
  } catch { return false; }
}
