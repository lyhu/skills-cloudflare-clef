# Clef Benchmark · 2026-10-04

**X 搜索结果读取与语义筛选：平均 9.04 s → 4.02 s，2.25×，耗时减少 55.6%。**

## 浏览器对比

`jev typesafe` · X Latest · 相同 8 条公开帖子及文本哈希 · ego-browser · A–B–B–A · 每组 2 次。

| 执行方式 | 任务平均 s | 浏览器读取 s | 判断阶段 s | 每轮判断调用 |
| --- | --- | --- | --- | --- |
| 当前 Codex | 9.04 | 2.94 | 6.10 | 1 次 Agent 轮次 |
| Clef | 4.02 | 2.81 | 1.21 | 1 次 HTTP，8 个 Noul |

Clef 与 Agent 参考判断 **16/16 一致**（8 个独立帖子，不是外部准确率）。收益主要来自减少 Agent 判断轮次；固定导航与 DOM 读取仍由代码执行。

这是热会话、熟悉输入的小样本试验。Agent 判断时间含推理与工具传输，未取得纯推理时间和确切模型 ID；不包含展开原帖、事实核验与撰写报告，也不代表任意浏览器任务的速度。

## 真实 HTTP 决策测试

| 测试集 | 独立样本 | 有效 / 请求 | 符合 / 请求 | p50 ms | p95 ms |
| --- | --- | --- | --- | --- | --- |
| [Smoke](reports/live/smoke/report.md) | 18 | 54/54 | 54/54 | 375.7 | 521.1 |
| [BoolQ](reports/live/boolq/report.md) | 24 | 72/72 | 66/72 | 386.4 | 538.4 |
| [BANKING77 · 12 类适配](reports/live/banking77/report.md) | 24 | 72/72 | 69/72 | 415.8 | 555.9 |

每例重复 3 次、每套预热 3 次、串行、零重试；HTTP 经 Nginx 到 A800 GPU 7。重复不增加独立样本数；经典数据集为选取的小子集，BANKING77 非原版 77 类成绩。

首次批量请求触发 CUDA OOM，随后单问题也失败。经授权为服务推理线程添加 `torch.inference_mode()` 并重启后复测；[修复前失败记录](reports/live/service-incident.md)完整保留。

[测量与复现方法](METHODOLOGY.md) · [数据来源与许可](NOTICE.md) · [逐轮浏览器原始数据](reports/live/browser/) · [X 应用场景与证据](X-APPLICATIONS.md) · [验证记录](reports/live/validation.md)
