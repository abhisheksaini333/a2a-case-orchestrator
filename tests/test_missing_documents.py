import unittest
from supplier_case import domain as d


class Documents(unittest.TestCase):
    def test_requests_missing_tax_document(self):
        self.assertEqual(
            d.document_check({"name": "Acme", "tax_id": "AB1", "documents": []})[
                "missing"
            ],
            ["tax_certificate"],
        )
        result = d.document_check(
            {
                "name": "Acme",
                "tax_id": "AB1",
                "documents": [{"type": "tax_certificate", "tax_id": "AB1"}],
            }
        )
        self.assertEqual(result["status"], "verified")

    def test_rejects_mismatched_certificate(self):
        with self.assertRaises(d.DomainError):
            d.document_check(
                {
                    "name": "Acme",
                    "tax_id": "AB1",
                    "documents": [{"type": "tax_certificate", "tax_id": "XX1"}],
                }
            )
