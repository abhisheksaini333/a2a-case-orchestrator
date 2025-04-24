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
        raise DomainError('invalid_input', 'Supplier must be an object')
    name = str(data.get('name', '')).strip()
    tax_id = str(data.get('tax_id', '')).strip().upper()
    if not 2 <= len(name) <= 120 or not re.fullmatch(r'[A-Z0-9-]{3,40}', tax_id):
        raise DomainError('invalid_identity', 'Provide a legal name and a valid tax identifier')
    return {'name': name, 'tax_id': tax_id}

def document_check(data):
    identity = supplier_identity(data)
    docs = data.get('documents', [])
    if not isinstance(docs, list) or len(docs) > 12:
        raise DomainError('invalid_documents', 'At most twelve documents are accepted')
    matches = [x for x in docs if isinstance(x, dict) and x.get('type') == 'tax_certificate']
    if not matches:
        return {'status': 'input-required', 'missing': ['tax_certificate'], **identity}
    if len(matches) != 1 or str(matches[0].get('tax_id', '')).upper() != identity['tax_id']:
        raise DomainError('document_mismatch', 'Certificate must match the supplier tax identifier')
    return {'status': 'verified', 'missing': [], **identity}
