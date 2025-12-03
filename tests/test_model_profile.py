import unittest, json, threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from supplier_case.model import extract


class Profile(unittest.TestCase):
    def test_non_thinking_profile_is_explicit_in_generation_request(self):
        observed = []

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                observed.append(
                    json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                )
                output = {
                    "supplier": {"name": "Acme", "tax_id": "AB1"},
                    "skills": ["document-check", "catalog-match"],
                }
                body = json.dumps(
                    {"choices": [{"message": {"content": json.dumps(output)}}]}
                ).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = HTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            result = extract(
                "Acme AB1", "http://127.0.0.1:" + str(server.server_port), no_think=True
            )
            self.assertEqual(result["supplier"]["name"], "Acme")
            self.assertIn("/no_think", observed[0]["messages"][0]["content"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
