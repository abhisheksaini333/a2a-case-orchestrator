import unittest
from supplier_case import domain as d


class Approval(unittest.TestCase):
    def test_altered_or_self_approved_decision_fails(self):
        record = {"name": "Acme"}
        h = d.digest(record)
        self.assertEqual(
            d.authorize_approval(record, h, "reviewer", "applicant"), "reviewer"
        )
        with self.assertRaises(d.DomainError):
            d.authorize_approval(record, "wrong", "reviewer", "applicant")
        with self.assertRaises(d.DomainError):
            d.authorize_approval(record, h, "applicant", "applicant")
