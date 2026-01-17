import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from supplier_case.client import Client
from supplier_case.domain import DomainError


class RedirectTests(unittest.TestCase):
    def test_redirect_never_reaches_destination_or_forwards_credential(self):
        received = []

        class Destination(BaseHTTPRequestHandler):
            def do_GET(self):
                received.append(self.headers.get("Authorization"))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{}')
            def log_message(self, *args):
                pass

        destination = ThreadingHTTPServer(("127.0.0.1", 0), Destination)

        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1:" + str(destination.server_port) + "/stolen")
                self.end_headers()
            def log_message(self, *args):
                pass

        source = ThreadingHTTPServer(("127.0.0.1", 0), Redirect)
        threads = [threading.Thread(target=s.serve_forever, daemon=True) for s in (source, destination)]
        for thread in threads:
            thread.start()
        try:
            client = Client("http://127.0.0.1:" + str(source.server_port), "t" * 32, "document", "check")
            with self.assertRaises(DomainError):
                client.fetch("/agent")
            self.assertEqual(received, [])
        finally:
            for service in (source, destination):
                service.shutdown()
                service.server_close()
            for thread in threads:
                thread.join()
