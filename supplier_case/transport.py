"""Small bounded local HTTP transport for independent service processes."""

import json
import threading
import socket
from urllib.parse import urlsplit
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from .domain import DomainError
from .security import authenticate
from .protocol import request, error_response, stream_frames


class BoundedServer(ThreadingHTTPServer):
    daemon_threads = True
    request_queue_size = 32

    def __init__(self, address, handler, max_connections):
        self.slots = threading.BoundedSemaphore(max_connections)
        super().__init__(address, handler)

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            try:
                request.sendall(
                    b"HTTP/1.1 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
                )
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


def server(
    service,
    tokens,
    host="127.0.0.1",
    port=0,
    ui_dir=None,
    max_connections=16,
    request_deadline=15,
):
    class Handler(BaseHTTPRequestHandler):
        def setup(self):
            super().setup()
            self.connection.settimeout(request_deadline)
            self.deadline = threading.Timer(request_deadline, self.expire)
            self.deadline.daemon = True
            self.deadline.start()

        def handle(self):
            try:
                super().handle()
            except OSError:
                pass  # A peer disconnect or absolute request deadline closes the socket.

        def expire(self):
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

        def finish(self):
            self.deadline.cancel()
            try:
                super().finish()
            except OSError:
                pass

        def log_message(self, format, *args):
            pass

        def send(self, status, value, kind="application/json"):
            body = (
                json.dumps(value, default=str) if kind == "application/json" else value
            ).encode()
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Cache-Control", "no-store")
            self.send_header(
                "Content-Security-Policy",
                (
                    "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
                    if kind != "application/json"
                    else "default-src 'none'; frame-ancestors 'none'"
                ),
            )
            self.end_headers()
            try:
                self.wfile.write(body)
            except OSError:
                pass

        def guard(self):
            if (
                len(self.headers.get_all("Host", [])) != 1
                or len(self.headers.get_all("Authorization", [])) > 1
                or len(self.headers.get_all("Origin", [])) > 1
            ):
                self.send(400, {"error": "ambiguous_headers"})
                return False
            if (
                self.headers.get("Host", "").strip().lower()
                not in self.server.allowed_hosts
            ):
                self.send(403, {"error": "untrusted_host"})
                return False
            origin = self.headers.get("Origin")
            if origin is not None and origin not in self.server.allowed_origins:
                self.send(403, {"error": "untrusted_origin"})
                return False
            return True

        def do_GET(self):
            if not self.guard():
                return
            assets = {
                "/": ("index.html", "text/html"),
                "/assets/main.js": ("main.js", "text/javascript"),
                "/assets/main.css": ("main.css", "text/css"),
            }
            if ui_dir and self.path in assets:
                filename, kind = assets[self.path]
                path = Path(ui_dir) / filename
                if path.is_file():
                    return self.send(200, path.read_text(), kind)
            if self.path == "/health":
                return self.send(200, {"status": "ok", "service": service.name})
            if self.path in {"/.well-known/agent.json", "/.well-known/agent-card.json"}:
                return self.send(200, service.card())
            if self.path.startswith("/api/") and hasattr(service, "api"):
                try:
                    principal = authenticate(self.headers.get("Authorization"), tokens)
                    return self.send(200, service.api("GET", self.path, {}, principal))
                except DomainError as exc:
                    return self.send(
                        (
                            401
                            if exc.code == "unauthorized"
                            else 403 if exc.code == "forbidden" else 404
                        ),
                        {"error": exc.code, "message": str(exc)},
                    )
                except Exception:
                    return self.send(500, {"error": "internal_service_error"})
            self.send(404, {"error": "not_found"})

        def do_POST(self):
            if not self.guard():
                return
            request_id = None
            try:
                if len(self.headers.get_all("Content-Length", [])) > 1:
                    return self.send(400, {"error": "ambiguous_length"})
                if self.path not in {"/a2a", "/direct"} and not self.path.startswith(
                    "/api/"
                ):
                    return self.send(404, {"error": "not_found"})
                if self.headers.get("Transfer-Encoding"):
                    return self.send(400, {"error": "unsupported_transfer_encoding"})
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    return self.send(400, {"error": "invalid_length"})
                if not 0 < length <= 65536:
                    return self.send(413, {"error": "body_limit"})
                if (
                    self.headers.get("Content-Type", "").split(";")[0]
                    != "application/json"
                ):
                    return self.send(415, {"error": "json_required"})
                principal = authenticate(self.headers.get("Authorization"), tokens)
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length)
                if len(raw) != length:
                    return self.send(400, {"error": "incomplete_body"})
                payload = json.loads(raw)
                if self.path.startswith("/api/") and hasattr(service, "api"):
                    if not isinstance(payload, dict):
                        return self.send(400, {"error": "object_required"})
                    return self.send(
                        200, service.api("POST", self.path, payload, principal)
                    )
                if self.path == "/direct":
                    if not isinstance(payload, dict) or set(payload) - {
                        "data",
                        "contextId",
                        "messageId",
                        "taskId",
                    }:
                        raise DomainError(
                            "invalid_direct_request",
                            "Expected a plain data and context request",
                        )
                    message = {
                        "kind": "message",
                        "role": "user",
                        "messageId": payload.get("messageId"),
                        "contextId": payload.get("contextId"),
                        "parts": [{"kind": "data", "data": payload.get("data")}],
                    }
                    if payload.get("taskId"):
                        message["taskId"] = payload["taskId"]
                    return self.send(
                        200,
                        service.rpc("message/send", {"message": message}, principal),
                    )
                method, params, request_id = request(payload)
                result = service.rpc(method, params, principal)
                if method == "message/stream":
                    return self.send(
                        200,
                        "".join(stream_frames(request_id, result)),
                        "text/event-stream",
                    )
                self.send(200, {"jsonrpc": "2.0", "id": request_id, "result": result})
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                self.send(400, {"error": "invalid_json"})
            except DomainError as exc:
                if self.path.startswith("/api/"):
                    return self.send(
                        (
                            401
                            if exc.code == "unauthorized"
                            else 403 if exc.code == "forbidden" else 409
                        ),
                        {"error": exc.code, "message": str(exc)},
                    )
                self.send(
                    (
                        401
                        if exc.code == "unauthorized"
                        else 403 if exc.code == "forbidden" else 200
                    ),
                    error_response(request_id, exc),
                )
            except OSError:
                return
            except Exception as exc:
                self.send(500, error_response(request_id, exc))

    http = BoundedServer((host, port), Handler, max_connections)
    http.allowed_hosts = {
        f"127.0.0.1:{http.server_port}",
        f"localhost:{http.server_port}",
    }
    http.allowed_origins = {"http://" + authority for authority in http.allowed_hosts}
    card = service.card() if hasattr(service, "card") else {}
    public = urlsplit(card.get("url", ""))
    if public.scheme in {"http", "https"} and public.netloc:
        http.allowed_hosts.add(public.netloc.lower())
        http.allowed_origins.add(public.scheme + "://" + public.netloc)
    return http
