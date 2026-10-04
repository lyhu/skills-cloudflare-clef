# Clef-Browser 默认接入

## 用户怎么用

完成一次安装和端点配置后，用户直接说浏览器任务：

- “打开这个 GitHub 项目的贡献指南。”
- “找到这个仓库的命令行入口源码。”
- “在 X 上找 Jev 的浏览器应用案例，打开原帖看看。”

不要求用户提到 Clef、函数名、阈值或调试输出。成功后回答任务结果和来源。中间的模型判断留在工具内部；用户要求评测时才展示轨迹。

## 一次性安装（Agent 执行）

用用户给定的端点运行 `<skill-dir>/scripts/install-browser.py --endpoint <url>`。它写入 `~/.config/clef-browser/config.json`，并在已有 `~/.agents/skills/ego-browser/SKILL.md` 中加入默认路由提示。原文件备份在配置目录中，重复安装不追加重复提示；未安装 ego-browser 时不创建冒充的浏览器技能。

配置文件仅需 `{"endpoint":"http://127.0.0.1:8000/v1/systemone","enabled":true}`。进程中的 `CLEF_BACKEND_URL` 优先；浏览器运行时不继承终端变量时仍可读取该文件。将 `enabled` 改为 `false` 可停用默认接入。浏览器技能升级可能覆盖本地提示，此时重新运行安装脚本即可恢复。

## Agent 的默认流程

读取 ego-browser 的 TaskSpace/Page 规则。用户指定的单一 URL 可以直接打开；当需要选择页面链接时，使用当前 Page 调用：

```javascript
const { navigate } = await import('/absolute/path/cloudflare-clef/scripts/browser.mjs');
const result = await navigate(page, userGoal, { targetUrl: observedTargetUrl });
```

`observedTargetUrl` 来自实际页面或用户给定目标。目标无法预先确定时，由 Agent 提供 `verify(observation)`，验证 URL 或 DOM 中的真实目标状态。GitHub 仓库阅读和 X 搜索/原帖有内置路由范围及正文等待条件；其他站点由主 Agent 接手，或按任务提供明确的 `allowNavigation`。

`completed` 后读取页面并报告用户所需内容。`handoff` 是**交回主 Agent**，主 Agent 检查当前页面后，沿用同一 TaskSpace/Page 继续普通 ego-browser 操作；不能因为模型不可用就要求用户选择后端。仅当用户确实需要登录、处理浏览器权限或授权时才调用 `task.handOff()` 交给用户。不要默认打印 `trace` 或延迟表。

这个接入借鉴 [ego-jev](https://github.com/ZephyrDeng/ego-jev) 的 Agent 内部决策循环与完成验证模式；当前仍只有只读链接导航，没有复制其表单/菜单执行器。自动路由属于技能指引，需要宿主 Agent 加载这些技能；不拦截所有底层浏览器 API，也不能隐藏宿主界面的工具调用。

## 底层原型与高级调用

将已有 ego-browser Page 的**链接导航决策**交给 Clef。代码提取页面文字和链接，Clef 每步用一次 `choice` 选择链接、完成或交接；代码控制范围、预算与执行，并独立核对完成条件。主 Agent 仍负责目标拆解和内容总结。

运行依赖：已安装且可用的 ego-browser、Node.js 22+、Python 3.9+、可达的 Clef 服务。模块只使用 Node 标准库和随技能分发的 `evaluate.py`，不安装或启动另一个浏览器。

### 高级调用示例

将下面的绝对路径替换为实际安装路径。TaskSpace 由调用方创建、复用和结束。

```bash
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"
ego-browser nodejs <<'JS'
const { runClefBrowser } = await import('/absolute/path/cloudflare-clef/scripts/browser.mjs');
const task = await taskSpace('Clef-Browser: read contribution guide');
const page = task.page('p1');
await page.goto('https://github.com/jkudish/jev-browser');

const result = await runClefBrowser(page, {
  goal: 'Open the CONTRIBUTING.md file of jkudish/jev-browser.',
  allowNavigation: u => u.origin === 'https://github.com' && !u.search &&
    (u.pathname === '/jkudish/jev-browser' ||
     /^\/jkudish\/jev-browser\/(blob|tree)\/main\//.test(u.pathname)),
  verify: state => new URL(state.url).pathname ===
    '/jkudish/jev-browser/blob/main/CONTRIBUTING.md',
  maxSteps: 6,
  maxSeconds: 60,
  threshold: 0.6,
});
console.log(result);
if (result.status === 'completed') await task.finish({ keep: [] });
// Otherwise the main agent inspects the page and continues in this TaskSpace.
JS
```

`allowNavigation(URL)` 必须由调用方按已授权任务列出**只读路由**。同域并不代表只读；不要用“允许整个网站”替代路由规则。`verify(observation)` 必须独立验证目标，不能直接引用 Clef 的判断作为证明。

动态网站可传入 `waitForPage(page)`，在每次观察及导航后等待正文。例如 X：

```javascript
waitForPage: p => p.waitForFunction(
  () => !!document.querySelector('article [data-testid="tweetText"]'),
  undefined, { timeout: 10000 }),
```

### 输出和边界

- `status`：`completed` 仅表示调用方的完成检查通过；其他情况为 `handoff`。
- `trace`：每步起始 URL、候选数、选择、概率、决策和导航耗时。不存储完整页面正文或凭据。
- `decision_ms` 包含 Python 进程启动、HTTP 和服务处理；不是纯 GPU 推理耗时。
- 最多提供 24 个去重链接，剔除当前和已访问 URL。超出候选预算的链接不会被选中。
- 只通过 `goto()` 跟随已观察到的 HTTP(S) 链接，不执行页面提供的代码。未实现按钮点击、输入、提交、登录、发布、付款、下载或截图视觉导航。
- 低于阈值、服务异常、页面未就绪、导航失败、范围越界或完成检查不通过，停止自动导航并交回调用方。`handoff` 本身不会调用另一模型或取得新授权。
- 时间预算在步骤之间检查；正在运行的浏览器调用使用其自身超时，不保证硬实时截止。重定向目标在导航后检查，不能阻止初始重定向请求；范围严格时应配合浏览器或网络层拦截。

这是可复用的导航原型，不是通用浏览器 Agent。复杂规划、阅读理解及未覆盖交互由主 Agent 处理；概率阈值需要用具体任务校准。
