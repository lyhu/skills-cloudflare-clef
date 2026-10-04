/** Site-independent semantic controls. All selectors and values come from code or observed DOM. */
const restricted = /(?:log[ -]?in|sign[ -]?in|password|checkout|payment|purchase|delete|upload|download|publish|send|save|subscribe|transfer|登录|密码|付款|支付|购买|删除|上传|下载|发布|发送|保存|订阅|转账)/i;

export function safeNavigation(url) {
  let path;
  try { path = decodeURIComponent(url.pathname); } catch { return false; }
  return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password &&
    !restricted.test(path) && !/(?:^|\/)(?:edit|new|settings|account|logout|signout)(?:\/|$)/i.test(path) &&
    ![...url.searchParams.keys()].some(key => /^(?:edit|delete|publish|logout|action)$/i.test(key));
}

export async function observeSemanticPage(page) {
  const snapshot = await page.snapshot();
  const observation = await page.evaluate(() => {
    const clean = node => {
      const copy = node.cloneNode(true);
      copy.querySelectorAll('script, style, .immersive-translate-target-wrapper').forEach(n => n.remove());
      return copy.textContent.replace(/\s+/g, ' ').trim();
    };
    const visible = node => {
      const style = getComputedStyle(node);
      return node.getClientRects().length && style.visibility !== 'hidden' && style.display !== 'none';
    };
    const selector = node => {
      if (node.id && document.querySelectorAll('#' + CSS.escape(node.id)).length === 1) {
        return '#' + CSS.escape(node.id);
      }
      const parts = [];
      for (let n = node; n && n !== document.body; n = n.parentElement) {
        const siblings = [...n.parentElement.children].filter(s => s.tagName === n.tagName);
        parts.unshift(n.tagName.toLowerCase() + ':nth-of-type(' + (siblings.indexOf(n) + 1) + ')');
      }
      return 'body > ' + parts.join(' > ');
    };
    const controls = [];
    const nodes = document.querySelectorAll('a[href], button, input, select, textarea, summary, ' +
      '[role="button"], [role="tab"], [role="menuitem"], [role="option"], [role="checkbox"], ' +
      '[role="switch"], [role="radio"], [role="combobox"], [role="treeitem"]');
    const protectedPage = [...nodes].some(n => visible(n) &&
      (n.type === 'password' || /one-time-code|current-password|new-password|cc-/.test(n.autocomplete || '')));
    for (const node of nodes) {
      if (!visible(node) || node.disabled || node.getAttribute('aria-disabled') === 'true') continue;
      const rect = node.getBoundingClientRect();
      if (rect.bottom <= 0 || rect.top >= innerHeight) continue;
      if (node.type === 'password' || node.type === 'file') continue;
      const name = node.getAttribute('aria-label') || node.labels?.[0]?.textContent ||
        node.getAttribute('placeholder') || node.getAttribute('title') ||
        (['submit', 'button', 'reset'].includes(node.type) ? node.value : '') || clean(node);
      if (!name.trim()) continue;
      const tag = node.tagName.toLowerCase();
      controls.push({ selector: selector(node), tag, role: node.getAttribute('role') || tag,
        name: name.trim().slice(0, 120), type: node.type || '', href: tag === 'a' ? node.href : undefined,
        popup: node.getAttribute('aria-haspopup'), readonly: Boolean(node.readOnly),
        value: ['input', 'textarea', 'select'].includes(tag) && node.type !== 'password' ? node.value : undefined,
        checked: node.checked ?? node.getAttribute('aria-checked'),
        options: tag === 'select' ? [...node.options].filter(o => !o.disabled)
          .map(o => ({ label: o.textContent.trim(), value: o.value })) : undefined,
        context: node.closest('form')?.getAttribute('aria-label') ||
          node.closest('fieldset')?.querySelector('legend')?.textContent || '' });
      if (controls.length === 80) break;
    }
    const main = document.querySelector('main, [role="main"], article') || document.body;
    return { url: location.href, title: document.title, text: clean(main).slice(0, 2000),
      controls, protectedPage, scroll: { x: innerWidth / 2, y: innerHeight / 2,
        position: scrollY, canDown: scrollY + innerHeight < document.documentElement.scrollHeight - 2 } };
  });
  return { ...observation, snapshot: String(snapshot).slice(0, 2000) };
}

