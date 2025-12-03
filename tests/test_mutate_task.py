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

    def test_updates_lock_task_and_reject_non_owner(self):
        task = self.s.create_task(
            "document", "coordinator", self.message, "ctx", {"x": 1}
        )
        changed = self.s.mutate_task(
            task["id"], "document", "coordinator", lambda d: {**d, "state": "working"}
        )
        self.assertEqual(changed["data"]["state"], "working")
        with self.assertRaises(DomainError):
            self.s.mutate_task(task["id"], "document", "other", lambda d: d)
