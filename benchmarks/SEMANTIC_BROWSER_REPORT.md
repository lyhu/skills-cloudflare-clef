# Ego Clef 网页语义操作验证报告

验证日期：2026-10-04 · 环境：真实 `ego-browser` + 本地 Clef HTTP 服务 · 决策阈值：0.6。

本报告记录了将 Clef 扩展至通用无站点名单（Site-agnostic）语义控件决策的功能验证。在受控 HTML 页面与公开 Python 文档站点中，测试了菜单展开、输入填充、下拉选择、按钮点击及 Enter 提交等典型交互。所有任务完成均由代码层独立校验 DOM/URL 状态，严禁以模型概率作为完成证明。

---

## 1. 交互任务实测表现

| 任务场景 | 触发操作序列 | 有效决策次数 | 端到端循环耗时 | 校验结果 |
| :--- | :--- | :---: | :---: | :---: |
| **展开导航菜单**（受控页面） | `click` | 1 | 0.60 s | Verified |
| **表单填写并提交**（受控页面） | `fill` → `click` | 2 | 2.31 s | Verified |
| **分类选择与筛选**（受控页面） | `click` → `select` → `click` | 3 | 1.94 s | Verified |
| **文档搜索与回车提交**（公开站点） | `fill` → `press` | 2 | 1.96 s | Verified |

> **注**：循环耗时涵盖页面状态捕获、Python 客户端中转、HTTP 通信、浏览器 CDP 动作执行、DOM 状态等待及最终完成检查；不含初始页面导航时间。每次任务通过 `run_id` 与本地事件日志严格对应。

---

## 2. 关键工程问题与调优方案

在原型调试中暴露了三类典型工程问题，已针对性修复：
1. **整页控件塞入导致 Token 超限**：
   - *问题*：直接序列化全页 DOM 元素易超出服务 4,096 Token 上限。
   - *方案*：精简候选上下文，仅提取具有语义角色、非隐藏且可见的候选控件（单步上限 24 个）。
2. **输入未就绪提前触发提交**：
   - *问题*：模型在尚未填充搜索词时倾向于直接点击提交。
   - *方案*：主 Agent 策略注入前置条件约束（如目标输入框有值后方允许触发提交动作）。
3. **SPA 等待条件与 DOM 渲染竞争**：
   - *问题*：ARIA landmark 与原生 HTML 标签混淆，导致未等待结果就绪即触发完成核验。
   - *方案*：绑定具体结果容器的锚点属性检测（如 `dataset.ready === 'true'`）。

相关早期调试轨迹保留于 [development-findings.json](reports/semantic-browser/development-findings.json)。

---

## 3. 边界与复现指南

- **适用边界**：本验证确认了站点无关的语义 DOM 决策可行性。截图/Canvas、复杂拖拽、iframe/Shadow DOM 隔离、文件下载、登录认证、支付及弹窗确认等高敏感操作，统一由主 Agent 接管。
- **原始数据**：[results.json](reports/semantic-browser/results.json)。

### 本地复现步骤

```bash
# 1. 启动本地受控页面服务
python3 -m http.server 8878 --bind 127.0.0.1 --directory benchmarks/fixtures
```

在配置好端点的 `ego-browser nodejs` 环境中执行：
```javascript
const bench = await import("/path/to/benchmarks/semantic-browser.mjs");
const task = await taskSpace("Semantic Browser Test");
const page = task.page("p1");

// 运行受控页面试验（index: 0, 1, 2）
await bench.trial(page, "http://127.0.0.1:8878/semantic.html", 0);

// 运行公开站点搜索试验
await bench.pythonSearchTrial(page);

await task.finish({ keep: [] });
```

