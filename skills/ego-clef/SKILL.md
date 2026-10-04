---
name: ego-clef
description: 使用 Clef 加速 ego-browser 的只读链接导航。当用户要求进入 GitHub 文件或目录、从 X 搜索结果打开原帖等需要选择页面链接的任务时使用；复用现有浏览器会话，用户无需指定模型。依赖 ego-browser 和通用 cloudflare-clef 技能。
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: "Open Source Contributor"
---

# Ego Clef 浏览器技能

这是 ego-browser 的可选导航层，使用独立的 `cloudflare-clef` 决策客户端。不包含通用决策协议、模型权重或另一套浏览器。

## 依赖与路径

先安装 `ego-browser` 与 `cloudflare-clef`。运行需要 Node.js 22+、Python 3.9+ 和可达的 Clef 服务。解析 `<skill-dir>` 为本技能目录的绝对路径。

通用客户端优先从 `CLEF_SKILL_DIR` 指定的 cloudflare-clef 目录读取；未指定时查找同级 `cloudflare-clef`、`~/.agents/skills/cloudflare-clef`、`~/.codex/skills/cloudflare-clef`。其他安装位置可由 Agent 设置 `CLEF_SKILL_DIR`。通用技能单独使用不需要本技能或 ego-browser。

## 浏览器任务的默认接入

用户说“打开贡献指南”“进入源码目录”“找 X 上的案例并打开原帖”等普通浏览器任务时，无需用户点名本技能。使用 `ego-browser` 的现有 TaskSpace/Page，读取 [浏览器接入说明](references/browser.md)，在只读链接导航阶段优先调用 `navigate(page, goal, options)`。Agent 根据用户目标和已观察到的页面绑定完成检查，不让用户写函数、路由规则或阈值。

配置从 `CLEF_BACKEND_URL` 或 `~/.config/clef-browser/config.json` 读取。缺少配置、站点不支持、服务异常或低确定性时，将结果交回主 Agent；主 Agent 继续同一个任务与会话，不要求用户选择模型或切换后端。需要用户登录或已有权限要求时，仍按原授权规则处理。

默认只报告任务结果与来源，不展示 Clef 名称、置信度、延迟表或逐步技术日志。仅当用户要求调试、评测或解释实现时展示这些信息。浏览器 API 仍按正常工具调用执行，不能保证宿主界面隐藏工具调用。主 Agent 负责搜索策略、内容阅读和总结；已知单一链接可直接打开，无需额外模型判断。

运行元数据默认追加到 `~/.local/state/clef-browser/events.jsonl`。用户询问是否生效时，按时间与 `run_id` 核对 `decision` 的 HTTP 成功记录及 `run` 的完成/交接结果；仅有配置或路由提示不能证明实际调用。详细字段见浏览器接入说明。

## 执行边界

先读取 ego-browser 的 TaskSpace/Page 规则，复用同一任务与 Page。模型只能选择已观察到且在只读范围内的链接；代码负责执行、预算和独立完成验证。低置信度、失败或未覆盖交互交回主 Agent。不得由模型授权登录、提交、发布、付款或破坏性操作。

调用方式、一次性安装和日志字段见 [references/browser.md](references/browser.md)。普通任务仅报告结果；用户要求排查时才查看本地日志与轨迹。
