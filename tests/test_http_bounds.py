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
 def test_oversized_and_malformed_bodies_are_rejected(self):
  with self.assertRaises(urllib.error.HTTPError) as ctx:self.post({'x':'x'*70000})
  self.assertEqual(ctx.exception.code,413)
  request=urllib.request.Request(self.url+'/a2a',data=b'{',headers={'Content-Type':'application/json','Authorization':'Bearer '+'t'*32})
  with self.assertRaises(urllib.error.HTTPError) as ctx:urllib.request.urlopen(request)
  self.assertEqual(ctx.exception.code,400)
