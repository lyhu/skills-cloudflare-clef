---
name: ego-clef
description: 使用 Clef 为 ego-browser 的语义页面操作选择下一步。适用于各类网站的导航、搜索、菜单、筛选、已知值填写、下拉选择和滚动；复用现有浏览器会话，用户无需指定模型。依赖 ego-browser 和通用 cloudflare-clef。
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: "Open Source Contributor"
---

# Ego Clef 浏览器技能

这是 ego-browser 的可选语义决策层，使用独立的 `cloudflare-clef` 决策客户端。不包含通用决策协议、模型权重或另一套浏览器。

## 依赖与路径

先安装 `ego-browser` 与 `cloudflare-clef`。运行需要 Node.js 22+、Python 3.9+ 和可达的 Clef 服务。解析 `<skill-dir>` 为本技能目录的绝对路径。

通用客户端优先从 `CLEF_SKILL_DIR` 指定的 cloudflare-clef 目录读取；未指定时查找同级 `cloudflare-clef`、`~/.agents/skills/cloudflare-clef`、`~/.codex/skills/cloudflare-clef`。其他安装位置可由 Agent 设置 `CLEF_SKILL_DIR`。通用技能单独使用不需要本技能或 ego-browser。

## 浏览器任务的默认接入

先读取 ego-browser，复用已有 TaskSpace/Page。用户说普通浏览器任务时，Agent 内部将需要选择页面操作的连续步骤交给 Clef，不要求用户点名技能、写函数或配置站点。

- 单一已知 URL 或确定的工具操作可直接执行。
- 多步链接导航用 `navigate(page, goal, options)`；菜单、筛选、搜索、填写等用 `interact(page, goal, options)`。这两个入口均不按网站名单触发。
- Agent 根据用户目标与已观察到的控件绑定 `allowAction`、`allowNavigation` 和独立 `verify`。默认只开放同源导航和页面滚动；点击、悬停、填写、选择、Enter 等控件操作必须由 Agent 在授权任务范围内纳入操作策略。用户不用编写这些策略。
- `values` 只包含已知、非敏感的准确输入值与字段用途。Clef 仅选择值的键，代码原样填写；不得要求它生成新文字、密码或验证码。

配置读取 `CLEF_BACKEND_URL` 或 `~/.config/clef-browser/config.json`。缺配置、低置信度、目标变化、无进展、服务异常或未覆盖交互时，主 Agent 检查当前页面并在同一会话继续；不要求用户切换后端。

默认回答任务结果与来源，省略模型、概率和耗时表。浏览器元数据追加到 `~/.local/state/clef-browser/events.jsonl`；通用客户端同时记录 `~/.local/state/clef/events.jsonl`，来源为 `ego-clef`。用户要求统计时，用通用 `scripts/log_stats.py` 查询，两份日志以 `call_id` 和 `run_id` 关联，不能把浏览器 decision 与客户端 call 重复计数。详细字段见调用说明。工具调用是否显示由宿主界面决定。

## 执行边界

Clef 负责从观察到的元素与代码提供的操作中选下一步，ego-browser 负责执行，主 Agent 负责目标规划、权限、完成验证与内容理解。同源边界和关键词过滤不能证明操作无副作用，Agent 必须按任务收窄策略。

支持原生及带语义角色的 DOM 控件。截图/坐标、Canvas、拖拽、iframe/Shadow DOM 专项操作、文件与下载、登录/验证码、付款及发布/删除等交回主 Agent 的普通 ego-browser 流程；弹窗或对话框也交回，不自动接管新 Page 或确认对话框。主 Agent 可将复杂任务中的语义步骤交给本技能，其余步骤仍使用 ego-browser。

调用方式、能力表、安装和日志字段见 [references/browser.md](references/browser.md)。
