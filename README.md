# Foundry — Supplier Case Orchestrator

A supplier onboarding desk that coordinates independent Python and C# agents, preserves their evidence, and requires a different operator to approve one exact supplier record.

The Python document agent checks structured tax evidence. The C# catalog agent classifies supplied goods and applies a small risk rule. A Python coordinator retains the case, requests missing information, verifies signed artifacts and presents the proposed record in React. PostgreSQL commits the approval and outbox command together; delivery creates a unique supplier record and survives process failure.

## Run the complete application

Requires Docker Compose. The default browser port is **18130** and PostgreSQL binds only to localhost on **18139**.

```sh
python3 scripts/init_env.py
docker compose up --build -d
```

Open **http://127.0.0.1:18130**. Use the locally generated `OPERATOR_TOKEN` from `.env` to open the desk. The key stays in memory in that tab; it is not written to browser storage.

1. Select **New supplier**. Enter a legal name, a tax identifier such as `DEMO-100`, and goods such as “industrial bearings.”
2. Start checks. The document agent requests the missing certificate identifier.
3. Enter the identifier transcribed from the certificate. The same document task resumes; the catalog agent returns its evidence.
4. Inspect the proposed record and the evidence trail.
5. Sign out. Open the desk using `REVIEWER_TOKEN` and approve that exact record.
6. Inspect the completed case. Repeating approval does not create another supplier.

Certificate checks compare the supplied structured identifier; they do not perform OCR or verify an external tax registry. The catalog risk rule is a sample business policy, not a compliance determination.

## What is implemented

- AgentCard discovery, skill checks, bounded A2A v0.2/v0.3 HTTP/JSON-RPC adapters, and Python task/artifact/status SSE responses.
- Independent Python coordinator, Python document service, and C#/.NET catalog service, each running in its own process or container.
- Durable task receipts, same-task missing-input resume, cancellation, task ownership, artifact integrity and independent human approval.
- PostgreSQL case state, revision fencing, exclusive case coordination, transactional outbox delivery, unique supplier identifiers and restart recovery.
- Plain HTTP and A2A comparison adapters using the same business logic, with observed request/body-byte counts.
- An optional local-model intake preview that extracts fields and proposes the two allowed skills. It cannot approve a case or write a supplier.
- A React casebook showing the exact proposed record, the producing agents, errors, retries and approval status.

The adapters intentionally cover a bounded protocol profile. They do not implement gRPC, push notifications, remote file fetching, full protocol certification, production identity federation or a live supplier registry. See [architecture and protocol boundaries](docs/architecture.md).

## Verification

Native development requires Python 3.11+, Node 22.12+ and .NET SDK 8.0.407. Start an isolated PostgreSQL database, then set `DATABASE_URL` to it. Tests create and remove only their own randomly named schemas.

```sh
python3 -m venv .venv
. .venv/bin/activate
pip install -e . -r requirements-test.txt
npm --prefix frontend ci --ignore-scripts
npm --prefix frontend run build
export DOTNET=dotnet
export RUN_INTERPROCESS=1
python -m unittest discover -v
```

For the real browser flow:

```sh
cd frontend
npx --no-install playwright install chromium
cd ..
PYTHONPATH=. python scripts/run_browser_check.py
```

`CHROME=/path/to/chrome` uses an already installed browser instead. The harness launches three separate services and verifies intake, missing-input resume, exact independent approval and mobile layout. The GitHub Actions workflow runs the same path on Linux; hosted execution is separate from local evidence.

[Acceptance and evidence](docs/acceptance.md) · [Architecture](docs/architecture.md) · [Operations and recovery](docs/runbook.md) · [API examples](docs/api.md) · [Measured evaluation](docs/evaluation.md)
