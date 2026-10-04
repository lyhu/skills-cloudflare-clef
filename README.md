# Cloudflare Clef Agent Skill

面向 Claude Code、Codex、Google Antigravity、Grok Build、Pi 等 Coding Agent 的强类型 System One 决策技能。通过本地或内网部署的 **Cloudflare Clef (Qwen3.8-27B)** 决策引擎，快速返回 `noul`、`choice`、`score` 结构化判定与校准概率。

遵循 [Agent Skills 规范](https://agentskills.io/specification) 与 [typesafe-ai/skills](https://github.com/typesafe-ai/skills) 目录组织标准。本项目独立开源维护，不代表 Cloudflare 或 TypeSafe 官方发布。

---

## 核心特性

- ⚡️ **单次前向极速决策**：基于非自回归架构，免除自回归生成自由文本的延迟与 Token 开销，直接输出强类型决策与校准概率。
- 🎯 **三大强类型决策原语**：
  - `noul`：二元布尔命题概率（`[0, 1]`），精准量化风险与前置条件。
  - `choice`：多分类语义路由（1–64 选项），直连业务分流处理器。
  - `score`：多级梯度打分（0-based 加权期望值），实现代码审查与测试完备性评估。
- 🪶 **纯标准库零外部依赖**：仅需 **Python 3.9+ 标准库**，客户端不下载模型权重、不依赖重型推理框架，开箱即用。
- 🛡️ **安全隔离与容灾降级**：
  - **Prompt 防注入**：严格隔离数据（`--state`）与判定指令（`--instructions`）。
  - **故障封闭 (Fail-closed)**：高危操作遇服务不可用或低确定性时严禁自动放行。
  - **智能重试**：内置有限指数退避重试，防重定向以保障凭据安全。
- 🔌 **多 Agent 生态开箱支持**：适配 Claude Code、Codex CLI、Google Antigravity、Grok Build、DeepSeek Harness (dsh)、Pi 等平台。

---

## 实测性能与收益

在实际的“搜索结果语义筛选与场景识别”任务中，将 Agent 耗时的语义判断卸载至本地 Clef 处理：
**端到端决策耗时从 9.04 秒降至 4.02 秒，提速约 2.25 倍（耗时降低 55.6%）**。

| 评估指标 | 主 Agent 直接推断 | 接入 Clef 批量判断 | 收益变化 |
| :--- | :--- | :--- | :--- |
| **搜索读取与筛选总耗时** | 9.04 s | 4.02 s | **提速 2.25x (-55.6%)** |
| 页面导航与文本读取耗时 | 2.94 s | 2.81 s | 基本持平 |
| **语义判断阶段耗时** | 6.10 s | 1.21 s | **耗时降低 80.2%** |
| 交互轮次开销 | 1 轮长 Token 推理交互 | 1 次轻量 HTTP 请求 (8 并发命题) | 显著节省上下文开销 |

### 质量与准确率验证
- **BANKING77 适配集**（12 分类任务，24 样本 × 3 重复）：分类符合率达 **95.8%**。
- **BoolQ 公开子集**（文章级命题判定，24 样本 × 3 重复）：符合率达 **91.7%**。
- 完整评测方案与原始数据详见 [实测报告](benchmarks/REPORT.md) 与 [基准测试方法论](benchmarks/METHODOLOGY.md)。

---

## 快速开始

### 1. 配置端点并运行

```bash
# 1. 克隆仓库
git clone https://github.com/lyhu/skills-cloudflare-clef.git
cd skills-cloudflare-clef

# 2. 配置 Clef 本地/内网服务端点
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"

# 3. 发起一次语义分流评估
python3 skills/cloudflare-clef/scripts/evaluate.py \
  --state 'Checkout requests return HTTP 500 and customers cannot place orders.' \
  --type choice \
  --instructions 'Which handler should investigate?' \
  --choices technical billing review
```

### 2. 输出示例

CLI 仅在 stdout 输出结构化 JSON（退出码 `0` 表示成功）：

```json
{
  "type": "choice",
  "choice": "technical",
  "confidence": 0.92,
  "probabilities": {
    "technical": 0.92,
    "billing": 0.03,
    "review": 0.05
  }
}
```

> **内网环境提示**：若 Clef 服务部署在远程内网服务器，可通过 SSH 本地端口转发建立连接：
> ```bash
> ssh -N -L 8000:127.0.0.1:8000 user@clef-host
> ```

---

## 决策原语与使用场景

| 原语 | 核心定义 | CLI 参数规范 | 输出结构与范围 |
| :--- | :--- | :--- | :--- |
| **`noul`** | 单一命题成立的概率 | 无候选项参数 | `noul`：`[0, 1]` 区间浮点数（接近 0.5 表示高度不确定） |
| **`choice`** | 从离散候选集中选出单项 | `--choices` (1–64 个唯一标签) | `choice`、`confidence`、`probabilities` |
| **`score`** | 沿有序梯度的多级加权评分 | `--levels` (1–16 个递增描述) | `score` (期望值 `sum(i * p)`，基于 0..N-1)、`confidence`、`legend`、`probabilities` |

### 场景 1：高危操作前置风险阻断（Noul）
在执行清理、推送或资源删除前，评估指令是否存在预期外破坏风险：

```bash
python3 skills/cloudflare-clef/scripts/evaluate.py \
  --state 'command: rm -rf ./build; cwd: /work/project; scope: generated build files only' \
  --type noul \
  --instructions 'Could this command destroy valuable data outside the generated build directory?'
```
> **安全准则**：此评估不构成执行授权。若服务不可用或结果呈高度不确定性，宿主系统必须中断自动化流程并转由人工确认（Fail-closed）。

### 场景 2：工作流语义动态路由（Choice）
替代复杂的 Prompt 交互，将用户反馈或故障信息精准分流至指定业务模块：

```bash
python3 skills/cloudflare-clef/scripts/evaluate.py \
  --state 'Customer reports being charged twice for subscription renewal.' \
  --type choice \
  --instructions 'Which department should handle this ticket?' \
  --choices billing tech_support fraud review
```

### 场景 3：自动化代码审查打分（Score）
对特定维度的代码质量或测试覆盖完备性进行量化打分：

```bash
python3 skills/cloudflare-clef/scripts/evaluate.py \
  --state 'Diff adds retry handling. Tests cover timeout and success, but omit HTTP 429.' \
  --type score \
  --instructions 'How complete is test coverage for retry behavior?' \
  --levels 'No relevant tests' 'Some retry cases tested' 'All specified retry cases tested'
```

---

## 安装与平台接入

### 💬 Agent 对话部署安装话术（推荐）

无需手动记忆终端参数，可直接将以下自然语言指令复制发送给你的 Coding Agent（如 Claude Code、Codex、Google Antigravity 等），Agent 将自动完成安装、环境配置与连通性验证：

#### 基础一键安装部署
> **📋 复制发给 Agent**：
>
> 「请帮我在当前项目中部署并配置 `cloudflare-clef` 决策技能：
> 1. 执行 `npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef` 安装技能；
> 2. 检查本地环境，确保具备 Python 3.9+ 运行环境；
> 3. 设置后端服务环境变量：`export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"`（可按实际服务端点修改）；
> 4. 执行一条简单的 Noul 评估测试，确认技能安装成功且服务连通。」

#### 内网/远程 GPU 服务器接入话术
> **📋 复制发给 Agent**：
>
> 「请帮我接入远程私有网络中的 Clef 决策服务并安装技能：
> 1. 安装技能：`npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef`；
> 2. 在后台建立到远程主机的端口映射：`ssh -N -L 8000:127.0.0.1:8000 <user>@<clef-host>`；
> 3. 设置端点环境变量：`export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"`；
> 4. 发起一次测试请求验证网络连通性与模型判定输出。」

#### Cloudflare 官方 Workers AI 托管服务接入话术
> **📋 复制发给 Agent**：
>
> 「请帮我将当前项目的 `cloudflare-clef` 技能接入 Cloudflare 官方 Workers AI：
> 1. 安装技能：`npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef`；
> 2. 设置官方 API 端点：`export CLEF_BACKEND_URL="https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/ai/run/@cf/cloudflare/clef"`；
> 3. 设置 API Token 凭证：`export CLEF_API_KEY="<CLOUDFLARE_AUTH_TOKEN>"`；
> 4. 发起一条简单的 Noul 评估测试，确认能够正常与官方 Workers AI 通信。」

#### 💡 Agent 日常任务调用话术示例
安装就绪后，可在日常会话中直接通过自然语言指示 Agent 触发决策评估：
- **高危操作前置风控**：
  > “在执行清理命令前，请先调用 `cloudflare-clef` 技能评估命令风险，若 Noul 风险概率高于 0.7 则暂停并提示我确认。”
- **语义路由分流**：
  > “请读取工单内容，使用 `cloudflare-clef` 的 choice 原语在 `[billing, technical, fraud, review]` 中做出分类并分发。”
- **代码审查打分**：
  > “请分析最近一次 commit 的 diff，调用 `cloudflare-clef` 用 score 原语评估测试覆盖完备性，并报告分值。”

---

### 命令行快速安装

通过官方 [skills CLI](https://github.com/vercel-labs/skills) 可一键安装至任意支持的 Coding Agent：

```bash
# 全局安装（所有项目可用）
npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -g

# 或安装至当前项目
npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef
```

### 各平台接入对照表

| 目标平台 | 安装命令 / 链接路径 | 说明 |
| :--- | :--- | :--- |
| **Claude Code** | `npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -a claude-code`<br>或软链接至 `.claude/skills/cloudflare-clef` | 自动识别项目级 `.claude/skills/` |
| **Codex CLI** | `npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -a codex`<br>或软链接至 `.agents/skills/cloudflare-clef` | 支持 `$cloudflare-clef` 显式调用或自动路由 |
| **Google Antigravity** | `npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -a antigravity` | 安装到工作区 `.agents/skills/` |
| **Grok Build** | `npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -a grok` | 映射至 `.grok/skills/` 目录 |
| **Pi Coding Agent** | `pi install git:github.com/lyhu/skills-cloudflare-clef` | 支持标准包管理与 `/skill:cloudflare-clef` 触发 |
| **DeepSeek Harness (dsh)** | 复制至 `~/.agents/skills/cloudflare-clef` | 使用标准 filesystem skill provider 自动发现 |

### 本地开发或 Submodule 集成
```bash
# 本地路径直接安装
npx skills add /path/to/skills-cloudflare-clef --skill cloudflare-clef

# 或作为 Git Submodule 引入
git submodule add https://github.com/lyhu/skills-cloudflare-clef.git .vendor/skills-cloudflare-clef
mkdir -p .agents/skills
ln -s "$PWD/.vendor/skills-cloudflare-clef/skills/cloudflare-clef" .agents/skills/cloudflare-clef
```

---

## 协议契约与运行配置

本客户端采用统一适配层设计，**开箱同时支持本地私有化部署（System One 原生接口）与 Cloudflare 官方 Workers AI 托管服务**，自动解包并对齐响应数据。

### 双模式接入配置

#### 模式 A：本地 / 私网 GPU 私有化部署（默认）
适合低延迟、数据隐私敏感、无需外部网络依赖的本地推理场景：
```bash
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"
export CLEF_MODEL="clef"
```

#### 模式 B：Cloudflare 官方 Workers AI 托管服务
适合免运维、全球边缘网络托管直接调用的云端场景：
```bash
# 配置为官方 Client v4 API 端点
export CLEF_BACKEND_URL="https://api.cloudflare.com/client/v4/accounts/<ACCOUNT_ID>/ai/run/@cf/cloudflare/clef"
export CLEF_API_KEY="<CLOUDFLARE_AUTH_TOKEN>"
export CLEF_MODEL="clef"  # 也支持 @cf/cloudflare/clef 或 clef-flash
```

---

### 私有化接口 vs 官网 Workers AI 差异对比

| 对比维度 | 本地私有化部署 (System One) | 官网 Workers AI 托管服务 | 客户端适配与兼容机制 |
| :--- | :--- | :--- | :--- |
| **接入端点** | `http://<ip>:<port>/v1/systemone` | `https://api.cloudflare.com/client/v4/accounts/{id}/ai/run/@cf/cloudflare/clef` | 通过 `CLEF_BACKEND_URL` 动态切换，完全兼容 |
| **鉴权认证** | 默认免密直连；网关可选 Bearer Token | 必须提供 Cloudflare API Token | 通过 `CLEF_API_KEY` 注入 `Authorization: Bearer` 头部 |
| **请求载荷** | `{"model": "...", "state": ..., "questions": {...}}` | `{"model": "...", "state": ..., "questions": {...}}` | **完全一致**（底层同宗同源决策协议） |
| **响应信封** | 直接返回原生 `{"answers": {...}, "usage": {...}}` | 标准 Cloudflare v4 信封 `{"result": {...}, "success": true}` | **自动解包**：自动识别 `result` 信封，提取 `answers` |
| **错误透传** | HTTP 状态码 + 结构化错误 JSON | 包含 `errors: [{"code": ..., "message": ...}]` | 自动捕获官方错误明细并格式化输出 |
| **上下文上限** | 默认配置通常为 **4,096 tokens** | 标称支持 **65,536 tokens** | 本地环境聚焦高频低延迟推理，超限即报警 |
| **超限处理** | **Fail-closed 严格语义**：超限返回 HTTP 413，**绝不静默截断** | 超限静默截断长文本 (`Long text is truncated`) | 本地模式严密保障高危操作风险判定的完整性 |
| **候选规模** | Choice 1–64 项；Score 1–16 级 | Choice 2–255 项；Score 2–10 级 | 均覆盖标准业务路由与代码审查需求 |
| **多模态** | 客户端聚焦纯文本子集（Text-only） | 支持 `images` 参数（Base64 / Data URL 最多 4 张） | 客户端后续可无缝拓展图像支持 |

---

### 环境变量配置

| 变量名 | 默认值 | 作用说明 |
| :--- | :--- | :--- |
| `CLEF_BACKEND_URL` | `http://127.0.0.1:8000/v1/systemone` | Clef 服务的完整 HTTP(S) API 端点（本地私网或官方 v4 端点） |
| `CLEF_MODEL` | `clef` | 模型标识符（支持 `clef`、`clef-flash`、`Cloudflare/clef`、`@cf/cloudflare/clef`、`@cf/cloudflare/clef-flash`） |
| `CLEF_API_KEY` | 空 | 可选的网关 Bearer Token 或 Cloudflare API Auth Token |
| `CLEF_TIMEOUT` | `10.0` | 单次 Socket 连接与读取超时（秒） |
| `CLEF_MAX_RETRIES` | `2` | 瞬态网络故障的最大重试次数（0–5，指数退避 0.5s/1.0s） |

### 错误处理与容灾契约

发生故障时，客户端返回结构化错误并退出（退出码 `1`）：
```json
{
  "error": "CLEF_SERVICE_UNAVAILABLE",
  "message": "Connection failed or timed out after retries",
  "fallback_used": true
}
```

- **错误类型**：`CLEF_INVALID_INPUT`、`CLEF_INVALID_CONFIG`、`CLEF_HTTP_ERROR`、`CLEF_INVALID_RESPONSE`、`CLEF_SERVICE_UNAVAILABLE`。
- **重试范围**：仅对网络异常、超时及 HTTP 429/500/502/503/504 进行有限重试；配置错误、鉴权失败（401/403）与超限（413）等立即失败返回。

---

## 应用集成示例

### Clef-Browser：浏览器导航原型

已提供 [Clef-Browser 模块](skills/cloudflare-clef/scripts/browser.mjs)，可在现有 `ego-browser` 会话中运行“页面观察 → Clef 选择链接 → 导航 → 核对完成条件”的循环。主 Agent 给定目标与只读路由范围，Clef 每步返回强类型决策，代码执行并记录耗时；不需要另装浏览器自动化框架。

支持多步链接导航、低置信度交接、步数与时间预算，以及独立完成检查。当前范围为只读导航；按钮、表单、登录、发布及视觉操作需要后续实现。

使用方法见 [调用说明](skills/cloudflare-clef/references/browser.md)，真实 GitHub 与 X 导航测试见 [可行性评测](benchmarks/CLEF_BROWSER_REPORT.md)。该测试独立于前面的搜索结果筛选评测，速度收益须通过同任务的配对实验测量。

### Python 集成
使用随技能分发的 [Python 模板](skills/cloudflare-clef/templates/client.py)：

```python
from client import route_issue

# 发起语义路由判定
result = route_issue("Checkout requests fail with HTTP 500.")

# 提取判定结果或执行错误降级
handler = "review" if "error" in result else result["choice"]
print(f"Assigning to: {handler}")
```

### TypeScript / Node.js 集成
使用 [TypeScript 模板](skills/cloudflare-clef/templates/client.ts)（零外部 npm 依赖，安全调用 Python CLI 进程）：

```typescript
import { evaluateClef } from "./client.ts";

const result = await evaluateClef(
  "/path/to/skills/cloudflare-clef/scripts/evaluate.py",
  "Checkout service throws 500.",
  {
    type: "choice",
    instructions: "Which handler should investigate?",
    choices: ["technical", "billing", "review"],
  }
);

const handler = "error" in result ? "review" : result.choice;
console.log(`Handler: ${handler}`);
```

---

## 本地开发与质量验证

```bash
# 安装开发测试依赖（仅用于 schema 校验与测试）
python3 -m pip install -r requirements-dev.txt

# 1. 元数据、语法、Schema 与打包完整性校验
python3 scripts/validate.py

# 2. 执行完整单元测试集（30 项测试用例，覆盖协议、退避重试与安全边界）
python3 -m unittest discover -s tests -v

# 3. 运行基准测试集
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --repeats 3 --warmup 3
```

---

## 参考与许可

- **模型与权重**：[Cloudflare Clef 模型权重与文档 (HuggingFace)](https://huggingface.co/Cloudflare/clef)
- **协议规范**：[Agent Skills 规范标准](https://agentskills.io/specification) | [TypeSafe 决策原语文档](https://docs.typesafe.ai/primitives/noul)
- **代码许可**：本项目代码基于 [Apache-2.0](LICENSE) 协议开源。公开基准测试集遵循其各自原许可协议，详见 [NOTICE](benchmarks/NOTICE.md)。
