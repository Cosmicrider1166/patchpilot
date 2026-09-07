import unittest

import config


class TestConfiguration(unittest.TestCase):

    def test_repository_configuration(self):
        self.assertEqual(
            config.REPO_PATH,
            "/work/patchpilot",
        )

        self.assertEqual(
            config.BASE_BRANCH,
            "master",
        )

    def test_commit_configuration(self):
        self.assertEqual(
            config.COMMIT_AUTHOR,
            "PatchPilot",
        )

        self.assertEqual(
            config.COMMIT_EMAIL,
            "patchpilot@example.com",
        )

    def test_retry_configuration(self):
        self.assertEqual(
            config.MAX_REPAIR_ATTEMPTS,
            3,
        )

    def test_context_configuration(self):
        self.assertEqual(
            config.MAX_CONTEXT_FILES,
            20,
        )

        self.assertEqual(
            config.MAX_CONTEXT_CHARS,
            30000,
        )

        self.assertEqual(
            config.MAX_FILE_CONTEXT_CHARS,
            12000,
        )

    def test_valid_configuration(self):
        self.assertTrue(
            config.validate_configuration()
        )

    def test_custom_valid_configuration(self):
        self.assertTrue(
            config.validate_configuration(
                max_repair_attempts=5,
                max_context_files=10,
                max_context_chars=20000,
                max_file_context_chars=8000,
            )
        )

    def test_zero_value_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "must be greater than zero",
        ):
            config.validate_configuration(
                max_repair_attempts=0
            )

    def test_negative_value_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "must be greater than zero",
        ):
            config.validate_configuration(
                max_context_files=-1
            )

    def test_non_integer_rejected(self):
        with self.assertRaisesRegex(
            ValueError,
            "must be an integer",
        ):
            config.validate_configuration(
                max_context_chars="30000"
            )


if __name__ == "__main__":
    unittest.main()
