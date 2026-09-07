import asyncio
import os
import re

from solari_sandbox import SandboxClient


BASE_URL = "https://api.getsolari.com"


async def create_sandbox():
    client = SandboxClient(
        api_key=os.environ["SOLARI_API_KEY"],
        base_url=BASE_URL,
    )

    sandbox = await client.create(
        template="base",
        timeout_ms=5 * 60_000,
    )

    await sandbox.connect()

    ctx = await sandbox.create_code_context(
        "python"
    )

    return client, sandbox, ctx


async def run_python(
    sandbox,
    ctx,
    code: str,
):
    result = await sandbox.run_code(
        code,
        context_id=ctx,
    )

    return result


async def run_command(
    sandbox,
    command: str,
    args: list[str] | None = None,
    cwd: str | None = None,
):
    result = await sandbox.commands.run(
        command,
        args=args or [],
        cwd=cwd,
    )

    return result


async def write_file(
    sandbox,
    path: str,
    content: str,
):
    await sandbox.files.write(
        path,
        content,
    )


async def read_file(
    sandbox,
    path: str,
):
    return await sandbox.files.read_text(
        path
    )


async def list_files(
    sandbox,
    path: str = "/work",
):
    return await run_command(
        sandbox,
        "find",
        [
            path,
            "-type",
            "f",
        ],
    )


async def read_project(
    sandbox,
    repo_path: str = "/work/patchpilot",
):
    """
    Read all Git-tracked files from a repository.

    Git-tracked files are used so dependency directories,
    generated files, and other untracked sandbox artifacts
    are excluded.

    Returns:
        dict[str, str]:
            Mapping of relative file paths to file contents.
    """

    result = await run_command(
        sandbox,
        "git",
        [
            "-C",
            repo_path,
            "ls-files",
        ],
    )

    if result.exitCode != 0:
        raise RuntimeError(
            "Could not list project files:\n"
            f"{result.stderr}"
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

        full_path = (
            f"{repo_path}/{relative_path}"
        )

        try:

            content = await read_file(
                sandbox,
                full_path,
            )

            project[relative_path] = content

        except Exception:
            raise

    return project


async def run_tests(
    sandbox,
    test_path: str = "/work/test_main.py",
):
    return await run_command(
        sandbox,
        "python3",
        [
            "-m",
            "pytest",
            test_path,
            "-v",
        ],
    )


def parse_test_result(
    result,
    framework="pytest",
):
    """
    Convert a test command result into a common
    PatchPilot test-result structure.

    Supported frameworks:

        pytest
        npm
        maven
        gradle
        go
        cargo
    """

    stdout = result.stdout or ""
    stderr = result.stderr or ""

    output = (
        stdout
        + "\n"
        + stderr
    )

    passed = (
        result.exitCode == 0
    )

    parsed = {
        "passed": passed,
        "exit_code": result.exitCode,
        "stdout": stdout,
        "stderr": stderr,
        "framework": framework,
        "failed_tests": [],
        "assertion": None,
        "summary": {
            "passed": 0,
            "failed": 0,
            "errors": 0,
        },
    }

    # ========================================================
    # pytest
    # ========================================================

    if framework == "pytest":

        failed_tests = re.findall(
            r"FAILED\s+(.+?)::([^\s]+)",
            output,
        )

        for file_path, test_name in failed_tests:

            parsed["failed_tests"].append(
                {
                    "file": file_path,
                    "test": test_name,
                }
            )

        assertion_match = re.search(
            r"E\s+assert\s+(.+?)\s*==\s*(.+?)\s*$",
            output,
            re.MULTILINE,
        )

        if assertion_match:

            parsed["assertion"] = {
                "actual": (
                    assertion_match
                    .group(1)
                    .strip()
                ),
                "expected": (
                    assertion_match
                    .group(2)
                    .strip()
                ),
            }

        passed_match = re.search(
            r"(\d+)\s+passed",
            output,
            re.IGNORECASE,
        )

        failed_match = re.search(
            r"(\d+)\s+failed",
            output,
            re.IGNORECASE,
        )

        error_match = re.search(
            r"(\d+)\s+errors?",
            output,
            re.IGNORECASE,
        )

        if passed_match:

            parsed["summary"]["passed"] = int(
                passed_match.group(1)
            )

        if failed_match:

            parsed["summary"]["failed"] = int(
                failed_match.group(1)
            )

        if error_match:

            parsed["summary"]["errors"] = int(
                error_match.group(1)
            )

    # ========================================================
    # npm / Node.js
    # ========================================================

    elif framework == "npm":

        failed_match = re.findall(
            r"FAIL\s+(.+)",
            output,
            re.IGNORECASE,
        )

        for test_name in failed_match:

            parsed["failed_tests"].append(
                {
                    "file": "",
                    "test": test_name.strip(),
                }
            )

        passed_tests = re.search(
            r"(\d+)\s+(?:passing|passed)",
            output,
            re.IGNORECASE,
        )

        failed_tests_count = re.search(
            r"(\d+)\s+(?:failing|failed)",
            output,
            re.IGNORECASE,
        )

        if passed_tests:

            parsed["summary"]["passed"] = int(
                passed_tests.group(1)
            )

        if failed_tests_count:

            parsed["summary"]["failed"] = int(
                failed_tests_count.group(1)
            )

    # ========================================================
    # Maven
    # ========================================================

    elif framework == "maven":

        tests_match = re.search(
            r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)",
            output,
            re.IGNORECASE,
        )

        if tests_match:

            parsed["summary"]["passed"] = (
                int(tests_match.group(1))
                - int(tests_match.group(2))
                - int(tests_match.group(3))
            )

            parsed["summary"]["failed"] = (
                int(tests_match.group(2))
            )

            parsed["summary"]["errors"] = (
                int(tests_match.group(3))
            )

        failure_matches = re.findall(
            r"\[ERROR\]\s+([A-Za-z0-9_.$]+).*",
            output,
        )

        for test_name in failure_matches:

            parsed["failed_tests"].append(
                {
                    "file": "",
                    "test": test_name.strip(),
                }
            )

    # ========================================================
    # Gradle
    # ========================================================

    elif framework == "gradle":

        failed_matches = re.findall(
            r"FAILED\s+([^\s]+)",
            output,
            re.IGNORECASE,
        )

        for test_name in failed_matches:

            parsed["failed_tests"].append(
                {
                    "file": "",
                    "test": test_name.strip(),
                }
            )

        failed_count = re.search(
            r"(\d+)\s+tests?\s+completed,\s*(\d+)\s+failed",
            output,
            re.IGNORECASE,
        )

        if failed_count:

            total = int(
                failed_count.group(1)
            )

            failed = int(
                failed_count.group(2)
            )

            parsed["summary"]["failed"] = (
                failed
            )

            parsed["summary"]["passed"] = (
                total - failed
            )

    # ========================================================
    # Go
    # ========================================================

    elif framework == "go":

        failed_matches = re.findall(
            r"--- FAIL:\s+(\S+)",
            output,
        )

        for test_name in failed_matches:

            parsed["failed_tests"].append(
                {
                    "file": "",
                    "test": test_name.strip(),
                }
            )

        passed_count = len(
            re.findall(
                r"--- PASS:",
                output,
            )
        )

        failed_count = len(
            failed_matches
        )

        parsed["summary"]["passed"] = (
            passed_count
        )

        parsed["summary"]["failed"] = (
            failed_count
        )

    # ========================================================
    # Rust / Cargo
    # ========================================================

    elif framework == "cargo":

        failed_matches = re.findall(
            r"test\s+([^\s]+)\s+\.\.\.\s+FAILED",
            output,
            re.IGNORECASE,
        )

        passed_matches = re.findall(
            r"test\s+([^\s]+)\s+\.\.\.\s+ok",
            output,
            re.IGNORECASE,
        )

        for test_name in failed_matches:

            parsed["failed_tests"].append(
                {
                    "file": "",
                    "test": test_name.strip(),
                }
            )

        parsed["summary"]["passed"] = (
            len(passed_matches)
        )

        parsed["summary"]["failed"] = (
            len(failed_matches)
        )

    # ========================================================
    # Unknown framework
    # ========================================================

    else:

        if not passed:

            parsed["summary"]["failed"] = 1

    return parsed


