# Clef 结构化决策基准评测报告

UTC 时间：2026-10-04T07:54:45.154674+00:00 · 数据集：`benchmarks/datasets/banking77.json` · 24 用例 × 3 次重复 · 排除 3 次预热。

| 原语 | 有效 / 请求 | 符合 / 请求 | p50 ms | p95 ms | Brier / MAE |
| :--- | :--- | :--- | :--- | :--- | :--- |
| choice | 72/72 | 69/72 | 415.84 | 555.86 | 0.041445 |

网络与部署：通过 Nginx 局域网代理至 A800 GPU 7；已应用 inference_mode 补丁；无并发干扰。模型：`clef`；超时：10.0 s；重试：0；异常数：0。

说明：有效请求时延涵盖 HTTP 往返、推理、重试退避与 Schema 校验；分位数采用 Nearest-Rank。判定准则：Noul 阈值 0.5；Choice 标签精确匹配；Score 容差 0.5。Brier/MAE 仅统计有效响应；符合率包含异常请求。重复测试用于检验时延方差，不构成独立样本。

子集评测仅供工程验证与性能诊断，不代表官方排行榜或生产环境全貌。详见 [评测方法论](../../../METHODOLOGY.md) 与 [原始结果](results.json)。

未符合用例： `banking77-test-0` (lost_or_stolen_card)。

