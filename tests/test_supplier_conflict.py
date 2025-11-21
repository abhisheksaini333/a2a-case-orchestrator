import unittest,os,uuid
from tests.database import DatabaseCase
from supplier_case.store import Store
from supplier_case.domain import digest
@unittest.skipUnless(os.getenv('DATABASE_URL'), 'requires PostgreSQL')
class Conflict(DatabaseCase):
 def test_duplicate_tax_identifier_does_not_block_other_approved_commands(self):
  store=Store(os.environ['DATABASE_URL']);store.migrate();cases=[]
  for tax in ['DUP-100','DUP-100','OTHER-100']:
   case=store.create_case({'name':'Acme','tax_id':tax},'operator',uuid.uuid4().hex)
   record={'name':'Acme','tax_id':tax,'category':'office','risk':'low'}
   store.update_case(case['id'],1,state='review',proposal=record,proposal_digest=digest(record));store.approve(case['id'],digest(record),'reviewer');cases.append(case)
  store.deliver()
  self.assertEqual(len(store.suppliers()),2)
  self.assertEqual(store.get_case(cases[1]['id'])['state'],'conflict')
  self.assertEqual(store.get_case(cases[2]['id'])['state'],'completed')
  self.assertEqual(store.pending_count(),0)
