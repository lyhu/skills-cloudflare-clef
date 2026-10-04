[English](NOTICE.md) | **简体中文**

# 基准测试数据归属与开源许可声明

本仓库代码基于 **Apache-2.0** 协议开源。基准测试中引用的公开数据集遵循其各自原开源许可协议：

| 数据集文件 | 来源与作者 | 开源协议 | 适配与截取说明 |
| :--- | :--- | :--- | :--- |
| `datasets/boolq.json` | [BoolQ](https://github.com/google-research-datasets/boolean-questions) (Clark et al., 2019); [Google 镜像源](https://huggingface.co/datasets/google/boolq) | [CC-BY-SA-3.0](https://creativecommons.org/licenses/by-sa/3.0/) | 选取前 100 行验证集中两种标签各前 12 条样本（共 24 例）；完整保留原始篇章与问题并封装为 Noul 请求。适配后文件同样遵循 CC-BY-SA-3.0。 |
| `datasets/banking77.json` | [BANKING77](https://github.com/PolyAI-LDN/task-specific-datasets) (Casanueva et al., 2020, PolyAI) | [CC-BY-4.0](https://creativecommons.org/licenses/by-4.0/) | 选取 12 个代表性意图类别，每类取前 2 条测试样本（共 24 例）；保留原始语料与标签，附加意图描述后转换为 Choice 选项请求。 |

---

## 数据集元数据与构建机制

- 数据集元数据包含源行号、下载 URL 及 SHA-256 哈希校验码。可通过执行 `python3 benchmarks/import_classics.py` 重建。
- 上游字节变动须经过显式哈希审计：BoolQ API 镜像哈希用于锚定下载字节内容；BANKING77 CSV 链接则精确锚定至特定 Git Commit。

## 学术文献引用

- **BoolQ**：
  > Christopher Clark, Kenton Lee, Ming-Wei Chang, Tom Kwiatkowski, Michael Collins, Kristina Toutanova. *BoolQ: Exploring the Surprising Difficulty of Natural Yes/No Questions*. NAACL 2019.
- **BANKING77**：
  > Iñigo Casanueva, Tadas Temčinas, Daniela Gerz, Matthew Henderson, Ivan Vulić. *Efficient Intent Detection with Dual Sentence Encoders*. NLP for Conversational AI Workshop, 2020.

---

## 原创数据与隐私安全边界

- `cases.json` 包含本项目原创编写的 Smoke 冒烟测试用例，基于 Apache-2.0 协议分发。
- 浏览器测试轨迹仅记录公开推文 URL、文本 SHA-256 哈希及模型判定标签；推文完整正文与账号界面数据均严格存放于本地忽略目录（`.local/`），不随本仓库分发。
