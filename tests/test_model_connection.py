import unittest
from supplier_case import model as m
from supplier_case.domain import DomainError

class ModelConnection(unittest.TestCase):
 def test_missing_endpoint_and_unbounded_intake_fail_before_network(self):
  with self.assertRaises(DomainError) as e:m.extract('Acme','')
  self.assertEqual(e.exception.code,'model_not_configured')
  with self.assertRaises(DomainError):m.extract('x'*4001,'http://localhost')
