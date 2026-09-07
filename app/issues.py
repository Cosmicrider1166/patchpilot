import subprocess
import json


def get_issue(
    repo_owner: str,
    repo_name: str,
    issue_number: int,
):
    """
    Retrieve a GitHub Issue using the GitHub CLI.
    """

    command = [
        "gh",
        "issue",
        "view",
        str(issue_number),
        "--repo",
        f"{repo_owner}/{repo_name}",
        "--json",
        "number,title,body",
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if result.returncode != 0:
        raise RuntimeError(
            "Could not retrieve GitHub Issue:\n"
            f"{result.stderr.strip()}"
        )

    issue = json.loads(result.stdout)

    return {
        "number": issue["number"],
        "title": issue["title"],
        "body": issue["body"] or "",
    }


def build_issue_prompt(issue):
    """
    Build the basic instructions from a GitHub Issue.
    """

    return f"""You are an autonomous software debugging agent.

You are working on a GitHub repository inside
an isolated sandbox.

The following GitHub Issue describes the problem
that needs to be fixed.

GitHub Issue #{issue["number"]}

TITLE:
{issue["title"]}

DESCRIPTION:
{issue["body"]}

TASK:

Investigate the repository and determine the
root cause of the issue.

Modify the source code necessary to fix the issue.

Do not modify test files.

After making the repair, the project tests
will be executed to verify your solution.
"""


def build_issue_repair_prompt(
    issue,
    project,
    test_result,
    attempt=1,
    project_type=None,
    language=None,
    test_framework=None,
):
    """
    Build the complete language-aware prompt sent
    to Claude.

    The prompt contains:
    - GitHub Issue
    - Project type
    - Programming language
    - Test framework
    - Relevant repository files
    - Latest test failure
    - Repair attempt number
    - Multi-file repair instructions
    """

    prompt_parts = [
        "You are an autonomous software debugging agent.",
        "",
        "You are working on a GitHub repository inside",
        "an isolated sandbox.",
        "",
        f"REPAIR ATTEMPT: {attempt}",
        "",
    ]

    if project_type:
        prompt_parts.extend(
            [
                "PROJECT TYPE:",
                project_type,
                "",
            ]
        )

    if language:
        prompt_parts.extend(
            [
                "PROGRAMMING LANGUAGE:",
                language,
                "",
            ]
        )

    if test_framework:
        prompt_parts.extend(
            [
                "TEST FRAMEWORK:",
                test_framework,
                "",
            ]
        )

    prompt_parts.extend(
        [
            "A GitHub Issue describes the problem that needs",
            "to be fixed.",
            "",
            f"GitHub Issue #{issue['number']}",
            "",
            "TITLE:",
            issue["title"],
            "",
            "DESCRIPTION:",
            issue["body"],
            "",
            "RELEVANT PROJECT FILES:",
        ]
    )

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
            "LATEST TEST RESULT:",
            "",
            f"Exit code: {test_result['exit_code']}",
            "",
            test_result["stdout"],
        ]
    )

    if test_result.get("stderr"):
        prompt_parts.extend(
            [
                "",
                "STDERR:",
                test_result["stderr"],
            ]
        )

    if test_result.get("failed_tests"):
        prompt_parts.extend(
            [
                "",
                "FAILED TESTS:",
            ]
        )

        for failed_test in test_result[
            "failed_tests"
        ]:
            prompt_parts.append(
                f"- {failed_test['file']}::"
                f"{failed_test['test']}"
            )

    if test_result.get("assertion"):
        assertion = test_result["assertion"]

        prompt_parts.extend(
            [
                "",
                "ASSERTION FAILURE:",
                f"Actual: {assertion['actual']}",
                f"Expected: {assertion['expected']}",
            ]
        )

    prompt_parts.extend(
        [
            "",
            "IMPORTANT:",
            "The repository may have already been modified",
            "by a previous repair attempt.",
            "",
            "Analyze the CURRENT project files and the",
            "LATEST test failure.",
            "",
            "Do not assume that a previous repair was correct.",
            "",
            "Do not modify any test files.",
            "",
            "Only modify the minimum source code necessary",
            "to resolve the GitHub Issue.",
            "",
            "The selected files must be source files,",
            "not test files.",
            "",
            "A repair may require changes to one or more",
            "source files.",
            "",
            "Return ONLY a JSON object with exactly these",
            "fields:",
            "",
            "{",
            '  "explanation": "short explanation of the root cause",',
            '  "changes": [',
            "    {",
            '      "file": "relative/path/to/source/file",',
            '      "code": "complete corrected source code"',
            "    }",
            "  ]",
            "}",
            "",
            "The changes array must contain every source file",
            "that needs to be modified.",
            "",
            "Only include files that actually need changes.",
            "",
            "Do not include test files.",
            "",
            "Do not include unchanged files.",
            "",
            "Each file must contain its complete corrected",
            "source code.",
        ]
    )

    return "\n".join(prompt_parts)

    