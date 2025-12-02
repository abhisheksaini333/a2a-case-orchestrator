import unittest,threading
from supplier_case.client import Client
from supplier_case.transport import server
from supplier_case.protocol import agent_card,task
from supplier_case.domain import DomainError
class Fake:
 name='document'
 def card(self):return agent_card('document','http://localhost/a2a','document-check')
 def rpc(self,m,p,who):return task('t1',p.get('message',{}).get('contextId','c1'),'completed')
class ClientTest(unittest.TestCase):
 def setUp(self):
  self.s=server(Fake(),{'coordinator':'t'*32});self.thread=threading.Thread(target=self.s.serve_forever,daemon=True);self.thread.start()
  self.client=Client('http://127.0.0.1:'+str(self.s.server_port),'t'*32,'document','document-check')
 def tearDown(self):self.s.shutdown();self.s.server_close();self.thread.join()
 def test_expected_skill_is_required(self):
  self.assertEqual(self.client.discover()['name'],'document')
  self.client.skill='wrong'
  with self.assertRaises(DomainError):self.client.discover()
 def test_unsupported_protocol_revision_fails_before_sending_business_data(self):
  original=Fake.card
  Fake.card=lambda self:{**original(self),'protocolVersion':'9.9.0'}
  try:
   with self.assertRaises(DomainError):self.client.discover()
  finally:Fake.card=original
