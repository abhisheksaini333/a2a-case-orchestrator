import unittest
from supplier_case import protocol as p

class Failures(unittest.TestCase):
 def test_standard_errors_do_not_expose_internal_objects(self):
  self.assertEqual(p.error_response(8,p.RPCError(-32001,'Task not found'))['error']['code'],-32001)
  self.assertEqual(p.error_response(8,RuntimeError('secret database path'))['error']['message'],'Internal service error')
 def test_standard_task_error_codes_survive_domain_mapping(self):
  from supplier_case.domain import DomainError
  self.assertEqual(p.error_response(1,DomainError('task_not_found','Task not found'))['error']['code'],-32001)
  self.assertEqual(p.error_response(1,DomainError('not_cancelable','Terminal task'))['error']['code'],-32002)
