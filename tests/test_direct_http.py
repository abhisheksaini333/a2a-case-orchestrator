import unittest,threading
from supplier_case.client import DirectClient
from supplier_case.transport import server
from supplier_case.protocol import task
class Direct(unittest.TestCase):
 def test_plain_http_payload_executes_the_same_skill_without_rpc_envelope(self):
  calls=[]
  class Service:
   name='document'
   def rpc(self,method,params,principal):
    calls.append((method,params,principal));return task('t1',params['message']['contextId'],'completed')
  http=server(Service(),{'coordinator':'t'*32});thread=threading.Thread(target=http.serve_forever,daemon=True);thread.start()
  try:
   client=DirectClient('http://127.0.0.1:'+str(http.server_port),'t'*32,'document','document-check')
   result=client.send({'name':'Acme'},'c1','m1')
   self.assertEqual(result['id'],'t1');self.assertEqual(calls[0][1]['message']['parts'][0]['data'],{'name':'Acme'})
   self.assertEqual(client.measurements['requests'],1)
  finally:http.shutdown();http.server_close();thread.join()
