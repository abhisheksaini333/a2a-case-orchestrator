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
