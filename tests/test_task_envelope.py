import unittest
from supplier_case import protocol as p


class Task(unittest.TestCase):
    def test_task_contains_stable_context_and_owned_state(self):
        t = p.task("t1", "c1", "input-required", {"missing": ["tax_certificate"]})
        self.assertEqual(t["kind"], "task")
        self.assertEqual(t["contextId"], "c1")
        self.assertEqual(t["status"]["message"]["taskId"], "t1")
        self.assertEqual(t["status"]["state"], "input-required")
