import asyncio
import os
import re
import subprocess

from solari import (
    create_sandbox,
    run_command,
    run_tests,
    read_file,
    write_file,
    parse_test_result,
    generate_repair,
)


# ============================================================
# GitHub configuration
# ============================================================

REPO_OWNER = "Cosmicrider1166"
REPO_NAME = "patchpilot-demo"

REPO_URL = (
    f"https://github.com/"
    f"{REPO_OWNER}/{REPO_NAME}.git"
)

REPO_PATH = "/work/repo"

BRANCH_NAME = "patchpilot/fix-test-add-pr"
BASE_BRANCH = "master"

COMMIT_AUTHOR = "PatchPilot"
COMMIT_EMAIL = "patchpilot@example.com"
COMMIT_MESSAGE = "Fix failing add test"

PR_TITLE = "Fix failing add test"

PR_BODY = """## Summary

PatchPilot automatically diagnosed and repaired a failing test.

### What PatchPilot did

- Cloned the repository
- Created a repair branch
- Ran the test suite
- Diagnosed the failing test using Claude
- Applied the source-code repair
- Re-ran the tests
- Committed the repair
- Pushed the repair branch
- Created this pull request

### Test result

All tests pass after the repair.

Generated automatically by PatchPilot.
"""


# ============================================================
# Read Git project
# ============================================================

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


# ============================================================
# Build Claude repair prompt
# ============================================================

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


# ============================================================
# Parse Claude response
# ============================================================

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


# ============================================================
# Validate Claude's selected path
# ============================================================

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


# ============================================================
# Create GitHub Pull Request
# ============================================================

