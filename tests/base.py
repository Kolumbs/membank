"""Common methods and constants for all tests."""
import enum
import os
import unittest

import membank


TEST_DATABASE_PATH = "tests/data/test_database.db"


class DBPath(str, enum.Enum):
    """Enum for database paths."""

    RELATIVE = f"sqlite://{TEST_DATABASE_PATH}"
    ABSOLUTE = f"sqlite://{os.getcwd()}/{TEST_DATABASE_PATH}"


class TestCase(unittest.TestCase):
    """Generic TestCase class."""


def add_memory(path=None, reset=False):
    """Decorate TestCase with memory."""
    def decorator(cls):
        """Add memory to TestCase cls."""
        class MemoryTestCase(cls):
            """Add memory to TestCase."""

            def setUp(self):
                """Set up memory."""
                if path:
                    self.memory = membank.LoadMemory(path)
                else:
                    self.memory = membank.LoadMemory()
                super().setUp()

            def tearDown(self):
                """Tear down memory."""
                super().tearDown()
                if reset:
                    self.memory.reset()
        return MemoryTestCase
    return decorator
