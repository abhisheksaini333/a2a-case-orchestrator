"""Local credential and artifact trust boundaries."""
import hashlib
import hmac
import secrets
from .domain import DomainError, canonical

def authenticate(header, tokens):
    if not isinstance(header, str) or not header.startswith('Bearer '):
        raise DomainError('unauthorized', 'A bearer credential is required')
    candidate = header[7:]
    for principal, token in tokens.items():
        if len(token) >= 32 and hmac.compare_digest(candidate, token):
            return principal
    raise DomainError('unauthorized', 'Credential was not accepted')
