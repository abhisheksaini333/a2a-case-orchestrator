import json
import socket
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from supplier_case.domain import DomainError
from supplier_case.model import extract


class Deadline(unittest.TestCase):
    def test_stalled_and_trickling_models_release_the_call_before_http_deadline(self):
        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                self.rfile.read(int(self.headers["Content-Length"]))
                if self.path == "/stalled":
                    time.sleep(0.6)
                    return
                self.send_response(200)
                self.send_header("Content-Length", "1000")
                self.end_headers()
                try:
                    for _ in range(20):
                        self.wfile.write(b" ")
                        self.wfile.flush()
                        time.sleep(0.05)
                except OSError:
                    pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for route in ["stalled", "trickling"]:
                started = time.monotonic()
                with self.assertRaises(DomainError) as error:
                    extract(
                        "Acme AB1",
                        f"http://127.0.0.1:{server.server_port}/{route}",
                        timeout=0.2,
                    )
                self.assertEqual(error.exception.code, "model_unavailable")
                self.assertLess(time.monotonic() - started, 0.5)
                self.assertNotIn("127.0.0.1", str(error.exception))
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_operator_cannot_configure_an_unbounded_model_deadline(self):
        for timeout in [0, -1, 11, "nan", "bad"]:
            with self.assertRaises(DomainError) as error:
                extract("Acme AB1", "http://localhost", timeout=timeout)
            self.assertEqual(error.exception.code, "invalid_model_timeout")
