import unittest
from supplier_case import protocol as p

class Failures(unittest.TestCase):
 def test_standard_errors_do_not_expose_internal_objects(self):
  self.assertEqual(p.error_response(8,p.RPCError(-32001,'Task not found'))['error']['code'],-32001)
  self.assertEqual(p.error_response(8,RuntimeError('secret database path'))['error']['message'],'Internal service error')
