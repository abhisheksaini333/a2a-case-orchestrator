import unittest,os,uuid
from supplier_case.coordinator import Coordinator
from supplier_case.store import Store
from supplier_case.document import DocumentAgent
from supplier_case.security import sign_artifact
from supplier_case.protocol import task
from supplier_case.domain import DomainError
class LocalDocument:
 def __init__(self,s):self.a=DocumentAgent(s,'d'*32,'http://localhost')
 def discover(self):return self.a.card()
 def send(self,data,context,message_id,task_id=None):
  message={'kind':'message','role':'user','messageId':message_id,'contextId':context,'parts':[{'kind':'data','data':data}]}
  if task_id:message['taskId']=task_id
  return self.a.rpc('message/send',{'message':message},'coordinator')
 def rpc(self,m,p):return self.a.rpc(m,p,'coordinator')
class Catalog:
 def discover(self):return {'name':'catalog'}
 def send(self,data,context,message_id,task_id=None):
  return task('catalog-task',context,'completed',artifacts=[sign_artifact('catalog','catalog-task',context,{'category':'office','risk':'low'},'c'*32)])
@unittest.skipUnless(os.getenv('DATABASE_URL'), 'requires isolated PostgreSQL')
class Flow(unittest.TestCase):
 def setUp(self):
  self.s=Store(os.environ['DATABASE_URL']);self.s.migrate();self.c=Coordinator(self.s,LocalDocument(self.s),Catalog(),{'document':'d'*32,'catalog':'c'*32})
  self.row=self.s.create_case({'name':'Acme','tax_id':'T-'+uuid.uuid4().hex[:8]},'operator',uuid.uuid4().hex)
 def test_cancel_propagates_to_owned_document_task(self):
  self.c.run(self.row['id']);row=self.c.cancel(self.row['id'],'operator')
  self.assertEqual(row['state'],'canceled')
  task_id=[e['detail']['task_id'] for e in self.s.events(row['id']) if e['kind']=='document-task'][-1]
  self.assertEqual(self.c.document.rpc('tasks/get',{'id':task_id})['status']['state'],'canceled')
