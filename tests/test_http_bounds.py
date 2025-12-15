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

    def test_oversized_and_malformed_bodies_are_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.post({"x": "x" * 70000})
        self.assertEqual(ctx.exception.code, 413)
        request = urllib.request.Request(
            self.url + "/a2a",
            data=b"{",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + "t" * 32,
            },
        )
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(request)
        self.assertEqual(ctx.exception.code, 400)

    def test_eof_before_declared_body_length_never_dispatches_valid_json(self):
        import socket

        client = socket.create_connection(self.s.server_address)
        client.settimeout(2)
        host = ("127.0.0.1:" + str(self.s.server_port)).encode()
        body = b'{"jsonrpc":"2.0","id":1,"method":"message/send","params":{}}'
        client.sendall(
            b"POST /a2a HTTP/1.1\r\nHost: "
            + host
            + b"\r\nContent-Type: application/json\r\nAuthorization: Bearer "
            + b"t" * 32
            + b"\r\nContent-Length: 200\r\n\r\n"
            + body
        )
        client.shutdown(socket.SHUT_WR)
        self.assertIn(b"400", client.recv(1024))
        client.close()
