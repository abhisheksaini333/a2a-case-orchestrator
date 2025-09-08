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
 def test_cancel_blocks_late_results_and_approval(self):
  case=self.case();self.store.cancel_case(case['id'],'operator')
  self.assertEqual(self.store.get_case(case['id'])['state'],'canceled')
  with self.assertRaises(DomainError):self.store.update_case(case['id'],1,state='review')
  with self.assertRaises(DomainError):self.store.approve(case['id'],'bad','reviewer')
