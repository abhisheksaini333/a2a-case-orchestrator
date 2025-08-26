import unittest,os,json,subprocess,tempfile,time,urllib.request,urllib.error,socket
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(os.getenv('DOTNET'), 'requires .NET SDK')
class CatalogHTTP(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  result=subprocess.run([os.environ['DOTNET'],'build','catalog','-o','catalog/bin/test','--nologo'],cwd=ROOT,text=True,capture_output=True)
  if result.returncode:raise AssertionError(result.stdout+result.stderr)
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.token='c'*32
  with socket.socket() as s:s.bind(('127.0.0.1',0));self.port=s.getsockname()[1]
  self.env={**os.environ,'PORT':str(self.port),'CATALOG_STATE':self.tmp.name,'AGENT_TOKEN':self.token,'ARTIFACT_KEY':'k'*32}
  self.url='http://127.0.0.1:'+str(self.port);self.start()
 def start(self):
  self.process=subprocess.Popen([os.environ['DOTNET'],str(ROOT/'catalog/bin/test/Catalog.dll'),'serve'],env=self.env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  for _ in range(60):
   try:urllib.request.urlopen(self.url+'/health',timeout=.3).close();return
   except (OSError,urllib.error.URLError):time.sleep(.05)
  self.fail('Catalog did not start')
 def tearDown(self):
  self.process.terminate();self.process.wait(timeout=5);self.tmp.cleanup()
 def rpc(self,method,params,auth=True):
  req=urllib.request.Request(self.url+'/a2a',data=json.dumps({'jsonrpc':'2.0','id':1,'method':method,'params':params}).encode(),headers={'Content-Type':'application/json',**({'Authorization':'Bearer '+self.token} if auth else {})})
  with urllib.request.urlopen(req) as r:return json.load(r)
 def message(self):return {'message':{'kind':'message','messageId':'message-1','role':'user','contextId':'case-1','parts':[{'kind':'data','data':{'description':'laptop repair'}}]}}
 def test_live_card_and_python_to_csharp_message(self):
  with urllib.request.urlopen(self.url+'/.well-known/agent.json') as r:self.assertEqual(json.load(r)['skills'][0]['id'],'catalog-match')
  result=self.rpc('message/send',self.message())['result']
  self.assertEqual(result['status']['state'],'completed');self.assertEqual(result['contextId'],'case-1')
  with self.assertRaises(urllib.error.HTTPError) as ctx:self.rpc('message/send',self.message(),False)
  self.assertEqual(ctx.exception.code,401)
 def test_catalog_artifact_verifies_in_python_and_tamper_fails(self):
  from supplier_case.security import verify_artifact
  from supplier_case.domain import DomainError
  result=self.rpc('message/send',self.message())['result'];artifact=result['artifacts'][0]
  value=verify_artifact(artifact,'catalog',result['id'],'case-1',{'catalog':'k'*32})
  self.assertEqual(value,{'category':'technology','risk':'low'})
  artifact['parts'][0]['data']['risk']='blocked'
  with self.assertRaises(DomainError):verify_artifact(artifact,'catalog',result['id'],'case-1',{'catalog':'k'*32})
 def test_restart_returns_same_task_for_duplicate_delivery(self):
  original=self.rpc('message/send',self.message())['result']
  self.process.kill();self.process.wait(timeout=5);self.start()
  resumed=self.rpc('message/send',self.message())['result']
  self.assertEqual(resumed,original)
  self.assertEqual(self.rpc('tasks/get',{'id':original['id']})['result'],original)
