import unittest
from supplier_case import protocol as p

class Message(unittest.TestCase):
 def test_extracts_structured_user_message_and_rejects_agent_impersonation(self):
  m={'kind':'message','messageId':'m1','role':'user','parts':[{'kind':'data','data':{'name':'Acme'}}]}
  self.assertEqual(p.message_data({'message':m})[1],{'name':'Acme'})
  with self.assertRaises(p.RPCError):p.message_data({'message':{**m,'role':'agent'}})
  with self.assertRaises(p.RPCError):p.message_data({'message':{**m,'parts':[{'kind':'file','file':{'uri':'http://internal'}}]}})
