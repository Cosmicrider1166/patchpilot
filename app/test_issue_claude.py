import asyncio

from agent import (
    generate_repair,
    parse_repair_response,
    validate_repair_target,
)

from issues import (
    get_issue,
    build_issue_repair_prompt,
)

from solari import (
    create_sandbox,
    run_command,
    run_tests,
    read_file,
    parse_test_result,
)


REPO_OWNER = "Cosmicrider1166"
REPO_NAME = "patchpilot-demo"

ISSUE_NUMBER = 4

REPO_URL = (
    f"https://github.com/"
    f"{REPO_OWNER}/{REPO_NAME}.git"
)

REPO_PATH = "/work/patchpilot"


async def read_project(sandbox):
    """
    Read all Git-tracked project files.
    """

    result = await run_command(
        sandbox,
        "git",
        [
            "-C",
            REPO_PATH,
            "ls-files",
        ],
    )

    if result.exitCode != 0:
        raise RuntimeError(
            f"Could not list project files:\n"
            f"{result.stderr}"
        )

    files = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    project = {}

    for relative_path in files:

        full_path = (
            f"{REPO_PATH}/{relative_path}"
        )

        try:
            content = await read_file(
                sandbox,
                full_path,
            )

            project[relative_path] = content

        except Exception as error:

            print(
                f"Could not read {relative_path}: "
                f"{error}"
            )

    return project


async def run_test():
    """
    Test the complete:

    GitHub Issue
        ↓
    Solari repository
        ↓
    Test failure
        ↓
    Claude
        ↓
    Repair selection
    """

    print()
    print("==========================================")
    print("     PATCHPILOT ISSUE → CLAUDE TEST")
    print("==========================================")
    print()

    # --------------------------------------------------------
    # 1. Read GitHub Issue
    # --------------------------------------------------------

    print("=== Reading GitHub Issue ===")

    issue = get_issue(
        REPO_OWNER,
        REPO_NAME,
        ISSUE_NUMBER,
    )

    print(
        "Issue:",
        f"#{issue['number']}",
    )

    print(
        "Title:",
        issue["title"],
    )

    # --------------------------------------------------------
    # 2. Create Solari sandbox
    # --------------------------------------------------------

    print()
    print("=== Creating Solari sandbox ===")

    client, sandbox, ctx = await create_sandbox()

    try:

        print(
            "Sandbox created."
        )

        # ----------------------------------------------------
        # 3. Clone repository
        # ----------------------------------------------------

        print()
        print("=== Cloning repository ===")

        await sandbox.git.clone(
            REPO_URL,
            path=REPO_PATH,
        )

        print(
            "Repository cloned."
        )

        # ----------------------------------------------------
        # 4. Read project
        # ----------------------------------------------------

        print()
        print("=== Reading project ===")

        project = await read_project(
            sandbox
        )

        for file_path in project:
            print(
                "Found:",
                file_path,
            )

        # ----------------------------------------------------
        # 5. Install dependencies
        # ----------------------------------------------------

        print()
        print("=== Installing dependencies ===")

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

        if result.exitCode != 0:
            raise RuntimeError(
                "Dependency installation failed:\n"
                f"{result.stderr}"
            )

        print(
            "Dependencies installed."
        )

        # ----------------------------------------------------
        # 6. Run failing tests
        # ----------------------------------------------------

        print()
        print("=== Running tests ===")

        result = await run_tests(
            sandbox,
            f"{REPO_PATH}/test_calculator.py",
        )

        test_result = parse_test_result(
            result
        )

        print(
            "Tests passed:",
            test_result["passed"],
        )

        if test_result["passed"]:
            raise RuntimeError(
                "Expected the demo repository "
                "to have a failing test."
            )

        print(
            "Test failure detected."
        )

        # ----------------------------------------------------
        # 7. Build Issue + repository + failure prompt
        # ----------------------------------------------------

        print()
        print(
            "=== Building Issue + Test Prompt ==="
        )

        prompt = build_issue_repair_prompt(
            issue,
            project,
            test_result,
        )

        print(
            "Prompt created."
        )

        # ----------------------------------------------------
        # 8. Send to Claude
        # ----------------------------------------------------

        print()
        print("=== Asking Claude for repair ===")

        response = await generate_repair(
            prompt
        )

        print(
            "Claude response received."
        )

        print()
        print("=== Claude Response ===")
        print(response)

        # ----------------------------------------------------
        # 9. Parse Claude response
        # ----------------------------------------------------

        print()
        print("=== Parsing Claude Response ===")

        repair = parse_repair_response(
            response
        )

        repair_file = validate_repair_target(
            repair["file"]
        )

        print(
            "Claude selected:",
            repair_file,
        )

        print()
        print(
            "SUCCESS: GitHub Issue successfully "
            "reached Claude."
        )

    finally:

        print()
        print(
            "=== Cleaning up Solari sandbox ==="
        )

        await sandbox.kill()


def main():
    asyncio.run(
        run_test()
    )


if __name__ == "__main__":
    main()
    