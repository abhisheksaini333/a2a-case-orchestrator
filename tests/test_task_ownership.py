import unittest
from supplier_case import security as s
from supplier_case.domain import DomainError


class Ownership(unittest.TestCase):
    def test_task_owner_is_required_for_resume_read_and_cancel(self):
        task = {"owner": "coordinator"}
        self.assertIsNone(s.owns(task, "coordinator"))
        with self.assertRaises(DomainError):
            s.owns(task, "attacker")
