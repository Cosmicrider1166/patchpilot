import unittest
from unittest.mock import MagicMock, patch

import github


class FakeResult:

    def __init__(
        self,
        returncode=0,
        stdout="",
        stderr="",
    ):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestPullRequestSafety(unittest.TestCase):

    @patch("github.subprocess.run")
    def test_create_pull_request_success(
        self,
        run_mock,
    ):
        run_mock.return_value = FakeResult(
            stdout="https://github.com/example/repo/pull/1\n"
        )

        result = github.create_pull_request(
            "example",
            "repo",
            "patchpilot/issue-1",
            "master",
            "PatchPilot: Fix issue",
            "Automated repair.",
        )

        self.assertEqual(
            result,
            "https://github.com/example/repo/pull/1",
        )

        run_mock.assert_called_once()

    @patch("github.subprocess.run")
    def test_create_pull_request_rejects_cli_failure(
        self,
        run_mock,
    ):
        run_mock.return_value = FakeResult(
            returncode=1,
            stderr="authentication failed",
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Pull Request creation failed",
        ):
            github.create_pull_request(
                "example",
                "repo",
                "patchpilot/issue-1",
                "master",
                "PatchPilot: Fix issue",
                "Automated repair.",
            )

    @patch("github.subprocess.run")
    def test_create_pull_request_handles_existing_pr(
        self,
        run_mock,
    ):
        run_mock.side_effect = [
            FakeResult(
                returncode=1,
                stderr="a pull request already exists",
            ),
            FakeResult(
                stdout=(
                    "https://github.com/"
                    "example/repo/pull/7\n"
                )
            ),
        ]

        result = github.create_pull_request(
            "example",
            "repo",
            "patchpilot/issue-1",
            "master",
            "PatchPilot: Fix issue",
            "Automated repair.",
        )

        self.assertEqual(
            result,
            "https://github.com/example/repo/pull/7",
        )

        self.assertEqual(
            run_mock.call_count,
            2,
        )

    @patch("github.subprocess.run")
    def test_create_pull_request_rejects_empty_url(
        self,
        run_mock,
    ):
        run_mock.return_value = FakeResult(
            stdout="   \n"
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "did not return a Pull Request URL",
        ):
            github.create_pull_request(
                "example",
                "repo",
                "patchpilot/issue-1",
                "master",
                "PatchPilot: Fix issue",
                "Automated repair.",
            )

    @patch("github.subprocess.run")
    def test_existing_pr_lookup_failure_is_reported(
        self,
        run_mock,
    ):
        run_mock.side_effect = [
            FakeResult(
                returncode=1,
                stderr="a pull request already exists",
            ),
            FakeResult(
                returncode=1,
                stderr="could not find pull request",
            ),
        ]

        with self.assertRaisesRegex(
            RuntimeError,
            "Pull Request creation failed",
        ):
            github.create_pull_request(
                "example",
                "repo",
                "patchpilot/issue-1",
                "master",
                "PatchPilot: Fix issue",
                "Automated repair.",
            )


if __name__ == "__main__":
    unittest.main()
