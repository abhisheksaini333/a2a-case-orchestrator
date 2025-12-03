from tests.database import DatabaseCase
import unittest, os, uuid
from supplier_case.store import Store
from supplier_case.domain import DomainError


@unittest.skipUnless(os.getenv("DATABASE_URL"), "requires isolated PostgreSQL")
class TaskStore(DatabaseCase):
    def setUp(self):
        self.s = Store(os.environ["DATABASE_URL"])
        self.s.migrate()
        self.message = uuid.uuid4().hex

    def test_idempotent_agent_message_preserves_task_and_context(self):
        a = self.s.create_task("document", "coordinator", self.message, "ctx", {"x": 1})
        b = self.s.create_task("document", "coordinator", self.message, "ctx", {"x": 1})
        self.assertEqual(a["id"], b["id"])
        self.assertEqual(a["context_id"], "ctx")
        with self.assertRaises(DomainError):
            self.s.create_task("document", "coordinator", self.message, "ctx", {"x": 2})
