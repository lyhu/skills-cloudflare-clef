# Cloudflare Clef Local Decision Skill

面向 Claude Code、Codex、Google Antigravity、Grok Build 等 Coding Agent 的
独立 Agent Skill。通过本地或私有网络中的 **Cloudflare Clef（Qwen3.8-27B）**
评估上下文，返回 `noul`、`choice`、`score` 结构化决策。

遵循 [Agent Skills 格式](https://agentskills.io/specification) 和
[typesafe-ai/skills](https://github.com/typesafe-ai/skills) 的技能组织方式。
项目独立维护，不代表 Cloudflare 或 TypeSafe 官方发布。

Clef 是单次前向计算的决策模型，不生成自由文本；实现及基础权重见
[官方模型卡](https://huggingface.co/Cloudflare/clef)。客户端不下载模型、不启动推理服务，
运行时仅需 **Python 3.9+ 标准库**。延迟、校准效果及判断质量需要在实际部署中验证，
本项目不承诺低于 100ms，也不把概率判断视为确定事实。

## 快速开始

```bash
git clone https://github.com/lyhu/skills-cloudflare-clef.git
cd skills-cloudflare-clef

export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"

python3 skills/cloudflare-clef/scripts/evaluate.py \
  --state 'Checkout requests return HTTP 500 and customers cannot place orders.' \
  --type choice \
  --instructions 'Which handler should investigate?' \
  --choices technical billing review
```

示例返回（概率仅用于说明，实际结果由模型决定）：

```json
{
  "type": "choice",
  "choice": "technical",
  "confidence": 0.92,
  "probabilities": {"technical": 0.92, "billing": 0.03, "review": 0.05}
}
```

服务位于内网时，可在有访问权限的机器上调用，或通过 SSH 隧道映射到本地：

```bash
ssh -N -L 8000:127.0.0.1:8000 user@clef-host
```

隧道在单独终端运行，客户端继续使用本地地址。技能不会自行建立隧道。

## 安装与平台接入

发布到 GitHub 后使用 [skills CLI](https://github.com/vercel-labs/skills)：

```bash
npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef
```

选择目标 Agent；默认安装到当前项目，加 `-g` 为全局安装。也可使用完整仓库 URL：

```bash
npx skills add https://github.com/lyhu/skills-cloudflare-clef.git --skill cloudflare-clef
```

开发中可直接安装当前本地目录，无需先发布到 GitHub：

```bash
npx skills add /path/to/skills-cloudflare-clef --skill cloudflare-clef -a codex
```

`npx skills` 通过 `SKILL.md` 发现技能，不要求先发布 npm 包。
根目录 `package.json` 提供 npm 打包元数据，GitHub 地址按 `lyhu/skills-cloudflare-clef` 配置。

### Claude Code

```bash
npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -a claude-code
```

或在目标项目中创建链接：

```bash
mkdir -p .claude/skills
ln -s /path/to/skills-cloudflare-clef/skills/cloudflare-clef .claude/skills/cloudflare-clef
```

项目技能入口位于 `.claude/skills/cloudflare-clef/SKILL.md`。
环境变量要由启动 Agent 的终端或宿主配置提供；本客户端不自动读取 `.env`。

### Codex CLI

```bash
npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -a codex
```

也可使用 [Codex 官方支持的项目技能目录](https://learn.chatgpt.com/docs/build-skills)：

```bash
mkdir -p .agents/skills
ln -s /path/to/skills-cloudflare-clef/skills/cloudflare-clef .agents/skills/cloudflare-clef
```

在提示中使用 `$cloudflare-clef`，或让 Agent 根据描述自动发现技能。
本仓库分发的是技能目录，未提供 Codex 插件清单，因此不使用 PRD 中的
`codex plugin add ... --name ...` 命令安装。

### Google Antigravity

```bash
npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -a antigravity
```

skills CLI 当前将项目技能安装到 `.agents/skills/`；全局可加 `-g`。
这里使用已记录的 skills CLI 接口，不依赖未核实的 `agy plugin install` 命令。

### Grok Build

```bash
npx skills add lyhu/skills-cloudflare-clef --skill cloudflare-clef -a grok
```

skills CLI 的 Grok Build 项目路径为 `.grok/skills/`。其他宿主是否支持技能发现及
脚本执行，应以对应宿主文档为准。

### DeepSeek Harness（dsh）与通用技能目录

参考 [typesafe-ai/skills](https://github.com/typesafe-ai/skills)，复用标准技能目录。
从本仓库根目录安装到用户指定的通用位置：

```bash
mkdir -p "$HOME/.agents/skills"
cp -R skills/cloudflare-clef "$HOME/.agents/skills/"
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"
```

[DeepSeek Harness 的 filesystem skill provider](https://github.com/deepseek-ai/deepseek-harness/blob/master/packages/skill/skill-filesystem/README.md)
默认发现 `~/.agents/skills/<name>/SKILL.md`，也发现项目 `.agents/skills/` 和 `.dsh/skills/`。
自定义 dsh 配置需启用 filesystem skill provider 及技能工具，并保留默认扫描根目录。
启动 dsh 后要求加载 `cloudflare-clef` 并执行其中的 Python CLI；端点环境变量需传给宿主。
不需要新增 dsh 专用插件或协议。

### Pi Coding Agent

[Pi 官方技能文档](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/skills.md)
同样支持 `~/.agents/skills/`，上述通用安装可直接复用。使用 `/reload` 重载，
`/skill:cloudflare-clef` 显式调用。

也可使用 [Pi package 安装](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md)：

```bash
pi install /absolute/path/to/skills-cloudflare-clef
# 发布后：
pi install git:github.com/lyhu/skills-cloudflare-clef
```

根 `package.json` 声明 `pi.skills: ["./skills/cloudflare-clef"]`。
Pi 安装的是相同技能资源；调用仍需要 Python 3 与可达的 Clef 服务。
当前本机未安装 Pi，已验证包布局与资源声明，未声称完成 Pi 会话实测。

### Git Submodule

在消费此技能的 Git 项目中执行：

```bash
git submodule add https://github.com/lyhu/skills-cloudflare-clef.git .vendor/skills-cloudflare-clef
git submodule update --init --recursive
mkdir -p .agents/skills
ln -s "$PWD/.vendor/skills-cloudflare-clef/skills/cloudflare-clef" .agents/skills/cloudflare-clef
```

Claude Code 可将最后两条命令的 `.agents/skills` 换成 `.claude/skills`。
上例使用绝对链接；搬迁项目后需要重新建立链接。

## 决策原语与示例

| 原语 | 含义 | CLI 参数 | 返回值 |
| --- | --- | --- | --- |
| `noul` | 一个真假命题成立的概率 | 无候选参数 | `noul`，范围 `[0, 1]` |
| `choice` | 从命名选项中选择一项 | `--choices`，1–64 个唯一标签 | `choice`、`confidence`、`probabilities` |
| `score` | 按有序描述等级评价 | `--levels`，1–16 个等级 | `score`、`confidence`、`legend`、`probabilities` |

`score = sum(index * probability)`，等级从 `0` 开始；三个等级的值在 `[0, 2]`，
不是固定在 `[0, 1]`。单等级是服务器接受的退化情况，实际评分通常应提供至少两个等级。
`noul` 接近 0.5 表示真假不确定；它不是严重性分数。
本部署中 `choice` 和 `score` 的 `confidence` 是最大选项概率，
不直接沿用 TypeSafe 托管 API 的置信度计算方式。

### 高危命令前置评估

```bash
python3 skills/cloudflare-clef/scripts/evaluate.py \
  --state 'command: rm -rf ./build; cwd: /work/project; scope: generated build files only' \
  --type noul \
  --instructions 'Could this command destroy valuable data outside the generated build directory?'
```

问题应明确概率方向：这里高 `noul` 表示风险高。宿主应根据自己的策略设定阈值，
在服务故障或结果不确定时停止自动执行，保留原有授权要求。返回成功仅代表评估成功。

**安装 Skill 不会自动拦截 shell。** 真正的前置拦截需要宿主 hook 在执行前调用客户端，
检查退出码、错误结构与策略阈值，并执行阻止或复核分支。客户端从不执行被评估命令。

### 自动化代码审查

```bash
python3 skills/cloudflare-clef/scripts/evaluate.py \
  --state 'Diff adds retry handling. Tests cover timeout and success, but omit HTTP 429.' \
  --type score \
  --instructions 'How complete is test coverage for retry behavior?' \
  --levels 'No relevant tests' 'Some retry cases tested' 'All specified retry cases tested'
```

实际使用时提供聚焦的 diff、需求和测试证据，评分辅助分流，仍需保留测试与审查规则。
路由选项应覆盖可用处理器，证据不足时提供 `review` 选项；精确条件交给普通代码判断。

## HTTP 契约与配置

此客户端面向部署文档核实的 **Clef 原生 Jev/SystemOne 文本子集**：

```json
{
  "model": "clef",
  "state": "Checkout requests fail.",
  "questions": {
    "verdict": {
      "type": "choice",
      "instructions": "Which handler should investigate?",
      "criteria": {"technical": "Bugs or outages", "review": "Insufficient evidence"}
    }
  }
}
```

`POST /v1/systemone` 返回 `model`、`answers`、`usage`，客户端提取并验证
`answers.verdict`。相对于初始 PRD，已修正 `/v1/decision`、虚构的模型别名、
`choices` 请求字段以及 `result.answers` 响应嵌套。
标准 chat/completions 端点不能直接处理这个协议；vLLM/SGLang 只有额外提供同样的
SystemOne 适配端点时才可接入，不声明通用兼容。

服务限制：每请求 1–16 个问题，choice 最多 64 个选项，score 最多 16 个等级，
完整提示上限 4096 tokens，超限返回 413，不静默截断。本 CLI 每次发送一个问题；
图片、视频、结构化 instructions 和自定义 Noul criteria 不属于本客户端的部署子集。
`state` 在 Python API 中可传 JSON 值，在 CLI 中为文本。

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `CLEF_BACKEND_URL` | `http://127.0.0.1:8000/v1/systemone` | 完整 HTTP(S) 端点 |
| `CLEF_MODEL` | `clef` | `clef` 或 `Cloudflare/clef` |
| `CLEF_API_KEY` | 空 | 可选网关 Bearer token；原生部署未声明鉴权 |
| `CLEF_TIMEOUT` | `10.0` | 每次尝试的正数 socket 超时，单位秒 |
| `CLEF_MAX_RETRIES` | `2` | 初次请求之后的重试次数，范围 `0..5` |

配置在每次调用时读取。超时不是整个调用的严格截止时间；默认最多 3 次尝试，
两次退避分别为 0.5 秒和 1 秒。客户端不跟随重定向，以免把上下文和凭据发往其他端点。

网络错误、超时和 HTTP 429/500/502/503/504 有限重试；413/422、鉴权失败、
重定向及其他 HTTP 错误直接返回。JSON 损坏、类型错误、越界概率、缺失候选、
分布不合理或等级不匹配也直接返回错误。允许原生服务四位小数舍入带来的偏差。

```json
{
  "error": "CLEF_SERVICE_UNAVAILABLE",
  "message": "Connection failed or timed out after retries",
  "fallback_used": true
}
```

`fallback_used` 表示进入错误降级路径，不表示生成了备用决策。
错误类型还包括 `CLEF_INVALID_INPUT`、`CLEF_INVALID_CONFIG`、`CLEF_HTTP_ERROR`、
`CLEF_INVALID_RESPONSE`；TypeScript 包装器另有 `CLEF_CLIENT_ERROR`。
CLI 退出码：`0` 有效答案，`1` 评估错误，`2` 参数解析错误（参数错误说明输出到 stderr）。

## 集成模板

- [Python 模板](skills/cloudflare-clef/templates/client.py)：将模板与
  [evaluate.py](skills/cloudflare-clef/scripts/evaluate.py) 复制到同一应用目录，
  导入 `evaluate_clef` 或示例函数。支持命名选项描述和 JSON 状态。
- [TypeScript 模板](skills/cloudflare-clef/templates/client.ts)：通过 `execFile`
  调用同一 Python CLI，复用重试、验证与故障降级；传入脚本的绝对路径，环境变量继承。
  无 npm 运行依赖，仍需 Python。Node 24 可直接加载这个 `.ts` 模板；普通 TS 工程也可编译使用。
- [原语 JSON Schema](skills/cloudflare-clef/references/primitives.json)：根 schema 验证请求，
  `$defs` 中提供问题、答案、响应和错误定义；跨字段校验由客户端执行。

Python 消费示例（复制模板及客户端后）：

```python
from client import route_issue

result = route_issue("Checkout requests fail with HTTP 500.")
handler = "review" if "error" in result else result["choice"]
print(handler)
```

TypeScript 消费示例：

```typescript
import { evaluateClef } from "./client.ts";

const result = await evaluateClef("/absolute/path/to/evaluate.py", "Checkout fails.", {
  type: "choice",
  instructions: "Which handler should investigate?",
  choices: ["technical", "billing", "review"],
});
const handler = "error" in result ? "review" : result.choice;
console.log(handler);
```

## 开发、验证与发布

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
npm pack --dry-run
npx skills add . --list
```

PyYAML 和 jsonschema 仅供仓库开发校验，安装后的客户端不需要它们。
CI 在 Python 3.9/3.12/3.14 上检查元数据、语法、schema、单元测试和 npm 打包。
测试使用本地假服务，不要求 GPU、集群访问或 API key。

### Benchmark 用例与报告

[简洁总报告](benchmarks/REPORT.md) 汇总真实服务测试和 X 浏览器试验；
[测量方法](benchmarks/METHODOLOGY.md) 与 JSON 原始结果保留复现细节。

| 测试集 | 样本 | 目标 |
| --- | --- | --- |
| [Smoke](benchmarks/cases.json) | 18 个原创用例 | 高危操作判断、路由、审查评分 |
| [BoolQ](benchmarks/datasets/boolq.json) | 24 个公开验证样本 | 基于完整文章的真假判断 |
| [BANKING77 适配版](benchmarks/datasets/banking77.json) | 24 个公开测试样本，12 类 | 银行业务意图分流 |
| [X 浏览器试验](benchmarks/browser.mjs) | 前 8 条公开搜索结果 | 当前 Agent 与 Clef 的应用场景筛选耗时 |

BANKING77 原版有 77 类，本地接口上限为 64 个选项，因此采用 12 类子任务，
不称为官方成绩。数据集按原许可证分发，见 [来源与许可](benchmarks/NOTICE.md)。
运行用例中的 shell 命令仅作为文本输入，不会实际执行。

```bash
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --repeats 3 --warmup 3
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --cases benchmarks/datasets/boolq.json \
  --output-dir benchmarks/reports/live/boolq
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --cases benchmarks/datasets/banking77.json \
  --output-dir benchmarks/reports/live/banking77
# 完成四轮浏览器试验后：
python3 benchmarks/report.py
```

每套默认预热 3 次、每例重复 3 次，串行发送。`--cases` 选择测试集，
`--output-dir` 保存批次，`--transport-note` 记录部署说明。报告包含符合率、
有效答案率、p50/p95、Brier/MAE；错误计入失败。小样本重复不构成生产准确率证明。

浏览器对比共用 ego-browser 和相同读取预算；Clef 仅替代应用场景判断，
固定搜索 URL 和 DOM 提取仍由代码完成。详情见测量方法，不将此试验解释为所有浏览器任务的加速。

[早期 SSH 隧道 Smoke 测试](benchmarks/reports/2026-10-04/report.md) 保留为历史记录，
不同端点和服务版本的延迟不能直接比较。CI 使用假服务验证故障行为与统计公式，
不会自动访问内网模型。

按照 Agent Skills 规范，`version`、`author`、架构和原语列表放在 `metadata` 中，
全部采用字符串；保留 PRD 的元信息，同时避免非标准顶层字段和数组。

首次发布时将当前仓库推送到上述 GitHub 地址即可通过 skills CLI 分发。
`npm pack` 可额外生成分发包；本地初始化不自动创建远程仓库或发布 npm 包。

## 参考与许可证

接口与行为以已部署服务为准，上游资料用于解释模型和原语：

- [Cloudflare Clef 模型与原生 SystemOne 接口](https://huggingface.co/Cloudflare/clef)
- [TypeSafe HTTP API](https://docs.typesafe.ai/api)
- [Noul](https://docs.typesafe.ai/primitives/noul)、[Choice](https://docs.typesafe.ai/primitives/choice)、[Score](https://docs.typesafe.ai/primitives/score)
- [TypeSafe 技能仓库](https://github.com/typesafe-ai/skills) 与 [Agent Skills 规范](https://agentskills.io/specification)
- [skills CLI 平台路径及参数](https://github.com/vercel-labs/skills)

本仓库代码使用 [Apache-2.0](LICENSE)；公开 benchmark 数据集按 [NOTICE](benchmarks/NOTICE.md) 中的原许可证分发。模型权重需单独从官方来源获取，本仓库不包含权重。
