"""Validation and transitions independent of network and storage."""

import hashlib
import json
import re


class DomainError(ValueError):
    def __init__(self, code, message):
        self.code = code
        super().__init__(message)


def supplier_identity(data):
    if not isinstance(data, dict):
        raise DomainError("invalid_input", "Supplier must be an object")
    if not isinstance(data.get("name"), str) or not isinstance(data.get("tax_id"), str):
        raise DomainError(
            "invalid_identity", "Legal name and tax identifier must be text"
        )
    name = data["name"].strip()
    tax_id = data["tax_id"].strip().upper()
    if not 2 <= len(name) <= 120 or not re.fullmatch(r"[A-Z0-9-]{3,40}", tax_id):
        raise DomainError(
            "invalid_identity", "Provide a legal name and a valid tax identifier"
        )
    return {"name": name, "tax_id": tax_id}


def document_check(data):
    identity = supplier_identity(data)
    docs = data.get("documents", [])
    if not isinstance(docs, list) or len(docs) > 12:
        raise DomainError("invalid_documents", "At most twelve documents are accepted")
    matches = [
        x for x in docs if isinstance(x, dict) and x.get("type") == "tax_certificate"
    ]
    if not matches:
        return {"status": "input-required", "missing": ["tax_certificate"], **identity}
    if (
        len(matches) != 1
        or not isinstance(matches[0].get("tax_id"), str)
        or matches[0]["tax_id"].strip().upper() != identity["tax_id"]
    ):
        raise DomainError(
            "document_mismatch", "Certificate must match the supplier tax identifier"
        )
    return {"status": "verified", "missing": [], **identity}


TRANSITIONS = {
    "submitted": {"working", "canceled"},
    "working": {"input-required", "completed", "failed", "canceled"},
    "input-required": {"working", "canceled"},
    "completed": set(),
    "failed": set(),
    "canceled": set(),
}


def transition(old, new):
    if new not in TRANSITIONS.get(old, set()):
        raise DomainError("invalid_transition", f"Cannot move task from {old} to {new}")
    return new


def canonical(value):
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        encoded.encode("utf-8")
        return encoded
    except (ValueError, TypeError) as exc:
        raise DomainError(
            "invalid_json",
            "Only finite JSON values and valid Unicode text are accepted",
        ) from exc


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def proposal(document, catalog):
    if document.get("status") != "verified" or catalog.get("risk") != "low":
        raise DomainError(
            "not_approvable",
            "Verified documents and a low-risk catalog match are required",
        )
    category = catalog.get("category")
    if category not in {"office", "technology", "industrial"}:
        raise DomainError(
            "invalid_category", "Catalog returned an unsupported category"
        )
    return {**supplier_identity(document), "category": category, "risk": "low"}


def authorize_approval(record, supplied_digest, reviewer, creator):
    if not reviewer or reviewer == creator:
        raise DomainError(
            "independent_approval_required", "Another operator must approve this case"
        )
    if supplied_digest != digest(record):
        raise DomainError(
            "stale_approval",
            "The record changed; review the exact current record again",
        )
    return reviewer


def case_input(data):
    identity = supplier_identity(data)
    if set(data) - {"name", "tax_id", "description", "documents"}:
        raise DomainError(
            "unknown_fields",
            "Only supplier identity, description and documents may be supplied",
        )
    description = data.get("description", "")
    if not isinstance(description, str) or len(description) > 4000:
        raise DomainError(
            "invalid_description", "Description must contain at most 4000 characters"
        )
    docs = data.get("documents", [])
    if not isinstance(docs, list) or len(docs) > 12:
        raise DomainError("invalid_documents", "At most twelve documents are accepted")
    return {**identity, "description": description.strip(), "documents": docs}
