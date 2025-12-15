import unittest
from supplier_case import security as s
from supplier_case.domain import DomainError


class Bearer(unittest.TestCase):
    def test_credentials_resolve_only_known_principals(self):
        self.assertEqual(
            s.authenticate("Bearer " + "a" * 32, {"alice": "a" * 32}), "alice"
        )
        for value in ["", "Basic aaa", "Bearer wrong"]:
            with self.assertRaises(DomainError):
                s.authenticate(value, {"alice": "a" * 32})

    def test_non_ascii_credentials_fail_as_unauthorized(self):
        with self.assertRaises(DomainError) as error:
            s.authenticate("Bearer café", {"alice": "a" * 32})
        self.assertEqual(error.exception.code, "unauthorized")
