import os, uuid, unittest
from tests.test_coordinator_missing import Flow
from supplier_case.domain import DomainError


@unittest.skipUnless(os.getenv("DATABASE_URL"), "requires PostgreSQL")
class CoordinatorProtocol(Flow):
    def test_onboarding_is_a_discoverable_owned_task_with_same_task_resume(self):
        message = {
            "kind": "message",
            "role": "user",
            "messageId": uuid.uuid4().hex,
            "parts": [
                {
                    "kind": "data",
                    "data": {
                        "name": "Protocol Supplier",
                        "tax_id": "A2A-" + uuid.uuid4().hex[:8],
                    },
                }
            ],
        }
        initial = self.c.rpc("message/send", {"message": message}, "case-client")
        self.assertEqual(initial["status"]["state"], "input-required")
        with self.assertRaises(DomainError):
            self.c.rpc("tasks/get", {"id": initial["id"]}, "operator")
        tax = message["parts"][0]["data"]["tax_id"]
        message.update(
            messageId=uuid.uuid4().hex,
            taskId=initial["id"],
            contextId=initial["contextId"],
        )
        message["parts"][0]["data"] = {
            "documents": [{"type": "tax_certificate", "tax_id": tax}]
        }
        result = self.c.rpc("message/send", {"message": message}, "case-client")
        self.assertEqual(result["id"], initial["id"])
        self.assertEqual(result["status"]["state"], "input-required")
        self.assertEqual(
            result["status"]["message"]["parts"][0]["data"]["reason"], "human-review"
        )
