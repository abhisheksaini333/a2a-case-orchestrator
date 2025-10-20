"""Optional local-model intake. Model text cannot authorize a supplier write."""
import json
import re
import time
import urllib.request
import urllib.error
from .domain import DomainError, case_input

def parse_output(text):
    if not isinstance(text, str) or len(text) > 16000:
        raise DomainError('invalid_model_output', 'Model response exceeded the text limit')
    text = re.sub(r'^\s*<think>\s*</think>', '', text).strip()
    if text.startswith('```'):
        match = re.fullmatch(r'```(?:json)?\s*(.*?)\s*```', text, re.S)
        if not match:
            raise DomainError('invalid_model_output', 'Model response contains an incomplete code fence')
        text = match.group(1)
    try:
        data = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise DomainError('invalid_model_output', 'Model did not return one JSON object') from exc
    if not isinstance(data, dict) or set(data) != {'supplier', 'skills'}:
        raise DomainError('invalid_model_output', 'Model output must include supplier and skills only')
    if data['skills'] != ['document-check', 'catalog-match']:
        raise DomainError('unsafe_route', 'Supplier onboarding always requires both approved skills')
    return {'supplier': case_input(data['supplier']), 'skills': data['skills']}
