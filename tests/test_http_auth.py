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
