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

    def rpc(self, method, params):
        request_id = uuid.uuid4().hex
        response = self.fetch('/a2a', {'jsonrpc': '2.0', 'id': request_id, 'method': method, 'params': params})
        if response.get('jsonrpc') != '2.0' or response.get('id') != request_id:
            raise DomainError('invalid_agent_response', 'Agent response did not match the request')
        if 'error' in response:
            raise DomainError('agent_error', str(response['error'].get('message', 'Agent rejected the request')))
        result = response.get('result')
        if not isinstance(result, dict) or result.get('kind') != 'task':
            raise DomainError('invalid_agent_response', 'Agent did not return a task')
        return result

    def send(self, data, context, message_id, task_id=None):
        message = {'kind': 'message', 'role': 'user', 'messageId': message_id, 'contextId': context,
                   'parts': [{'kind': 'data', 'data': data}]}
        if task_id:
            message['taskId'] = task_id
        result = self.rpc('message/send', {'message': message})
        if result.get('contextId') != context or (task_id and result.get('id') != task_id):
            raise DomainError('context_mismatch', 'Agent changed the task or context binding')
        return result
