import { test } from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import { copyFile, cp, mkdir, mkdtemp, readFile, rm } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const execute = promisify(execFile);

test("generic CLI runs from an isolated install with only Python standard library", async () => {
  const dir = await mkdtemp(join(tmpdir(), "clef-generic-"));
  const client = join(dir, "evaluate.py");
  const server = createServer(async (request, response) => {
    let input = "";
    for await (const chunk of request) input += chunk;
    assert.equal(JSON.parse(input).questions.verdict.type, "noul");
    response.end(JSON.stringify({ answers: { verdict: { type: "noul", noul: 0.9 } } }));
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  try {
    await copyFile(new URL("../skills/cloudflare-clef/scripts/evaluate.py", import.meta.url), client);
    const { stdout } = await execute("python3", ["-S", client, "--state", "A checkout outage",
      "--type", "noul", "--instructions", "Does this require technical support?"], {
      cwd: dir, env: { ...process.env, CLEF_BACKEND_URL:
        `http://127.0.0.1:${server.address().port}/v1/systemone` },
    });
    assert.deepEqual(JSON.parse(stdout), { type: "noul", noul: 0.9 });
  } finally {
    await new Promise(resolve => server.close(resolve));
    await rm(dir, { recursive: true });
  }
});

test("separately installed browser skill uses generic client; missing dependency hands off", async () => {
  const dir = await mkdtemp(join(tmpdir(), "ego-clef-install-"));
  const generic = join(dir, "custom-generic");
  const browser = join(dir, "custom-browser");
  const logFile = join(dir, "events.jsonl");
  const previous = { endpoint: process.env.CLEF_BACKEND_URL, skill: process.env.CLEF_SKILL_DIR };
  let requests = 0;
  const server = createServer(async (request, response) => {
    requests++;
    let input = "";
    for await (const chunk of request) input += chunk;
    const choices = Object.keys(JSON.parse(input).questions.verdict.criteria);
    const choice = choices.at(-2);
    response.end(JSON.stringify({ answers: { verdict: { type: "choice", choice, confidence: 1,
      probabilities: Object.fromEntries(choices.map(key => [key, key === choice ? 1 : 0])) } } }));
  });
  await new Promise(resolve => server.listen(0, "127.0.0.1", resolve));
  try {
    await mkdir(join(generic, "scripts"), { recursive: true });
    await copyFile(new URL("../skills/cloudflare-clef/scripts/evaluate.py", import.meta.url),
      join(generic, "scripts/evaluate.py"));
    await cp(new URL("../skills/ego-clef/scripts/", import.meta.url), browser, { recursive: true });
    process.env.CLEF_SKILL_DIR = generic;
    process.env.CLEF_BACKEND_URL = `http://127.0.0.1:${server.address().port}/v1/systemone`;
    const { runClefBrowser, resolveClefClient } = await import(pathToFileURL(join(browser, "browser.mjs")));
    assert.equal(await resolveClefClient(), join(generic, "scripts/evaluate.py"));
    const page = { evaluate: async () => ({ url: "https://example.test/docs", title: "Docs",
      text: "Guide", links: [] }), waitForFunction: async () => {},
      goto: async () => { assert.fail("Should not navigate"); } };
    const options = { goal: "Read guide", allowNavigation: () => true, verify: () => true, logFile };
    assert.equal((await runClefBrowser(page, options)).status, "completed");
    process.env.CLEF_SKILL_DIR = join(dir, "missing-generic");
    const failed = await runClefBrowser(page, options);
    assert.equal(failed.status, "handoff");
    assert.equal(failed.reason, "decision_error");
    assert.equal(requests, 1);
    const events = (await readFile(logFile, "utf8")).trim().split("\n").map(JSON.parse);
    assert.equal(events.at(-2).error_code, "CLEF_CLIENT_NOT_INSTALLED");
    assert.equal(events.at(-1).successful_decisions, 0);
  } finally {
    for (const [key, value] of [["CLEF_BACKEND_URL", previous.endpoint], ["CLEF_SKILL_DIR", previous.skill]]) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
    await new Promise(resolve => server.close(resolve));
    await rm(dir, { recursive: true });
  }
});
