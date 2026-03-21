import unittest
from unittest.mock import patch
from supplier_case.client import Client
from supplier_case.domain import DomainError
from supplier_case.protocol import agent_card


class ShapeTests(unittest.TestCase):
    def setUp(self):
        self.client = Client("http://127.0.0.1:1", "t" * 32, "document", "document-check")

    def test_malformed_cards_fail_with_domain_errors(self):
        valid = agent_card("document", "http://ignored", "document-check")
        cards = [None, [], "document"]
        for key, values in {"skills": [None, {}, [None], [{"id": []}]], "defaultInputModes": [None, "application/json"], "protocolVersion": [[]]}.items():
            cards.extend({**valid, key: value} for value in values)
        for card in cards:
            with self.subTest(card=card), patch.object(self.client, "fetch", return_value=card), self.assertRaises(DomainError):
                self.client.discover()

    def test_supported_cards_retain_revision_negotiation(self):
        for version in ("0.2.0", "0.3.0"):
            card = agent_card("document", "http://ignored", "document-check", version)
            with patch.object(self.client, "fetch", return_value=card):
                self.assertEqual(self.client.discover(), card)
                self.assertEqual(self.client.negotiated_version, version)
