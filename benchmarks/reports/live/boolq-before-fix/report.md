# Clef 结构化决策基准评测报告（修复前记录）

UTC 时间：2026-10-04T07:43:52.958992+00:00 · 数据集：`benchmarks/datasets/boolq.json` · 24 用例 × 3 次重复 · 排除 3 次预热。

| 原语 | 有效 / 请求 | 符合 / 请求 | p50 ms | p95 ms | Brier / MAE |
| :--- | :--- | :--- | :--- | :--- | :--- |
| noul | 0/72 | 0/72 | N/A | N/A | N/A |

网络与部署：局域网直连用户端点；无 SSH 隧道；服务硬件与负载未采集。模型：`clef`；超时：10.0 s；重试：0；异常数：72。

说明：有效请求时延涵盖 HTTP 往返、推理、重试退避与 Schema 校验；分位数采用 Nearest-Rank。判定准则：Noul 阈值 0.5；Choice 标签精确匹配；Score 容差 0.5。Brier/MAE 仅统计有效响应；符合率包含异常请求。重复测试用于检验时延方差，不构成独立样本。

子集评测仅供工程验证与性能诊断，不代表官方排行榜或生产环境全貌。详见 [评测方法论](../../../METHODOLOGY.md) 与 [原始结果](results.json)。

未符合用例： `boolq-validation-0` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-1` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-2` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-3` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-4` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-5` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-6` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-7` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-8` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-9` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-10` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-11` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-12` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-13` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-14` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-20` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-27` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-32` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-36` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-38` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-39` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-41` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-43` (CLEF_SERVICE_UNAVAILABLE), `boolq-validation-52` (CLEF_SERVICE_UNAVAILABLE)。

