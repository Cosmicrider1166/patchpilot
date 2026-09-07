import asyncio

from solari import (
    create_sandbox,
    run_command,
    run_tests,
    read_file,
    write_file,
    parse_test_result,
    generate_repair,
    extract_code_block,
)


REPO_URL = "https://github.com/Cosmicrider1166/patchpilot-demo.git"
REPO_PATH = "/work/repo"
TARGET_FILE = "/work/repo/calculator.py"


async def read_git_project(sandbox):
    """
    Read files tracked by Git from the cloned repository.

    This avoids reading the .git directory and other generated files.
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
            f"Could not list Git files:\n{result.stderr}"
        )

    files = [
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip()
    ]

    project = {}

    for relative_path in files:
        full_path = f"{REPO_PATH}/{relative_path}"

        try:
            content = await read_file(
                sandbox,
                full_path,
            )
            project[full_path] = content

        except Exception as e:
            print(
                f"Could not read {full_path}: {e}"
            )

    return project


def build_github_repair_prompt(
    project,
    test_result,
):
    """
    Build the prompt sent to Claude.
    """

    prompt_parts = [
        "You are a Python debugging assistant.",
        "",
        "You are debugging a GitHub repository inside a sandbox.",
        "",
        "The repository contains a failing test.",
        "",
        "PROJECT FILES:",
    ]

    for file_path, content in project.items():
        prompt_parts.append("")
        prompt_parts.append(
            f"--- {file_path} ---"
        )
        prompt_parts.append(content)

    prompt_parts.extend(
        [
            "",
            "TEST FAILURE:",
            "",
            f"Exit code: {test_result['exit_code']}",
            "",
            "Pytest output:",
            test_result["stdout"],
        ]
    )

    if test_result["stderr"]:
        prompt_parts.extend(
            [
                "",
                "Pytest stderr:",
                test_result["stderr"],
            ]
        )

    prompt_parts.extend(
        [
            "",
            "TASK:",
            "Find the cause of the failing test.",
            "",
            "The tests must NOT be modified.",
            "",
            "Return ONLY the corrected contents of the source file "
            "that needs to be fixed.",
            "",
            "Put the corrected source code inside a Python code block.",
        ]
    )

    return "\n".join(prompt_parts)


async def main():
    client, sandbox, ctx = await create_sandbox()

    try:
        # ----------------------------------------
        # 1. Create sandbox
        # ----------------------------------------

        print("=== Sandbox created ===")
        print("Sandbox ready")

        # ----------------------------------------
        # 2. Clone GitHub repository
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
        # 3. Read repository
        # ----------------------------------------

        print("=== Reading repository ===")

        project = await read_git_project(sandbox)

        for file_path, content in project.items():
            print()
            print(f"--- {file_path} ---")
            print(content)

        # ----------------------------------------
        # 4. Install requirements
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
        # 5. Run tests before repair
        # ----------------------------------------

        print("=== Running tests before repair ===")

        result = await run_tests(
            sandbox,
            f"{REPO_PATH}/test_calculator.py",
        )

        print("=== Initial test result ===")

        print("Exit code:", result.exitCode)
        print("stdout:")
        print(result.stdout)
        print("stderr:")
        print(result.stderr)

        test_result = parse_test_result(result)

        print("Tests passed:", test_result["passed"])

        if test_result["passed"]:
            raise RuntimeError(
                "The demo repository is expected to fail "
                "before the repair."
            )

        # ----------------------------------------
        # 6. Build Claude repair prompt
        # ----------------------------------------

        print("=== Building Claude repair prompt ===")

        repair_prompt = build_github_repair_prompt(
            project,
            test_result,
        )

        print(repair_prompt)

        # ----------------------------------------
        # 7. Ask Claude to repair the code
        # ----------------------------------------

        print("=== Asking Claude to diagnose and repair ===")

        claude_response = await generate_repair(
            repair_prompt
        )

        print("=== Claude response ===")
        print(claude_response)

        # ----------------------------------------
        # 8. Extract corrected code
        # ----------------------------------------

        print("=== Extracting corrected code ===")

        fixed_code = extract_code_block(
            claude_response
        )

        print("=== Corrected code ===")
        print(fixed_code)

        # ----------------------------------------
        # 9. Apply Claude's fix
        # ----------------------------------------

        print("=== Applying Claude's fix ===")

        await write_file(
            sandbox,
            TARGET_FILE,
            fixed_code,
        )

        # ----------------------------------------
        # 10. Read modified file
        # ----------------------------------------

        print("=== Modified calculator.py ===")

        modified_code = await read_file(
            sandbox,
            TARGET_FILE,
        )

        print(modified_code)

        # ----------------------------------------
        # 11. Run tests after repair
        # ----------------------------------------

        print("=== Running tests after repair ===")

        result = await run_tests(
            sandbox,
            f"{REPO_PATH}/test_calculator.py",
        )

        print("=== Final test result ===")

        print("Exit code:", result.exitCode)

        print("stdout:")
        print(result.stdout)

        print("stderr:")
        print(result.stderr)

        final_test_result = parse_test_result(
            result
        )

        print("=== Final status ===")

        print(
            "Tests passed:",
            final_test_result["passed"],
        )

        if final_test_result["passed"]:
            print(
                "SUCCESS: Claude repaired the repository."
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
    