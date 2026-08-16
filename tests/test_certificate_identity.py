import unittest
from supplier_case.domain import document_check, DomainError


class CertificateIdentityTests(unittest.TestCase):
    def test_numeric_certificate_identifier_cannot_pass_through_string_coercion(self):
        with self.assertRaises(DomainError):
            document_check({"name": "Acme", "tax_id": "123", "documents": [{"type": "tax_certificate", "tax_id": 123}]})

    def test_certificate_and_supplier_identity_use_same_normalization(self):
        result = document_check({"name": "Acme", "tax_id": " ab-123 ", "documents": [{"type": "tax_certificate", "tax_id": " ab-123 "}]})
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["tax_id"], "AB-123")
