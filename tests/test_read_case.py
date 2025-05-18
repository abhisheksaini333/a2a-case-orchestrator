import unittest, os, uuid
from supplier_case.store import Store
from supplier_case.domain import DomainError, digest

@unittest.skipUnless(os.getenv('DATABASE_URL'), 'requires an isolated PostgreSQL database')
class Database(unittest.TestCase):
 def setUp(self):
  self.store=Store(os.environ['DATABASE_URL']); self.store.migrate();self.key=uuid.uuid4().hex
 def case(self,creator='operator'):
  return self.store.create_case({'name':'Acme','tax_id':'T-'+self.key[:8]},creator,self.key)
 def test_read_and_list_preserve_creation_order_and_report_missing(self):
  case=self.case()
  self.assertEqual(self.store.get_case(case['id'])['input']['name'],'Acme')
  self.assertIn(case['id'],[x['id'] for x in self.store.list_cases()])
  with self.assertRaises(DomainError):self.store.get_case('absent')
