import unittest
from unittest.mock import AsyncMock, patch

import main


class TestRetryExhaustion(unittest.IsolatedAsyncioTestCase):

    async def test_three_failed_attempts_stop_repair(self):
        reset_mock = AsyncMock()

        with patch.object(
            main,
            "MAX_REPAIR_ATTEMPTS",
            3,
        ):
            attempts = list(
                range(
                    1,
                    main.MAX_REPAIR_ATTEMPTS + 1,
                )
            )

            repair_succeeded = False

            for attempt in attempts:
                repair_succeeded = False

                if attempt < main.MAX_REPAIR_ATTEMPTS:
                    await reset_mock(
                        object(),
                        main.REPO_PATH,
                    )

            self.assertEqual(
                len(attempts),
                3,
            )

            self.assertEqual(
                reset_mock.await_count,
                2,
            )

            self.assertFalse(
                repair_succeeded
            )

            with self.assertRaisesRegex(
                RuntimeError,
                "PatchPilot could not repair",
            ):
                if not repair_succeeded:
                    raise RuntimeError(
                        "PatchPilot could not repair "
                        "the repository within "
                        f"{main.MAX_REPAIR_ATTEMPTS} attempts."
                    )


if __name__ == "__main__":
    unittest.main()
