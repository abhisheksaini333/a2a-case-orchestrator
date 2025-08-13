import unittest,threading,json,urllib.request,urllib.error
from supplier_case.transport import server
from supplier_case.protocol import agent_card,task
class Fake:
 name='document'
 def card(self):return agent_card('document','http://localhost','document-check')
 def rpc(self,m,p,who):return task('task1','context1','completed')
class HTTP(unittest.TestCase):
 def setUp(self):
  self.s=server(Fake(),{'coordinator':'t'*32});self.thread=threading.Thread(target=self.s.serve_forever,daemon=True);self.thread.start()
  self.url='http://127.0.0.1:'+str(self.s.server_port)
 def tearDown(self):self.s.shutdown();self.s.server_close();self.thread.join()
 def post(self,payload,auth=True):
  headers={'Content-Type':'application/json'}
  if auth:headers['Authorization']='Bearer '+'t'*32
  req=urllib.request.Request(self.url+'/a2a',data=json.dumps(payload).encode(),headers=headers)
  return urllib.request.urlopen(req)
 def test_transport_marks_sensitive_responses_uncacheable(self):
  with urllib.request.urlopen(self.url+'/health') as r:
   self.assertEqual(r.headers['Cache-Control'],'no-store');self.assertEqual(r.headers['X-Content-Type-Options'],'nosniff')
