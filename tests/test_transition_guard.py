import unittest
from supplier_case import domain as d


class Transitions(unittest.TestCase):
    def test_terminal_tasks_cannot_resume(self):
        self.assertEqual(d.transition("input-required", "working"), "working")
        self.assertEqual(d.transition("working", "completed"), "completed")
        for old, new in [
            ("completed", "working"),
            ("canceled", "completed"),
            ("failed", "working"),
        ]:
            with self.assertRaises(d.DomainError):
                d.transition(old, new)
