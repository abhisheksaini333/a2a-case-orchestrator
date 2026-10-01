import unittest
from unittest.mock import patch
from supplier_case.client import Client, DirectClient
from supplier_case.domain import DomainError


class ResponseTests(unittest.TestCase):
    def test_malformed_rpc_envelopes_fail_as_domain_errors(self):
        client = Client("http://127.0.0.1:1", "t" * 32, "document", "check")
        cases = [
            None,
            [],
            "task",
            {"result": {"kind": "task"}, "error": {"code": -1, "message": "bad"}},
            {"error": None},
            {"error": []},
            {"error": {"code": True, "message": "bad"}},
            {"error": {"code": -1, "message": []}},
        ]
        for case in cases:

            def response(path, data):
                return (
                    {"jsonrpc": "2.0", "id": data["id"], **case}
                    if isinstance(case, dict)
                    else case
                )

            with (
                self.subTest(case=case),
                patch.object(client, "fetch", side_effect=response),
            ):
                with self.assertRaises(DomainError) as caught:
                    client.rpc("tasks/get", {"id": "task-1"})
                self.assertEqual(caught.exception.code, "invalid_agent_response")

    def test_well_formed_peer_error_remains_an_agent_error(self):
        client = Client("http://127.0.0.1:1", "t" * 32, "document", "check")

        def response(path, data):
            return {
                "jsonrpc": "2.0",
                "id": data["id"],
                "error": {"code": -32001, "message": "missing"},
            }

        with (
            patch.object(client, "fetch", side_effect=response),
            self.assertRaises(DomainError) as caught,
        ):
            client.rpc("tasks/get", {})
        self.assertEqual(caught.exception.code, "agent_error")

    def test_direct_adapter_rejects_nonobject_responses(self):
        client = DirectClient("http://127.0.0.1:1", "t" * 32, "document", "check")
        for value in (None, [], 10):
            with (
                self.subTest(value=value),
                patch.object(client, "fetch", return_value=value),
                self.assertRaises(DomainError),
            ):
                client.send({}, "context", "message")
