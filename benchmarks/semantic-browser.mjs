/** Controlled semantic UI tasks: real browser and real Clef; no speed-comparison baseline. */
import { interact } from '../skills/ego-clef/scripts/browser.mjs';
import { observeSemanticPage } from '../skills/ego-clef/scripts/semantic.mjs';

export const cases = [
  { id: 'menu', goal: 'Open the Filters menu so the Category selector is visible.',
    selectors: ['#filters'], verify: () => !document.querySelector('#filter-panel').hidden },
  { id: 'search', goal: 'Search the catalog for local inference. Submit the search and show its results.',
    selectors: ['#query', '#search'], values: { query: { value: 'local inference', hint: 'Catalog search query' } },
    verify: () => document.querySelector('#results').dataset.query === 'local inference' },
  { id: 'filter', goal: 'Open Filters, choose the Tools category, and apply filters until Applied category: Tools is visible.',
    selectors: ['#filters', '#category', '#apply'],
    verify: () => document.querySelector('#results').dataset.category === 'tools' },
];

export async function trial(page, startUrl, index) {
  const scenario = cases[index];
  const started = performance.now();
  await page.goto(startUrl);
  const permitted = new Set(scenario.selectors);
  const result = await interact(page, scenario.goal, {
    values: scenario.values || {},
    allowAction: (action, state) => permitted.has(action.selector) &&
      ['click', 'fill', 'press', 'select'].includes(action.kind) &&
      // Submitting an empty search cannot meet this task's goal.
      !(scenario.id === 'search' && ['click', 'press'].includes(action.kind) &&
        state.controls.find(control => control.selector === '#query')?.value !== scenario.values.query.value),
    verify: (_, p) => p.evaluate(scenario.verify),
    maxSteps: 8,
  });
  return { task: scenario.id, status: result.status, reason: result.reason, run_id: result.run_id,
    end_to_end_ms: performance.now() - started, loop_ms: result.total_ms, decision_ms: result.decision_ms,
    successful_decisions: result.trace.filter(step => step.request_ok).length,
    operations: result.trace.map(step => step.action).filter(Boolean), log_written: result.log_written };
}

export async function pythonSearchTrial(page) {
  await page.goto('https://docs.python.org/3/');
  const state = await observeSemanticPage(page);
  const field = state.controls.find(control => control.type === 'search' && control.name === 'Quick search');
  const started = performance.now();
  const result = await interact(page, 'Use the current Quick search field to search Python documentation for pathlib. Submit the search and show its search results.', {
    values: { query: { value: 'pathlib', hint: 'Quick search query' } },
    allowNavigation: u => u.origin === 'https://docs.python.org' &&
      (u.pathname === '/3/' || (u.pathname === '/3/search.html' && u.searchParams.get('q') === 'pathlib')),
    allowAction: (action, observation) => action.selector === field.selector &&
      (action.kind === 'fill' || (action.kind === 'press' &&
        observation.controls.find(control => control.selector === field.selector)?.value === 'pathlib')),
    waitForPage: p => p.waitForFunction(() => document.readyState !== 'loading' && !!document.body &&
      (location.pathname !== '/3/search.html' || [...document.querySelectorAll('a[href]')]
        .some(a => a.href.includes('/library/pathlib.html'))), undefined, { timeout: 15000 }),
    verify: (observation, p) => new URL(observation.url).pathname === '/3/search.html' &&
      new URL(observation.url).searchParams.get('q') === 'pathlib' && p.evaluate(() =>
        [...document.querySelectorAll('a[href]')].some(a => a.href.includes('/library/pathlib.html'))),
  });
  return { task: 'python-docs-search', status: result.status, reason: result.reason, run_id: result.run_id,
    loop_ms: result.total_ms, decision_ms: result.decision_ms, end_to_end_ms: performance.now() - started,
    successful_decisions: result.trace.filter(step => step.request_ok).length,
    operations: result.trace.map(step => step.action).filter(Boolean), log_written: result.log_written };
}
