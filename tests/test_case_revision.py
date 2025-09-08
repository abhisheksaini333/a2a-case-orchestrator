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
 def test_stale_agent_result_cannot_overwrite_new_case_revision(self):
  case=self.case();self.store.update_case(case['id'],1,state='input-required')
  updated=self.store.resume_case(case['id'],{'documents':[{'type':'tax_certificate','tax_id':case['input']['tax_id']}]})
  self.assertEqual(updated['revision'],2)
  with self.assertRaises(DomainError):self.store.update_case(case['id'],1,state='review')
