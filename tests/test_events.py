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
 def test_case_events_keep_agent_attribution_in_order(self):
  case=self.case()
  self.store.event(case['id'],'document','input-required',{'missing':['tax_certificate']})
  self.store.event(case['id'],'catalog','completed',{'category':'office'})
  events=self.store.events(case['id']);self.assertEqual([x['actor'] for x in events],['document','catalog'])
  self.assertLess(events[0]['id'],events[1]['id'])
