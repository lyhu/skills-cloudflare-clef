# 客户端、故障降级与 Benchmark 验证报告

验证日期：2026-10-04。环境：Python 3.12.14、Node 24.18.0、macOS ARM64。

这些结果来自本地 HTTP 假服务、受控异常注入和代码校验，不作为 Clef 模型性能结果。
真实服务的 54 次测量见 [report.md](report.md)，逐次数据见 [results.json](results.json)。

## 单元测试

```text
python3 -m unittest discover -s tests -v
Ran 29 tests in 1.528s
OK
```

21 项客户端/模板测试与 8 项 Benchmark 测试全部通过，无跳过项。
每项测试可能包含多个 `subTest`；29 是 unittest 测试方法数，不是独立故障案例数。

| 范围 | 注入或验证内容 | 观察到的结果 |
| --- | --- | --- |
| 原生协议 | Noul、Choice 标签/描述、Score、JSON 状态、Unicode、Bearer、模型别名 | 使用 `/v1/systemone`、`criteria`、`answers.verdict`；输出保留原语语义 |
| 临时服务错误 | HTTP 429/500/502/503/504 后恢复 | 有限重试后得到有效答案；退避符合配置 |
| 重试耗尽 | 持续 429、连接拒绝和超时异常 | 最多 3 次尝试；错误结构不含任何替代答案 |
| 永久 HTTP 错误 | 400/401/403/404/413/422 | 单次返回错误，不重试 |
| 实际 socket 超时 | 本地服务延迟超过 0.01 秒超时 | 返回 `CLEF_SERVICE_UNAVAILABLE`，不会放行 |
| 重定向 | 带凭据请求收到 HTTP 307 | 不跟随重定向，不向第二端点转发状态或凭据 |
| 不合法响应 | 损坏 JSON/UTF-8、错误嵌套、缺失类型、错误信封 | 返回 `CLEF_INVALID_RESPONSE`，不重试 |
| 不合法答案 | 布尔冒充概率、NaN/Infinity、越界、未知标签、分布错误、额外字段、置信度不一致、错误等级 | 拒绝答案，不生成允许操作的决策 |
| 原生舍入 | 64 个 Choice 候选、16 个 Score 等级 | 接受四位小数舍入产生的合理误差 |
| 输入和配置 | 缺失候选、重复标签、超限等级、错误超时/重试、非法 URL/模型/鉴权头 | 请求前拒绝，不访问服务 |
| CLI | 成功、评估错误、参数错误；禁用 Python site packages | 退出码分别为 0/1/2；运行时无第三方依赖 |
| Python 模板 | 将模板与客户端复制到独立临时应用目录 | 成功调用假服务并返回命名路由 |
| TypeScript 模板 | 字面传递 shell 元字符、正常结果和服务错误 | 通过无 shell 的 `execFile` 调用 Python；复用验证与错误降级 |
| Benchmark 用例 | 18 个唯一 ID、原语 schema 与预期标签合法性 | 三种原语均有用例，标签和请求符合契约 |
| Benchmark 统计 | nearest-rank p50/p95、Brier、multiclass Brier、MAE、阈值边界 | 公式及边界符合报告方法 |
| Benchmark 故障统计 | 部分失败、全部失败、预热排除、凭据不入报告 | 错误计入符合率分母；误差指标只含有效答案；没有虚构成绩 |
| Benchmark 访问控制 | 未显式设置端点 | 在发请求前以使用错误退出 |

## 分发与静态校验

以下检查通过：

- `python3 scripts/validate.py`：Frontmatter、版本/许可证一致性、Python/JSON/YAML 语法、JSON Schema、交付文件。
- skill-creator 的 `quick_validate.py skills/cloudflare-clef`：`Skill is valid!`。
- `npx skills add . --list`：识别到唯一技能 `cloudflare-clef`；只列出，未安装到用户宿主。
- `npm pack --dry-run`：包括核心技能、客户端、原语 schema、Python/TS 模板、README 与 Apache-2.0；不包含 `__pycache__` 或 `.pyc`。
- Node 24 加载 TypeScript 模板；另用本机 TypeScript 4.7.4 的 `tsc --noEmit --strict` 完成类型检查。

## 复现与边界

```bash
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate.py
python3 -m unittest discover -s tests -v
node --input-type=module -e "await import('./skills/cloudflare-clef/templates/client.ts')"
npm pack --dry-run
npx skills add . --list
```

CI 已配置 Python 3.9/3.12/3.14 和 Node 24。此本地报告只证明上述本机版本的结果；
GitHub Actions 需在仓库推送后运行，不能把配置矩阵当作已执行结果。

这些测试验证协议与故障路径，没有实际执行破坏性命令、停止模型服务或模拟 GPU 故障。
Skill 指令不构成宿主强制拦截 hook；自动执行策略须由集成方落实。
