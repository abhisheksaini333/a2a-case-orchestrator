import unittest
from supplier_case import security as s
from supplier_case.domain import DomainError


class Sign(unittest.TestCase):
    def test_artifact_signature_binds_owner_task_context_and_data(self):
        a = s.sign_artifact("document", "t1", "c1", {"status": "verified"}, "k" * 32)
        self.assertEqual(
            s.verify_artifact(a, "document", "t1", "c1", {"document": "k" * 32}),
            {"status": "verified"},
        )
        a["parts"][0]["data"]["status"] = "altered"
        with self.assertRaises(DomainError):
            s.verify_artifact(a, "document", "t1", "c1", {"document": "k" * 32})

    def test_other_agent_and_replayed_case_rejected(self):
        a = s.sign_artifact("catalog", "t2", "c2", {"category": "office"}, "x" * 32)
        with self.assertRaises(DomainError):
            s.verify_artifact(a, "document", "t2", "c2", {"document": "x" * 32})
        with self.assertRaises(DomainError):
            s.verify_artifact(a, "catalog", "t2", "wrong", {"catalog": "x" * 32})
