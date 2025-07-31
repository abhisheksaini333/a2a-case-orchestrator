"""Bounded A2A HTTP/JSON-RPC adapter, with explicit supported operations."""
import json
import uuid
from .domain import DomainError

class RPCError(DomainError):
    def __init__(self, number, message):
        super().__init__('rpc_error', message)
        self.number = number

def request(value):
    if not isinstance(value, dict) or value.get('jsonrpc') != '2.0' or not isinstance(value.get('method'), str):
        raise RPCError(-32600, 'Invalid JSON-RPC request')
    if not isinstance(value.get('params', {}), dict) or isinstance(value.get('id'), (dict, list, bool)):
        raise RPCError(-32602, 'Invalid JSON-RPC parameters')
    return value['method'], value.get('params', {}), value.get('id')

def message_data(params):
    m = params.get('message')
    if not isinstance(m, dict) or m.get('kind') != 'message' or m.get('role') != 'user' or not isinstance(m.get('messageId'), str) or not 1 <= len(m['messageId']) <= 100:
        raise RPCError(-32602, 'A user message with messageId is required')
    parts = m.get('parts', [])
    if not isinstance(parts, list) or len(parts) != 1 or not isinstance(parts[0], dict) or parts[0].get('kind') != 'data' or not isinstance(parts[0].get('data'), dict):
        raise RPCError(-32005, 'This skill accepts one application/json data part')
    return m, parts[0]['data']

def agent_card(name, url, skill, version='0.2.0'):
    card = {'name': name, 'description': f'Supplier onboarding {name} service', 'url': url,
            'version': '1.0.0', 'capabilities': {'streaming': True, 'pushNotifications': False},
            'defaultInputModes': ['application/json'], 'defaultOutputModes': ['application/json'],
            'skills': [{'id': skill, 'name': skill.replace('-', ' '), 'description': f'Perform {skill} for one supplier case', 'tags': ['supplier', name]}],
            'securitySchemes': {'bearer': {'type': 'http', 'scheme': 'bearer'}}, 'security': [{'bearer': []}]}
    return card

def task(task_id, context_id, state, data=None, artifacts=None):
    result = {'kind': 'task', 'id': task_id, 'contextId': context_id, 'status': {'state': state}, 'artifacts': artifacts or []}
    if data is not None:
        result['status']['message'] = {'kind': 'message', 'messageId': uuid.uuid4().hex, 'role': 'agent',
                                       'taskId': task_id, 'contextId': context_id, 'parts': [{'kind': 'data', 'data': data}]}
    return result
