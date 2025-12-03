import os, unittest, uuid
from tests.test_coordinator_missing import Flow
from supplier_case.domain import DomainError


@unittest.skipUnless(os.getenv("DATABASE_URL"), "requires PostgreSQL")
class Recovery(Flow):
    def test_catalog_failure_retries_without_resuming_completed_document(self):
        self.row = self.s.create_case(
            {"name": "Acme", "tax_id": "T-" + uuid.uuid4().hex[:8], "documents": []},
            "operator",
            uuid.uuid4().hex,
        )
        self.c.run(self.row["id"])
        original = self.c.catalog.send
        self.c.catalog.send = lambda *a, **k: (_ for _ in ()).throw(
            DomainError("agent_unavailable", "offline")
        )
        with self.assertRaises(DomainError):
            self.c.resume(
                self.row["id"],
                {
                    "documents": [
                        {
                            "type": "tax_certificate",
                            "tax_id": self.row["input"]["tax_id"],
                        }
                    ]
                },
            )
        self.c.catalog.send = original
        self.assertEqual(self.c.run(self.row["id"])["state"], "review")

    def test_startup_recovery_finds_interrupted_cases(self):
        self.s.update_case(self.row["id"], 1, state="working")
        ids = self.s.recoverable_cases()
        self.assertIn(self.row["id"], ids)
        self.c.recover()
        self.assertEqual(self.s.get_case(self.row["id"])["state"], "input-required")
