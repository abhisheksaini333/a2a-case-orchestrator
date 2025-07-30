import unittest
from supplier_case import protocol as p

class Discovery(unittest.TestCase):
 def test_card_declares_supported_skill_auth_and_streaming(self):
  card=p.agent_card('document','http://127.0.0.1:18131','document-check')
  self.assertEqual(card['skills'][0]['id'],'document-check');self.assertTrue(card['capabilities']['streaming'])
  self.assertFalse(card['capabilities']['pushNotifications']);self.assertEqual(card['security'],[{'bearer':[]}])
