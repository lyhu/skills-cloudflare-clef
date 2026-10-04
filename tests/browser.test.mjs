import { test } from "node:test";
import assert from "node:assert/strict";
import { candidates, runClefBrowser } from "../skills/cloudflare-clef/scripts/browser.mjs";

const home = "https://example.test/docs";
const target = "https://example.test/docs/contributing";
const allowNavigation = url => url.origin === "https://example.test" && url.pathname.startsWith("/docs");
const verdict = (choice, confidence = 0.9) => ({ type: "choice", choice, confidence });

function fakePage() {
  let url = home;
  const calls = [];
  return { calls,
    evaluate: async () => ({ url, title: "Docs", text: url === target ? "Contributing guide" : "Home",
      links: [{ url: target, text: "Contributing", context: "" }] }),
    goto: async next => { calls.push(next); url = next; },
    waitForFunction: async () => {}, url: async () => url,
  };
}

test("scope rejects credentials, non-HTTP links, duplicates, current and visited pages", () => {
  const links = [home, target, target + "#test", "https://evil.test/docs", "javascript:alert(1)",
    "https://user:pass@example.test/docs/secret"].map(url => ({ url, text: "link" }));
  assert.deepEqual(candidates({ url: home, links }, allowNavigation).map(x => x.url), [target]);
  assert.equal(candidates({ url: home, links }, allowNavigation, new Set([target])).length, 0);
});

test("navigates then independently verifies completion", async () => {
  const page = fakePage();
  const result = await runClefBrowser(page, { goal: "Open contributing guide", allowNavigation,
    verify: state => state.url === target && state.text.includes("Contributing"),
    decide: async (state, choices) => verdict(state.url === home ? choices[0] : choices.at(-2)),
  });
  assert.equal(result.status, "completed");
  assert.deepEqual(page.calls, [target]);
  assert.equal(result.trace.length, 2);
});

for (const [name, decide, reason] of [
  ["low confidence", async (_, choices) => verdict(choices[0], 0.2), "low_confidence"],
  ["unknown action", async () => verdict("execute shell"), "invalid_answer"],
  ["service failure", async () => { throw Error("timeout"); }, "decision_error"],
  ["false completion", async (_, choices) => verdict(choices.at(-2)), "completion_unverified"],
]) test(`${name} stops without navigation`, async () => {
  const page = fakePage();
  const result = await runClefBrowser(page, { goal: "Open guide", allowNavigation, verify: () => false, decide });
  assert.equal(result.reason, reason);
  assert.deepEqual(page.calls, []);
});

test("redirect outside scope stops before another decision", async () => {
  const page = fakePage();
  page.url = async () => "https://evil.test/";
  const result = await runClefBrowser(page, { goal: "Open guide", allowNavigation, verify: () => false,
    decide: async (_, choices) => verdict(choices[0]) });
  assert.equal(result.reason, "redirect_outside_scope");
  assert.equal(result.trace.length, 1);
});

test("step budget bounds the loop", async () => {
  const result = await runClefBrowser(fakePage(), { goal: "Open guide", allowNavigation,
    verify: () => true, maxSteps: 1, decide: async (_, choices) => verdict(choices[0]) });
  assert.equal(result.reason, "step_budget");
});

test("unready page returns control without deciding or navigating", async () => {
  const page = fakePage();
  let decisions = 0;
  const result = await runClefBrowser(page, { goal: "Open guide", allowNavigation, verify: () => true,
    waitForPage: async () => { throw Error("page still loading"); },
    decide: async () => { decisions++; } });
  assert.equal(result.reason, "page_not_ready");
  assert.equal(decisions, 0);
  assert.deepEqual(page.calls, []);
});

test("failed navigation is handed back without a retry", async () => {
  const page = fakePage();
  page.goto = async url => { page.calls.push(url); throw Error("navigation failed"); };
  const result = await runClefBrowser(page, { goal: "Open guide", allowNavigation, verify: () => true,
    decide: async (_, choices) => verdict(choices[0]) });
  assert.equal(result.reason, "navigation_error");
  assert.deepEqual(page.calls, [target]);
});
