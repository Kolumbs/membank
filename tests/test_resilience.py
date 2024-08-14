"""Resilience tests."""
from tests import base as b
from tests.test_interface import Perforator

import sqlalchemy as sa


@b.add_memory()
class CleanData(b.TestCase):
    """Testcase that cleans __meta_dataclasses__ table while membank has been loaded."""

    def test_delete_meta(self):
        """Clean __meta_dataclasses__ table."""
        p = Perforator("test")
        self.memory.put(p)
        self.assertTrue(self.memory.get.perforator(name="test"))
        engine = self.memory._get_engine()
        with engine.connect() as conn:
            conn.execute(sa.text("DELETE FROM __meta_dataclasses__"))
            conn.commit()
        result = self.memory.get.perforator(name="test")
        # Here might be even better if result is working as expected
        self.assertIsNone(result)
        self.memory.put(Perforator("some other perforator"))
        self.assertTrue(self.memory.get.perforator(name="some other perforator"))
        self.assertEqual(p, self.memory.get.perforator(name="test"))
