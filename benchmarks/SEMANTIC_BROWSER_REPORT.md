# Ego Clef 语义操作验证

2026-10-04 · 真实 ego-browser + 本地 Clef HTTP · 阈值 0.6 · 每任务最终验证 1 次。

移除 GitHub/X 站点名单，新增语义控件决策。受控页面验证菜单、输入、下拉及按钮；公开 Python 文档站点验证搜索和 Enter 提交。每次完成均由 DOM/URL 检查确认，模型概率不作为完成证明。

| 任务 | 操作序列 | 有效 HTTP 决策 | 循环耗时 | 结果 |
| --- | --- | ---: | ---: | --- |
| 展开菜单（受控页面） | click | 1 | 0.60 s | verified |
| 填写并提交搜索（受控页面） | fill → click | 2 | 2.31 s | verified |
| 选择分类并应用筛选（受控页面） | click → select → click | 3 | 1.94 s | verified |
| Python 文档搜索（公开站点） | fill → press | 2 | 1.96 s | verified |

循环耗时包含观察、Python 客户端、HTTP、浏览器动作、等待及完成检查；不包含初始页面加载。请求与完成记录可用原始数据中的 `run_id` 对照本机调用日志。

**结论与限制**：当前实现能处理站点无关的语义 DOM 操作。这是开发后功能验证，测试任务参与了调试；单次、小样本且没有同任务的主 Agent 基线，不能据此推断普遍成功率或速度收益。截图/Canvas、拖拽、iframe/Shadow DOM 专项操作、文件、登录、支付、发布及弹窗处理仍由主 Agent 接手。

调试中发现整页控件超出服务 4096-token 限额、空搜索提前提交、等待条件混淆 ARIA main 与 HTML main；分别通过精简决策上下文、提交前状态策略、实际结果锚点验证修正。初期失败摘要保留在 [development-findings.json](reports/semantic-browser/development-findings.json)。操作策略由主 Agent 根据授权任务绑定，不由模型授予权限。

原始结果与源码摘要：[results.json](reports/semantic-browser/results.json)。复现入口：[semantic-browser.mjs](semantic-browser.mjs)，受控页面：[semantic.html](fixtures/semantic.html)。

```bash
python3 -m http.server 8878 --bind 127.0.0.1 --directory benchmarks/fixtures
```

在已配置端点的 ego-browser 同一个 TaskSpace/Page 中，调用 `trial(page, "http://127.0.0.1:8878/semantic.html", index)`（index 为 0、1、2）；公开站点调用 `pythonSearchTrial(page)`。由调用方在全部完成后结束该 TaskSpace。调试输出和测试脚本只用于复现，日常用户仍直接描述浏览器任务。
