import asyncio
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
BRANCH_NAME = "patchpilot/fix-test-add"

COMMIT_AUTHOR = "PatchPilot"
COMMIT_EMAIL = "patchpilot@example.com"
COMMIT_MESSAGE = "Fix failing add test"


async def read_git_project(sandbox):
    """Read files tracked by Git."""

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
    """Build Claude's repair prompt."""

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
            "Identify the root cause of the failing test.",
            "Identify the source file that needs to change.",
            "Do not modify any test files.",
            "",
            "Return exactly:",
            "",
            "FILE: relative/path/to/file.py",
            "",
            "```python",
            "corrected source code",
            "```",
        ]
    )

    return "\n".join(prompt_parts)


def parse_claude_repair(response):
    """Parse Claude's selected file and corrected code."""

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
            "Claude response did not contain a code block."
        )

    return {
        "file": file_path,
        "content": code_match.group(1).strip(),
    }


def validate_repair_path(file_path):
    """Prevent Claude from modifying files outside the repo."""

    normalized = file_path.replace("\\", "/").strip()

    if normalized.startswith("/"):
        raise ValueError(
            "Claude returned an absolute path."
        )

    if normalized.startswith("../"):
        raise ValueError(
            "Claude returned an unsafe path."
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

        await sandbox.git.clone(
            REPO_URL,
            path=REPO_PATH,
        )

        print("Repository cloned.")

        # ----------------------------------------
        # 2. Create PatchPilot branch
        # ----------------------------------------

        print("=== Creating PatchPilot branch ===")

        await sandbox.git.checkout(
            BRANCH_NAME,
            cwd=REPO_PATH,
            create=True,
        )

        status = await sandbox.git.status(
            REPO_PATH
        )

        print("Current branch:", status.branch)
        print("Working tree clean:", status.clean)

        if status.branch != BRANCH_NAME:
            raise RuntimeError(
                f"Expected branch {BRANCH_NAME}, "
                f"got {status.branch}"
            )

        # ----------------------------------------
        # 3. Read repository
        # ----------------------------------------

        print("=== Reading repository ===")

        project = await read_git_project(
            sandbox
        )

        for file_path in project:
            print("Found:", file_path)

        # ----------------------------------------
        # 4. Install dependencies
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

        if result.exitCode != 0:
            raise RuntimeError(
                f"Installing requirements failed:\n"
                f"{result.stderr}"
            )

        # ----------------------------------------
        # 5. Run initial tests
        # ----------------------------------------

        print("=== Running initial tests ===")

        result = await run_tests(
            sandbox,
            f"{REPO_PATH}/test_calculator.py",
        )

        test_result = parse_test_result(
            result
        )

        print(
            "Initial tests passed:",
            test_result["passed"],
        )

        print(
            "Initial exit code:",
            test_result["exit_code"],
        )

        if test_result["passed"]:
            raise RuntimeError(
                "Expected the demo test to fail."
            )

        # ----------------------------------------
        # 6. Ask Claude for repair
        # ----------------------------------------

        print("=== Asking Claude for repair ===")

        repair_prompt = build_repair_prompt(
            project,
            test_result,
        )

        claude_response = await generate_repair(
            repair_prompt
        )

        print("=== Claude response ===")
        print(claude_response)

        # ----------------------------------------
        # 7. Parse Claude repair
        # ----------------------------------------

        repair = parse_claude_repair(
            claude_response
        )

        repair_file = validate_repair_path(
            repair["file"]
        )

        print(
            "File selected by Claude:",
            repair_file,
        )

        # ----------------------------------------
        # 8. Protect test files
        # ----------------------------------------

        if (
            repair_file.startswith("test_")
            or repair_file.endswith("_test.py")
        ):
            raise ValueError(
                "Claude attempted to modify a test file."
            )

        repair_path = (
            f"{REPO_PATH}/{repair_file}"
        )

        # ----------------------------------------
        # 9. Apply repair
        # ----------------------------------------

        print("=== Applying repair ===")

        await write_file(
            sandbox,
            repair_path,
            repair["content"],
        )

        print("Modified source:")

        modified_code = await read_file(
            sandbox,
            repair_path,
        )

        print(modified_code)

        # ----------------------------------------
        # 10. Run tests after repair
        # ----------------------------------------

        print("=== Running tests after repair ===")

        result = await run_tests(
            sandbox,
            f"{REPO_PATH}/test_calculator.py",
        )

        final_result = parse_test_result(
            result
        )

        print("Final exit code:", result.exitCode)

        print("stdout:")
        print(result.stdout)

        print("stderr:")
        print(result.stderr)

        print(
            "Tests passed:",
            final_result["passed"],
        )

        if not final_result["passed"]:
            raise RuntimeError(
                "Tests still fail after Claude's repair."
            )

        print("Tests passed successfully.")

        # ----------------------------------------
        # 11. Check Git status
        # ----------------------------------------

        print("=== Git status before commit ===")

        status = await sandbox.git.status(
            REPO_PATH
        )

        print("Branch:", status.branch)
        print("Clean:", status.clean)
        print("Modified:", status.modified)
        print("Untracked:", status.untracked)

        if status.clean:
            raise RuntimeError(
                "Expected a modified file before commit."
            )

        # ----------------------------------------
        # 12. Stage the repair
        # ----------------------------------------

        print("=== Staging repair ===")

        await sandbox.git.add(
            ["."],
            cwd=REPO_PATH,
        )

        status = await sandbox.git.status(
            REPO_PATH
        )

        print("Staged:", status.staged)
        print("Modified:", status.modified)

        if not status.staged:
            raise RuntimeError(
                "No files were staged."
            )

        # ----------------------------------------
        # 13. Create commit
        # ----------------------------------------

        print("=== Creating commit ===")

        commit_result = await sandbox.git.commit(
            COMMIT_MESSAGE,
            cwd=REPO_PATH,
            author=COMMIT_AUTHOR,
            email=COMMIT_EMAIL,
        )

        print("Commit result:", commit_result)

        if isinstance(commit_result, dict):
            commit_hash = (
                commit_result.get("hash")
                or commit_result.get("commitHash")
                or commit_result.get("sha")
            )
        else:
            commit_hash = getattr(
                commit_result,
                "hash",
                None,
            )

        if commit_hash:
            print(
                "Commit hash:",
                commit_hash,
            )
        else:
            print(
                "Commit created successfully."
            )

        # ----------------------------------------
        # 14. Verify final Git status
        # ----------------------------------------

        print("=== Final Git status ===")

        status = await sandbox.git.status(
            REPO_PATH
        )

        print("Branch:", status.branch)
        print("Clean:", status.clean)
        print("Ahead:", status.ahead)
        print("Behind:", status.behind)

        if not status.clean:
            raise RuntimeError(
                "Working tree is not clean after commit."
            )

        # ----------------------------------------
        # 15. Show Git log
        # ----------------------------------------

        print("=== Git log ===")

        commits = await sandbox.git.log(
            cwd=REPO_PATH,
            max_count=2,
        )

        for commit in commits:
            if isinstance(commit, dict):
                commit_hash = (
                    commit.get("hash")
                    or commit.get("sha")
                    or commit.get("commitHash")
                )

                message = (
                    commit.get("message")
                    or commit.get("subject")
                    or ""
                )
            else:
                commit_hash = getattr(
                    commit,
                    "hash",
                    None,
                )

                message = getattr(
                    commit,
                    "message",
                    "",
                )

            print(
                commit_hash,
                "|",
                message,
            )

        print()
        print(
            "SUCCESS: Repair committed to PatchPilot branch."
        )

    finally:
        print("=== Cleaning up sandbox ===")
        await sandbox.kill()


if __name__ == "__main__":
    asyncio.run(main())