import unittest, os, json, subprocess, tempfile, time, urllib.request, urllib.error, socket
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(os.getenv("DOTNET"), "requires .NET SDK")
class CatalogHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        result = subprocess.run(
            [
                os.environ["DOTNET"],
                "build",
                "catalog",
                "-o",
                "catalog/bin/test",
                "--nologo",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.token = "c" * 32
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.env = {
            **os.environ,
            "PORT": str(self.port),
            "CATALOG_STATE": self.tmp.name,
            "AGENT_TOKEN": self.token,
            "ARTIFACT_KEY": "k" * 32,
        }
        self.url = "http://127.0.0.1:" + str(self.port)
        self.start()

    def start(self):
        self.process = subprocess.Popen(
            [os.environ["DOTNET"], str(ROOT / "catalog/bin/test/Catalog.dll"), "serve"],
            env=self.env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(60):
            try:
                urllib.request.urlopen(self.url + "/health", timeout=0.3).close()
                return
            except (OSError, urllib.error.URLError):
                time.sleep(0.05)
        self.fail("Catalog did not start")

    def tearDown(self):
        self.process.terminate()
        self.process.wait(timeout=5)
        self.tmp.cleanup()

    def rpc(self, method, params, auth=True):
        req = urllib.request.Request(
            self.url + "/a2a",
            data=json.dumps(
                {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
            ).encode(),
            headers={
                "Content-Type": "application/json",
                **({"Authorization": "Bearer " + self.token} if auth else {}),
            },
        )
        with urllib.request.urlopen(req) as r:
            return json.load(r)

    def message(self):
        return {
            "message": {
                "kind": "message",
                "messageId": "message-1",
                "role": "user",
                "contextId": "case-1",
                "parts": [{"kind": "data", "data": {"description": "laptop repair"}}],
            }
        }

    def test_live_card_and_python_to_csharp_message(self):
        with urllib.request.urlopen(self.url + "/.well-known/agent.json") as r:
            self.assertEqual(json.load(r)["skills"][0]["id"], "catalog-match")
        result = self.rpc("message/send", self.message())["result"]
        self.assertEqual(result["status"]["state"], "completed")
        self.assertEqual(result["contextId"], "case-1")
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            self.rpc("message/send", self.message(), False)
        self.assertEqual(ctx.exception.code, 401)

    def test_catalog_artifact_verifies_in_python_and_tamper_fails(self):
        from supplier_case.security import verify_artifact
        from supplier_case.domain import DomainError

        result = self.rpc("message/send", self.message())["result"]
        artifact = result["artifacts"][0]
        value = verify_artifact(
            artifact, "catalog", result["id"], "case-1", {"catalog": "k" * 32}
        )
        self.assertEqual(value, {"category": "technology", "risk": "low"})
        artifact["parts"][0]["data"]["risk"] = "blocked"
        with self.assertRaises(DomainError):
            verify_artifact(
                artifact, "catalog", result["id"], "case-1", {"catalog": "k" * 32}
            )

    def test_restart_returns_same_task_for_duplicate_delivery(self):
        original = self.rpc("message/send", self.message())["result"]
        self.process.kill()
        self.process.wait(timeout=5)
        self.start()
        resumed = self.rpc("message/send", self.message())["result"]
        self.assertEqual(resumed, original)
        self.assertEqual(
            self.rpc("tasks/get", {"id": original["id"]})["result"], original
        )

    def test_message_reuse_with_changed_content_is_rejected(self):
        self.rpc("message/send", self.message())
        changed = self.message()
        changed["message"]["parts"][0]["data"]["description"] = "industrial steel"
        response = self.rpc("message/send", changed)
        self.assertIn("error", response)

    def test_v03_discovery_and_task_conform_to_the_same_pinned_schema(self):
        from jsonschema import Draft7Validator

        schema = json.loads((ROOT / "contracts/v0.3.0.json").read_text())
        with urllib.request.urlopen(self.url + "/.well-known/agent-card.json") as r:
            card = json.load(r)
        self.assertEqual(card["protocolVersion"], "0.3.0")
        Draft7Validator({**schema, "$ref": "#/definitions/AgentCard"}).validate(card)
        Draft7Validator({**schema, "$ref": "#/definitions/Task"}).validate(
            self.rpc("message/send", self.message())["result"]
        )

    def test_incomplete_bodies_have_a_deadline_and_chunked_requests_are_rejected(self):
        self.process.terminate()
        self.process.wait(timeout=5)
        self.env.update(REQUEST_DEADLINE_MS="300", MAX_REQUESTS="2")
        self.start()
        client = socket.create_connection(("127.0.0.1", self.port))
        client.settimeout(3)
        client.sendall(
            (
                "POST /a2a HTTP/1.1\r\nHost: 127.0.0.1:"
                + str(self.port)
                + "\r\nContent-Type: application/json\r\nAuthorization: Bearer "
            ).encode()
            + b"c" * 32
            + b"\r\nContent-Length: 100\r\n\r\n{"
        )
        started = time.monotonic()
        data = client.recv(1024)
        self.assertLess(time.monotonic() - started, 2)
        self.assertIn(b"408", data)
        client.close()
        client = socket.create_connection(("127.0.0.1", self.port))
        client.settimeout(3)
        client.sendall(
            (
                "POST /a2a HTTP/1.1\r\nHost: 127.0.0.1:"
                + str(self.port)
                + "\r\nTransfer-Encoding: chunked\r\nContent-Type: application/json\r\nAuthorization: Bearer "
            ).encode()
            + b"c" * 32
            + b"\r\n\r\n0\r\n\r\n"
        )
        self.assertIn(b"400", client.recv(1024))
        client.close()

    def test_catalog_admission_is_bounded_and_partial_headers_expire(self):
        self.process.terminate()
        self.process.wait(timeout=5)
        self.env.update(REQUEST_DEADLINE_MS="1000", MAX_REQUESTS="2")
        self.start()
        clients = []
        try:
            for _ in range(2):
                client = socket.create_connection(("127.0.0.1", self.port))
                client.settimeout(3)
                client.sendall(
                    (
                        "POST /a2a HTTP/1.1\r\nHost: 127.0.0.1:"
                        + str(self.port)
                        + "\r\nContent-Type: application/json\r\nAuthorization: Bearer "
                    ).encode()
                    + b"c" * 32
                    + b"\r\nContent-Length: 100\r\n\r\n{"
                )
                clients.append(client)
            time.sleep(0.1)
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(self.url + "/health")
            self.assertEqual(error.exception.code, 503)
        finally:
            for client in clients:
                client.close()
        time.sleep(0.2)
        client = socket.create_connection(("127.0.0.1", self.port))
        client.settimeout(5)
        client.sendall(b"GET /health HTTP/1.1\r\nHost: localhost\r\nX-Incomplete: ")
        self.assertIn(b"408", client.recv(1024))
        client.close()

    def test_catalog_state_limit_keeps_old_receipts_available(self):
        self.process.terminate()
        self.process.wait(timeout=5)
        self.env.update(MAX_TASKS="1", PUBLIC_URL="http://catalog.example.test:18132")
        self.start()
        original = self.rpc("message/send", self.message())["result"]
        other = self.message()
        other["message"]["messageId"] = "message-2"
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.rpc("message/send", other)
        self.assertEqual(error.exception.code, 503)
        self.assertEqual(self.rpc("message/send", self.message())["result"], original)
        with urllib.request.urlopen(
            self.url + "/.well-known/agent-card.json"
        ) as response:
            self.assertEqual(
                json.load(response)["url"], "http://catalog.example.test:18132/a2a"
            )

    def test_direct_http_reuses_catalog_business_logic_and_receipt(self):
        from supplier_case.client import DirectClient

        original = self.rpc("message/send", self.message())["result"]
        direct = DirectClient(self.url, self.token, "catalog", "catalog-match")
        result = direct.send({"description": "laptop repair"}, "case-1", "message-1")
        self.assertEqual(result, original)
        self.assertEqual(direct.measurements["requests"], 1)

    def test_standard_method_task_and_cancellation_error_codes(self):
        self.assertEqual(self.rpc("unknown/method", {})["error"]["code"], -32601)
        self.assertEqual(
            self.rpc("tasks/get", {"id": "absent"})["error"]["code"], -32001
        )
        task = self.rpc("message/send", self.message())["result"]
        self.assertEqual(
            self.rpc("tasks/cancel", {"id": task["id"]})["error"]["code"], -32002
        )

    def test_catalog_health_command_observes_the_running_service(self):
        result = subprocess.run(
            [
                os.environ["DOTNET"],
                str(ROOT / "catalog/bin/test/Catalog.dll"),
                "health",
            ],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_catalog_rejects_untrusted_hosts_origins_and_duplicate_auth(self):
        for headers in [
            {"Host": "evil.example", "Origin": "http://evil.example"},
            {"Origin": "http://evil.example"},
        ]:
            request = urllib.request.Request(self.url + "/health", headers=headers)
            with self.assertRaises(urllib.error.HTTPError) as error:
                urllib.request.urlopen(request)
            self.assertEqual(error.exception.code, 403)
        with socket.create_connection(("127.0.0.1", self.port)) as client:
            client.settimeout(3)
            client.sendall(
                (
                    "GET /health HTTP/1.1\r\nHost: 127.0.0.1:"
                    + str(self.port)
                    + "\r\nAuthorization: Bearer one\r\nAuthorization: Bearer two\r\n\r\n"
                ).encode()
            )
            self.assertIn(b"400", client.recv(1024))

    def test_catalog_accepts_configured_public_authority(self):
        self.process.terminate()
        self.process.wait(timeout=5)
        self.env["PUBLIC_URL"] = "http://catalog.example.test:18132"
        self.start()
        request = urllib.request.Request(
            self.url + "/health",
            headers={
                "Host": "catalog.example.test:18132",
                "Origin": "http://catalog.example.test:18132",
            },
        )
        with urllib.request.urlopen(request) as response:
            self.assertEqual(response.status, 200)
