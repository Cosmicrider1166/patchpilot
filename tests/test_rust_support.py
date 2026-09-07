import unittest

from project import detect_project
from tests import (
    discover_test_files,
    detect_test_framework,
    build_test_command,
)


class TestRustSupport(unittest.TestCase):

    def test_detect_rust_project(self):
        files = [
            "Cargo.toml",
            "src/main.rs",
            "src/lib.rs",
            "src/calculator_test.rs",
        ]

        project = detect_project(files)

        self.assertTrue(project["supported"])
        self.assertEqual(
            project["type"],
            "rust",
        )
        self.assertEqual(
            project["language"],
            "Rust",
        )
        self.assertEqual(
            project["package_manager"],
            "Cargo",
        )

    def test_detect_rust_test_files(self):
        files = [
            "src/main.rs",
            "src/lib.rs",
            "src/calculator_test.rs",
            "src/formatter_test.rs",
        ]

        test_files = discover_test_files(
            *files
        )

        self.assertEqual(
            test_files,
            [
                "src/calculator_test.rs",
                "src/formatter_test.rs",
            ],
        )

    def test_detect_rust_test_framework(self):
        files = [
            "Cargo.toml",
            "src/main.rs",
            "src/calculator_test.rs",
        ]

        framework = detect_test_framework(
            files,
            project_type="rust",
        )

        self.assertEqual(
            framework,
            "cargo",
        )

    def test_build_rust_test_command(self):
        command = build_test_command(
            "cargo",
            None,
        )

        self.assertEqual(
            command,
            [
                "cargo",
                "test",
            ],
        )


if __name__ == "__main__":
    unittest.main()
