import unittest, threading, json, urllib.request, urllib.error
from supplier_case.transport import server
from supplier_case.protocol import agent_card, task


class Fake:
    name = "document"

    def card(self):
        return agent_card("document", "http://localhost", "document-check")

    def rpc(self, m, p, who):
        return task("task1", "context1", "completed")


class HTTP(unittest.TestCase):
    def setUp(self):
        self.s = server(Fake(), {"coordinator": "t" * 32})
        self.thread = threading.Thread(target=self.s.serve_forever, daemon=True)
        self.thread.start()
        self.url = "http://127.0.0.1:" + str(self.s.server_port)

    def tearDown(self):
        self.s.shutdown()
        self.s.server_close()
        self.thread.join()

    def post(self, payload, auth=True):
        headers = {"Content-Type": "application/json"}
        if auth:
            headers["Authorization"] = "Bearer " + "t" * 32
        req = urllib.request.Request(
            self.url + "/a2a", data=json.dumps(payload).encode(), headers=headers
        )
        return urllib.request.urlopen(req)

    def test_live_http_discovery_and_authenticated_request(self):
        with urllib.request.urlopen(self.url + "/.well-known/agent.json") as r:
            self.assertEqual(json.load(r)["name"], "document")
        payload = {"jsonrpc": "2.0", "id": 1, "method": "message/send", "params": {}}
        with self.post(payload) as r:
            self.assertEqual(json.load(r)["result"]["id"], "task1")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post(payload, False)
        self.assertEqual(ctx.exception.code, 401)

    def test_application_api_is_authenticated_and_routed(self):
        def api(method, path, payload, principal):
            return {"principal": principal, "method": method}

        Fake.api = staticmethod(api)
        req = urllib.request.Request(
            self.url + "/api/cases", headers={"Authorization": "Bearer " + "t" * 32}
        )
        with urllib.request.urlopen(req) as r:
            self.assertEqual(json.load(r)["principal"], "coordinator")

    def test_forged_host_matching_origin_and_duplicate_credentials_are_rejected(self):
        req = urllib.request.Request(
            self.url + "/health",
            headers={"Host": "evil.example", "Origin": "http://evil.example"},
        )
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(req)
        self.assertEqual(error.exception.code, 403)
        req = urllib.request.Request(
            self.url + "/health", headers={"Origin": "http://evil.example"}
        )
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(req)
        self.assertEqual(error.exception.code, 403)
        import socket

        client = socket.create_connection(self.s.server_address)
        client.settimeout(2)
        host = ("127.0.0.1:" + str(self.s.server_port)).encode()
        client.sendall(
            b"GET /health HTTP/1.1\r\nHost: "
            + host
            + b"\r\nAuthorization: Bearer one\r\nAuthorization: Bearer two\r\n\r\n"
        )
        self.assertIn(b"400", client.recv(1024))
        client.close()

    def test_non_ascii_bearer_is_an_http_unauthorized_response(self):
        request = urllib.request.Request(
            self.url + "/api/cases", headers={"Authorization": "Bearer café"}
        )
        with self.assertRaises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request)
        self.assertEqual(error.exception.code, 401)
