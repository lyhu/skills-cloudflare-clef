/** Live navigation pilot; call trial() inside one ego-browser TaskSpace. */
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { fileURLToPath } from "node:url";
import { runClefBrowser } from "../skills/cloudflare-clef/scripts/browser.mjs";

const repository = "https://github.com/jkudish/jev-browser";
export const tasks = [
  { id: "contributing", start: repository,
    goal: "Open the CONTRIBUTING.md file of jkudish/jev-browser to read contribution instructions.",
    expectedPath: "/jkudish/jev-browser/blob/main/CONTRIBUTING.md" },
  { id: "source", start: repository,
    goal: "Open the src/cli.ts source file in jkudish/jev-browser. Navigate through the src directory if necessary.",
    expectedPath: "/jkudish/jev-browser/blob/main/src/cli.ts" },
  { id: "x-browser", start: "https://x.com/search?q=Jev%20typesafe&src=typed_query",
    goal: "Open the original X post by Asteri (@Asteri_eth) listing Jev browser-agent projects. " +
      "It begins 'People already built a browser agent, a Claude Code bridge and a LangGraph router'. " +
      "Reach the original post detail page, not just the search results.",
    expectedPath: "/Asteri_eth/status/2106014727595807105" },
];

function allowed(url) {
  if (url.search || url.hash) {
    if (!(url.origin === "https://x.com" && url.pathname === "/search")) return false;
  }
  if (url.origin === "https://github.com") return url.pathname === "/jkudish/jev-browser" ||
    /^\/jkudish\/jev-browser\/(blob|tree)\/main\//.test(url.pathname);
  return url.origin === "https://x.com" &&
    (url.pathname === "/search" || /^\/\w+\/status\/\d+$/.test(url.pathname));
}

export async function trial(page, taskIndex, repeat) {
  const task = tasks[taskIndex];
  const started = performance.now();
  await page.goto(task.start);
  await page.waitForFunction((onX) => onX ? !!document.querySelector('article [data-testid="tweetText"]') :
    !!document.querySelector('main a[href*="/tree/main/src"]'), task.id === "x-browser", { timeout: 15000 });
  const setup_ms = performance.now() - started;
  const result = await runClefBrowser(page, {
    goal: task.goal, allowNavigation: allowed,
    verify: state => new URL(state.url).pathname === task.expectedPath,
    waitForPage: async p => p.waitForFunction(() => location.hostname === "x.com" ?
      !!document.querySelector('article [data-testid="tweetText"]') :
      document.readyState !== "loading" && !!document.querySelector("main"), undefined, {timeout:10000}),
    maxSteps: 5, maxSeconds: 45,
  });
  const record = { task: task.id, repeat, timestamp: new Date().toISOString(),
    setup_ms, end_to_end_ms: performance.now() - started, ...result };
  const output = fileURLToPath(new URL("./reports/clef-browser/", import.meta.url));
  await mkdir(output, { recursive: true });
  await writeFile(`${output}${task.id}-${repeat}.json`, JSON.stringify(record, null, 2) + "\n");
  return record;
}

export async function summarize() {
  const output = fileURLToPath(new URL("./reports/clef-browser/", import.meta.url));
  const records = [];
  for (const task of tasks) for (let repeat = 1; repeat <= 3; repeat++) {
    records.push(JSON.parse(await readFile(`${output}${task.id}-${repeat}.json`, "utf8")));
  }
  const driver = fileURLToPath(new URL("../skills/cloudflare-clef/scripts/browser.mjs", import.meta.url));
  const report = { model: "clef", transport: "Python stdlib client over HTTP", browser: "ego-browser",
    threshold: 0.6, max_steps: 5, repeats: 3,
    driver_sha256: createHash("sha256").update(await readFile(driver)).digest("hex"),
    records };
  await writeFile(`${output}results.json`, JSON.stringify(report, null, 2) + "\n");
  return records.map(r => ({task:r.task, repeat:r.repeat, status:r.status, reason:r.reason,
    end_to_end_ms:Math.round(r.end_to_end_ms), decision_ms:Math.round(r.decision_ms), calls:r.trace.length}));
}
