**English** | [简体中文](NOTICE_zh.md)

# Benchmark Data Attribution & Open-Source Licensing

Source code in this repository is licensed under **Apache-2.0**. Public benchmark datasets referenced within adhere to their respective original licenses:

| Dataset File | Source & Authors | License | Adaptation & Sampling Details |
| :--- | :--- | :--- | :--- |
| `datasets/boolq.json` | [BoolQ](https://github.com/google-research-datasets/boolean-questions) (Clark et al., 2019); [Google Mirror](https://huggingface.co/datasets/google/boolq) | [CC-BY-SA-3.0](https://creativecommons.org/licenses/by-sa/3.0/) | First 12 examples of each label from the first 100 validation rows (24 cases total); original passages and questions preserved verbatim and packaged as Noul requests. Adapted file remains under CC-BY-SA-3.0. |
| `datasets/banking77.json` | [BANKING77](https://github.com/PolyAI-LDN/task-specific-datasets) (Casanueva et al., 2020, PolyAI) | [CC-BY-4.0](https://creativecommons.org/licenses/by-4.0/) | 12 representative intent classes, first 2 test cases per class (24 cases total); original queries and labels preserved, mapped to Choice requests with intent descriptions. |

---

## Dataset Metadata & Generation Mechanics

- Dataset metadata includes source row numbers, download URLs, and SHA-256 integrity checksums. Rebuild via `python3 benchmarks/import_classics.py`.
- Upstream changes undergo explicit hash auditing: BoolQ API mirror hash locks payload bytes; BANKING77 CSV URL pins to a specific Git commit hash.

## Academic Citations

- **BoolQ**:
  > Christopher Clark, Kenton Lee, Ming-Wei Chang, Tom Kwiatkowski, Michael Collins, Kristina Toutanova. *BoolQ: Exploring the Surprising Difficulty of Natural Yes/No Questions*. NAACL 2019.
- **BANKING77**:
  > Iñigo Casanueva, Tadas Temčinas, Daniela Gerz, Matthew Henderson, Ivan Vulić. *Efficient Intent Detection with Dual Sentence Encoders*. NLP for Conversational AI Workshop, 2020.

---

## Original Data & Privacy Guardrails

- `cases.json` contains original smoke test cases authored for this project and distributed under the Apache-2.0 license.
- Browser test traces only record public tweet URLs, text SHA-256 digests, and model verdicts; full tweet contents and authenticated UI states reside strictly in local untracked directories (`.local/`) and are never distributed.
