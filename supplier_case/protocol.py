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
