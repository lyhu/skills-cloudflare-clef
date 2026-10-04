# Clef service incident · 2026-10-04

Status: **resolved after an authorized one-line server patch and restart**.
Before repair, inference was unavailable despite `/healthz` returning `ok`.

- Three short single-question calls succeeded before the browser pilot.
- The first eight-question X triage batch returned HTTP 500: `CUDA out of memory`.
- A shorter batch retry also failed. All 72 subsequent BoolQ requests failed, plus
  the three excluded warmups. A minimal one-question health-of-inference probe also failed.
- Read-only GPU inspection: Clef PID 1949691, physical GPU 7, approximately 81,130 MiB
  used by this process; GPU had 13 MiB free. No second compute process on GPU 7 was listed.
- Error response reported ~78.68 GiB allocated by PyTorch, ~51 MiB reserved but unused.
  Therefore this is not supported by evidence as a simple excess cache reservation problem.
- Server `_run_systemone` called `ClefModel.forward` directly, without disabling autograd.
  The upstream `systemone` helper is decorated with inference mode, but this HTTP path bypassed it.
  Model `.eval()` does not disable gradient recording; see [PyTorch autograd documentation](https://docs.pytorch.org/docs/2.14/notes/autograd.html).

## Recovery and verification

- User explicitly authorized applying the prepared patch and restarting only the verified Clef process.
- Added `@torch.inference_mode()` to `_run_systemone`, the thread-pool worker.
- Backed up `server.py` before mutation; preserved original command, environment and physical GPU 7.
- Old PID 1949691 exited gracefully; new PID 952811 started at server time 2026-10-04 15:47:09.
- Restored real inference, including the same eight-question browser batch.
- Post-fix suites: 198/198 valid measured responses, zero HTTP/protocol errors; 9/9 warmups valid.
- Final GPU observation: NVIDIA A800-SXM4-80GB, 53,657 MiB used, 27,495 MiB free.
- No other GPU process was stopped or changed.

Failed-request latency is **not** successful decision latency. Failure and repaired results
remain separate. The repair eliminated observed failures; this is not an exhaustive load test.

[BoolQ raw failures](boolq-before-fix/results.json) · [browser failure](browser/clef-1-failed.json)
