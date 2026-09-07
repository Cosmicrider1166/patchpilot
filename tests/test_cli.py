import sys
import unittest
from unittest.mock import patch

import main


class TestCLI(unittest.TestCase):

    def test_valid_arguments_use_defaults(self):
        with patch.object(
            sys,
            "argv",
            [
                "main.py",
                "example/repo",
                "12",
            ],
        ):
            result = main.get_arguments()

        self.assertEqual(
            result,
            (
                "example",
                "repo",
                12,
                main.MAX_REPAIR_ATTEMPTS,
                main.MAX_CONTEXT_FILES,
                main.MAX_CONTEXT_CHARS,
                main.MAX_FILE_CONTEXT_CHARS,
            ),
        )

    def test_custom_configuration(self):
        with patch.object(
            sys,
            "argv",
            [
                "main.py",
                "example/repo",
                "12",
                "--max-attempts",
                "5",
                "--max-context-files",
                "10",
                "--max-context-chars",
                "20000",
                "--max-file-context-chars",
                "8000",
            ],
        ):
            result = main.get_arguments()

        self.assertEqual(
            result,
            (
                "example",
                "repo",
                12,
                5,
                10,
                20000,
                8000,
            ),
        )

    def test_invalid_repository_format(self):
        with patch.object(
            sys,
            "argv",
            [
                "main.py",
                "invalid-repository",
                "12",
            ],
        ):
            with self.assertRaises(SystemExit):
                main.get_arguments()

    def test_invalid_issue_number(self):
        with patch.object(
            sys,
            "argv",
            [
                "main.py",
                "example/repo",
                "0",
            ],
        ):
            with self.assertRaises(SystemExit):
                main.get_arguments()

    def test_non_integer_issue_number(self):
        with patch.object(
            sys,
            "argv",
            [
                "main.py",
                "example/repo",
                "abc",
            ],
        ):
            with self.assertRaises(SystemExit):
                main.get_arguments()

    def test_invalid_max_attempts(self):
        with patch.object(
            sys,
            "argv",
            [
                "main.py",
                "example/repo",
                "12",
                "--max-attempts",
                "0",
            ],
        ):
            with self.assertRaises(SystemExit):
                main.get_arguments()


if __name__ == "__main__":
    unittest.main()
