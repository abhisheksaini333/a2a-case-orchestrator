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

    def test_weak_key_is_not_accepted_even_with_a_matching_signature(self):
        import hashlib
        import hmac
        from supplier_case.domain import canonical

        artifact = s.sign_artifact(
            "document", "t1", "c1", {"status": "verified"}, "k" * 32
        )
        signed = {
            "owner": "document",
            "taskId": "t1",
            "contextId": "c1",
            "data": {"status": "verified"},
        }
        artifact["metadata"]["signature"] = hmac.new(
            b"short", canonical(signed).encode(), hashlib.sha256
        ).hexdigest()
        with self.assertRaises(DomainError):
            s.verify_artifact(artifact, "document", "t1", "c1", {"document": "short"})

    def test_malformed_keys_fail_through_domain_contract(self):
        artifact = s.sign_artifact("document", "t1", "c1", {}, "k" * 32)
        for key in (None, 99, b"k" * 32, "\ud800" * 32):
            with (
                self.subTest(operation="sign", key=repr(key)),
                self.assertRaises(DomainError),
            ):
                s.sign_artifact("document", "t1", "c1", {}, key)
            with (
                self.subTest(operation="verify", key=repr(key)),
                self.assertRaises(DomainError),
            ):
                s.verify_artifact(artifact, "document", "t1", "c1", {"document": key})
