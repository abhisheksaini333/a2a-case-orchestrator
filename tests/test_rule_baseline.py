import unittest
from supplier_case import model as m
from supplier_case.domain import DomainError

class Baseline(unittest.TestCase):
 def test_explicit_rule_baseline_extracts_labeled_intake(self):
  data=m.extract_rules('name: Acme Tools; tax_id: AB-123; description: server repair')
  self.assertEqual(data['supplier']['description'],'server repair')
  self.assertEqual(data['mode'],'rules')
  with self.assertRaises(DomainError):m.extract_rules('Supplier Acme has no tax identifier')
