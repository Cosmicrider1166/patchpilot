import asyncio
import json
import posixpath


MAX_REPAIR_CODE_CHARS = 100000


async def generate_repair(repair_prompt: str):
    """
    Send a debugging prompt to Claude Code and require
    a validated structured JSON repair response.
    """

    schema = {
        "type": "object",
        "properties": {
            "explanation": {
                "type": "string",
            },
            "changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "file": {
                            "type": "string",
                        },
                        "code": {
                            "type": "string",
                        },
                    },
                    "required": [
                        "file",
                        "code",
                    ],
                    "additionalProperties": False,
                },
                "minItems": 1,
            },
        },
        "required": [
            "explanation",
            "changes",
        ],
        "additionalProperties": False,
    }

    schema_json = json.dumps(schema)

    process = await asyncio.create_subprocess_exec(
        "claude",
        "-p",
        repair_prompt,
        "--output-format",
        "json",
        "--json-schema",
        schema_json,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        raise RuntimeError(
            f"Claude failed with exit code "
            f"{process.returncode}:\n"
            f"{stderr.decode().strip()}"
        )

    return stdout.decode().strip()


def build_repair_prompt(
    project,
    test_result,
    project_type=None,
):
    """
    Build a language-agnostic repair prompt.
    """

    prompt_parts = [
        "You are an autonomous software debugging agent.",
        "",
        "You are working on a GitHub repository inside",
        "an isolated sandbox.",
        "",
        "A test is failing.",
    ]

    if project_type:
        prompt_parts.extend(
            [
                "",
                f"PROJECT TYPE: {project_type}",
            ]
        )

    prompt_parts.extend(
        [
            "",
            "PROJECT FILES:",
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
            "TEST FAILURE:",
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
            "TASK:",
            "Identify the root cause of the failing test.",
            "Identify the source file or files that need",
            "to change.",
            "Do not modify any test files.",
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
        ]
    )

    return "\n".join(prompt_parts)


def build_issue_repair_prompt(
    issue,
    project,
    test_result,
    attempt=1,
    project_type=None,
):
    """
    Build the complete language-agnostic prompt
    sent to Claude.
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
                f"PROJECT TYPE: {project_type}",
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


def parse_repair_response(response: str):
    """
    Parse Claude Code's structured repair response.

    Expected structure:

        {
            "explanation": "...",
            "changes": [
                {
                    "file": "relative/path",
                    "code": "complete source code"
                }
            ]
        }
    """

    try:
        outer = json.loads(response)

    except json.JSONDecodeError as error:
        raise ValueError(
            "Claude response was not valid JSON."
        ) from error

    if not isinstance(
        outer,
        dict,
    ):
        raise ValueError(
            "Claude response must be a JSON object."
        )

    if isinstance(
        outer.get("structured_output"),
        dict,
    ):

        repair = outer[
            "structured_output"
        ]

    elif isinstance(
        outer.get("result"),
        str,
    ):

        try:
            repair = json.loads(
                outer["result"]
            )

        except json.JSONDecodeError as error:
            raise ValueError(
                "Claude result field did not contain "
                "valid JSON."
            ) from error

    else:

        repair = outer

    if not isinstance(
        repair,
        dict,
    ):
        raise ValueError(
            "Claude structured response must be an object."
        )

    if "explanation" not in repair:
        raise ValueError(
            "Claude response is missing "
            "required field: explanation"
        )

    if "changes" not in repair:
        raise ValueError(
            "Claude response is missing "
            "required field: changes"
        )

    allowed_repair_fields = {
        "explanation",
        "changes",
    }

    unexpected_repair_fields = (
        set(repair.keys())
        - allowed_repair_fields
    )

    if unexpected_repair_fields:
        fields = ", ".join(
            sorted(unexpected_repair_fields)
        )

        raise ValueError(
            "Claude response contains unexpected "
            f"field(s): {fields}"
        )

    if not isinstance(
        repair["explanation"],
        str,
    ):
        raise ValueError(
            "Claude response field 'explanation' "
            "must be a string."
        )

    explanation = repair[
        "explanation"
    ].strip()

    if not explanation:
        raise ValueError(
            "Claude response contains an empty "
            "explanation."
        )

    if not isinstance(
        repair["changes"],
        list,
    ):
        raise ValueError(
            "Claude response field 'changes' "
            "must be an array."
        )

    if not repair["changes"]:
        raise ValueError(
            "Claude response must contain "
            "at least one change."
        )

    changes = []
    seen_files = set()

    for index, change in enumerate(
        repair["changes"],
        start=1,
    ):

        if not isinstance(
            change,
            dict,
        ):
            raise ValueError(
                f"Claude change #{index} "
                "must be an object."
            )

        required_change_fields = {
            "file",
            "code",
        }

        unexpected_change_fields = (
            set(change.keys())
            - required_change_fields
        )

        if unexpected_change_fields:
            fields = ", ".join(
                sorted(unexpected_change_fields)
            )

            raise ValueError(
                f"Claude change #{index} contains "
                f"unexpected field(s): {fields}"
            )

        if "file" not in change:
            raise ValueError(
                f"Claude change #{index} "
                "is missing required field: file"
            )

        if "code" not in change:
            raise ValueError(
                f"Claude change #{index} "
                "is missing required field: code"
            )

        if not isinstance(
            change["file"],
            str,
        ):
            raise ValueError(
                f"Claude change #{index} "
                "field 'file' must be a string."
            )

        if not isinstance(
            change["code"],
            str,
        ):
            raise ValueError(
                f"Claude change #{index} "
                "field 'code' must be a string."
            )

        file_path = change["file"].strip()
        code = change["code"]

        if not file_path:
            raise ValueError(
                f"Claude change #{index} "
                "contains an empty file path."
            )

        if not code.strip():
            raise ValueError(
                f"Claude change #{index} "
                "contains empty source code."
            )

        if len(code) > MAX_REPAIR_CODE_CHARS:
            raise ValueError(
                f"Claude change #{index} "
                f"exceeds the maximum allowed source "
                f"size of {MAX_REPAIR_CODE_CHARS} characters."
            )

        normalized_path = file_path.replace(
            "\\",
            "/",
        )

        if normalized_path in seen_files:
            raise ValueError(
                "Claude response contains duplicate "
                f"repair file: {file_path}"
            )

        seen_files.add(
            normalized_path
        )

        changes.append(
            {
                "file": file_path,
                "code": code,
            }
        )

    return {
        "explanation": explanation,
        "changes": changes,
    }


def validate_repair_path(file_path: str):
    """
    Make sure Claude can only select a safe,
    repository-relative file path.
    """

    if not isinstance(
        file_path,
        str,
    ):
        raise ValueError(
            "Claude returned a non-string file path."
        )

    normalized = file_path.replace(
        "\\",
        "/",
    ).strip()

    if not normalized:
        raise ValueError(
            "Claude returned an empty file path."
        )

    if normalized.startswith("/"):
        raise ValueError(
            "Claude returned an absolute path."
        )

    if normalized.startswith("//"):
        raise ValueError(
            "Claude returned an absolute UNC path."
        )

    if (
        len(normalized) >= 2
        and normalized[1] == ":"
        and normalized[0].isalpha()
    ):
        raise ValueError(
            "Claude returned a Windows absolute path."
        )

    if normalized.endswith("/"):
        raise ValueError(
            "Claude returned a directory path."
        )

    path_parts = normalized.split("/")

    if any(
        part in {".", ".."}
        for part in path_parts
    ):
        raise ValueError(
            "Claude returned an unsafe path."
        )

    normalized_path = posixpath.normpath(
        normalized
    )

    if normalized_path in {
        "",
        ".",
        "..",
    }:
        raise ValueError(
            "Claude returned an invalid path."
        )

    if normalized_path.startswith("../"):
        raise ValueError(
            "Claude returned an unsafe path."
        )

    if normalized_path.startswith("/"):
        raise ValueError(
            "Claude returned an absolute path."
        )

    return normalized_path


def validate_repair_target(file_path: str):
    """
    Prevent Claude from modifying test files
    across supported languages.
    """

    normalized = validate_repair_path(
        file_path
    )

    filename = normalized.split("/")[-1]

    test_patterns = (
        filename.startswith("test_")
        or filename.endswith("_test.py")
        or filename.endswith(".test.js")
        or filename.endswith(".spec.js")
        or filename.endswith("Test.java")
        or filename.startswith("Test")
        or filename.endswith("_test.go")
        or filename.endswith("_test.rs")
    )

    if test_patterns:
        raise ValueError(
            "Claude attempted to modify a test file."
        )

    return normalized