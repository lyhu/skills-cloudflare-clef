#!/usr/bin/env python3
"""Generate a concise report from persisted live measurements; makes no HTTP requests."""

import json
import statistics
from pathlib import Path


HERE = Path(__file__).resolve().parent
LIVE = HERE / "reports/live"


def main():
    trials = [json.loads(p.read_text()) for p in sorted((LIVE / "browser").glob("normalized-*.json"))]
    groups = {arm: [t for t in trials if t["arm"] == arm] for arm in ("agent", "clef")}
    if any(len(group) != 2 for group in groups.values()):
        raise ValueError("Expected two completed trials per arm")
    reference = groups["agent"][0]["judgments"]
    corpus = [(j["url"], j["text_sha256"]) for j in reference]
    if len(corpus) != 8 or any([(j["url"], j["text_sha256"]) for j in t["judgments"]] != corpus for t in trials):
        raise ValueError("Live inputs differ: cannot report an identical-corpus comparison")
    if len({t["driver_sha256"] for t in trials}) != 1:
        raise ValueError("Browser driver changed between trials")
    means = {arm: {key: statistics.mean(t[key] for t in group) / 1000
                   for key in ("total_ms", "browser_ms", "decision_ms")} for arm, group in groups.items()}
    agreement = sum(j["application"] == reference[i]["application"]
                    for t in groups["clef"] for i, j in enumerate(t["judgments"]))
    a, b = means["agent"], means["clef"]
    date = max(t["timestamp_utc"] for t in trials)[:10]
    lines = [f"# Clef 基准评测报告 · {date}", "",
             f"**X 平台搜索结果读取与语义筛选：平均耗时 {a['total_ms']:.2f}s → {b['total_ms']:.2f}s，"
             f"提速 {a['total_ms']/b['total_ms']:.2f}×，耗时降低 {(1-b['total_ms']/a['total_ms'])*100:.1f}%。**", "",
             "---", "",
             "## 1. 浏览器对照实验", "",
             "`jev typesafe` · X Latest · 8 条公开推文（URL 与文本哈希完全对齐）· ego-browser · A–B–B–A 交叉测试 · 每组 2 次试验。", "",
             "| 执行方案 | 任务平均耗时 | 浏览器读取耗时 | 语义判定耗时 | 判定交互轮次 |",
             "| :--- | :--- | :--- | :--- | :--- |",
             f"| **Codex 对照组** | {a['total_ms']:.2f} s | {a['browser_ms']:.2f} s | {a['decision_ms']:.2f} s | 1 轮长 Token 推理交互 |",
             f"| **Clef 实验组** | {b['total_ms']:.2f} s | {b['browser_ms']:.2f} s | {b['decision_ms']:.2f} s | 1 次 HTTP 请求 (8 并发 Noul) |", "",
             f"- **符合率**：Clef 判定与 Agent 参考判定达 **{agreement}/16 完全一致**（基于 8 个独立样本推文）。",
             "- **收益归因**：性能提升主要源于省去了主 Agent 的大模型长思考与轮次交互开销；固定 URL 导航与 DOM 提取仍由代码执行。",
             "- **边界说明**：本试验属于热会话受控测试。Agent 耗时包含模型思考与工具通信，未测定纯 GPU 时间；不含外部链接延展、事实核验与报告撰写流程。", "",
             "---", "",
             "## 2. 真实 HTTP 决策基准测试", "",
             "| 测试集 | 独立样本量 | 有效响应率 | 判定符合率 | 时延 p50 | 时延 p95 |",
             "| :--- | :--- | :--- | :--- | :--- | :--- |"]
    for suite, label in (("smoke", "Smoke 冒烟集"), ("boolq", "BoolQ 子集"), ("banking77", "BANKING77 (12 类适配)")):
        result = json.loads((LIVE / suite / "results.json").read_text())
        m = result["summary"]
        latency = m["successful_latency_ms"]
        p50, p95 = (f"{latency['p50']:.1f} ms", f"{latency['p95']:.1f} ms") if latency else ("N/A", "N/A")
        lines.append(f"| [{label}](reports/live/{suite}/report.md) | {result['metadata']['case_count']} | "
                     f"{m['successful']}/{m['requests']} | {m['matched']}/{m['requests']} | {p50} | {p95} |")
    lines += ["",
              "- **测试配置**：每用例串行重复 3 次，每套预热 3 次，零网络重试；通过 Nginx 接入 A800 GPU 7 单卡服务。",
              "- **样本说明**：重复测试用于检验时延方差，不增加独立样本量；BANKING77 经 12 类适配，非原版 77 分类成绩。",
              "- **运维记录**：初次批量请求曾因梯度未关闭触发 CUDA OOM，经授权在推理服务中加入 `@torch.inference_mode()` 修复并重启复测；[故障复盘报告](reports/live/service-incident.md)已完整归档。", "",
              "---", "",
              "## 3. 相关文档索引", "",
              "- [评测协议与方法论](METHODOLOGY.md)",
              "- [数据来源与开源许可](NOTICE.md)",
              "- [逐轮浏览器原始数据](reports/live/browser/)",
              "- [X 平台落地场景与证据](X-APPLICATIONS.md)",
              "- [静态与运行时验证记录](reports/live/validation.md)", ""]
    (HERE / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Browser: {a['total_ms']:.3f}s -> {b['total_ms']:.3f}s, {a['total_ms']/b['total_ms']:.3f}x; agreement {agreement}/16")


if __name__ == "__main__":
    main()
