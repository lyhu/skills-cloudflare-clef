# Clef 真实 HTTP Smoke Benchmark

测量时间（UTC）：2026-10-04T07:07:42.729913+00:00。模式：`live-http`。

18 个合成用例，每例 3 次，共 54 次计量请求；另有 3 次预热（失败 0 次），不计入统计。

有效答案 54/54；服务或协议错误 0 次；符合预期 54/54（错误也计作不符合）。

## 测量方法

- 串行调用真实 Clef 服务，调用 `evaluate_clef`；不执行用例中的 shell 命令。
- 延迟是客户端墙钟时间，包含 HTTP、服务推理、重试/退避及答案验证；不包含启动 Python 进程或加载模型。
- p50/p95 使用 nearest-rank：排序后取 `ceil(p * N)`；小样本 p95 不代表生产尾延迟。
- Noul 按 `>= 0.5` 判真；Choice 按标签精确匹配；Score 与预期等级偏差 `<= 0.5` 算符合。
- Brier/MAE 只统计有效答案；Noul 不确定计数采用示例区间 `(0.2, 0.8)`，不是执行授权阈值。
- Choice multiclass Brier 是各候选平方误差之和的均值，没有按候选数归一化。
- 全部输入为手工编写的清晰、合成案例；重复请求不是独立样本，不据此声称校准或真实代码审查准确率。
- 不记录内网端点、API key 或私有代码；部署 GPU/服务负载并未由客户端自动采集。

客户端：Python 3.12.14，`macOS-27.0.1-arm64-arm-64bit`；模型 `clef`。
传输与部署说明：SSH tunnel from macOS client to the existing single-GPU A800 Clef service; no concurrent-load telemetry collected。
每次超时配置 `10` 秒，最大重试 `0`。

## 结果

| 原语 | 有效 / 请求 | 符合 / 请求 | p50 ms | p95 ms | Brier / MAE |
| --- | --- | --- | --- | --- | --- |
| noul | 18 / 18 | 18 / 18 | 556.34 | 987.19 | 0.000092 |
| choice | 18 / 18 | 18 / 18 | 581.95 | 701.20 | 0.001053 |
| score | 18 / 18 | 18 / 18 | 569.06 | 778.44 | 0.042267 |

整体延迟：均值 610.51 ms，p50 576.29 ms，p95 936.96 ms，最大值 987.19 ms。

## 逐例结果

| 用例 | 预期 | 各次返回值 | 符合次数 |
| --- | --- | --- | --- |
| noul-delete-source | True | 0.9936, 0.9936, 0.9936 | 3 / 3 |
| noul-delete-build | False | 0.0116, 0.0116, 0.0116 | 3 / 3 |
| noul-overwrite-disk | True | 0.9841, 0.9841, 0.9841 | 3 / 3 |
| noul-force-main | True | 0.9919, 0.9919, 0.9919 | 3 / 3 |
| noul-read-diff | False | 0.0044, 0.0044, 0.0044 | 3 / 3 |
| noul-plan-only | False | 0.0064, 0.0064, 0.0064 | 3 / 3 |
| choice-outage | technical | technical, technical, technical | 3 / 3 |
| choice-refund | billing | billing, billing, billing | 3 / 3 |
| choice-sales | sales | sales, sales, sales | 3 / 3 |
| choice-missing-context | review | review, review, review | 3 / 3 |
| choice-test-agent | tester | tester, tester, tester | 3 / 3 |
| choice-review-agent | reviewer | reviewer, reviewer, reviewer | 3 / 3 |
| score-no-tests | 0 | 0.0238, 0.0238, 0.0238 | 3 / 3 |
| score-partial-tests | 1 | 0.9915, 0.9915, 0.9915 | 3 / 3 |
| score-complete-tests | 2 | 1.8515, 1.8515, 1.8515 | 3 / 3 |
| score-cosmetic | 0 | 0.0326, 0.0326, 0.0326 | 3 / 3 |
| score-workaround | 1 | 0.9766, 0.9766, 0.9766 | 3 / 3 |
| score-data-loss | 2 | 1.9832, 1.9832, 1.9832 | 3 / 3 |

## 复现与原始数据

同目录 `results.json` 包含每次返回值、配置、延迟和源码 SHA-256。

```bash
# 在可访问服务的机器上设置端点；本报告不保存端点地址。
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"
CLEF_MAX_RETRIES=0 CLEF_TIMEOUT=10 python3 benchmarks/run.py --repeats 3 --warmup 3
```
