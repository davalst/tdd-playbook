"""Tests for the read-only tool classification.

`test_two_copies_agree_today` checks that tools.py and audit.py list the same read-only
tools — updating only one copy makes it fail.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import READ_ONLY_TOOLS, is_read_only  # noqa: E402
from audit import _READ_ONLY, mutating  # noqa: E402


class TestReadOnlyClassification(unittest.TestCase):
    def test_known(self):
        self.assertTrue(is_read_only("view"))
        self.assertFalse(is_read_only("delete"))

    def test_mutating_is_inverse(self):
        self.assertFalse(mutating("view"))
        self.assertTrue(mutating("delete"))

    def test_two_copies_agree_today(self):
        self.assertEqual(set(READ_ONLY_TOOLS), set(_READ_ONLY))


if __name__ == "__main__":
    unittest.main()
