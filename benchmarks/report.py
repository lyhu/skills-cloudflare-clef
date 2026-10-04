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
    lines = [f"# Clef Benchmark · {date}", "",
             f"**X 搜索结果读取与语义筛选：平均 {a['total_ms']:.2f} s → {b['total_ms']:.2f} s，"
             f"{a['total_ms']/b['total_ms']:.2f}×，耗时减少 {(1-b['total_ms']/a['total_ms'])*100:.1f}%。**", "",
             "## 浏览器对比", "",
             "`jev typesafe` · X Latest · 相同 8 条公开帖子及文本哈希 · ego-browser · A–B–B–A · 每组 2 次。", "",
             "| 执行方式 | 任务平均 s | 浏览器读取 s | 判断阶段 s | 每轮判断调用 |",
             "| --- | --- | --- | --- | --- |",
             f"| 当前 Codex | {a['total_ms']:.2f} | {a['browser_ms']:.2f} | {a['decision_ms']:.2f} | 1 次 Agent 轮次 |",
             f"| Clef | {b['total_ms']:.2f} | {b['browser_ms']:.2f} | {b['decision_ms']:.2f} | 1 次 HTTP，8 个 Noul |", "",
             f"Clef 与 Agent 参考判断 **{agreement}/16 一致**（8 个独立帖子，不是外部准确率）。"
             "收益主要来自减少 Agent 判断轮次；固定导航与 DOM 读取仍由代码执行。", "",
             "这是热会话、熟悉输入的小样本试验。Agent 判断时间含推理与工具传输，未取得纯推理时间和确切模型 ID；"
             "不包含展开原帖、事实核验与撰写报告，也不代表任意浏览器任务的速度。", "",
             "## 真实 HTTP 决策测试", "",
             "| 测试集 | 独立样本 | 有效 / 请求 | 符合 / 请求 | p50 ms | p95 ms |",
             "| --- | --- | --- | --- | --- | --- |"]
    for suite, label in (("smoke", "Smoke"), ("boolq", "BoolQ"), ("banking77", "BANKING77 · 12 类适配")):
        result = json.loads((LIVE / suite / "results.json").read_text())
        m = result["summary"]
        latency = m["successful_latency_ms"]
        p50, p95 = (f"{latency['p50']:.1f}", f"{latency['p95']:.1f}") if latency else ("N/A", "N/A")
        lines.append(f"| [{label}](reports/live/{suite}/report.md) | {result['metadata']['case_count']} | "
                     f"{m['successful']}/{m['requests']} | {m['matched']}/{m['requests']} | {p50} | {p95} |")
    lines += ["", "每例重复 3 次、每套预热 3 次、串行、零重试；HTTP 经 Nginx 到 A800 GPU 7。"
              "重复不增加独立样本数；经典数据集为选取的小子集，BANKING77 非原版 77 类成绩。", "",
              "首次批量请求触发 CUDA OOM，随后单问题也失败。经授权为服务推理线程添加 "
              "`torch.inference_mode()` 并重启后复测；[修复前失败记录](reports/live/service-incident.md)完整保留。", "",
              "[测量与复现方法](METHODOLOGY.md) · [数据来源与许可](NOTICE.md) · "
              "[逐轮浏览器原始数据](reports/live/browser/) · [X 应用场景与证据](X-APPLICATIONS.md) · "
              "[验证记录](reports/live/validation.md)", ""]
    (HERE / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Browser: {a['total_ms']:.3f}s -> {b['total_ms']:.3f}s, {a['total_ms']/b['total_ms']:.3f}x; agreement {agreement}/16")


if __name__ == "__main__":
    main()
