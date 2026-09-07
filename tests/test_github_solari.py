import asyncio

from solari import (
    create_sandbox,
    run_command,
    list_files,
)


REPO_URL = "https://github.com/Cosmicrider1166/patchpilot-demo.git"
REPO_PATH = "/work/repo"


async def main():
    client, sandbox, ctx = await create_sandbox()

    try:
        print("=== Sandbox created ===")
        print("Sandbox ready")

        # ----------------------------------------
        # Clone GitHub repository
        # ----------------------------------------

        print("=== Cloning GitHub repository ===")

        result = await run_command(
            sandbox,
            "git",
            [
                "clone",
                REPO_URL,
                REPO_PATH,
            ],
        )

        print("Exit code:", result.exitCode)
        print("stdout:")
        print(result.stdout)

        print("stderr:")
        print(result.stderr)

        if result.exitCode != 0:
            raise RuntimeError(
                f"Git clone failed:\n{result.stderr}"
            )

        # ----------------------------------------
        # List cloned repository
        # ----------------------------------------

        print("=== Repository files ===")

        files = await list_files(
            sandbox,
            REPO_PATH,
        )

        print("Exit code:", files.exitCode)
        print("stdout:")
        print(files.stdout)

        print("stderr:")
        print(files.stderr)

        if files.exitCode != 0:
            raise RuntimeError(
                f"Could not list repository files:\n"
                f"{files.stderr}"
            )

        # ----------------------------------------
        # Install requirements
        # ----------------------------------------

        print("=== Installing requirements ===")

        result = await run_command(
            sandbox,
            "python3",
            [
                "-m",
                "pip",
                "install",
                "-r",
                f"{REPO_PATH}/requirements.txt",
            ],
        )

        print("Exit code:", result.exitCode)

        print("stdout:")
        print(result.stdout)

        print("stderr:")
        print(result.stderr)

        if result.exitCode != 0:
            raise RuntimeError(
                f"Installing requirements failed:\n"
                f"{result.stderr}"
            )

        # ----------------------------------------
        # Run tests
        # ----------------------------------------

        print("=== Running repository tests ===")

        result = await run_command(
            sandbox,
            "python3",
            [
                "-m",
                "pytest",
                REPO_PATH,
                "-v",
            ],
        )

        print("=== Test result ===")

        print("Exit code:", result.exitCode)

        print("stdout:")
        print(result.stdout)

        print("stderr:")
        print(result.stderr)

    finally:
        print("=== Cleaning up sandbox ===")
        await sandbox.kill()


if __name__ == "__main__":
    asyncio.run(main())
    