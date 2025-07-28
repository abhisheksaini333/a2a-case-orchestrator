import unittest
from supplier_case import protocol as p

class Envelope(unittest.TestCase):
 def test_preserves_request_id_and_rejects_wrong_version(self):
  r={'jsonrpc':'2.0','id':7,'method':'tasks/get','params':{'id':'x'}}
  self.assertEqual(p.request(r),('tasks/get',{'id':'x'},7))
  for invalid in [{**r,'jsonrpc':'1.0'},[],{**r,'params':[]}]:
   with self.assertRaises(p.RPCError):p.request(invalid)
