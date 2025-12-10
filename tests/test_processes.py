"""Real independent Python coordinator, Python document agent and C# catalog."""

import json, os, socket, subprocess, sys, tempfile, time, unittest, urllib.request, urllib.error, uuid
from pathlib import Path
from tests.database import DatabaseCase

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(
    os.getenv("DOTNET") and os.getenv("DATABASE_URL") and os.getenv("RUN_INTERPROCESS"),
    "requires .NET and isolated PostgreSQL",
)
class Processes(DatabaseCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        subprocess.run(
            [
                os.environ["DOTNET"],
                "build",
                "catalog",
                "-o",
                "catalog/bin/test",
                "--nologo",
            ],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
        )

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.children = []
        self.addCleanup(self.tearDown)
        self.ports = []
        for _ in range(3):
            with socket.socket() as s:
                s.bind(("127.0.0.1", 0))
                self.ports.append(s.getsockname()[1])
        self.env = {
            **os.environ,
            "COORDINATOR_TOKEN": "t" * 32,
            "OPERATOR_TOKEN": "o" * 32,
            "REVIEWER_TOKEN": "r" * 32,
            "DOCUMENT_KEY": "d" * 32,
            "CATALOG_KEY": "k" * 32,
            "AGENT_TOKEN": "t" * 32,
            "ARTIFACT_KEY": "k" * 32,
            "CATALOG_STATE": self.tmp.name,
            "PORT": str(self.ports[2]),
            "DOCUMENT_URL": f"http://127.0.0.1:{self.ports[1]}",
            "CATALOG_URL": f"http://127.0.0.1:{self.ports[2]}",
        }
        self.start(
            [os.environ["DOTNET"], str(ROOT / "catalog/bin/test/Catalog.dll"), "serve"],
            self.ports[2],
        )
        self.start(
            [
                sys.executable,
                "-m",
                "supplier_case",
                "serve",
                "document",
                "--port",
                str(self.ports[1]),
            ],
            self.ports[1],
        )
        self.start(
            [
                sys.executable,
                "-m",
                "supplier_case",
                "serve",
                "coordinator",
                "--port",
                str(self.ports[0]),
            ],
            self.ports[0],
        )
        self.base = f"http://127.0.0.1:{self.ports[0]}"

    def start(self, command, port):
        log = open(Path(self.tmp.name) / f"{port}.log", "a")
        child = subprocess.Popen(
            command, cwd=ROOT, env=self.env, stdout=log, stderr=log
        )
        log.close()
        self.children.append(child)
        for _ in range(100):
            try:
                urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health", timeout=0.2
                ).close()
                return child
            except OSError:
                time.sleep(0.05)
        self.fail("Process failed: " + Path(self.tmp.name, f"{port}.log").read_text())

    def tearDown(self):
        for p in self.children:
            if p.poll() is None:
                p.terminate()
        for p in self.children:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
                p.wait()
        self.tmp.cleanup()

    def call(self, path, data=None, role="operator"):
        token = {"operator": "o" * 32, "reviewer": "r" * 32}[role]
        req = urllib.request.Request(
            self.base + path,
            data=None if data is None else json.dumps(data).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + token,
            },
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.load(r)

    def test_three_process_onboarding_requires_exact_independent_approval(self):
        tax = "T-" + uuid.uuid4().hex[:8]
        case = self.call(
            "/api/cases",
            {
                "request_key": uuid.uuid4().hex,
                "supplier": {
                    "name": "Acme Tools",
                    "tax_id": tax,
                    "description": "Industrial bearings",
                },
            },
        )
        self.assertEqual(case["state"], "input-required")
        events = self.call("/api/cases/" + case["id"])["events"]
        task_id = [
            e["detail"]["task_id"] for e in events if e["kind"] == "document-task"
        ][-1]
        ready = self.call(
            "/api/cases/" + case["id"] + "/resume",
            {"documents": [{"type": "tax_certificate", "tax_id": tax}]},
        )
        self.assertEqual(ready["state"], "review")
        self.assertEqual(ready["proposal"]["category"], "industrial")
        events = self.call("/api/cases/" + case["id"])["events"]
        self.assertEqual(
            [e["detail"]["task_id"] for e in events if e["kind"] == "document-task"][
                -1
            ],
            task_id,
        )
        self.assertEqual(
            {e["actor"] for e in events if e["kind"] == "artifact"},
            {"document", "catalog"},
        )
        for role, h in [
            ("operator", ready["proposal_digest"]),
            ("reviewer", "altered"),
        ]:
            with self.assertRaises(urllib.error.HTTPError):
                self.call("/api/cases/" + case["id"] + "/approve", {"digest": h}, role)
        self.call(
            "/api/cases/" + case["id"] + "/approve",
            {"digest": ready["proposal_digest"]},
            "reviewer",
        )
        self.children[-1].kill()
        self.children[-1].wait()
        self.start(
            [
                sys.executable,
                "-m",
                "supplier_case",
                "serve",
                "coordinator",
                "--port",
                str(self.ports[0]),
            ],
            self.ports[0],
        )
        self.call(
            "/api/cases/" + case["id"] + "/approve",
            {"digest": ready["proposal_digest"]},
            "reviewer",
        )
        records = [
            x
            for x in self.call("/api/suppliers")["suppliers"]
            if x["case_id"] == case["id"]
        ]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["record"], ready["proposal"])

    def test_wrong_agent_signing_key_cannot_create_an_approvable_case(self):
        self.children[0].terminate()
        self.children[0].wait(timeout=5)
        self.env["ARTIFACT_KEY"] = "z" * 32
        self.start(
            [os.environ["DOTNET"], str(ROOT / "catalog/bin/test/Catalog.dll"), "serve"],
            self.ports[2],
        )
        tax = "UNTRUSTED-" + uuid.uuid4().hex[:8].upper()
        with self.assertRaises(urllib.error.HTTPError) as error:
            self.call(
                "/api/cases",
                {
                    "request_key": uuid.uuid4().hex,
                    "supplier": {
                        "name": "Untrusted Evidence",
                        "tax_id": tax,
                        "description": "paper",
                        "documents": [{"type": "tax_certificate", "tax_id": tax}],
                    },
                },
            )
        self.assertEqual(json.load(error.exception)["error"], "invalid_artifact")
        case = next(
            c for c in self.call("/api/cases")["cases"] if c["input"]["tax_id"] == tax
        )
        self.assertEqual(case["state"], "failed")
        self.assertIsNone(case["proposal"])
        self.assertFalse(
            any(
                row["tax_id"] == tax for row in self.call("/api/suppliers")["suppliers"]
            )
        )

    def test_document_public_url_is_independent_of_its_bind_address(self):
        self.children[1].terminate()
        self.children[1].wait(timeout=5)
        self.env["DOCUMENT_PUBLIC_URL"] = "https://agents.example.test/document/a2a"
        self.start(
            [
                sys.executable,
                "-m",
                "supplier_case",
                "serve",
                "document",
                "--port",
                str(self.ports[1]),
            ],
            self.ports[1],
        )
        with urllib.request.urlopen(
            f"http://127.0.0.1:{self.ports[1]}/.well-known/agent-card.json"
        ) as response:
            self.assertEqual(
                json.load(response)["url"], self.env["DOCUMENT_PUBLIC_URL"]
            )
