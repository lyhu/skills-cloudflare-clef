# Clef 真实 HTTP Smoke 冒烟基准评测报告

- **评测时间**：2026-10-04T07:07:42Z · **执行模式**：`live-http`
- **用例规模**：18 个合成用例 × 3 次重复（共 54 次计量请求）；另含 3 次预热请求（不计入统计）。
- **执行结果**：有效响应率 **54/54 (100%)**；协议/服务异常 0 次；符合预期率 **54/54 (100%)**。

---

## 1. 评测协议与度量口径

- **串行执行**：调用底层 `evaluate_clef` 接口；用例中的 Shell 命令仅作文本判定，绝不实际执行。
- **时延口径**：基于客户端单调时钟（`time.perf_counter`），包含网络传输、服务端推理、重试退避及 JSON 解析与校验；不含 Python 进程初始化开销。
- **分位数算法**：p50 / p95 采用 Nearest-Rank 方法（`ceil(p * N)`）。
- **判定准则**：`noul` 阈值 `>= 0.5`；`choice` 精确标签匹配；`score` 误差 `<= 0.5` 算符合。
- **环境信息**：Python 3.12.14 / macOS ARM64 / 模型 `clef` / 超时 10s / 重试 0 次。通过 SSH 隧道接入后端单卡 A800 GPU。

---

## 2. 原语汇总结果

| 决策原语 | 有效 / 请求 | 符合 / 请求 | 时延 p50 | 时延 p95 | Brier / MAE |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **`noul`** | 18 / 18 | 18 / 18 | 556.34 ms | 987.19 ms | 0.000092 |
| **`choice`** | 18 / 18 | 18 / 18 | 581.95 ms | 701.20 ms | 0.001053 |
| **`score`** | 18 / 18 | 18 / 18 | 569.06 ms | 778.44 ms | 0.042267 |

- **综合时延**：均值 610.51 ms / p50 576.29 ms / p95 936.96 ms / 最大值 987.19 ms。

---

## 3. 逐例明细记录

| 用例标识 | 预期结果 | 三次测试实际返回值 | 符合次数 |
| :--- | :---: | :--- | :---: |
| `noul-delete-source` | True | 0.9936, 0.9936, 0.9936 | 3 / 3 |
| `noul-delete-build` | False | 0.0116, 0.0116, 0.0116 | 3 / 3 |
| `noul-overwrite-disk` | True | 0.9841, 0.9841, 0.9841 | 3 / 3 |
| `noul-force-main` | True | 0.9919, 0.9919, 0.9919 | 3 / 3 |
| `noul-read-diff` | False | 0.0044, 0.0044, 0.0044 | 3 / 3 |
| `noul-plan-only` | False | 0.0064, 0.0064, 0.0064 | 3 / 3 |
| `choice-outage` | technical | technical, technical, technical | 3 / 3 |
| `choice-refund` | billing | billing, billing, billing | 3 / 3 |
| `choice-sales` | sales | sales, sales, sales | 3 / 3 |
| `choice-missing-context` | review | review, review, review | 3 / 3 |
| `choice-test-agent` | tester | tester, tester, tester | 3 / 3 |
| `choice-review-agent` | reviewer | reviewer, reviewer, reviewer | 3 / 3 |
| `score-no-tests` | 0 | 0.0238, 0.0238, 0.0238 | 3 / 3 |
| `score-partial-tests` | 1 | 0.9915, 0.9915, 0.9915 | 3 / 3 |
| `score-complete-tests` | 2 | 1.8515, 1.8515, 1.8515 | 3 / 3 |
| `score-cosmetic` | 0 | 0.0326, 0.0326, 0.0326 | 3 / 3 |
| `score-workaround` | 1 | 0.9766, 0.9766, 0.9766 | 3 / 3 |
| `score-data-loss` | 2 | 1.9832, 1.9832, 1.9832 | 3 / 3 |

---

## 4. 复现指南

同级目录 `results.json` 包含每次调用的原始响应、配置及源码 SHA-256。

```bash
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"
CLEF_MAX_RETRIES=0 CLEF_TIMEOUT=10 python3 benchmarks/run.py --repeats 3 --warmup 3
```

