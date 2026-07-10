import unittest
from tools import files, shell
"""Unit tests for the agent's file tools.

Each test runs against a fresh temporary directory so the suite never
touches the real repository. The directory is created in setUp and
destroyed in tearDown, guaranteeing isolation between tests.
"""

import os
import tempfile
import unittest

from tools import files


class TestFileTools(unittest.TestCase):
    """Covers read_file and write_file."""

    def setUp(self):
        """Create a throwaway directory before every test."""
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = self._tmp.name

    def tearDown(self):
        """Delete the throwaway directory after every test."""
        self._tmp.cleanup()

    def test_write_creates_file(self):
        """write_file writes content to a plain path."""
        target = os.path.join(self.tmp_path, "hello.py")
        files.write_file(target, "print('hello')")
        with open(target) as f:
            self.assertEqual(f.read(), "print('hello')")

    def test_write_creates_missing_dirs(self):
        """write_file creates missing parent directories (the makedirs branch)."""
        target = os.path.join(self.tmp_path, "nested", "deep", "x.py")
        files.write_file(target, "data")
        self.assertTrue(os.path.exists(target))

    def test_write_overwrites_existing_file(self):
        """Pins the design decision: mode 'w' truncates, it does not append."""
        target = os.path.join(self.tmp_path, "x.txt")
        with open(target, "w") as f:
            f.write("old")
        files.write_file(target, "new")
        with open(target) as f:
            self.assertEqual(f.read(), "new")

    def test_read_returns_full_content(self):
        """read_file returns the entire file as one string, newlines intact."""
        target = os.path.join(self.tmp_path, "x.txt")
        with open(target, "w") as f:
            f.write("hello\nworld")
        self.assertEqual(files.read_file(target), "hello\nworld")

    def test_read_missing_file_raises(self):
        """Documents current behavior: a missing file propagates FileNotFoundError.

        This is a design fork, not a settled decision. If the agent should
        self-correct instead of crashing, read_file must catch this and
        return an error string as the observation.
        """
        target = os.path.join(self.tmp_path, "nope.txt")
        with self.assertRaises(FileNotFoundError):
            files.read_file(target)


if __name__ == "__main__":
    unittest.main()
