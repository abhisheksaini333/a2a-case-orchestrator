import unittest
from supplier_case import domain as d

class Digest(unittest.TestCase):
 def test_digest_is_order_independent_and_changes_with_content(self):
  self.assertEqual(d.digest({'b':2,'a':1}),d.digest({'a':1,'b':2}))
  self.assertNotEqual(d.digest({'a':1}),d.digest({'a':2}))
  with self.assertRaises(d.DomainError): d.digest({'x':float('nan')})
