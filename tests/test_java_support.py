import unittest

from project import detect_project
from tests import (
    discover_test_files,
    detect_test_framework,
    build_test_command,
)


class TestJavaSupport(unittest.TestCase):

    def test_detect_maven_java_project(self):
        files = [
            "pom.xml",
            "src/main/java/App.java",
            "src/test/java/AppTest.java",
        ]

        project = detect_project(files)

        self.assertTrue(project["supported"])
        self.assertEqual(project["type"], "java_maven")
        self.assertEqual(project["language"], "Java")
        self.assertEqual(project["package_manager"], "Maven")

    def test_detect_gradle_java_project(self):
        files = [
            "build.gradle",
            "src/main/java/App.java",
            "src/test/java/AppTest.java",
        ]

        project = detect_project(files)

        self.assertTrue(project["supported"])
        self.assertEqual(project["type"], "java_gradle")
        self.assertEqual(project["language"], "Java")
        self.assertEqual(project["package_manager"], "Gradle")

    def test_detect_java_test_files(self):
        files = [
            "src/main/java/App.java",
            "src/test/java/AppTest.java",
            "src/test/java/CalculatorTest.java",
            "src/test/java/TestFormatter.java",
        ]

        test_files = discover_test_files(*files)

        self.assertEqual(
            test_files,
            [
                "src/test/java/AppTest.java",
                "src/test/java/CalculatorTest.java",
                "src/test/java/TestFormatter.java",
            ],
        )

    def test_detect_maven_test_framework(self):
        files = [
            "pom.xml",
            "src/main/java/App.java",
            "src/test/java/AppTest.java",
        ]

        framework = detect_test_framework(
            files,
            project_type="java_maven",
        )

        self.assertEqual(
            framework,
            "maven",
        )

    def test_build_maven_test_command(self):
        command = build_test_command(
            "maven",
            None,
        )

        self.assertEqual(
            command,
            ["mvn", "test"],
        )


if __name__ == "__main__":
    unittest.main()