def create_pull_request():
    """Create the GitHub Pull Request using GitHub CLI."""

    print("=== Creating GitHub Pull Request ===")

    command = [
        "gh",
        "pr",
        "create",
        "--repo",
        f"{REPO_OWNER}/{REPO_NAME}",
        "--base",
        BASE_BRANCH,
        "--head",
        BRANCH_NAME,
        "--title",
        PR_TITLE,
        "--body",
        PR_BODY,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if result.returncode != 0:

        error = result.stderr.strip()

        # If a PR already exists, retrieve its URL instead
        if "already exists" in error.lower():
            print(
                "A Pull Request already exists for this branch."
            )

            existing = subprocess.run(
                [
                    "gh",
                    "pr",
                    "view",
                    BRANCH_NAME,
                    "--repo",
                    f"{REPO_OWNER}/{REPO_NAME}",
                    "--json",
                    "url",
                    "--jq",
                    ".url",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            if existing.returncode == 0:
                return existing.stdout.strip()

        raise RuntimeError(
            "GitHub Pull Request creation failed:\n"
            f"{error}"
        )

    pr_url = result.stdout.strip()

    if not pr_url:
        raise RuntimeError(
            "GitHub did not return a Pull Request URL."
        )

    return pr_url


# ============================================================
# Main PatchPilot workflow
# ============================================================

async def main():

    # --------------------------------------------------------
    # 0. Check GitHub token
    # --------------------------------------------------------

    github_token = os.environ.get(
        "GITHUB_TOKEN",
        "",
    ).strip()

    if not github_token:
        raise RuntimeError(
            "GITHUB_TOKEN environment variable is not set."
        )

    # --------------------------------------------------------
    # 1. Create Solari sandbox
    # --------------------------------------------------------

    client, sandbox, ctx = await create_sandbox()

    try:

        # ----------------------------------------------------
        # 2. Clone repository
        # ----------------------------------------------------

        print("=== Cloning repository ===")

        await sandbox.git.clone(
            REPO_URL,
            path=REPO_PATH,
        )

        print("Repository cloned.")

        # ----------------------------------------------------
        # 3. Create PatchPilot branch
        # ----------------------------------------------------

        print("=== Creating PatchPilot branch ===")

        await sandbox.git.checkout(
            BRANCH_NAME,
            cwd=REPO_PATH,
            create=True,
        )

        status = await sandbox.git.status(
            REPO_PATH
        )

        print(
            "Current branch:",
            status.branch,
        )

        print(
            "Working tree clean:",
            status.clean,
        )

        # ----------------------------------------------------
        # 4. Read repository
        # ----------------------------------------------------

        print("=== Reading repository ===")

        project = await read_git_project(
            sandbox
        )

        for file_path in project:
            print("Found:", file_path)

        # ----------------------------------------------------
        # 5. Install requirements
        # ----------------------------------------------------

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
                "Installing requirements failed:\n"
                f"{result.stderr}"
            )

        print("Requirements installed.")

        # ----------------------------------------------------
        # 6. Run initial tests
        # ----------------------------------------------------

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

        if test_result["passed"]:
            raise RuntimeError(
                "Expected the initial test to fail."
            )

        # ----------------------------------------------------
        # 7. Ask Claude to repair
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 8. Parse Claude repair
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 9. Protect test files
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 10. Apply repair
        # ----------------------------------------------------

        print("=== Applying repair ===")

        await write_file(
            sandbox,
            repair_path,
            repair["content"],
        )

        # ----------------------------------------------------
        # 11. Run tests after repair
        # ----------------------------------------------------

        print(
            "=== Running tests after repair ==="
        )

        result = await run_tests(
            sandbox,
            f"{REPO_PATH}/test_calculator.py",
        )

        final_result = parse_test_result(
            result
        )

        print(
            "Tests passed:",
            final_result["passed"],
        )

        if not final_result["passed"]:
            raise RuntimeError(
                "Tests still fail after Claude's repair."
            )

        print(
            "Tests passed successfully."
        )

        # ----------------------------------------------------
        # 12. Check Git status
        # ----------------------------------------------------

        print(
            "=== Git status before commit ==="
        )

        status = await sandbox.git.status(
            REPO_PATH
        )

        print(
            "Branch:",
            status.branch,
        )

        print(
            "Clean:",
            status.clean,
        )

        print(
            "Modified:",
            status.modified,
        )

        print(
            "Untracked:",
            status.untracked,
        )

        # ----------------------------------------------------
        # 13. Stage repair
        # ----------------------------------------------------

        print("=== Staging repair ===")

        await sandbox.git.add(
            ["."],
            cwd=REPO_PATH,
        )

        # ----------------------------------------------------
        # 14. Commit repair
        # ----------------------------------------------------

        print("=== Creating commit ===")

        commit_result = await sandbox.git.commit(
            COMMIT_MESSAGE,
            cwd=REPO_PATH,
            author=COMMIT_AUTHOR,
            email=COMMIT_EMAIL,
        )

        print(
            "Commit result:",
            commit_result,
        )

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

        # ----------------------------------------------------
        # 15. Verify clean tree
        # ----------------------------------------------------

        print(
            "=== Git status after commit ==="
        )

        status = await sandbox.git.status(
            REPO_PATH
        )

        print(
            "Branch:",
            status.branch,
        )

        print(
            "Clean:",
            status.clean,
        )

        print(
            "Ahead:",
            status.ahead,
        )

        print(
            "Behind:",
            status.behind,
        )

        if not status.clean:
            raise RuntimeError(
                "Working tree is not clean after commit."
            )

        # ----------------------------------------------------
        # 16. Push branch
        # ----------------------------------------------------

        print(
            "=== Pushing branch to GitHub ==="
        )

        await sandbox.git.push(
            cwd=REPO_PATH,
            branch=BRANCH_NAME,
            username=REPO_OWNER,
            password=github_token,
        )

        print(
            "Branch pushed successfully."
        )

    finally:

        # ----------------------------------------------------
        # 17. Clean up sandbox
        # ----------------------------------------------------

        print(
            "=== Cleaning up sandbox ==="
        )

        await sandbox.kill()

    # --------------------------------------------------------
    # 18. Create Pull Request
    # --------------------------------------------------------

    pr_url = create_pull_request()

    print()
    print(
        "=========================================="
    )

    print(
        "SUCCESS: Pull Request created."
    )

    print(
        "PR URL:",
        pr_url,
    )

    print(
        "=========================================="
    )


if __name__ == "__main__":
    asyncio.run(main())
