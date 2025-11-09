"""Resilience tests."""

import sqlalchemy as sa

from tests import base as b
from tests.test_interface import Perforator


@b.add_memory()
class CleanData(b.TestCase):
    """Testcase that cleans __meta_dataclasses__ table while membank has been loaded."""

    commit_stmts = (
        "DELETE FROM __meta_dataclasses__",
        "DROP TABLE __meta_dataclasses__",
    )

    def setUp(self):
        """Create initial test data."""
        super().setUp()
        self.p = Perforator("test")
        self.memory.put(self.p)
        self.assertTrue(self.memory.get.perforator(name="test"))

    def test(self):
        """Check recover of dataclasses."""
        for stmt in self.commit_stmts:
            with self.subTest(stmt=stmt):
                self.commit_stmt(stmt)
                result = self.memory.get(self.memory.perforator.name == "test")
                self.assertIsNotNone(result)
                result = self.memory.get.perforator(name="test")
                self.assertIsNotNone(result)
                self.assertTrue(result.name, "test")
                result.name = "test_updated"
                self.memory.put(result)
                self.memory.put(Perforator("some other perforator"))
                self.memory.put(Perforator("some more perforators"))
                self.assertTrue(
                    self.memory.get.perforator(name="some other perforator")
                )
                self.assertEqual(self.p, self.memory.get.perforator(name="test"))

    def test_fallback(self):
        """Check fallback dataclass storage."""
        for stmt in self.commit_stmts:
            with self.subTest(stmt=stmt):
                self.commit_stmt(stmt)
                result = self.memory.get.perforator(name="test")
                self.memory.put(result)
                result = self.memory.get.perforator(name="test")
                self.memory.put(Perforator("some other perforator"))
                result = self.memory.get.perforator(name="test")
                self.assertIsNotNone(result)
                self.assertEqual(result, self.p)

    def commit_stmt(self, stmt):
        """Destroy meta_dataclasses table."""
        engine = self.memory._get_engine()
        with engine.connect() as conn:
            conn.execute(sa.text(stmt))
            conn.commit()
