import unittest
from supplier_case import domain as d


class Proposal(unittest.TestCase):
    def test_exact_record_requires_both_agents(self):
        doc = {"status": "verified", "name": "Acme", "tax_id": "AB1"}
        cat = {"category": "office", "risk": "low"}
        proposal = d.proposal(doc, cat)
        self.assertEqual(
            proposal,
            {"name": "Acme", "tax_id": "AB1", "category": "office", "risk": "low"},
        )
        with self.assertRaises(d.DomainError):
            d.proposal({**doc, "status": "input-required"}, cat)
        with self.assertRaises(d.DomainError):
            d.proposal(doc, {"category": "office", "risk": "blocked"})
