"""
Common methods and constants for all tests
"""
import os
import unittest


TEST_DATABASE_PATH = "tests/data/test_database.db"


class TestCase(unittest.TestCase):
    """
    Generic TestCase class
    """
    relative_path = f"sqlite://{TEST_DATABASE_PATH }"
    absolute_path = f"sqlite://{os.getcwd()}/{TEST_DATABASE_PATH}"
