import asyncio

from solari import (
    create_sandbox,
    run_command,
    write_file,
    list_files,
    read_project,
    run_tests,
    parse_test_result,
    build_repair_prompt,
    generate_repair,
    extract_code_block,
)


async def main():
    client, sandbox, ctx = await create_sandbox()

    try:
        print("Sandbox created:", sandbox.sandboxId)

        # ----------------------------------------
        # Create a broken Python application
        # ----------------------------------------

        await write_file(
            sandbox,
            "/work/main.py",
            """
def add(a, b):
    return a - b
""",
        )

        # ----------------------------------------
        # Create tests
        # ----------------------------------------

        await write_file(
            sandbox,
            "/work/test_main.py",
            """
from main import add


def test_add():
    assert add(10, 20) == 30
""",
        )

        print("=== Project created ===")

        # ----------------------------------------
        # Read project source files
        # ----------------------------------------

        print("=== Project source ===")

        project = await read_project(sandbox)

        for file_path, content in project.items():
            print()
            print(f"--- {file_path} ---")
            print(content)

        # ----------------------------------------
        # List project files
        # ----------------------------------------

        print("=== Project files ===")

        files = await list_files(sandbox)

        print("Exit code:", files.exitCode)
        print("stdout:")
        print(files.stdout)

        print("stderr:")
        print(files.stderr)

        # ----------------------------------------
        # Install pytest
        # ----------------------------------------

        print("=== Installing pytest ===")

        result = await run_command(
            sandbox,
            "python3",
            ["-m", "pip", "install", "pytest"],
        )

        print("Exit code:", result.exitCode)

        print("stdout:")
        print(result.stdout)

        print("stderr:")
        print(result.stderr)

        # ----------------------------------------
        # Run pytest
        # ----------------------------------------

        print("=== Running pytest ===")

        result = await run_tests(sandbox)

        # ----------------------------------------
        # Display pytest result
        # ----------------------------------------

        print("=== Pytest result ===")

        print("Exit code:", result.exitCode)

        print("stdout:")
        print(result.stdout)

        print("stderr:")
        print(result.stderr)

        # ----------------------------------------
        # Parse failing test result
        # ----------------------------------------

        test_result = parse_test_result(result)

        print("=== Parsed test result ===")

        print("Tests passed:", test_result["passed"])
        print("Exit code:", test_result["exit_code"])

        print("Failed tests:")

        for failed_test in test_result["failed_tests"]:
            print("  Test:", failed_test["test"])
            print("  File:", failed_test["file"])

        if test_result.get("assertion"):
            print("Assertion:")
            print("  Actual:", test_result["assertion"]["actual"])
            print("  Expected:", test_result["assertion"]["expected"])

        # ----------------------------------------
        # Build repair prompt
        # ----------------------------------------

        print("=== Repair prompt ===")

        repair_prompt = build_repair_prompt(
            project,
            test_result,
        )

        print(repair_prompt)

        # ----------------------------------------
        # Ask Claude to analyze the failure
        # ----------------------------------------

        print("=== Asking Claude to diagnose failure ===")

        claude_response = await generate_repair(
            repair_prompt
        )

        print("=== Claude response ===")
        print(claude_response)

        # ----------------------------------------
        # Extract Claude's proposed code
        # ----------------------------------------

        print("=== Extracting Claude's fix ===")

        fixed_code = extract_code_block(
            claude_response
        )

        print("=== Code extracted from Claude ===")
        print(fixed_code)

        # ----------------------------------------
        # Apply Claude's fix to Solari
        # ----------------------------------------

        print("=== Applying Claude's fix to Solari ===")

        await write_file(
            sandbox,
            "/work/main.py",
            fixed_code,
        )

        # ----------------------------------------
        # Read the modified file
        # ----------------------------------------

        print("=== Modified source ===")

        modified_project = await read_project(sandbox)

        if "/work/main.py" in modified_project:
            print(modified_project["/work/main.py"])

        # ----------------------------------------
        # Run pytest after Claude's fix
        # ----------------------------------------

        print("=== Running pytest after fix ===")

        result = await run_tests(sandbox)

        # ----------------------------------------
        # Display fixed pytest result
        # ----------------------------------------

        print("=== Fixed pytest result ===")

        print("Exit code:", result.exitCode)

        print("stdout:")
        print(result.stdout)

        print("stderr:")
        print(result.stderr)

        # ----------------------------------------
        # Parse fixed test result
        # ----------------------------------------

        fixed_test_result = parse_test_result(result)

        print("=== Parsed fixed test result ===")

        print(
            "Tests passed:",
            fixed_test_result["passed"],
        )

        print(
            "Exit code:",
            fixed_test_result["exit_code"],
        )

        if fixed_test_result["failed_tests"]:
            print("Failed tests:")

            for failed_test in fixed_test_result["failed_tests"]:
                print(
                    "  Test:",
                    failed_test["test"],
                )

                print(
                    "  File:",
                    failed_test["file"],
                )

        if fixed_test_result.get("assertion"):
            print("Assertion:")
            print(
                "  Actual:",
                fixed_test_result["assertion"]["actual"],
            )
            print(
                "  Expected:",
                fixed_test_result["assertion"]["expected"],
            )

    finally:
        # ----------------------------------------
        # Clean up sandbox
        # ----------------------------------------

        await sandbox.kill()


if __name__ == "__main__":
    asyncio.run(main())