export function semanticActions(observation, values, allowNavigation, allowAction = () => false) {
  if (observation.protectedPage) return [];
  const actions = [];
  const add = (action, permitted = false) => {
    if (restricted.test(action.name || '') || (action.url && !safeNavigation(new URL(action.url)))) return;
    if (permitted || allowAction(action, observation) === true) actions.push(action);
  };
  for (const control of observation.controls) {
    const base = { selector: control.selector, name: control.name, role: control.role };
    if (control.tag === 'a') {
      const url = new URL(control.href);
      if (allowNavigation(url) && url.href !== observation.url) add({ ...base, kind: 'navigate', url: url.href }, true);
      if (control.popup || control.role === 'button') {
        add({ ...base, kind: 'click' });
        add({ ...base, kind: 'hover' });
      }
    } else if (['input', 'textarea'].includes(control.tag) &&
        ['', 'text', 'search', 'email', 'tel', 'url', 'number', 'date', 'textarea'].includes(control.type)) {
      for (const [key, input] of Object.entries(values)) {
        if (!control.readonly && control.value !== input.value) add({ ...base, kind: 'fill', valueKey: key, value: input.value });
      }
      if (control.value) add({ ...base, kind: 'press', key: 'Enter' });
    } else if (control.tag === 'select') {
      for (const option of control.options || []) {
        if (option.value !== control.value) add({ ...base, kind: 'select', option });
      }
    } else if (['button', 'summary', 'input'].includes(control.tag) ||
        ['button', 'tab', 'menuitem', 'option', 'checkbox', 'switch', 'radio', 'combobox', 'treeitem'].includes(control.role)) {
      if (control.type === 'file' || control.type === 'password') continue;
      add({ ...base, kind: 'click' });
      add({ ...base, kind: 'hover' });
    }
  }
  // Scrolling reveals more candidates; it never clicks or submits them.
  if (observation.scroll?.canDown) add({ kind: 'scroll', name: 'Scroll down to reveal more controls' }, true);
  const offered = actions.filter(action => action.kind !== 'scroll').slice(0, observation.scroll?.canDown ? 23 : 24);
  if (observation.scroll?.canDown) offered.push(actions.at(-1));
  return offered.map((action, i) => ({ ...action,
    label: `ACTION ${i}: ${action.kind} ${action.role || 'page'} ${JSON.stringify(action.name)}` +
      (action.url ? ` | ${action.url}` : '') +
      (action.valueKey ? ` using supplied value ${action.valueKey}` : '') +
      (action.option ? ` option ${JSON.stringify(action.option.label)}` : '') +
      (action.key ? ` ${action.key}` : '') }));
}

export function decisionState(observation, actions, values) {
  return { url: observation.url, title: observation.title, text: observation.text.slice(0, 1000),
    actions: actions.map((action, id) => {
      const control = observation.controls.find(c => c.selector === action.selector);
      return { id, kind: action.kind, name: action.name, role: action.role,
        current_value: control?.value, checked: control?.checked,
        value_key: action.valueKey, option: action.option?.label };
    }), values };
}

export function actionIdentity(action) {
  return JSON.stringify([action.kind, action.selector, action.name, action.url,
    action.valueKey, action.value, action.option, action.key]);
}

export async function executeSemanticAction(page, action, observation) {
  switch (action.kind) {
    case 'navigate': return page.goto(action.url);
    case 'click': return page.click(action.selector, { label: 'Choose requested page control' });
    case 'hover': return page.hover(action.selector, { label: 'Reveal requested menu options' });
    case 'fill': return page.fill(action.selector, action.value);
    case 'select': return page.selectOption(action.selector, { value: action.option.value });
    case 'press': return page.press(action.selector, action.key);
    case 'scroll':
      await page.mouse.move(observation.scroll.x, observation.scroll.y);
      return page.mouse.wheel(0, 600, { label: 'Reveal more page controls' });
    default: throw new TypeError('Unsupported semantic operation');
  }
}
