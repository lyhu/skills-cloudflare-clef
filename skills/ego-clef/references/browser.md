# Clef-Browser 默认接入

## 用户怎么用

完成一次安装和端点配置后，用户直接说浏览器任务：

- “在这个文档站搜索 pathlib，显示搜索结果。”
- “展开菜单，选择 Tools 分类并应用筛选。”
- “填写这些已知条件，再打开匹配的详情页。”

不要求用户提到 Clef、函数名、阈值或调试输出。成功后回答任务结果和来源。中间的模型判断留在工具内部；用户要求评测时才展示轨迹。

## 查看是否生效

默认持久化日志：`~/.local/state/clef-browser/events.jsonl`，首次运行时创建，每行一条 JSON。文件权限 0600，日志不进入仓库，不影响日常回答。

```bash
tail -f ~/.local/state/clef-browser/events.jsonl
```

- `event: decision`、`transport: http`、`outcome: success`：标准库 HTTP 客户端收到并验证了 Clef 答案，证明该次实际调用成功。包含所选动作类别、概率、耗时及请求的模型别名。
- `event: run`、`status: completed`、`reason: verified`：循环完成，独立目标检查通过。`successful_decisions` 是有效决策次数，`decision_attempts` 是尝试次数。目标已满足时可为零次，不能将零次完成记录视为实际模型调用。
- `status: handoff`：交回主 Agent，`reason` 表明配置、范围、低置信度或服务等原因；可能已经成功调用模型，也可能是零次调用。

同一次运行用 `run_id` 关联，时间为 UTC。只记录站点域名，不保存完整 URL、查询参数、正文、任务原文、链接文字、密钥或原始异常。日志写入失败不改变导航结果，真实后端运行的返回值 `log_written: false` 可用于排查。

通用客户端另外写入 `~/.local/state/clef/events.jsonl`：每次模型调用的 `source` 为 `ego-clef`，与这里的 `decision` 共用 `call_id` 和 `run_id`，包含原语、HTTP 尝试、重试、用量与客户端耗时。两个文件承担不同统计用途，不能将它们的每一行都当作一次调用。浏览器 `log_written` 仅反映浏览器日志写入；通用日志需单独检查。

```bash
# 模型调用统计，自动覆盖 ego-clef
python3 <cloudflare-clef-dir>/scripts/log_stats.py --today --source ego-clef

# 同时统计浏览器任务的完成/交接；不会重复计算 decision
python3 <cloudflare-clef-dir>/scripts/log_stats.py --today --json \
  --file ~/.local/state/clef/events.jsonl \
  --file ~/.local/state/clef-browser/events.jsonl
```

`schema_version: 1` 与 `source` 是新版浏览器记录字段；旧记录原样保留，没有补造调用历史。旧记录缺少 source 时统计归为 unknown。`CLEF_LOG_ENABLED=0` 可停用两种日志；`CLEF_LOG_PATH` 与 `CLEF_BROWSER_LOG_PATH` 分别更改客户端和浏览器日志路径。模拟 decider 不写默认调用记录。通用统计和配置见 cloudflare-clef 的 `references/logging.md`。

没有新增日志只能说明这个模块没有留下新记录，不能据此判断服务坏了：单一已知链接直接打开等步骤不需要调用它。用户可以直接问 Agent：“查看最近一次浏览器任务的日志，确认有没有调用 Clef。”

## 一次性安装（Agent 执行）

先安装 `cloudflare-clef`、`ego-clef` 与 `ego-browser`。`ego-clef` 不复制通用客户端；默认查找同级或用户级共享技能目录中的 cloudflare-clef。其他位置设置 `CLEF_SKILL_DIR` 为通用技能目录。缺少客户端时交回主 Agent，不能伪造模型决策。

用用户给定的端点运行 `<skill-dir>/scripts/install-browser.py --endpoint <url>`。它写入 `~/.config/clef-browser/config.json`，并在已有 `~/.agents/skills/ego-browser/SKILL.md` 中加入默认路由提示。原文件备份在配置目录中，重复安装不追加重复提示；未安装 ego-browser 时不创建冒充的浏览器技能。

配置文件仅需 `{"endpoint":"http://127.0.0.1:8000/v1/systemone","enabled":true}`。进程中的 `CLEF_BACKEND_URL` 优先；浏览器运行时不继承终端变量时仍可读取该文件。将 `enabled` 改为 `false` 可停用默认接入。浏览器技能升级可能覆盖本地提示，此时重新运行安装脚本即可恢复。

## Agent 的默认流程

先读取 ego-browser 的会话与权限规则。同一 TaskSpace/Page 中，确定操作可直接执行，需要连续选择语义控件时使用 `interact`；仅跟随链接时使用 `navigate`。不按域名名单触发。

