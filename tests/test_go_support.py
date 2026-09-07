import unittest

from project import detect_project
from tests import (
    discover_test_files,
    detect_test_framework,
    build_test_command,
)


class TestGoSupport(unittest.TestCase):

    def test_detect_go_project(self):
        files = [
            "go.mod",
            "main.go",
            "calculator.go",
            "calculator_test.go",
        ]

        project = detect_project(files)

        self.assertTrue(project["supported"])
        self.assertEqual(
            project["type"],
            "go",
        )
        self.assertEqual(
            project["language"],
            "Go",
        )
        self.assertEqual(
            project["package_manager"],
            "Go Modules",
        )

    def test_detect_go_test_files(self):
        files = [
            "main.go",
            "calculator.go",
            "calculator_test.go",
            "formatter_test.go",
        ]

        test_files = discover_test_files(
            *files
        )

        self.assertEqual(
            test_files,
            [
                "calculator_test.go",
                "formatter_test.go",
            ],
        )

    def test_detect_go_test_framework(self):
        files = [
            "go.mod",
            "main.go",
            "calculator_test.go",
        ]

        framework = detect_test_framework(
            files,
            project_type="go",
        )

        self.assertEqual(
            framework,
            "go",
        )

    def test_build_go_test_command(self):
        command = build_test_command(
            "go",
            None,
        )

        self.assertEqual(
            command,
            [
                "go",
                "test",
                "./...",
            ],
        )


if __name__ == "__main__":
    unittest.main()
