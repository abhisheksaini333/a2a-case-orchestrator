import os
import unittest
from tests.database import DatabaseCase
from supplier_case.store import Store
from supplier_case.domain import DomainError


@unittest.skipUnless(os.getenv("DATABASE_URL"), "requires PostgreSQL")
class Connections(DatabaseCase):
    def test_database_connections_close_after_each_transaction(self):
        store = Store(os.environ["DATABASE_URL"])
        with store.connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                self.assertEqual(cursor.fetchone()[0], 1)
        self.assertTrue(connection.closed)

    def test_case_lease_excludes_another_worker_and_releases_afterward(self):
        store = Store(os.environ["DATABASE_URL"])
        with store.case_lock("same-case"):
            with self.assertRaises(DomainError):
                with store.case_lock("same-case"):
                    self.fail("Another worker entered the same case")
        with store.case_lock("same-case"):
            pass
