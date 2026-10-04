# Validation · 2026-10-04

| Check | Result |
| --- | --- |
| Client, templates, failure handling and benchmark statistics | 30 unittest cases passed |
| Frontmatter, Pi skill path, package versions, JSON Schema, Python syntax and CI YAML | Passed |
| Native TypeScript template import | Passed on Node 24 |
| Browser benchmark JavaScript syntax | Passed |
| `npx skills add . --list` | Discovered `cloudflare-clef` |
| npm distribution | 9 expected files; skill resources included, scratch files excluded |
| Browser comparison input audit | Identical 8 URLs, text hashes and driver hash in all four included trials |
| Post-fix real inference | 198/198 measured + 9/9 warmup valid answers; no HTTP/protocol errors |
| Deployment handoff | Updated after verification; prior document and server source backed up |

Local test environment: Python 3.12, Node 24, macOS. CI also targets Python 3.9 and
3.14; those matrix jobs have not been run locally. dsh/Pi integration follows documented
shared skill discovery and Pi package metadata; complete harness sessions were not tested.
Pi is not installed on this machine.

Benchmark accuracy and latency appear in the [combined report](../../REPORT.md).
Successful client tests do not establish model accuracy; incorrect model judgments remain in raw results.
