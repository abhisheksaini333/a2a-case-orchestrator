import unittest
from unittest.mock import patch
from scripts.evaluate_intake import evaluate
from supplier_case.domain import DomainError


class Evaluation(unittest.TestCase):
    def test_malformed_model_output_is_not_semantic_success_on_negative_case(self):
        with patch(
            "scripts.evaluate_intake.extract",
            side_effect=DomainError("invalid_model_output", "not JSON"),
        ):
            report = evaluate(
                [{"id": "missing", "text": "no identity", "expected": None}],
                "local-model",
                "http://localhost",
            )
        self.assertEqual(report["correct"], 0)
        self.assertEqual(report["accepted"], 0)
