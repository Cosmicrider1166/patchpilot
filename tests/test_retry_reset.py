import unittest
from unittest.mock import AsyncMock, patch

import main


class TestResetBeforeRetry(unittest.IsolatedAsyncioTestCase):

    async def test_reset_before_retry_calls_reset(self):
        sandbox = object()
        reset_mock = AsyncMock()

        with patch.object(
            main,
            "reset_working_tree",
            reset_mock,
        ):
            await main.reset_before_retry(
                sandbox,
                "repo",
            )

        reset_mock.assert_awaited_once_with(
            sandbox,
            "repo",
        )

    async def test_reset_before_retry_wraps_reset_error(self):
        sandbox = object()

        reset_mock = AsyncMock(
            side_effect=RuntimeError("reset failed")
        )

        with patch.object(
            main,
            "reset_working_tree",
            reset_mock,
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "PatchPilot could not restore",
            ):
                await main.reset_before_retry(
                    sandbox,
                    "repo",
                )


if __name__ == "__main__":
    unittest.main()