def build_repair_prompt(
    project,
    test_result,
):
    prompt_parts = [
        "You are a Python debugging assistant.",
        "",
        "A test in the following project is failing.",
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
        ]
    )

    for failed_test in (
        test_result["failed_tests"]
    ):

        prompt_parts.append(
            f"Failed test: "
            f"{failed_test['test']}"
        )

        prompt_parts.append(
            f"Test file: "
            f"{failed_test['file']}"
        )

    assertion = test_result.get(
        "assertion"
    )

    if assertion:

        prompt_parts.extend(
            [
                "",
                "ASSERTION FAILURE:",
                (
                    "Actual value: "
                    f"{assertion['actual']}"
                ),
                (
                    "Expected value: "
                    f"{assertion['expected']}"
                ),
            ]
        )

    prompt_parts.extend(
        [
            "",
            "TASK:",
            "Determine the cause of the test failure.",
            "Provide the corrected source code.",
            "Do not modify the tests.",
        ]
    )

    return "\n".join(
        prompt_parts
    )


async def generate_repair(
    repair_prompt: str,
):
    process = (
        await asyncio.create_subprocess_exec(
            "claude",
            "-p",
            repair_prompt,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    )

    stdout, stderr = (
        await process.communicate()
    )

    if process.returncode != 0:

        raise RuntimeError(
            "Claude failed with exit code "
            f"{process.returncode}:\n"
            f"{stderr.decode().strip()}"
        )

    return stdout.decode().strip()


def extract_code_block(
    response: str,
):
    match = re.search(
        r"```(?:python)?\s*(.*?)```",
        response,
        re.DOTALL | re.IGNORECASE,
    )

    if not match:

        raise ValueError(
            "Claude response did not contain "
            "a code block."
        )

    return match.group(1).strip()