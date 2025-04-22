import unittest
from supplier_case import domain as d

class Identity(unittest.TestCase):
 def test_normalizes_and_requires_legal_identity(self):
  self.assertEqual(d.supplier_identity({'name':'  Acme  ', 'tax_id':' ab-123 '}), {'name':'Acme','tax_id':'AB-123'})
  with self.assertRaises(d.DomainError): d.supplier_identity({'name':'','tax_id':'abc'})
  with self.assertRaises(d.DomainError): d.supplier_identity({'name':'x','tax_id':'<script>'})
