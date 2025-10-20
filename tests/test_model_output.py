import unittest
from supplier_case import model as m
from supplier_case.domain import DomainError

class ModelOutput(unittest.TestCase):
 def test_bounded_json_accepts_fences_and_rejects_privileged_routes(self):
  valid='{"supplier":{"name":"Acme","tax_id":"AB1"},"skills":["document-check","catalog-match"]}'
  self.assertEqual(m.parse_output('```json\n'+valid+'\n```')['supplier']['name'],'Acme')
  self.assertEqual(m.parse_output('<think></think>'+valid)['skills'],['document-check','catalog-match'])
  for bad in [valid+' trailing',valid.replace('catalog-match','approve-supplier'),valid.replace('"tax_id":"AB1"','"tax_id":"AB1","approved":true')]:
   with self.assertRaises(DomainError):m.parse_output(bad)
