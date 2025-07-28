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
