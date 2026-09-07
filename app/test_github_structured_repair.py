import asyncio
import json
import re

from solari import (
    create_sandbox,
    run_command,
    run_tests,
    read_file,
    write_file,
    parse_test_result,
    generate_repair,
)


REPO_URL = "https://github.com/Cosmicrider1166/patchpilot-demo.git"
REPO_PATH = "/work/repo"


async def read_git_project(sandbox):
    """Read source files tracked by Git."""

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
            f"Could not list Git files:\n{result.stderr}"
        )

    files = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    project = {}

    for relative_path in files:
        # Only send text/source files to Claude.
        if relative_path.startswith(".git/"):
            continue

        full_path = f"{REPO_PATH}/{relative_path}"

        try:
            content = await read_file(
                sandbox,
                full_path,
            )

            project[relative_path] = content

        except Exception as e:
            print(
                f"Could not read {full_path}: {e}"
            )

    return project


def build_repair_prompt(project, test_result):
    """Build a structured repair request for Claude."""

    prompt_parts = [
        "You are an autonomous Python debugging agent.",
        "",
        "You are debugging a GitHub repository inside a sandbox.",
        "A test is failing.",
        "",
        "PROJECT FILES:",
    ]

    for file_path, content in project.items():
        prompt_parts.extend(
            [
                "",
                f"--- {file_path} ---",
                content,
            ]
        )

    prompt_parts.extend(
        [
            "",
            "TEST FAILURE:",
            f"Exit code: {test_result['exit_code']}",
            "",
            test_result["stdout"],
            "",
            "TASK:",
            "1. Identify the root cause of the failing test.",
            "2. Identify the source file that must be changed.",
            "3. Do not modify any test files.",
            "4. Return the corrected contents of ONLY the source file "
            "that needs to be changed.",
            "",
            "Your response MUST use exactly this format:",
            "",
            "FILE: relative/path/to/file.py",
            "",
            "```python",
            "corrected source code",
            "```",
            "",
            "Do not include any other files.",
        ]
    )

    return "\n".join(prompt_parts)


def parse_claude_repair(response):
    """
    Extract the file path and corrected source code
    from Claude's structured response.
    """

    file_match = re.search(
        r"FILE:\s*(.+)",
        response,
        re.IGNORECASE,
    )

    if not file_match:
        raise ValueError(
            "Claude response did not contain a FILE line."
        )

    file_path = file_match.group(1).strip()

    code_match = re.search(
        r"```(?:python)?\s*(.*?)```",
        response,
        re.DOTALL | re.IGNORECASE,
    )

    if not code_match:
        raise ValueError(
            "Claude response did not contain a Python code block."
        )

    code = code_match.group(1).strip()

    return {
        "file": file_path,
        "content": code,
    }


def validate_repair_path(file_path):
    """
    Make sure Claude can only modify files inside
    the cloned repository.
    """

    normalized = file_path.replace("\\", "/").strip()

    if normalized.startswith("/"):
        raise ValueError(
            "Claude returned an absolute path."
        )

    if normalized.startswith("../"):
        raise ValueError(
            "Claude returned a path outside the repository."
        )

    if "/../" in normalized:
        raise ValueError(
            "Claude returned an unsafe path."
        )

    if normalized == "..":
        raise ValueError(
            "Claude returned an unsafe path."
        )

    return normalized


async def main():
    client, sandbox, ctx = await create_sandbox()

    try:
        # ----------------------------------------
        # 1. Clone repository
        # ----------------------------------------

        print("=== Cloning repository ===")

        result = await run_command(
            sandbox,
            "git",
            [
                "clone",
                REPO_URL,
                REPO_PATH,
            ],
        )

        if result.exitCode != 0:
            raise RuntimeError(
                f"Git clone failed:\n{result.stderr}"
            )

        print("Repository cloned successfully.")

        # ----------------------------------------
        # 2. Read project
        # ----------------------------------------

        print("=== Reading repository ===")

        project = await read_git_project(sandbox)

        for file_path in project:
            print("Found:", file_path)

        # ----------------------------------------
        # 3. Install dependencies
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

        if result.exitCode != 0:
            raise RuntimeError(
                f"Installing requirements failed:\n"
                f"{result.stderr}"
            )

        print("Requirements installed.")

        # ----------------------------------------
        # 4. Run initial tests
        # ----------------------------------------

        print("=== Running initial tests ===")

        result = await run_tests(
            sandbox,
            f"{REPO_PATH}/test_calculator.py",
        )

        test_result = parse_test_result(result)

        print("Initial tests passed:", test_result["passed"])
        print("Initial exit code:", test_result["exit_code"])

        if test_result["passed"]:
            raise RuntimeError(
                "Expected the demo test to fail."
            )

        # ----------------------------------------
        # 5. Build Claude prompt
        # ----------------------------------------

        print("=== Building repair prompt ===")

        repair_prompt = build_repair_prompt(
            project,
            test_result,
        )

        # ----------------------------------------
        # 6. Ask Claude for repair
        # ----------------------------------------

        print("=== Asking Claude for repair ===")

        claude_response = await generate_repair(
            repair_prompt
        )

        print("=== Claude response ===")
        print(claude_response)

        # ----------------------------------------
        # 7. Parse Claude response
        # ----------------------------------------

        print("=== Parsing Claude repair ===")

        repair = parse_claude_repair(
            claude_response
        )

        repair_file = validate_repair_path(
            repair["file"]
        )

        repair_path = (
            f"{REPO_PATH}/{repair_file}"
        )

        print("File selected by Claude:", repair_file)

        # ----------------------------------------
        # 8. Prevent test modification
        # ----------------------------------------

        if (
            repair_file.startswith("test_")
            or repair_file.endswith("_test.py")
        ):
            raise ValueError(
                "Claude attempted to modify a test file."
            )

        # ----------------------------------------
        # 9. Apply repair
        # ----------------------------------------

        print("=== Applying Claude repair ===")

        await write_file(
            sandbox,
            repair_path,
            repair["content"],
        )

        # ----------------------------------------
        # 10. Show modified file
        # ----------------------------------------

        print("=== Modified file ===")

        modified_code = await read_file(
            sandbox,
            repair_path,
        )

        print(modified_code)

        # ----------------------------------------
        # 11. Inspect Git diff
        # ----------------------------------------

        print("=== Git diff ===")

        result = await run_command(
            sandbox,
            "git",
            [
                "-C",
                REPO_PATH,
                "diff",
            ],
        )

        print(result.stdout)

        if result.exitCode != 0:
            raise RuntimeError(
                f"git diff failed:\n{result.stderr}"
            )

        # ----------------------------------------
        # 12. Run tests again
        # ----------------------------------------

        print("=== Running tests after repair ===")

        result = await run_tests(
            sandbox,
            f"{REPO_PATH}/test_calculator.py",
        )

        final_test_result = parse_test_result(
            result
        )

        print("=== Final test result ===")

        print(
            "Tests passed:",
            final_test_result["passed"],
        )

        print(
            "Exit code:",
            final_test_result["exit_code"],
        )

        print(result.stdout)

        if final_test_result["passed"]:
            print(
                "SUCCESS: Autonomous repair completed."
            )
        else:
            print(
                "FAILURE: Tests are still failing."
            )

    finally:
        print("=== Cleaning up sandbox ===")
        await sandbox.kill()


if __name__ == "__main__":
    asyncio.run(main())

    