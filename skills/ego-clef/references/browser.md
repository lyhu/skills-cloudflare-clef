# Clef-Browser 浏览器集成指南

本指南说明如何在 `ego-browser` 中集成与使用 Clef 语义决策层，实现页面自动化交互中的强类型下一步推断。

---

## 1. 自然语言任务交互

完成一次性配置后，用户可在日常会话中直接描述浏览器任务，无需显式指定 Clef、底层函数名或决策阈值：

- “在当前文档站中搜索 `pathlib` 并定位核心用法。”
- “展开顶部导航菜单，筛选 Tools 分类并应用过滤。”
- “在表单中填入已知的账号名称，进入对应的设置页面。”

**交互约定**：
- 决策过程在 Agent 内部完成，正常情况下仅输出任务最终结果与信息来源。
- 仅在用户显式要求排查或性能评测时，才呈现中间决策轨迹与概率明细。

---

## 2. 状态验证与可观测性

浏览器操作日志默认存储于 `~/.local/state/clef-browser/events.jsonl`，权限设为 `0600`，不纳入代码仓库。

### 实时日志监听
```bash
tail -f ~/.local/state/clef-browser/events.jsonl
```

### 核心事件定义
- **`event: decision`**（`transport: http`, `outcome: success`）：表明 Clef 成功返回并校验了动作判定。包含所选操作类型、概率、决策耗时与模型标识。
- **`event: run`**（`status: completed`, `reason: verified`）：交互循环顺利完成，且通过独立的 `verify` 目标检查。
- **`status: handoff`**：控制权交回主 Agent，`reason` 包含配置缺失、置信度不足（< 0.6）、无进展死循环防护或服务超时等原因。

### 日志关联与统计分析
模型调用同时记录至通用日志 `~/.local/state/clef/events.jsonl`（`source: ego-clef`），二者通过 `call_id` 与 `run_id` 关联：

```bash
# 查询今日 ego-clef 的模型决策统计
python3 <cloudflare-clef-dir>/scripts/log_stats.py --today --source ego-clef

# 联合分析模型调用与浏览器工作流完成情况（防重复计数）
python3 <cloudflare-clef-dir>/scripts/log_stats.py --today --json \
  --file ~/.local/state/clef/events.jsonl \
  --file ~/.local/state/clef-browser/events.jsonl
```

---

## 3. 一次性安装与环境配置

安装依赖：`cloudflare-clef`、`ego-clef` 与 `ego-browser`。

### 初始化配置脚本
```bash
python3 <skill-dir>/scripts/install-browser.py --endpoint "http://127.0.0.1:8000/v1/systemone"
```

**配置说明**：
- 脚本写入配置文件 `~/.config/clef-browser/config.json`（内容：`{"endpoint": "...", "enabled": true}`）。
- 自动备份现有的 `~/.agents/skills/ego-browser/SKILL.md`，并注入指向 `ego-clef` 的默认路由提示。重复执行具有幂等性。
- 优先级：运行时的 `CLEF_BACKEND_URL` 优先于配置文件；如需停用默认接入，将配置中 `enabled` 设为 `false` 即可。

---

## 4. 控件交互模式（Interact）

在已有 `ego-browser` 页面中，通过 `interact` 驱动多步骤富控件操作：

### 原生能力矩阵
| 操作类型 | Clef 参与方式 | 策略要求 |
| :--- | :--- | :--- |
| **超链接导航** | 从已提取的页面超链接中挑选最优目标 | 默认严格同源；需在策略中收窄只读路由 |
| **菜单/筛选/按钮** | 选择符合语义的 `click` 或 `hover` 动作 | 目标选择器须显式包含在 `allowAction` 白名单中 |
| **文本输入** | 从传入的 `values` 字典中选定键，代码原样填入 | 仅提供非敏感已知值，严禁模型虚构密码或验证码 |
| **下拉选择** | 选择页面中实际存在的 `<option>` 候选 | 自定义下拉框通过点击序列完成 |
| **长页面探查** | 决策输出 `scroll` 动作触发滚动 | 滚动后重新捕获 DOM 进行下一轮决策 |
| **复杂/敏感操作** | 登录认证、支付、发布/删除、Canvas/拖拽、弹窗 | 立即中断并交回主 Agent 使用原生流程处理 |

### 代码调用示例

```javascript
import { interact } from '/path/to/ego-clef/scripts/browser.mjs';

const permittedSelectors = new Set(['#search-query', '#category-select', '#submit-btn']);

const result = await interact(page, userGoal, {
  // 仅注入已知的确切参数与用途提示
  values: {
    search: { value: 'pathlib', hint: 'Documentation search keyword' }
  },
  // 严格的操作与元素白名单
  allowAction: action => permittedSelectors.has(action.selector) &&
    ['fill', 'select', 'click', 'press'].includes(action.kind),
  // 独立结果验证器，不依赖模型的 DONE 判断
  verify: async (state, p) => p.evaluate(() =>
    document.querySelector('#search-results')?.dataset.loaded === 'true'),
  maxSteps: 6,
  maxSeconds: 60,
});
```

---

## 5. 链接导航模式（Navigate）

对于仅需在超链接之间跳转探索的场景，调用 `runClefBrowser`。该模式从 DOM 提取可见超链接，由 Clef 单步选择目标 URL。

### 代码调用示例

```javascript
import { runClefBrowser } from '/path/to/ego-clef/scripts/browser.mjs';

const result = await runClefBrowser(page, {
  goal: 'Open the CONTRIBUTING.md file in the repository.',
  // 只读路由白名单约束
  allowNavigation: url => url.origin === 'https://github.com' && !url.search &&
    (url.pathname === '/owner/repo' || /^\/owner\/repo\/(blob|tree)\/main\//.test(url.pathname)),
  // 独立目标完成校验
  verify: state => new URL(state.url).pathname === '/owner/repo/blob/main/CONTRIBUTING.md',
  maxSteps: 5,
  maxSeconds: 45,
  threshold: 0.6,
  // 针对 SPA 动态加载的等待条件
  waitForPage: p => p.waitForFunction(() => !document.querySelector('.loading-spinner'), { timeout: 8000 }),
});
```

### 契约与安全约束
- **候选预算**：单步最多评估 24 个去重链接（过滤当前及已访问 URL）。
- **完成确认**：仅当独立 `verify` 返回 `true` 时，状态才标记为 `completed`；模型输出 DONE 但验证未通过时交回主 Agent。
- **Fail-closed**：超出预算步数、连续无进展、置信度未达标或遇到异常重定向时，立即停止自动化并交接，绝不越权尝试。

