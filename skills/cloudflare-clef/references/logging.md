# Clef 调用日志与可观测性规范

`evaluate_clef` 默认在本地记录结构化元数据日志（路径：`~/.local/state/clef/events.jsonl`），覆盖 Python 模块、CLI 及子进程调用。标准输出、返回字典及退出码保持原协议不变，对上层调用透明。

---

## 1. 事件模型与统计口径

| 事件类型 (`event`) | 触发时机 | 核心统计用途 |
| :--- | :--- | :--- |
| **`call`** | 客户端调用完成（含输入验证与配置错误） | 调用总量、成功率、原语分布、来源标签、端到端耗时与 Token 用量 |
| **`attempt`** | 单次 HTTP 网络尝试完成（含重试） | 网络尝试次数、HTTP 状态码分布、单次网络往返时延 |
| **`run`** (可选) | 宿主工作流阶段完成/交接记录 | 业务任务状态追踪（不计入底层模型推理次数） |

### 标识关联与数据契约
- **`call_id`**：唯一标识一次客户端调用，关联其下可能发生的多次 HTTP `attempt`。
- **`run_id`**：可选 UUID，用于将同一任务内的多次调用关联至统一宿主工作流。
- **记录规格**：包含 `schema_version: 1`、UTC 时间戳、`source` 来源、`primitive` 原语、请求与响应模型标识、端到端耗时、重试计数、状态码及结果分布。
- **安全与数据脱敏**：**严格禁止记录** `--state`、`--instructions`、候选文本、完整 URL、API 密钥、响应正文或异常堆栈。

### Token 用量统计口径
- 字段 `input_tokens`、`output_tokens`、`total_tokens` 仅记录服务端明确返回的非负整数，缺失时不进行臆测或估算。
- 用量累加仅基于 `call` 事件，避免多次 `attempt` 重复计算。
- `usage_reported_calls` 统计用量覆盖率；未报告用量仅表示指标缺失，不代表零消耗。

---

## 2. 自然语言与 CLI 查询

### 自然语言查询映射
Agent 支持直接通过自然语言触发本地日志查询，自动解析技能路径并返回结构化中文摘要，无需用户手动输入命令：

| 自然语言输入 | CLI 对应参数 | 查询范围与说明 |
| :--- | :--- | :--- |
| “查看 Clef 日志统计” / “今日调用情况” | `--today --json` | 本地日期当天、全部调用来源 |
| “查看今天 ego-clef 的调用统计” | `--today --source ego-clef --json` | 本地日期当天、限定 `ego-clef` 来源 |
| “统计最近七天 Clef 调用” | `--since <7天前ISO时间> --json` | 最近 7 天区间内汇总 |
| “查看 ego-clef 任务完成情况” | `--today --source ego-clef --file ... --file ...` | 同时读取通用调用日志与浏览器工作流日志 |

### CLI 使用示例

```bash
# 1. 查询今日调用汇总（本地时区）
python3 <skill-dir>/scripts/log_stats.py --today

# 2. 指定来源与起始日期
python3 <skill-dir>/scripts/log_stats.py --source ego-clef --since 2026-10-01

# 3. 输出结构化 JSON（供脚本或下游分析）
python3 <skill-dir>/scripts/log_stats.py --today --json

# 4. 联合分析通用日志与浏览器工作流日志
python3 <skill-dir>/scripts/log_stats.py --today --json \
  --file ~/.local/state/clef/events.jsonl \
  --file ~/.local/state/clef-browser/events.jsonl
```

### 统计指标定义
- **耗时指标**：客户端 `duration_ms` 基于单调时钟，涵盖网络传输、输入校验、退避重试及日志追加开销（非纯 GPU 推理时延）。
- **分位数算法**：p50 / p95 采用 Nearest-Rank 方法（`ceil(p * N)`）。
- **去重与容错**：自动对重复 `call_id`、`attempt` 与 `run` 去重；跳过异常半行并报告损毁记录数；日志缺失时返回空指标，杜绝捏造数据。

---

## 3. 环境变量配置

| 环境变量 | 默认值 | 作用说明 |
| :--- | :--- | :--- |
| `CLEF_LOG_ENABLED` | `1` | 设为 `0` 完全关闭日志记录；不影响决策执行 |
| `CLEF_LOG_PATH` | `~/.local/state/clef/events.jsonl` | 日志存储路径，支持按环境或测试隔离 |
| `CLEF_LOG_SOURCE` | `cloudflare-clef` | 调用方来源标识（1–48 字符，限小写字母、数字、短横线及下划线） |
| `CLEF_RUN_ID` | 空 | 可选的任务关联 UUID |
| `CLEF_CALL_ID` | 自动生成 | 单次调用 UUID；严禁跨调用复用 |

### 文件安全与生命周期
- 日志文件默认以追加模式写入，权限受控为 `0600`（新建父目录为 `0700`）。
- 日志写入失败（如磁盘只读）静默容错，不阻断核心决策流，不污染 stdout/stderr。
- 日志轮转由宿主系统或外部工具负责，本工具不主动清理历史文件。

