import unittest

from github import reset_working_tree


class FakeResult:
    def __init__(self, exit_code=0, stdout="", stderr=""):
        self.exitCode = exit_code
        self.stdout = stdout
        self.stderr = stderr


class FakeCommands:
    def __init__(self, results=None):
        self.results = results or []
        self.calls = []

    async def run(self, command, args=None, cwd=None):
        self.calls.append(
            {
                "command": command,
                "args": args,
                "cwd": cwd,
            }
        )

        if self.results:
            return self.results.pop(0)

        return FakeResult()


class FakeSandbox:
    def __init__(self, results=None):
        self.commands = FakeCommands(results)


class TestResetWorkingTree(unittest.IsolatedAsyncioTestCase):

    async def test_reset_and_clean_are_executed(self):
        sandbox = FakeSandbox()

        result = await reset_working_tree(
            sandbox,
            "repo",
        )

        self.assertTrue(result)
        self.assertEqual(
            len(sandbox.commands.calls),
            2,
        )

        reset_call = sandbox.commands.calls[0]

        self.assertEqual(
            reset_call["command"],
            "git",
        )
        self.assertEqual(
            reset_call["args"],
            [
                "-C",
                "repo",
                "reset",
                "--hard",
                "HEAD",
            ],
        )
        self.assertEqual(
            reset_call["cwd"],
            "repo",
        )

        clean_call = sandbox.commands.calls[1]

        self.assertEqual(
            clean_call["command"],
            "git",
        )
        self.assertEqual(
            clean_call["args"],
            [
                "-C",
                "repo",
                "clean",
                "-fd",
            ],
        )
        self.assertEqual(
            clean_call["cwd"],
            "repo",
        )

    async def test_reset_failure_raises_error(self):
        sandbox = FakeSandbox(
            [
                FakeResult(
                    exit_code=1,
                    stderr="reset failed",
                )
            ]
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Could not reset the repository",
        ):
            await reset_working_tree(
                sandbox,
                "repo",
            )

        self.assertEqual(
            len(sandbox.commands.calls),
            1,
        )

    async def test_clean_failure_raises_error(self):
        sandbox = FakeSandbox(
            [
                FakeResult(),
                FakeResult(
                    exit_code=1,
                    stderr="clean failed",
                ),
            ]
        )

        with self.assertRaisesRegex(
            RuntimeError,
            "Could not clean untracked files",
        ):
            await reset_working_tree(
                sandbox,
                "repo",
            )

        self.assertEqual(
            len(sandbox.commands.calls),
            2,
        )


if __name__ == "__main__":
    unittest.main()
