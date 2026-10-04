---
name: ego-clef
description: 为 ego-browser 提供强类型语义决策支持。针对网页导航、搜索、菜单、筛选、已知值填写、原生下拉选择及页面滚动，通过 Clef 评估并选定下一步操作；完全复用既有浏览器会话，依赖 ego-browser 与通用 cloudflare-clef。
license: Apache-2.0
metadata:
  version: "1.0.0"
  author: "Open Source Contributor"
---

# Ego Clef 浏览器语义决策技能

本技能作为 `ego-browser` 的可选语义决策层，调用底层的 `cloudflare-clef` 决策客户端，在浏览器交互循环中为页面操作提供结构化判定。技能本身不包含模型权重，亦不启动冗余的浏览器实例。

---

## 1. 运行依赖与路径解析

- **环境要求**：Node.js 22+、Python 3.9+，以及可访问的 Clef 服务端点。
- **技能依赖**：需预先安装 `ego-browser` 与 `cloudflare-clef`。
- **路径解析**：优先读取环境变量 `CLEF_SKILL_DIR`；未指定时自动回退至同级目录 `cloudflare-clef`、`~/.agents/skills/cloudflare-clef` 或 `~/.codex/skills/cloudflare-clef`。若未检测到通用客户端，自动将任务交回主 Agent。

---

## 2. 交互模式与核心接口

在同一个 TaskSpace / Page 中，对无需决策的固定操作直接执行；对需依据页面实时语义推断下一步的场景，调用以下接口：

- **`navigate(page, goal, options)`**：多步超链接语义导航，从可见链接中挑选符合目标的最优路径。
- **`interact(page, goal, options)`**：富交互控件操作，支持菜单展开、筛选应用、关键词搜索、已知值填写及页面滚动。
- **动态策略约束**：主 Agent 根据具体任务提供 `allowAction`（操作与选择器白名单）及 `verify`（结果独立验证）。默认仅允许同源导航及页面滚动；点击、输入、提交等操作必须严格受控。
- **输入安全规范**：`values` 仅传递已知、确定且非敏感的输入映射（如搜索关键词）。Clef 仅做键选择，由运行时代码原样填入，严禁要求模型生成凭据、密码或验证码。

---

## 3. 架构分工与安全边界

| 角色 | 核心职责 |
| :--- | :--- |
| **Clef 决策引擎** | 依据当前页面观察（最多 24 个候选动作）输出强类型下一步决策或 DONE/HANDOFF。 |
| **ego-browser** | 负责底层 CDP 会话管理、DOM 事件触发、页面渲染与滚动执行。 |
| **主 Agent** | 掌控全局任务规划、权限边界授权、输入字段提供、独立结果核验及异常兜底。 |

### 兜底与交接契约（Handoff）
遇到以下情况时立即中断循环并触发 `handoff`，由主 Agent 在既有浏览器会话中接管：
- 配置缺失、服务网络异常或单步置信度低于阈值（默认 `0.6`）。
- 页面状态未发生实质进展（死循环防护）或超出预算步数（默认 6 步，上限 20 步）。
- 涉及登录认证、支付交易、内容发布/删除、文件下载、Canvas/拖拽及对话框确认等高敏感场景。

---

## 4. 可观测性与详细参考

- **任务日志**：浏览器操作流记录于 `~/.local/state/clef-browser/events.jsonl`，底层模型调用记录于 `~/.local/state/clef/events.jsonl`（`source: ego-clef`），二者通过 `call_id` 与 `run_id` 严格关联。
- **详细参考**：完整 API 参数、操作类型表及安装指南详见 [references/browser.md](references/browser.md)。

