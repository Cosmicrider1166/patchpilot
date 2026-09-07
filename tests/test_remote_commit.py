import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import github


class FakeResult:

    def __init__(
        self,
        exitCode=0,
        stdout="",
        stderr="",
    ):
        self.exitCode = exitCode
        self.stdout = stdout
        self.stderr = stderr


class TestRemoteCommitVerification(
    unittest.IsolatedAsyncioTestCase
):

    async def test_remote_commit_matches(self):
        run_mock = AsyncMock(
            return_value=FakeResult(
                stdout=(
                    "abc123 "
                    "refs/heads/"
                    "patchpilot/issue-1\n"
                )
            )
        )

        sandbox = SimpleNamespace(
            commands=SimpleNamespace(
                run=run_mock
            )
        )

        result = await github.verify_remote_commit_hash(
            sandbox,
            "/work/patchpilot",
            "patchpilot/issue-1",
            "abc123",
        )

        self.assertTrue(result)

        run_mock.assert_awaited_once_with(
            "git",
            args=[
                "-C",
                "/work/patchpilot",
                "ls-remote",
                "origin",
                "refs/heads/patchpilot/issue-1",
            ],
            cwd="/work/patchpilot",
        )

    async def test_remote_commit_rejects_mismatch(self):
        sandbox = SimpleNamespace()

        with patch.object(
            github,
            "get_current_commit_hash",
            AsyncMock(
                return_value="local123"
            ),
        ):

            run_mock = AsyncMock(
                return_value=FakeResult(
                    stdout=(
                        "remote456 "
                        "refs/heads/"
                        "patchpilot/issue-1\n"
                    )
                )
            )

            sandbox.commands = SimpleNamespace(
                run=run_mock
            )

            with self.assertRaisesRegex(
                RuntimeError,
                "remote commit mismatch",
            ):
                await github.verify_remote_commit_hash(
                    sandbox,
                    "/work/patchpilot",
                    "patchpilot/issue-1",
                    "local123",
                )

    async def test_remote_verification_requires_branch(
        self,
    ):
        sandbox = SimpleNamespace()

        with self.assertRaisesRegex(
            RuntimeError,
            "Branch name is required",
        ):
            await github.verify_remote_commit_hash(
                sandbox,
                "/work/patchpilot",
                "",
                "abc123",
            )

    async def test_remote_verification_requires_hash(
        self,
    ):
        sandbox = SimpleNamespace()

        with self.assertRaisesRegex(
            RuntimeError,
            "Expected commit hash is required",
        ):
            await github.verify_remote_commit_hash(
                sandbox,
                "/work/patchpilot",
                "patchpilot/issue-1",
                "",
            )


if __name__ == "__main__":
    unittest.main()
