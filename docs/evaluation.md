# Measured behavior and reproduction

These measurements use synthetic supplier inputs, local PostgreSQL, two Python processes and a separate .NET catalog process. They establish local functionality. They do not establish production throughput, universal model accuracy, or full A2A conformance.

## A2A and plain HTTP

The [recorded protocol run](../evaluation/results/protocol-benchmark.json) completes the same technology, industrial and office cases four times per mode. Industrial cases start without a certificate and resume the original document task. Both modes require independent exact-record approval and the same durable supplier write. The plain adapter sends JSON data directly; it omits discovery and the JSON-RPC envelope while retaining application task receipts.

| Observation | A2A | Plain HTTP |
|---|---:|---:|
| Completed cases | 12 / 12 | 12 / 12 |
| Median complete-case latency | 350.49 ms | 450.42 ms |
| Slowest case | 927.64 ms | 1,484.02 ms |
| Agent HTTP requests | 60 | 28 |
| Request body bytes | 13,100 | 8,200 |
| Response body bytes | 39,764 | 19,008 |
| Pending effects after cases | 0 | 0 |
| Coordinator kill/restart and duplicate approval | Passed | Passed |

The current client deliberately does not cache discovery, making its request overhead visible. Byte counters exclude HTTP headers, browser traffic and database traffic. Timings include application checks and approval, but exclude build and process startup. This sequential 12-case sample ran on a shared development host; scheduling and database load can dominate the transport difference. The request/byte counts demonstrate overhead. The timings do **not** support a general performance ranking. An earlier run was faster in direct mode.

Use a dedicated test database and the prerequisites from the README:

```sh
PYTHONPATH=. python scripts/benchmark_protocol.py --repetitions 4 --output artifacts/protocol-benchmark.json
```

Create `artifacts/` first. `DOTNET`, `DATABASE_URL` and `RUN_INTERPROCESS=1` must be set. The script launches the actual services, uses isolated database schemas and stops its own processes afterward.

## Actual local generation and deterministic extraction

The [six frozen inputs](../evaluation/intake.json) include labeled fields, prose, absent identity and an instruction to bypass the required skills. Four inputs have a valid expected supplier identity; two must be rejected. Correctness requires the exact expected name/tax identifier and the permitted skill route, or a semantic validation rejection for an invalid input. Malformed output and transport failures are **not** counted as correct, even when they safely prevent a write.

| Mode / generation profile | Correct | Accepted valid inputs | Median extraction latency |
|---|---:|---:|---:|
| Labeled-field rules | 5 / 6 | 3 / 4 | 0.02 ms |
| Qwen2.5-1.5B, default | 6 / 6 | 4 / 4 | 5,875.66 ms |
| Qwen3-0.6B, default | 0 / 6 | 0 / 4 | 5,557.66 ms |
| Qwen2.5-1.5B, explicit `/no_think` | 5 / 6 | 4 / 4 | 3,109.00 ms |
| Qwen3-0.6B, explicit `/no_think` | 6 / 6 | 4 / 4 | 1,138.91 ms |

The failed Qwen3 default profile exhausted the bounded generation/output contract. Explicit non-thinking generation made its extraction usable on this small sample. One invalid Qwen2.5 non-thinking response was safely rejected but is still scored incorrect. All results, including failures, remain in [default-profile results](../evaluation/results/model-evaluation.json) and [non-thinking results](../evaluation/results/model-evaluation-no-think.json). The host was under load during this refresh; these latencies are observations, not service objectives.

The rule baseline parses labeled fields. It performs no model inference. Both actual models receive the same extraction prompt with temperature zero and at most 256 output tokens. A schema/identity/route validator rejects unsafe or malformed replies. The model proposes only `document-check` and `catalog-match`; it cannot approve a case or insert a supplier. The browser presents a preview for operator review before any case is created.

### Reproduce the optional model environment

Models are separate optional services. The tested MLX profiles require Apple silicon; the core application and tests also run in Linux containers. Use separate Python 3.11 environments for the two model runtimes:

```sh
python3.11 -m venv .runtime/qwen25
.runtime/qwen25/bin/pip install -r evaluation/runtime/qwen25/requirements.lock
.runtime/qwen25/bin/huggingface-cli download mlx-community/Qwen2.5-1.5B-Instruct-4bit --revision 8b403126fc14f14cfc99bb4cfa72ecbc129ea677 --local-dir .runtime/models/qwen25
.runtime/qwen25/bin/python -m mlx_lm.server --model .runtime/models/qwen25 --host 127.0.0.1 --port 18100
```

In another terminal, use `evaluation/runtime/qwen3/requirements.lock`, repository `mlx-community/Qwen3-0.6B-4bit`, revision `73e3e38d981303bc594367cd910ea6eb48349da8`, a separate model directory and port **18101**. Inspect the upstream model license before distributing weights. Model files are not included in this repository. [The immutable model manifest](../evaluation/models.json) records every measured file URL, size and SHA-256; the runtime folders record selected wheel filenames, hashes and publication evidence.

```sh
mkdir -p artifacts
PYTHONPATH=. python scripts/evaluate_intake.py --endpoint http://127.0.0.1:18100/v1/chat/completions --endpoint http://127.0.0.1:18101/v1/chat/completions --output artifacts/default-profile.json
PYTHONPATH=. python scripts/evaluate_intake.py --endpoint http://127.0.0.1:18100/v1/chat/completions --endpoint http://127.0.0.1:18101/v1/chat/completions --no-think --output artifacts/non-thinking-profile.json
```

Generation has a maximum ten-second socket deadline, including stalled headers and trickling bodies. Configure only a trusted local model endpoint; this is a small synchronous preview, not a remote inference job queue. Six fixtures are insufficient for broad quality, fairness or adversarial-resilience claims. Further evaluation should add unseen suppliers, languages, malformed certificates and ambiguous tax identities before any operational adoption.
