"""Local credential and artifact trust boundaries."""

import hashlib
import hmac
import secrets
from .domain import DomainError, canonical


def authenticate(header, tokens):
    if not isinstance(header, str) or not header.startswith("Bearer "):
        raise DomainError("unauthorized", "A bearer credential is required")
    candidate = header[7:]
    if not candidate.isascii():
        raise DomainError("unauthorized", "Credential was not accepted")
    for principal, token in tokens.items():
        if (
            len(token) >= 32
            and token.isascii()
            and hmac.compare_digest(candidate.encode(), token.encode())
        ):
            return principal
    raise DomainError("unauthorized", "Credential was not accepted")


def sign_artifact(owner, task_id, context_id, data, key):
    if len(key) < 32:
        raise DomainError("weak_key", "Artifact keys require at least 32 characters")
    signed = {"owner": owner, "taskId": task_id, "contextId": context_id, "data": data}
    signature = hmac.new(
        key.encode(), canonical(signed).encode(), hashlib.sha256
    ).hexdigest()
    return {
        "artifactId": secrets.token_hex(16),
        "name": owner + " evidence",
        "parts": [{"kind": "data", "data": data}],
        "metadata": {
            "owner": owner,
            "taskId": task_id,
            "contextId": context_id,
            "signature": signature,
        },
    }


def verify_artifact(artifact, owner, task_id, context_id, keys):
    try:
        meta = artifact["metadata"]
        parts = artifact["parts"]
        if (
            len(parts) != 1
            or parts[0]["kind"] != "data"
            or (meta["owner"], meta["taskId"], meta["contextId"])
            != (owner, task_id, context_id)
        ):
            raise ValueError("binding")
        signed = {
            "owner": owner,
            "taskId": task_id,
            "contextId": context_id,
            "data": parts[0]["data"],
        }
        expected = hmac.new(
            keys[owner].encode(), canonical(signed).encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(meta["signature"], expected):
            raise ValueError("signature")
        return parts[0]["data"]
    except (KeyError, TypeError, IndexError, ValueError) as exc:
        raise DomainError(
            "invalid_artifact", "Agent evidence failed ownership or integrity checks"
        ) from exc


def require_role(principal, allowed):
    if principal not in allowed:
        raise DomainError("forbidden", "This principal cannot perform that operation")


def owns(task, principal):
    if task.get("owner") != principal:
        raise DomainError("forbidden", "Task belongs to another principal")
