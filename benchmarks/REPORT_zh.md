[English](REPORT.md) | **简体中文**

# Clef 基准评测报告 · 2026-10-04

**X 平台搜索结果读取与语义筛选：平均耗时 9.04s → 4.02s，提速 2.25×，耗时降低 55.6%。**

---

## 1. 浏览器对照实验

`jev typesafe` · X Latest · 8 条公开推文（URL 与文本哈希完全对齐）· ego-browser · A–B–B–A 交叉测试 · 每组 2 次试验。

| 执行方案 | 任务平均耗时 | 浏览器读取耗时 | 语义判定耗时 | 判定交互轮次 |
| :--- | :--- | :--- | :--- | :--- |
| **Codex 对照组** | 9.04 s | 2.94 s | 6.10 s | 1 轮长 Token 推理交互 |
| **Clef 实验组** | 4.02 s | 2.81 s | 1.21 s | 1 次 HTTP 请求 (8 并发 Noul) |

- **符合率**：Clef 判定与 Agent 参考判定达 **16/16 完全一致**（基于 8 个独立样本推文）。
- **收益归因**：性能提升主要源于省去了主 Agent 的大模型长思考与轮次交互开销；固定 URL 导航与 DOM 提取仍由代码执行。
- **边界说明**：本试验属于热会话受控测试。Agent 耗时包含模型思考与工具通信，未测定纯 GPU 时间；不含外部链接延展、事实核验与报告撰写流程。

---

## 2. 真实 HTTP 决策基准测试

| 测试集 | 独立样本量 | 有效响应率 | 判定符合率 | 时延 p50 | 时延 p95 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| [Smoke 冒烟集](reports/live/smoke/report.md) | 18 | 54/54 | 54/54 | 375.7 ms | 521.1 ms |
| [BoolQ 子集](reports/live/boolq/report.md) | 24 | 72/72 | 66/72 | 386.4 ms | 538.4 ms |
| [BANKING77 (12 类适配)](reports/live/banking77/report.md) | 24 | 72/72 | 69/72 | 415.8 ms | 555.9 ms |

- **测试配置**：每用例串行重复 3 次，每套预热 3 次，零网络重试；通过 Nginx 接入 A800 GPU 7 单卡服务。
- **样本说明**：重复测试用于检验时延方差，不增加独立样本量；BANKING77 经 12 类适配，非原版 77 分类成绩。
- **运维记录**：初次批量请求曾因梯度未关闭触发 CUDA OOM，经授权在推理服务中加入 `@torch.inference_mode()` 修复并重启复测；[故障复盘报告](reports/live/service-incident.md)已完整归档。

---

## 3. 相关文档索引

- [评测协议与方法论](METHODOLOGY.md) (中文: [METHODOLOGY_zh.md](METHODOLOGY_zh.md))
- [数据来源与开源许可](NOTICE.md) (中文: [NOTICE_zh.md](NOTICE_zh.md))
- [逐轮浏览器原始数据](reports/live/browser/)
- [X 平台落地场景与证据](X-APPLICATIONS.md) (中文: [X-APPLICATIONS_zh.md](X-APPLICATIONS_zh.md))
- [静态与运行时验证记录](reports/live/validation.md)