| 功能 | Clef 参与方式 |
| --- | --- |
| 页面、目录、详情、搜索结果导航 | 从观察到的链接选择目标；默认同源，Agent 按任务收窄或明确允许跨域 |
| 菜单、标签、筛选、复选项、语义按钮 | 选择已获任务策略允许的 click / hover |
| 搜索与表单 | 从 `values` 选择键，代码原样 fill；Enter 也须由操作策略允许 |
| 原生下拉框 | 选择页面实际提供的选项；自定义下拉框通过授权的点击序列处理 |
| 寻找页面下方控件 | 选择 scroll；ego-browser 执行滚动，再观察 |
| 内容阅读、截图/坐标、Canvas、拖拽、iframe/Shadow DOM 专项操作 | 主 Agent 使用普通 ego-browser；可将其中的语义子步骤交给 Clef |
| 登录、验证码、付款、发布/删除、文件、弹窗或对话框 | 交回主 Agent，按用户授权与 ego-browser 规则处理 |

Agent 根据当前观察和用户目标绑定策略，用户不需要写函数。例如已观察到 `#query`、`#category`、`#apply` 后：

```javascript
const { interact } = await import('/absolute/path/ego-clef/scripts/browser.mjs');
const permitted = new Set(['#query', '#category', '#apply']);
const result = await interact(page, userGoal, {
  values: { query: { value: knownQuery, hint: 'Site search query' } },
  allowAction: action => permitted.has(action.selector) &&
    ['fill', 'select', 'click', 'press'].includes(action.kind),
  verify: async (state, p) => p.evaluate(() =>
    document.querySelector('#results')?.dataset.ready === 'true'),
});
```

上述选择器和输入必须来自真实页面及用户任务，不照搬示例。模型不生成选择器、文本或新权限。同源与关键词过滤只能挡住部分明显风险，不能证明按钮无副作用；`allowAction` 必须按任务限制元素和操作，不直接返回 `true` 允许整站操作。值必须是非敏感的准确输入，不传密码、验证码或支付信息。

操作策略也应包含必要的状态条件，例如搜索字段达到给定值后才允许提交、选好分类后才允许应用。动态页面由 Agent 绑定 `waitForPage(page)` 等待实际内容就绪；页面已加载或表单已提交不能替代结果验证。

两个入口均需要独立 `verify(observation, page)` 或准确 `targetUrl`。每步观察页面及字段值，提供最多 24 个操作加 DONE/HANDOFF；只发送相关字段与精简上下文，避免将整页控件数据塞入模型请求；执行前重新观察，目标或策略改变即停止，同一状态的同一动作不会重复执行。默认 6 步/60 秒，复杂任务由 Agent 拆分，单次最多 20 步/300 秒。

仅有模型 DONE 不算完成；`verify` 通过才返回 `completed`。`handoff` 表示交回主 Agent，检查当前页面后继续同一会话，不能据此创建新 TaskSpace 或要求用户切换模型。实际登录或浏览器权限需要用户时才调用 `task.handOff()`。

缺配置、低置信度、目标变化、无进展、服务错误及弹窗/对话框均停止循环。弹窗可能已经产生，主 Agent 检查当前 TaskSpace 中的 Page 后处理。没有实现自动接管新窗口或确认对话框。

借鉴 [ego-jev](https://github.com/ZephyrDeng/ego-jev) 的 typed inner loop，使用独立 cloudflare-clef 客户端；不是对全部浏览器 API 的底层拦截，也不保证隐藏工具调用。正常回答只展示结果，调试与评测时才展示轨迹。

## 链接模式与高级调用

将已有 ego-browser Page 的**链接导航决策**交给 Clef。代码提取页面文字和链接，Clef 每步用一次 `choice` 选择链接、完成或交接；代码控制范围、预算与执行，并独立核对完成条件。主 Agent 仍负责目标拆解和内容总结。

运行依赖：已安装且可用的 ego-browser、Node.js 22+、Python 3.9+、可达的 Clef 服务。模块只使用 Node 标准库和独立 cloudflare-clef 技能的 `evaluate.py`，不安装或启动另一个浏览器。

### 高级调用示例

将下面的绝对路径替换为实际安装路径。TaskSpace 由调用方创建、复用和结束。

```bash
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"
ego-browser nodejs <<'JS'
const { runClefBrowser } = await import('/absolute/path/ego-clef/scripts/browser.mjs');
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

### 链接模式输出和边界

- `status`：`completed` 仅表示调用方的完成检查通过；其他情况为 `handoff`。
- `trace`：每步起始 URL、候选数、选择、概率、决策和导航耗时。不存储完整页面正文或凭据。
- `decision_ms` 包含 Python 进程启动、HTTP 和服务处理；不是纯 GPU 推理耗时。
- 最多提供 24 个去重链接，剔除当前和已访问 URL。超出候选预算的链接不会被选中。
- 只通过 `goto()` 跟随已观察到的 HTTP(S) 链接，不执行页面提供的代码。未实现按钮点击、输入、提交、登录、发布、付款、下载或截图视觉导航。
- 低于阈值、服务异常、页面未就绪、导航失败、范围越界或完成检查不通过，停止自动导航并交回调用方。`handoff` 本身不会调用另一模型或取得新授权。
- 时间预算在步骤之间检查；正在运行的浏览器调用使用其自身超时，不保证硬实时截止。重定向目标在导航后检查，不能阻止初始重定向请求；范围严格时应配合浏览器或网络层拦截。

两个入口都由主 Agent 规划、授权与验证；概率阈值需要用具体任务校准。
