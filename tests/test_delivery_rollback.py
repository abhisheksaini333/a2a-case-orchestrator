import unittest, os, uuid
from supplier_case.store import Store
from supplier_case.domain import DomainError, digest

@unittest.skipUnless(os.getenv('DATABASE_URL'), 'requires an isolated PostgreSQL database')
class Database(unittest.TestCase):
 def setUp(self):
  self.store=Store(os.environ['DATABASE_URL']); self.store.migrate();self.key=uuid.uuid4().hex
 def case(self,creator='operator'):
  return self.store.create_case({'name':'Acme','tax_id':'T-'+self.key[:8]},creator,self.key)
 def test_process_failure_before_commit_leaves_command_recoverable(self):
  case=self.case();record={'name':'Acme','tax_id':case['input']['tax_id'],'category':'office','risk':'low'}
  self.store.update_case(case['id'],1,state='review',proposal=record,proposal_digest=digest(record));self.store.approve(case['id'],digest(record),'reviewer')
  with self.assertRaises(RuntimeError):self.store.deliver(before_commit=lambda:(_ for _ in ()).throw(RuntimeError('crash')))
  self.assertFalse(any(x['case_id']==case['id'] for x in self.store.suppliers()))
  recovered=Store(os.environ['DATABASE_URL']);recovered.deliver()
  self.assertEqual(sum(x['case_id']==case['id'] for x in recovered.suppliers()),1)
  self.assertEqual(recovered.pending_count(),0)
