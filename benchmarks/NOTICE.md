# Benchmark data attribution

Repository code is Apache-2.0. The following dataset files retain their own licenses.

| File | Source and authors | License | Adaptation |
| --- | --- | --- | --- |
| `datasets/boolq.json` | [BoolQ](https://github.com/google-research-datasets/boolean-questions), Clark et al., 2019; [Google dataset mirror](https://huggingface.co/datasets/google/boolq) | [CC-BY-SA-3.0](https://creativecommons.org/licenses/by-sa/3.0/) | 24 validation examples, first 12 per label among the first 100 rows; full passages and questions preserved, wrapped as Noul requests. This adapted file is also CC-BY-SA-3.0. |
| `datasets/banking77.json` | [BANKING77](https://github.com/PolyAI-LDN/task-specific-datasets), Casanueva et al., 2020, PolyAI | [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) | First 2 test examples in each of 12 chosen intents; original utterances/labels, added intent descriptions, converted to Choice. |

Dataset metadata includes source rows, download URLs and SHA-256 hashes. Rebuild with
`python3 benchmarks/import_classics.py`; changed upstream bytes require explicit hash review.
The BoolQ rows API is a live mirror: its hash pins downloaded bytes, not a guaranteed immutable API URL.
The BANKING77 CSV URL pins a Git commit.

BoolQ citation: Christopher Clark, Kenton Lee, Ming-Wei Chang, Tom Kwiatkowski,
Michael Collins, Kristina Toutanova. *BoolQ: Exploring the Surprising Difficulty of
Natural Yes/No Questions*. NAACL 2019.

BANKING77 citation: Iñigo Casanueva, Tadas Temčinas, Daniela Gerz, Matthew Henderson,
Ivan Vulić. *Efficient Intent Detection with Dual Sentence Encoders*. NLP for
Conversational AI Workshop, 2020.

`cases.json` contains original hand-authored smoke cases, licensed Apache-2.0.
Browser traces contain public post URLs, text hashes and judgments. Full post text and
account UI remain in ignored `.local/` files and are not distributed.
