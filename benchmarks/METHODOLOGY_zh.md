[English](METHODOLOGY.md) | **简体中文**

# 基准测试方法论与评测协议

本规范定义了决策模型基准测试与浏览器对照实验的度量标准、执行协议与复现流程。

---

## 1. 结构化决策评测协议

### 数据集设计与划分
- **Smoke（冒烟测试集）**：18 个原创合成用例，覆盖高危风控拦截（Noul）、业务语义分流（Choice）及代码审查打分（Score）。
- **BoolQ 子集**：选取公开验证集前 100 行中平衡的 24 个样本（真/假各 12 例），保留完整原始篇章与问题，不进行文本截断。
- **BANKING77 适配集**：选取 12 个意图类别，每类取 2 条测试样本（共 24 例）。由于当前服务单次支持最多 64 个候选，因此适配为 12 分类任务，不直接等同于原始 77 分类基准。

### 度量标准与统计指标
- **执行规则**：每个用例串行重复执行 3 次，每套测试前包含 3 次不计入统计的预热请求。未针对测试样本进行 Prompt 或权重调优。
- **符合性判定**：
  - `noul`：概率 `>= 0.5` 判定为命题成立。
  - `choice`：输出标签与真实标签完全精确匹配。
  - `score`：期望得分与真实等级绝对偏差 `<= 0.5` 判定为符合。
- **误差指标**：
  - 服务错误计为不符合。Brier 分数与 MAE 仅统计返回有效答案的样本。
  - 多分类 Brier 分数（Multiclass Brier）计算所有候选类别概率平方误差的总和均值，未进行类别数归一化。
- **时延度量**：
  - 基于 Python 客户端的 `time.perf_counter` 单调时钟，涵盖 HTTP 网络往返、服务端推理、退避重试、响应反序列化及 Schema 校验耗时；不包含 Python 解释器启动与模型加载时间。
  - p50 / p95 分位数采用 Nearest-Rank 方法（`ceil(p * N)`）。重复请求用于评估时延波动性，不构成独立样本。

### 执行与复现指南

```bash
export CLEF_BACKEND_URL="http://127.0.0.1:8000/v1/systemone"

# 1. 运行 BoolQ 评测
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --cases benchmarks/datasets/boolq.json \
  --repeats 3 --warmup 3 --output-dir benchmarks/reports/live/boolq

# 2. 运行 BANKING77 评测
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --cases benchmarks/datasets/banking77.json \
  --repeats 3 --warmup 3 --output-dir benchmarks/reports/live/banking77

# 3. 运行 Smoke 冒烟评测
CLEF_MAX_RETRIES=0 python3 benchmarks/run.py --output-dir benchmarks/reports/live/smoke

# 4. 生成统一基准汇总报告
python3 benchmarks/report.py
```

> **评测局限性提示**：上述子集仅用于客户端协议与推理时延的工程诊断，不代表官方排行榜成绩、通用生产准确率、全局校准度或训练数据防污染评估。

---

## 2. 浏览器实机对照实验：X 平台应用分流

### 实验任务与受控环境
- **任务目标**：在 X 实时搜索 `jev typesafe`，读取并审查前 8 条加载的公开推文，判定哪些描述了具体的 Jev 落地应用场景。
- **受控变量**：完全相同的浏览器会话、页面上下文、搜索 URL、单帖 600 字符文本预算、相关性判定指令及 0.5 Clef 阈值。
- **DOM 脱敏与清洗**：克隆 DOM 节点并移除第三方沉浸式翻译插件注入的附属节点；在截断前对空白字符及 Unicode NFC 归一化，严禁篡改页面实时 DOM。
- **导航确定性**：两组实验均采用相同的三个底层 CDP 操作：`goto` 页面导航、条件等待 `waitForFunction`、DOM 提取 `evaluate`。本实验专一计量**阅读推文并完成语义判定的交互轮次**，而非 DOM 自主寻路。

### 对照组设计（A-B-B-A 交叉设计）
- **Agent 对照组（当前 Codex 会话）**：读取提取出的文本证据，在下一轮工具调用中提交 8 个布尔判定。决策耗时涵盖大模型推理、工具通信及第二次浏览器调用。
- **Clef 实验组**：发起一次轻量 HTTP 请求，单次批量评估全部 8 个 Noul 命题，并在同一浏览器调用内直接返回判定。无额外 Agent 交互轮次。
- **执行顺序**：按照 A–B–B–A 顺序交叉执行，每组各执行 2 次独立实验（记录为 `normalized-*`），消除缓存与会话预热造成的单向偏差。

### 实验代码复现

在 `ego-browser nodejs` 环境中，整个实验共用同一个 TaskSpace：

```javascript
const task = await taskSpace("Clef X triage pilot");
const bench = await import("file:///path/to/skills-cloudflare-clef/benchmarks/browser.mjs");

// 1. 运行 Agent 对照组试验 1
console.log(await bench.begin(task.page("p1"), "agent", "normalized-agent-1"));
// （在下一轮会话中读取 8 条推文，调用 bench.finish("normalized-agent-1", eightBooleans)）

// 2. 运行 Clef 实验组试验 1
console.log(await bench.runClef(task.page("p1"), "normalized-clef-1", "http://127.0.0.1:8000/v1/systemone"));

// 3. 依次运行 normalized-clef-2 与 normalized-agent-2，实验结束后销毁 TaskSpace
```

> **方法论边界**：本试验属于受控环境下的 4 轮基准探针，旨在量化将简单语义判定卸载给轻量模型带来的交互轮次与耗时收益。实验不包含全流程研究（如打开外部信源、深入事实核查、长文撰写）。对于结构固定的选择器与页面操作，应保持由原生代码执行，仅在需要模糊语义判断时引入 Clef。
