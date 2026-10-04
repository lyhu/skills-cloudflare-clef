# 客户端契约、故障降级与基准测试套件验证报告

- **验证日期**：2026-10-04
- **本地环境**：Python 3.12.14 / Node 24.18.0 / macOS ARM64
- **数据性质**：本报告记录基于 Mock 服务、故障异常注入及静态分析的防御性测试结果。真实服务 54 次计量表现详见 [report.md](report.md) 与 [results.json](results.json)。

---

## 1. 单元测试与边界校验

```text
python3 -m unittest discover -s tests -v
Ran 29 tests in 1.528s
OK
```

测试套件涵盖 21 项客户端/模板用例与 8 项基准测试用例，全部通过（0 失败、0 跳过）：

| 校验模块 | 测试注入与验证点 | 观测结果与契约对齐 |
| :--- | :--- | :--- |
| **原生协议** | Noul、Choice 标签与描述、Score、JSON 状态、Unicode、Bearer Token、模型别名 | 正确调用 `/v1/systemone` 端点；准确解析 `verdict`；保留原语语义 |
| **瞬态网络重试** | 注入 HTTP 429/500/502/503/504 瞬态错误并随后恢复 | 执行有限指数退避重试后获取成功结果；退避时序符合配置 |
| **重试耗尽** | 持续 429、网络拒绝连接及连接超时 | 达到最大重试后严格返回错误 JSON，绝不伪造决策 |
| **不可重试错误** | HTTP 400/401/403/404/413/422 状态码 | 立即终止并返回失败，不发起无效重试 |
| **Socket 超时** | 强制本地服务端响应时延超出设定超时 | 返回 `CLEF_SERVICE_UNAVAILABLE`，高危路径严格阻断 |
| **凭据安全** | 针对携带凭据的请求注入 HTTP 307 重定向响应 | 严格禁止自动跟随重定向，防止向不可信端点泄漏凭据 |
| **响应格式异常** | 损毁的 JSON、非 UTF-8 字符、字段嵌套损毁、外层信封缺失 | 返回 `CLEF_INVALID_RESPONSE`，不重试 |
| **非法判定拦截** | 概率越界、NaN/Infinity、未知选项、分布不合规、置信度冲突 | 严密校验并拒绝非法判定，杜绝错误放行风险 |
| **数值舍入容差** | Choice 64 候选项、Score 16 等级 | 兼容四位小数浮点运算在边界范围内的微小舍入误差 |
| **参数与输入校验** | 候选项缺失、标签重复、等级超限、超时/重试非法、URL 畸变 | 发起请求前执行前置防御性拦截，不浪费网络开销 |
| **CLI 规范** | 成功、评估异常与参数错误三类场景；禁用 site-packages | 准确返回退出码 0/1/2；严格实现标准库零第三方依赖 |
| **Python 集成模板** | 隔离环境中复制模板并调用 Mock 服务 | 正常执行并返回强类型判定 |
| **TypeScript 模板** | 传入特殊 Shell 字符、正常响应与异常降级 | 基于安全的 `execFile` 进程调用，复用参数校验与降级逻辑 |
| **基准用例契约** | 18 个测试用例 ID 唯一性、Schema 契约与预期标签格式 | 三种原语用例完备，测试集符合协议定义 |
| **基准统计方法** | Nearest-Rank 分位数、Brier 分数、Multiclass Brier、MAE | 算法公式与边界计算完全符合统计方法论 |
| **异常计入口径** | 部分失败、全部失败、预热过滤、敏感信息脱敏 | 错误率如实计入分母；敏感凭据严格禁止写入报告 |

---

## 2. 静态打包与规范完整性校验

- `python3 scripts/validate.py`：Frontmatter 格式、包版本一致性、Schema 规则与关键交付文件核验通过。
- `skill-creator` 工具链：执行 `quick_validate.py` 判定合规（`Skill is valid!`）。
- `npx skills add . --list`：正确识别通用决策技能 `cloudflare-clef`。
- `npm pack --dry-run`：打包清单仅包含交付代码、Schema、模板与许可证，彻底排除缓存与本地日志。
- TypeScript 类型检查：Node 24 原生导入测试通过，且通过 TypeScript 4.7.4 的 `tsc --noEmit --strict` 严格类型检查。

---

## 3. 复现验证指令

```bash
# 依赖准备与自动化测试
python3 -m pip install -r requirements-dev.txt
python3 scripts/validate.py
python3 -m unittest discover -s tests -v

# 跨语言模板与打包校验
node --input-type=module -e "await import('./skills/cloudflare-clef/templates/client.ts')"
npm pack --dry-run
npx skills add . --list
```

