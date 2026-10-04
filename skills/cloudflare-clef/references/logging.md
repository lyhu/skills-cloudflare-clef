# Clef 调用日志与统计

`evaluate_clef` 默认为 Python、CLI 和子进程调用写入 `~/.local/state/clef/events.jsonl`。标准输出、返回字典和退出码保持原协议；无需用户手动开启日志。

## 事件与统计口径

| 事件 | 含义 | 统计用途 |
| --- | --- | --- |
| `call` | 一次客户端调用结束；含输入/配置失败 | 调用量、成功率、原语、来源、总耗时与用量 |
| `attempt` | 一次网络尝试结束；重试单独记录 | HTTP 尝试量、状态码与单次耗时 |
| 可选的 `run` | 宿主工作流的完成/交接记录 | 任务结果；不能直接当作模型调用 |

`call_id` 关联一次调用与其网络尝试；`run_id` 可关联多次调用到同一工作流。记录包含 `schema_version: 1`、UTC 时间、`source`、`primitive`、请求模型别名、后端返回的已识别模型别名、耗时、尝试/重试次数、错误码/HTTP 状态、请求字节数、候选数，以及可用的概率或分数。**不保存 state、instructions、候选文字、完整 URL/端点、密钥、响应正文或原始异常。**

日志中的 `input_tokens`、`output_tokens`、`total_tokens` 仅采用后端提供的非负整数，缺失不估算。统计用量只累加 `call`，不重复累加 `attempt`。`usage_reported_calls` 显示输入用量覆盖率；输出中 token 总和为已报告值之和，缺失记录不代表零消耗。

客户端成功表示收到并验证了类型合法的答案，不保证工作流完成、答案正确或置信度满足业务阈值。网络尝试不证明远端完成推理。日志在事件结束时写入；强制结束进程可能留下不完整记录，不能作为计费账本。

## 查询

解析 `<skill-dir>` 为本技能的绝对安装目录：

```bash
# 今天的汇总（按运行机器的本地日期）
python3 <skill-dir>/scripts/log_stats.py --today

# 指定来源和起始时间；ISO 时间未写时区时采用本地时区
python3 <skill-dir>/scripts/log_stats.py --source ego-clef --since 2026-10-04

# 供后续分析、脚本或报表使用的 JSON
python3 <skill-dir>/scripts/log_stats.py --today --json
```

默认汇总调用量、成功/错误数、HTTP 尝试、重试、p50/p95 与来源用量。JSON 还提供原语/模型分组、错误码及 HTTP 状态分布、关联工作流数。耗时使用单调时钟；客户端 `call.duration_ms` 包含网络、验证、退避及尝试日志开销，不是 GPU 推理耗时。分位数采用 nearest-rank。

`--file` 可重复，用于读取轮转文件或宿主工作流日志；同一 `call_id` 的 call、同一 call/attempt、同一 run 会去重。只把 `call` 算作调用，忽略宿主额外的 `decision` 视图。无效/半行 JSON 会跳过并报告数量；没有文件时返回空统计，不补造历史。

## 配置

| 环境变量 | 默认值 | 用途 |
| --- | --- | --- |
| `CLEF_LOG_ENABLED` | `1` | 设为 `0` 关闭记录；决策结果不受影响 |
| `CLEF_LOG_PATH` | `~/.local/state/clef/events.jsonl` | 通用 JSONL 文件，可用于隔离评测或应用日志 |
| `CLEF_LOG_SOURCE` | `cloudflare-clef` | 非敏感来源标签，1–48 位小写字母、数字、`-`、`_` |
| `CLEF_RUN_ID` | 无 | 可选 UUID，用于关联工作流 |
| `CLEF_CALL_ID` | 每次自动生成 UUID | 宿主为单次调用提供 UUID；不要在多次调用之间复用 |

每条记录采用追加写入，文件权限 0600；新建日志目录权限 0700。日志写入失败不会阻断决策，也不改变 stdout/stderr。定期轮转由宿主或操作系统负责；脚本不会自动删除历史记录。
