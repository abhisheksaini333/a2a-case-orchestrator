"""Every database test class owns a disposable schema, never another app's data."""

import os
import unittest
import uuid
import psycopg2
from psycopg2 import sql
from psycopg2.extensions import make_dsn


class DatabaseCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_url = os.environ["DATABASE_URL"]
        cls.schema = "test_" + uuid.uuid4().hex
        with psycopg2.connect(cls.original_url) as c, c.cursor() as q:
            q.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(cls.schema)))
        os.environ["DATABASE_URL"] = make_dsn(
            cls.original_url, options="-c search_path=" + cls.schema
        )

    @classmethod
    def tearDownClass(cls):
        os.environ["DATABASE_URL"] = cls.original_url
        with psycopg2.connect(cls.original_url) as c, c.cursor() as q:
            q.execute(
                sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(cls.schema))
            )
