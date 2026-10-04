import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, stat } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createServer } from "node:http";
import { appendBrowserEvent } from "../skills/ego-clef/scripts/browser-log.mjs";
import { runClefBrowser } from "../skills/ego-clef/scripts/browser.mjs";

test("logs metadata only, appends valid lines and restricts file permissions", async () => {
  const dir = await mkdtemp(join(tmpdir(), "clef-log-"));
  const file = join(dir, "logs/events.jsonl");
  try {
    for (const event of ["decision", "run"]) assert.equal(await appendBrowserEvent({ event,
      run_id: "example", outcome: "success", url: "https://secret.test/?token=secret",
      state: "private page", goal: "private task", apiKey: "secret", choice: "private label" }, file), true);
    const text = await readFile(file, "utf8");
    assert.equal(text.includes("private"), false);
    assert.equal(text.includes("secret"), false);
    assert.equal(text.trim().split("\n").map(JSON.parse).length, 2);
    assert.equal((await stat(file)).mode & 0o777, 0o600);
    assert.equal(await appendBrowserEvent({event:"run"}, dir), false);
  } finally { await rm(dir, { recursive: true }); }
});

test("real stdlib HTTP calls and completed run share an ID; failed response logs error", async () => {
  const dir = await mkdtemp(join(tmpdir(), "clef-http-log-"));
  const file = join(dir, "events.jsonl");
  const originalEndpoint = process.env.CLEF_BACKEND_URL;
  const originalLog = process.env.CLEF_LOG_PATH;
  let failing = false;
  let requests = 0;
  const server = createServer(async (request, response) => {
    requests++;
    let input = "";
    for await (const chunk of request) input += chunk;
    if (failing) { response.writeHead(401); response.end(); return; }
    const payload = JSON.parse(input);
    const state = JSON.parse(payload.state);
    const keys = Object.keys(payload.questions.verdict.criteria);
    const choice = state.url.endsWith("/docs") ? keys[0] : keys.at(-2);
    response.setHeader("Content-Type", "application/json");
    response.end(JSON.stringify({answers:{verdict:{type:"choice", choice, confidence:1,
      probabilities:Object.fromEntries(keys.map(k=>[k, k===choice ? 1 : 0]))}}}));
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  process.env.CLEF_BACKEND_URL = `http://127.0.0.1:${server.address().port}/v1/systemone`;
  process.env.CLEF_LOG_PATH = join(dir, 'calls.jsonl');
  try {
    let url = "https://example.test/docs";
    const page = { evaluate:async()=>({url,title:"Docs",text:"private page body",
      links:[{url:"https://example.test/docs/guide",text:"Guide",context:"private context"}]}),
      goto:async next=>{url=next;}, waitForFunction:async()=>{}, url:async()=>url };
    const options = { goal:"private task", allowNavigation:()=>true, verify:()=>true, logFile:file };
    const completed = await runClefBrowser(page, options);
    assert.equal(completed.status, "completed");
    assert.equal(completed.log_written, true);
    let entries = (await readFile(file, "utf8")).trim().split("\n").map(JSON.parse);
    assert.deepEqual(entries.map(e=>e.event), ["decision","decision","run"]);
    assert.equal(new Set(entries.map(e=>e.run_id)).size, 1);
    assert.equal(entries[2].successful_decisions, 2);
    assert.equal(entries[2].run_id, completed.run_id);
    const clientEvents = (await readFile(process.env.CLEF_LOG_PATH, 'utf8')).trim().split('\n').map(JSON.parse);
    const calls = clientEvents.filter(e=>e.event==='call');
    assert.equal(calls.length,2);
    assert.deepEqual(calls.map(e=>e.call_id),entries.slice(0,2).map(e=>e.call_id));
    assert.ok(calls.every(e=>e.source==='ego-clef' && e.run_id===completed.run_id));
    assert.equal(clientEvents.filter(e=>e.event==='attempt').length,2);
    assert.equal((await readFile(file,"utf8")).includes("private"), false);
    failing = true;
    const failed = await runClefBrowser(page, options);
    assert.equal(failed.reason, "decision_error");
    entries = (await readFile(file, "utf8")).trim().split("\n").map(JSON.parse);
    assert.equal(entries[3].outcome, "error");
    assert.equal(entries[3].http_status, 401);
    assert.equal(entries[3].error_code, "CLEF_HTTP_ERROR");
    assert.equal(entries[4].successful_decisions, 0);
    assert.equal(requests, 3);
    const unlogged = await runClefBrowser(page, {...options, logFile:dir});
    assert.equal(unlogged.reason, "decision_error");
    assert.equal(unlogged.log_written, false);
  } finally {
    if (originalEndpoint === undefined) delete process.env.CLEF_BACKEND_URL;
    else process.env.CLEF_BACKEND_URL = originalEndpoint;
    if (originalLog === undefined) delete process.env.CLEF_LOG_PATH;
    else process.env.CLEF_LOG_PATH = originalLog;
    await new Promise(resolve => server.close(resolve));
    await rm(dir, { recursive: true });
  }
});
