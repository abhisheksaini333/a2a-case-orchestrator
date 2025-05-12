import unittest
from supplier_case import security as s
from supplier_case.domain import DomainError

class Roles(unittest.TestCase):
 def test_agent_cannot_approve_and_operator_cannot_impersonate_coordinator(self):
  s.require_role('reviewer', {'reviewer','operator'})
  with self.assertRaises(DomainError):s.require_role('document',{'reviewer'})
  with self.assertRaises(DomainError):s.require_role('operator',{'coordinator'})
