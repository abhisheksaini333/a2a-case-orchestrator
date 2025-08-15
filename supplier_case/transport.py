"""Small bounded local HTTP transport for independent service processes."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .domain import DomainError
from .security import authenticate
from .protocol import request, error_response, stream_frames

def server(service, tokens, host='127.0.0.1', port=0):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            pass
        def send(self, status, value, kind='application/json'):
            body = (json.dumps(value, default=str) if kind == 'application/json' else value).encode()
            self.send_response(status)
            self.send_header('Content-Type', kind)
            self.send_header('Content-Length', str(len(body)))
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('X-Frame-Options', 'DENY')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Security-Policy', "default-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)
        def do_GET(self):
            if self.path == '/health':
                return self.send(200, {'status': 'ok', 'service': service.name})
            if self.path == '/.well-known/agent.json':
                return self.send(200, service.card())
            self.send(404, {'error': 'not_found'})
        def do_POST(self):
            request_id = None
            try:
                self.connection.settimeout(10)
                if self.path not in {'/a2a', '/direct'} and not self.path.startswith('/api/'):
                    return self.send(404, {'error': 'not_found'})
                if self.headers.get('Transfer-Encoding'):
                    return self.send(400, {'error': 'unsupported_transfer_encoding'})
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                except ValueError:
                    return self.send(400, {'error': 'invalid_length'})
                if not 0 < length <= 65536:
                    return self.send(413, {'error': 'body_limit'})
                if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                    return self.send(415, {'error': 'json_required'})
                principal = authenticate(self.headers.get('Authorization'), tokens)
                length = int(self.headers.get('Content-Length', '0'))
                payload = json.loads(self.rfile.read(length))
                method, params, request_id = request(payload)
                result = service.rpc(method, params, principal)
                self.send(200, {'jsonrpc': '2.0', 'id': request_id, 'result': result})
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                self.send(400, {'error': 'invalid_json'})
            except DomainError as exc:
                self.send(401 if exc.code == 'unauthorized' else 403 if exc.code == 'forbidden' else 200, error_response(request_id, exc))
            except Exception as exc:
                self.send(500, error_response(request_id, exc))
    return ThreadingHTTPServer((host, port), Handler)
