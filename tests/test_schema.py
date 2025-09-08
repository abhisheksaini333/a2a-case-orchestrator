from tests.database import DatabaseCase
import unittest, os, uuid
from supplier_case.store import Store
from supplier_case.domain import DomainError, digest

@unittest.skipUnless(os.getenv('DATABASE_URL'), 'requires an isolated PostgreSQL database')
class Database(DatabaseCase):
 def setUp(self):
  self.store=Store(os.environ['DATABASE_URL']); self.store.migrate();self.key=uuid.uuid4().hex
 def case(self,creator='operator'):
  return self.store.create_case({'name':'Acme','tax_id':'T-'+self.key[:8]},creator,self.key)
 def test_migrations_are_repeatable_and_database_is_reachable(self):
  self.store.migrate()
  with self.store.connection() as c:
   with c.cursor() as q:
    q.execute("SELECT count(*) FROM cases")
    self.assertGreaterEqual(q.fetchone()[0],0)
