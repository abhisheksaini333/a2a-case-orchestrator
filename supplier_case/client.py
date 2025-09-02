"""Pinned-endpoint A2A client. Cards never choose arbitrary network destinations."""
import json
import urllib.request
import urllib.error
import uuid
from .domain import DomainError

class Client:
    def __init__(self, url, token, name, skill):
        self.url, self.token, self.name, self.skill = url.rstrip('/'), token, name, skill
    def fetch(self, path, data=None):
        request = urllib.request.Request(self.url + path, data=None if data is None else json.dumps(data).encode(),
                headers={'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                raw = response.read(1048577)
                if len(raw) > 1048576:
                    raise DomainError('response_limit', 'Agent response exceeded its size limit')
                return json.loads(raw)
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise DomainError('agent_unavailable', f'{self.name} service could not be reached or returned invalid JSON') from exc

    def discover(self):
        card = self.fetch('/.well-known/agent.json')
        if card.get('name') != self.name or self.skill not in {s.get('id') for s in card.get('skills', [])}:
            raise DomainError('skill_mismatch', 'Discovered agent does not offer the configured skill')
        if 'application/json' not in card.get('defaultInputModes', []):
            raise DomainError('mode_mismatch', 'Agent cannot accept structured supplier records')
        return card
