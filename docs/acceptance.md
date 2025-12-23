# Acceptance evidence

The final local verification passed **99 Python unit/integration tests with no skips** using Python 3.11.11, PostgreSQL 16.4 and .NET SDK 8.0.407. C# built with zero warnings. The rebuilt four-container application passed the actual Chromium operator flow. These are local results; a GitHub-hosted workflow run is a separate verification after publication.

| Required capability | Implemented behavior and reproducible evidence |
|---|---|
| Three independent services across languages | Python coordinator and document service plus a separately launched C# process: [`test_processes.py`](../tests/test_processes.py), [`test_catalog_http.py`](../tests/test_catalog_http.py). Docker Compose also runs each independently. |
| Agent discovery, skills and versioned contracts | Pinned official v0.2/v0.3 schemas; actual C# v0.3 card/task validation and Python negotiation tests: [`test_protocol_profiles.py`](../tests/test_protocol_profiles.py), [`test_client_negotiation.py`](../tests/test_client_negotiation.py). |
| Task, artifact and SSE lifecycle | Python task snapshot, signed artifact updates and final status event: [`test_http_stream.py`](../tests/test_http_stream.py), [`test_sse_frame.py`](../tests/test_sse_frame.py). Catalog truthfully advertises no streaming. |
| Missing input and original-task resume | Certificate request followed by same document task ID: [`test_coordinator_resume.py`](../tests/test_coordinator_resume.py), actual browser flow. |
| Ownership and cancellation | Credential role checks, task ownership, terminal-state guards and revision fencing: [`test_task_ownership.py`](../tests/test_task_ownership.py), [`test_coordinator_cancel.py`](../tests/test_coordinator_cancel.py). |
| Exact independent human approval | Creator cannot approve; changed/stale digest fails; a reviewer authorizes the exact record: [`test_approval_guard.py`](../tests/test_approval_guard.py), [`test_processes.py`](../tests/test_processes.py). |
| Durable supplier and transactional outbox | One approved supplier per case and tax identity, with atomic acknowledgement: [`test_delivery.py`](../tests/test_delivery.py), [`test_supplier_conflict.py`](../tests/test_supplier_conflict.py). |
| Crash and duplicate delivery | Actual SIGKILL after insert/before commit, six competing workers, process restart, duplicate approval and persisted C# receipts: [`test_worker_crash.py`](../tests/test_worker_crash.py), [`test_catalog_http.py`](../tests/test_catalog_http.py). |
| Altered or unauthorized evidence rejected | Tampered signed data and an actual wrong-key catalog process fail without a supplier: [`test_artifact_signature.py`](../tests/test_artifact_signature.py), [`test_processes.py`](../tests/test_processes.py). |
| User/operator interface and attribution | Intake, missing evidence, producing agents, proposed record, independent approval, in-memory credentials and 390-pixel layout: [`frontend/smoke.mjs`](../frontend/smoke.mjs). Actual optional-model preview also exercised. |
| Plain HTTP comparison | Same 24 total cases, two genuine adapters, latency/body-byte/request counts and restart proof: [`protocol-benchmark.json`](../evaluation/results/protocol-benchmark.json). |
| Actual local-model mode | Two immutable model revisions, default and non-thinking profiles, strict proposal validation and separately measured rules: [evaluation](evaluation.md). |
| Bounded and authenticated transport | Real sockets exercise partial headers/bodies, admission limits, duplicate credentials, forged authorities/origins and non-ASCII tokens: [`test_http_capacity.py`](../tests/test_http_capacity.py), [`test_http_auth.py`](../tests/test_http_auth.py), [`test_catalog_http.py`](../tests/test_catalog_http.py). |
| Bounded generation and safe errors | Actual stalled/trickling model responses release the call; failures expose no exception details: [`test_model_deadline.py`](../tests/test_model_deadline.py), [`test_http_auth.py`](../tests/test_http_auth.py). |
| Portable packaging and operation | Version-pinned Docker builds, separate state volumes, generated local credentials, pinned GitHub Actions and [backup/recovery procedures](runbook.md). |

## Boundaries

The result is an independently runnable supplier-workflow application and interoperability demonstration. It is not a complete A2A implementation or certification, a production IAM system, a tax-registry integration, an OCR pipeline or a multi-writer catalog cluster. HMAC establishes shared-secret service trust, not public-key non-repudiation. Structured certificate checks and the small catalog risk vocabulary are explicit sample policies. Model quality is a six-input local sample, not a general capability claim. Hosted CI, public TLS operation and real supplier onboarding remain unverified.
