# Operation and recovery

## Health and bounded resources

```sh
docker compose ps
docker compose logs --tail=50 coordinator document catalog
curl http://127.0.0.1:18130/health
```

The coordinator starts after both agent health checks pass. Its startup recovery delivers pending approved commands and resumes up to 50 submitted/working cases. Failed business cases remain visible for operator review instead of looping indefinitely. An operator can use **Retry checks** after correcting an unavailable service; terminal, approved and completed cases are protected from that action.

For an interrupted approved command, run the recovery command against the existing state:

```sh
docker compose run --rm coordinator recover coordinator
```

The command is idempotent. A process killed after the supplier insert but before transaction commit leaves no partial record. A later delivery inserts the record once. A competing worker uses `FOR UPDATE SKIP LOCKED`, while unique constraints retain one record per case and tax identifier.

A duplicate tax identifier creates a `conflict` case and a `supplier-conflict` event. It does not overwrite the existing supplier or block unrelated outbox commands. Inspect the existing business identity and start a corrected case if appropriate; there is no “force approval” bypass.

| Symptom | Check and action |
|---|---|
| `input-required` | Provide the certificate tax identifier; the document agent resumes the original task. |
| `invalid_artifact` | Check that the coordinator verification key and agent signing key belong to the same deployment. Restore keys from the matching backup; do not disable verification. |
| `stale_approval` | Reload the case and review its current exact record. |
| `independent_approval_required` | Use another operator identity; the creator cannot approve their own case. |
| `case_busy` | Another worker holds the case lease. Retry after it completes or its database transaction closes. |
| `catalog_capacity_limit` | Existing receipts remain usable. Stop admission and archive the deployment state; increase `MAX_TASKS` only within an explicit memory/storage budget. |
| `model_not_configured` / invalid model output | Continue using reviewed manual fields or labeled-field extraction. No case is created by a failed preview. |
| HTTP 503 / 408 | Request capacity or an absolute deadline was reached. Use bounded retries; inspect service health and slow clients. |

## Back up matching state and keys

Stop writes before taking a matching application/database/journal snapshot. The following creates backups without deleting live data:

```sh
mkdir -p artifacts/backup
chmod 700 artifacts/backup
docker compose stop coordinator document catalog
docker compose exec -T postgres pg_dump -U postgres cases > artifacts/backup/cases.sql
docker compose cp catalog:/state/tasks.json artifacts/backup/catalog-tasks.json
cp .env artifacts/backup/deployment.env
chmod 600 artifacts/backup/*
docker compose up -d
```

A journal does not exist until the catalog has handled its first task; record that empty-state condition rather than inventing a file. Preserve the exact image digests and source revision with the backup. Do not put credentials or database dumps in Git.

Restore into a fresh isolated Compose project and empty database/volume, preserving the original deployment. Import the SQL before starting either Python service, restore the catalog journal with ownership UID 1654, and load the matching keys. Start the catalog/document services, then the coordinator. Verify an existing receipt, the pending outbox count and one new independently approved case before switching traffic. Replaying an old request with new signing keys is intentionally rejected.

`docker compose down` retains named volumes. Do not use `down --volumes` for an environment whose history must be retained. PostgreSQL is the durable application store; catalog state must remain on its named volume, never a container's temporary layer.

## Native development

Use a dedicated PostgreSQL database. Generate credentials with `scripts/init_env.py`; the command refuses to overwrite an existing `.env`. Load these generated shell-safe values only from your own local file:

```sh
set -a
. ./.env
set +a
export DATABASE_URL="postgresql://postgres:${POSTGRES_PASSWORD}@127.0.0.1:18139/cases"
```

Run each service in a separate terminal with those environment variables:

```sh
python -m supplier_case serve document --port 18131
```

```sh
dotnet build catalog
AGENT_TOKEN="$COORDINATOR_TOKEN" ARTIFACT_KEY="$CATALOG_KEY" dotnet catalog/bin/Debug/net8.0/Catalog.dll serve
```

```sh
python -m supplier_case serve coordinator --port 18130
```

`DOCUMENT_PUBLIC_URL`, `COORDINATOR_PUBLIC_URL` and the C# `PUBLIC_URL` control discovery addresses independently of bind addresses. Set externally reachable HTTPS URLs behind a TLS ingress for a non-local deployment. The coordinator still contacts only its configured `DOCUMENT_URL` and `CATALOG_URL`.

## Local model preview

Run a local OpenAI-compatible endpoint separately and set `MODEL_ENDPOINT` to its `/v1/chat/completions` URL. `MODEL_NAME` defaults to `default_model`. Qwen2.5 uses the default profile; Qwen3 should use `MODEL_NO_THINK=1` for the measured bounded extraction profile. A container needs a reachable host address; `127.0.0.1` inside a container means that container itself.

`MODEL_TIMEOUT_SECONDS` defaults to 10 and must be between 0.05 and 10 seconds. The client closes a stalled or trickling model connection at its deadline; failed previews leave the case list unchanged.

The model is optional. It drafts fields and the mandatory `document-check`/`catalog-match` skill pair. The operator reviews these fields before starting a case. It has no tool that can approve or create a supplier directly. Exact measured model revisions and limitations are recorded in [evaluation](evaluation.md).
