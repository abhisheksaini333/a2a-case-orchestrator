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
                principal = authenticate(self.headers.get('Authorization'), tokens)
                length = int(self.headers.get('Content-Length', '0'))
                payload = json.loads(self.rfile.read(length))
                method, params, request_id = request(payload)
                result = service.rpc(method, params, principal)
                self.send(200, {'jsonrpc': '2.0', 'id': request_id, 'result': result})
            except DomainError as exc:
                self.send(401 if exc.code == 'unauthorized' else 403 if exc.code == 'forbidden' else 200, error_response(request_id, exc))
            except Exception as exc:
                self.send(500, error_response(request_id, exc))
    return ThreadingHTTPServer((host, port), Handler)
