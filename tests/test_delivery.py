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
 def test_replayed_delivery_creates_one_exact_supplier(self):
  case=self.case();record={'name':'Acme','tax_id':case['input']['tax_id'],'category':'office','risk':'low'}
  self.store.update_case(case['id'],1,state='review',proposal=record,proposal_digest=digest(record))
  self.store.approve(case['id'],digest(record),'reviewer')
  self.store.deliver();self.store.deliver()
  rows=self.store.suppliers();match=[x for x in rows if x['case_id']==case['id']]
  self.assertEqual(len(match),1);self.assertEqual(match[0]['record'],record)
  self.assertEqual(self.store.get_case(case['id'])['state'],'completed')
