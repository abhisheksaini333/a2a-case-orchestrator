# API examples

All operator endpoints require `Authorization: Bearer <operator-or-reviewer-key>` and JSON request bodies. Service credentials cannot use this API. Examples assume locally generated environment variables and the default coordinator port.

```sh
curl -H "Authorization: Bearer $OPERATOR_TOKEN" http://127.0.0.1:18130/api/cases
```

Create a case with a stable request key. Retrying exactly the same request/key returns the same case; changing its content returns an idempotency conflict.

```sh
curl -H "Authorization: Bearer $OPERATOR_TOKEN" -H 'Content-Type: application/json' \
  --data '{"request_key":"supplier-demo-100","supplier":{"name":"Northstar Components","tax_id":"DEMO-100","description":"industrial bearings"}}' \
  http://127.0.0.1:18130/api/cases
```

Resume the returned case ID with the requested structured certificate:

```sh
curl -H "Authorization: Bearer $OPERATOR_TOKEN" -H 'Content-Type: application/json' \
  --data '{"documents":[{"type":"tax_certificate","tax_id":"DEMO-100"}]}' \
  http://127.0.0.1:18130/api/cases/CASE_ID/resume
```

Read `/api/cases/CASE_ID` to inspect the exact proposal and agent-attributed events. A different identity approves the returned `proposal_digest`:

```sh
curl -H "Authorization: Bearer $REVIEWER_TOKEN" -H 'Content-Type: application/json' \
  --data '{"digest":"EXACT_PROPOSAL_DIGEST"}' \
  http://127.0.0.1:18130/api/cases/CASE_ID/approve
```

| Method | Route | Meaning |
|---|---|---|
| GET | `/api/session` | Current principal, without credentials |
| GET | `/api/cases` | Latest 200 cases and pending effect count |
| GET | `/api/cases/ID` | Case and ordered evidence events |
| GET | `/api/suppliers` | Latest 200 durable supplier records |
| GET | `/api/metrics` | Agent request/body-byte counters and pending effects |
| POST | `/api/cases` | Create/retry an idempotent case |
| POST | `/api/cases/ID/resume` | Provide the requested documents |
| POST | `/api/cases/ID/run` | Retry eligible checks; `{}` body |
| POST | `/api/cases/ID/cancel` | Cancel an eligible case; `{}` body |
| POST | `/api/cases/ID/approve` | Independently approve the exact digest |
| POST | `/api/extract` | Preview `{text, mode}` where mode is `rules` or `local-model` |

## Agent transport

Each agent exposes `/a2a` and discovery cards. A document request uses the case ID as its context; the bearer identity is the coordinator:

```json
{
  "jsonrpc": "2.0",
  "id": "request-1",
  "method": "message/send",
  "params": {
    "message": {
      "kind": "message",
      "messageId": "case-100-document-1",
      "role": "user",
      "contextId": "case-100",
      "parts": [{"kind": "data", "data": {"name": "Northstar", "tax_id": "DEMO-100", "documents": []}}]
    }
  }
}
```

The returned task ID is retained for resume. A resumed message includes that `taskId`, the same `contextId`, a new deterministic `messageId`, and the requested document data. `message/stream` on Python services returns `text/event-stream` containing JSON-RPC task, artifact and final status events. The C# card explicitly advertises no streaming.

For a new coordinator task, omit `contextId`: the application allocates it and returns it with the task. `case-client` may send, read and cancel its own task, but human approval remains exclusively on the operator API.

The comparison endpoint `/direct` accepts a simpler payload such as `{"messageId":"m-100","contextId":"case-100","data":{"description":"industrial bearings"}}`. It returns the application's durable task receipt directly. It is not a JSON-RPC alias.
