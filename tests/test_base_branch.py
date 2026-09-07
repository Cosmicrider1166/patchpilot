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


class TestBaseBranchVerification(
    unittest.IsolatedAsyncioTestCase
):

    async def test_get_current_branch(self):
        run_mock = AsyncMock(
            return_value=FakeResult(
                stdout="master\n"
            )
        )

        sandbox = SimpleNamespace(
            commands=SimpleNamespace(
                run=run_mock
            )
        )

        branch = await github.get_current_branch(
            sandbox,
            "/work/patchpilot",
        )

        self.assertEqual(
            branch,
            "master",
        )

        run_mock.assert_awaited_once_with(
            "git",
            args=[
                "-C",
                "/work/patchpilot",
                "rev-parse",
                "--abbrev-ref",
                "HEAD",
            ],
            cwd="/work/patchpilot",
        )

    async def test_verify_base_branch_succeeds(self):
        sandbox = object()

        with patch.object(
            github,
            "get_current_branch",
            AsyncMock(
                return_value="master"
            ),
        ) as branch_mock:

            result = await github.verify_base_branch(
                sandbox,
                "/work/patchpilot",
                "master",
            )

        self.assertTrue(result)

        branch_mock.assert_awaited_once_with(
            sandbox,
            "/work/patchpilot",
        )

    async def test_verify_base_branch_rejects_wrong_branch(
        self,
    ):
        sandbox = object()

        with patch.object(
            github,
            "get_current_branch",
            AsyncMock(
                return_value="feature/other-work"
            ),
        ):

            with self.assertRaisesRegex(
                RuntimeError,
                "expected the repository",
            ):
                await github.verify_base_branch(
                    sandbox,
                    "/work/patchpilot",
                    "master",
                )


if __name__ == "__main__":
    unittest.main()
