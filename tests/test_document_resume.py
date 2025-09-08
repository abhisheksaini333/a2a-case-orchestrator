from tests.database import DatabaseCase
import unittest, os, uuid
from supplier_case.document import DocumentAgent
from supplier_case.store import Store
from supplier_case.domain import DomainError
from supplier_case.protocol import RPCError
@unittest.skipUnless(os.getenv('DATABASE_URL'), 'requires isolated PostgreSQL')
class Document(DatabaseCase):
 def setUp(self):
  self.s=Store(os.environ['DATABASE_URL']);self.s.migrate();self.a=DocumentAgent(self.s,'d'*32,'http://localhost')
  self.ctx=uuid.uuid4().hex;self.data={'name':'Acme','tax_id':'AB1','documents':[]}
 def send(self,data=None,task_id=None):
  m={'kind':'message','messageId':uuid.uuid4().hex,'role':'user','contextId':self.ctx,'parts':[{'kind':'data','data':data or self.data}]}
  if task_id:m['taskId']=task_id
  return self.a.rpc('message/send',{'message':m},'coordinator')
 def test_missing_input_resumes_same_task_without_changing_context(self):
  t=self.send();data={**self.data,'documents':[{'type':'tax_certificate','tax_id':'AB1'}]}
  resumed=self.send(data,t['id'])
  self.assertEqual(resumed['id'],t['id']);self.assertEqual(resumed['status']['state'],'completed')
  self.assertEqual(resumed['artifacts'][0]['metadata']['owner'],'document')
