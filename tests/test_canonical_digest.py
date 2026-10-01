import unittest
from supplier_case import domain as d


class Digest(unittest.TestCase):
    def test_digest_is_order_independent_and_changes_with_content(self):
        self.assertEqual(d.digest({"b": 2, "a": 1}), d.digest({"a": 1, "b": 2}))
        self.assertNotEqual(d.digest({"a": 1}), d.digest({"a": 2}))
        with self.assertRaises(d.DomainError):
            d.digest({"x": float("nan")})

    def test_unpaired_unicode_surrogates_are_controlled_domain_errors(self):
        for value in (
            {"text": "\ud800"},
            {"\udfff": "value"},
            ["nested", {"text": "\ud800"}],
        ):
            for operation in (d.canonical, d.digest):
                with (
                    self.subTest(value=repr(value), operation=operation.__name__),
                    self.assertRaises(d.DomainError),
                ):
                    operation(value)

    def test_valid_multilingual_canonical_data_retains_exact_digest(self):
        import hashlib

        value = {"name": "अभिषेक", "description": "Café 😀"}
        encoded = d.canonical(value).encode("utf-8")
        self.assertEqual(d.digest(value), hashlib.sha256(encoded).hexdigest())
        self.assertIn("अभिषेक", d.canonical(value))
