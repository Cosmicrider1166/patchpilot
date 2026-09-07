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


class TestCommitVerification(
    unittest.IsolatedAsyncioTestCase
):

    async def test_get_current_commit_hash(self):
        run_mock = AsyncMock(
            return_value=FakeResult(
                stdout="abc123\n"
            )
        )

        sandbox = SimpleNamespace(
            commands=SimpleNamespace(
                run=run_mock
            )
        )

        commit_hash = await github.get_current_commit_hash(
            sandbox,
            "/work/patchpilot",
        )

        self.assertEqual(
            commit_hash,
            "abc123",
        )

        run_mock.assert_awaited_once_with(
            "git",
            args=[
                "-C",
                "/work/patchpilot",
                "rev-parse",
                "HEAD",
            ],
            cwd="/work/patchpilot",
        )

    async def test_verify_commit_hash_succeeds(self):
        sandbox = object()

        with patch.object(
            github,
            "get_current_commit_hash",
            AsyncMock(
                return_value="abc123"
            ),
        ) as hash_mock:

            result = await github.verify_commit_hash(
                sandbox,
                "/work/patchpilot",
                "abc123",
            )

        self.assertTrue(result)

        hash_mock.assert_awaited_once_with(
            sandbox,
            "/work/patchpilot",
        )

    async def test_verify_commit_hash_rejects_mismatch(
        self,
    ):
        sandbox = object()

        with patch.object(
            github,
            "get_current_commit_hash",
            AsyncMock(
                return_value="different456"
            ),
        ):

            with self.assertRaisesRegex(
                RuntimeError,
                "commit mismatch",
            ):
                await github.verify_commit_hash(
                    sandbox,
                    "/work/patchpilot",
                    "abc123",
                )

    async def test_verify_commit_hash_requires_expected_hash(
        self,
    ):
        sandbox = object()

        with self.assertRaisesRegex(
            RuntimeError,
            "Expected commit hash is required",
        ):
            await github.verify_commit_hash(
                sandbox,
                "/work/patchpilot",
                "",
            )


if __name__ == "__main__":
    unittest.main()
