import unittest
from supplier_case import domain as d

class Identity(unittest.TestCase):
 def test_normalizes_and_requires_legal_identity(self):
  self.assertEqual(d.supplier_identity({'name':'  Acme  ', 'tax_id':' ab-123 '}), {'name':'Acme','tax_id':'AB-123'})
  with self.assertRaises(d.DomainError): d.supplier_identity({'name':'','tax_id':'abc'})
  with self.assertRaises(d.DomainError): d.supplier_identity({'name':'x','tax_id':'<script>'})
 def test_non_string_identities_are_not_silently_coerced(self):
  for data in [{'name':None,'tax_id':'ABC'},{'name':['Acme'],'tax_id':'ABC'},{'name':'Acme','tax_id':12345}]:
   with self.assertRaises(d.DomainError):d.supplier_identity(data)
