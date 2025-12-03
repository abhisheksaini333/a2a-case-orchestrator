import unittest
from supplier_case import domain as d


class Input(unittest.TestCase):
    def test_strict_case_payload_and_bounds(self):
        self.assertEqual(
            d.case_input({"name": "Acme", "tax_id": "AB1", "description": "  Paper  "})[
                "description"
            ],
            "Paper",
        )
        with self.assertRaises(d.DomainError):
            d.case_input({"name": "Acme", "tax_id": "AB1", "description": "x" * 4001})
        with self.assertRaises(d.DomainError):
            d.case_input({"name": "Acme", "tax_id": "AB1", "approved": True})
