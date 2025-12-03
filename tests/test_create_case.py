from tests.database import DatabaseCase
import unittest, os, uuid
from supplier_case.store import Store
from supplier_case.domain import DomainError, digest


@unittest.skipUnless(
    os.getenv("DATABASE_URL"), "requires an isolated PostgreSQL database"
)
class Database(DatabaseCase):
    def setUp(self):
        self.store = Store(os.environ["DATABASE_URL"])
        self.store.migrate()
        self.key = uuid.uuid4().hex

    def case(self, creator="operator"):
        return self.store.create_case(
            {"name": "Acme", "tax_id": "T-" + self.key[:8]}, creator, self.key
        )

    def test_duplicate_submission_returns_same_case_but_changed_payload_conflicts(self):
        a = self.case()
        b = self.case()
        self.assertEqual(a["id"], b["id"])
        with self.assertRaises(DomainError):
            self.store.create_case(
                {"name": "Other", "tax_id": "T-" + self.key[:8]}, "operator", self.key
            )
