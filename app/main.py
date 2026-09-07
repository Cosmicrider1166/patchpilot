import asyncio
import argparse
import logging
import os
import sys
from datetime import datetime

from agent import (
    generate_repair,
    parse_repair_response,
    validate_repair_target,
)

from github import (
    clone_repository,
    create_branch,
    get_status,
    verify_base_branch,
    reset_working_tree,
    stage_all,
    commit_changes,
    push_branch,
    create_pull_request,
    get_commit_hash,
    verify_commit_hash,
    verify_remote_commit_hash,
)

from issues import (
    get_issue,
    build_issue_repair_prompt,
)

from tests import (
    discover_test_files,
    detect_test_framework,
    build_test_command,
    build_dependency_command,
)

from context import (
    select_relevant_files,
    summarize_context,
)

from safety import (
    validate_changed_files,
    validate_diff_content,
    summarize_diff,
)

from project import (
    detect_project,
    build_project_summary,
)

from solari import (
    create_sandbox,
    run_command,
    read_file,
    write_file,
    parse_test_result,
    read_project,
)

from config import (
    REPO_PATH,
    BASE_BRANCH,
    COMMIT_AUTHOR,
    COMMIT_EMAIL,
    MAX_REPAIR_ATTEMPTS,
    MAX_CONTEXT_FILES,
    MAX_CONTEXT_CHARS,
    MAX_FILE_CONTEXT_CHARS,
    validate_configuration,
)


logger = logging.getLogger("patchpilot")


def configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s: %(message)s",
    )


def get_arguments():
    """
    Parse PatchPilot command-line arguments.

    Usage:

        python app/main.py owner/repository issue_number

    Example:

        python app/main.py Cosmicrider1166/patchpilot-demo 4
    """

    parser = argparse.ArgumentParser(
        prog="patchpilot",
        description=(
            "PatchPilot autonomously investigates "
            "a GitHub Issue, repairs the repository, "
            "runs tests, and creates a Pull Request."
        ),
    )

    parser.add_argument(
        "repository",
        help=(
            "GitHub repository in the format "
            "<owner>/<repository>"
        ),
    )

    parser.add_argument(
        "issue_number",
        type=int,
        help="GitHub Issue number to repair.",
    )

    parser.add_argument(
        "--max-attempts",
        type=int,
        default=MAX_REPAIR_ATTEMPTS,
        help=(
            "Maximum number of Claude repair attempts "
            f"(default: {MAX_REPAIR_ATTEMPTS})."
        ),
    )

    parser.add_argument(
        "--max-context-files",
        type=int,
        default=MAX_CONTEXT_FILES,
        help=(
            "Maximum number of context files "
            f"(default: {MAX_CONTEXT_FILES})."
        ),
    )

    parser.add_argument(
        "--max-context-chars",
        type=int,
        default=MAX_CONTEXT_CHARS,
        help=(
            "Maximum total context characters "
            f"(default: {MAX_CONTEXT_CHARS})."
        ),
    )

    parser.add_argument(
        "--max-file-context-chars",
        type=int,
        default=MAX_FILE_CONTEXT_CHARS,
        help=(
            "Maximum characters per context file "
            f"(default: {MAX_FILE_CONTEXT_CHARS})."
        ),
    )

    args = parser.parse_args()

    repository = args.repository.strip()

    if "/" not in repository:

        parser.error(
            "repository must use the format "
            "<owner>/<repository>"
        )

    parts = repository.split("/")

    if len(parts) != 2:

        parser.error(
            "repository must use the format "
            "<owner>/<repository>"
        )

    repo_owner = parts[0].strip()
    repo_name = parts[1].strip()

    if not repo_owner or not repo_name:

        parser.error(
            "repository owner and name "
            "cannot be empty"
        )

    issue_number = args.issue_number

    if args.max_attempts <= 0:

        parser.error(
            "--max-attempts must be greater than zero"
        )

    if args.max_context_files <= 0:

        parser.error(
            "--max-context-files must be greater than zero"
        )

    if args.max_context_chars <= 0:

        parser.error(
            "--max-context-chars must be greater than zero"
        )

    if args.max_file_context_chars <= 0:

        parser.error(
            "--max-file-context-chars must be greater than zero"
        )

    if issue_number <= 0:

        parser.error(
            "issue_number must be greater than zero"
        )

    return (
        repo_owner,
        repo_name,
        issue_number,
        args.max_attempts,
        args.max_context_files,
        args.max_context_chars,
        args.max_file_context_chars,
    )


def create_unique_branch_name(
    issue_number,
):
    timestamp = datetime.now().strftime(
        "%Y%m%d-%H%M%S"
    )

    return (
        f"patchpilot/"
        f"issue-{issue_number}-"
        f"{timestamp}"
    )


async def install_dependencies(
    sandbox,
    project_type,
    project_files,
):
    logger.info(
        "=== Installing dependencies ==="
    )

    command = build_dependency_command(
        project_type,
        REPO_PATH,
        project_files,
    )

    if command is None:

        logger.info(
            "No dependency installation required."
        )

        return

    result = await run_command(
        sandbox,
        command[0],
        command[1:],
        cwd=REPO_PATH,
    )

    if result.exitCode != 0:

        raise RuntimeError(
            "Dependency installation failed:\n"
            f"{result.stderr}"
        )

    logger.info(
        "Dependencies installed."
    )


async def run_project_tests(
    sandbox,
    framework,
    project_path,
):
    logger.info(
        "=== Running project tests ==="
    )

    command = build_test_command(
        framework,
        project_path,
    )

    result = await run_command(
        sandbox,
        command[0],
        command[1:],
        cwd=project_path,
    )

    return parse_test_result(
        result,
        framework,
    )


async def apply_repairs(
    sandbox,
    repair_changes,
):
    """
    Apply one or more source-file repairs.
    """

    logger.info(
        "=== Applying repair ==="
    )

    for change in repair_changes:

        repair_file = change["file"]
        repair_content = change["code"]

        repair_path = (
            f"{REPO_PATH}/{repair_file}"
        )

        await write_file(
            sandbox,
            repair_path,
            repair_content,
        )

        logger.info(
            "Repair applied to: %s",
            repair_file,
        )


def build_commit_message(issue):
    title = issue["title"].strip()

    if len(title) > 60:
        title = title[:57] + "..."

    return (
        f"Fix issue #{issue['number']}: "
        f"{title}"
    )


def build_pr_title(issue):
    return (
        f"PatchPilot: "
        f"#{issue['number']} "
        f"{issue['title']}"
    )


def build_pr_body(
    issue,
    commit_hash,
    attempts,
):
    body = (
        "## Summary\n\n"
        "PatchPilot automatically investigated and repaired "
        f"GitHub Issue #{issue['number']}.\n\n"
        "### Issue\n\n"
        f"**{issue['title']}**\n\n"
        f"{issue['body']}\n\n"
        "### Automated workflow\n\n"
        "- Read the GitHub Issue\n"
        "- Created an isolated Solari sandbox\n"
        "- Cloned the repository\n"
        "- Verified the base branch\n"
        "- Created a unique PatchPilot branch\n"
        "- Detected the project's project type\n"
        "- Detected the project's test framework\n"
        "- Discovered the project's test files\n"
        "- Selected relevant repository context\n"
        "- Applied a context-size budget\n"
        "- Installed project dependencies\n"
        "- Ran the project tests\n"
        "- Investigated the failure with Claude\n"
        "- Applied the generated repair\n"
        "- Re-ran the project tests\n"
        "- Verified that the tests pass\n"
        "- Inspected and validated the Git diff\n"
        "- Committed the repair\n"
        "- Verified the commit hash\n"
        "- Pushed the branch\n"
        "- Verified the remote commit\n\n"
        "### Validation\n\n"
        "All project tests pass after the repair.\n\n"
        "Repair attempts: "
        + str(attempts)
        + "\n\n"
        "### Commit\n\n"
        "`"
        + str(commit_hash)
        + "`\n\n"
        "Generated automatically by PatchPilot.\n"
    )

    return body


async def reset_before_retry(
    sandbox,
    repo_path,
):
    """
    Restore the repository before starting
    another repair attempt.
    """

    logger.info(
        "=== Resetting failed repair ==="
    )

    try:

        await reset_working_tree(
            sandbox,
            repo_path,
        )

        logger.info(
            "Repository restored to "
            "the pre-repair state."
        )

    except Exception as reset_error:

        raise RuntimeError(
            "PatchPilot could not restore "
            "the repository after a failed "
            "repair:\n"
            f"{reset_error}"
        )

    logger.info(
        "PatchPilot will give Claude "
        "another attempt."
    )


async def run_patchpilot(
    repo_owner,
    repo_name,
    issue_number,
    max_attempts=MAX_REPAIR_ATTEMPTS,
    max_context_files=MAX_CONTEXT_FILES,
    max_context_chars=MAX_CONTEXT_CHARS,
    max_file_context_chars=MAX_FILE_CONTEXT_CHARS,
):
    validate_configuration(
        max_repair_attempts=max_attempts,
        max_context_files=max_context_files,
        max_context_chars=max_context_chars,
        max_file_context_chars=max_file_context_chars,
    )

    logger.info(
        "=========================================="
    )
    logger.info(
        "          PATCHPILOT STARTING"
    )
    logger.info(
        "=========================================="
    )

    repo_url = (
        f"https://github.com/"
        f"{repo_owner}/{repo_name}.git"
    )

    github_token = os.environ.get(
        "GITHUB_TOKEN",
        "",
    ).strip()

    if not github_token:

        raise RuntimeError(
            "GITHUB_TOKEN environment variable "
            "is not set."
        )

    logger.info(
        "GitHub authentication available."
    )

    logger.info(
        "=== Reading GitHub Issue ==="
    )

    issue = get_issue(
        repo_owner,
        repo_name,
        issue_number,
    )

    logger.info(
        "Issue: #%s",
        issue["number"],
    )

    logger.info(
        "Title: %s",
        issue["title"],
    )

    branch_name = create_unique_branch_name(
        issue["number"]
    )

    commit_message = build_commit_message(
        issue
    )

    pr_title = build_pr_title(
        issue
    )

    logger.info(
        "Repository: %s/%s",
        repo_owner,
        repo_name,
    )

    logger.info(
        "PatchPilot branch: %s",
        branch_name,
    )

    logger.info(
        "=== Creating Solari sandbox ==="
    )

    client, sandbox, ctx = await create_sandbox()

    try:

        logger.info(
            "Solari sandbox created."
        )

        logger.info(
            "=== Cloning repository ==="
        )

        await clone_repository(
            sandbox,
            repo_url,
            REPO_PATH,
        )

        logger.info(
            "Repository cloned."
        )

        logger.info(
            "=== Verifying base branch ==="
        )

        await verify_base_branch(
            sandbox,
            REPO_PATH,
            BASE_BRANCH,
        )

        logger.info(
            "Base branch verified: %s",
            BASE_BRANCH,
        )

        logger.info(
            "=== Creating PatchPilot branch ==="
        )

        await create_branch(
            sandbox,
            branch_name,
            REPO_PATH,
        )

        status = await get_status(
            sandbox,
            REPO_PATH,
        )

        logger.info(
            "Current branch: %s",
            status.branch,
        )

        if status.branch != branch_name:

            raise RuntimeError(
                "PatchPilot branch was not "
                "created correctly."
            )

        logger.info(
            "=== Reading project ==="
        )

        project = await read_project(
            sandbox
        )

        for file_path in project:

            logger.info(
                "Found: %s",
                file_path,
            )

        logger.info(
            "=== Detecting project type ==="
        )

        project_info = detect_project(
            project.keys()
        )

        logger.info(
            build_project_summary(
                project_info
            )
        )

        if not project_info["supported"]:

            raise RuntimeError(
                "PatchPilot detected an "
                "unsupported project type."
            )

        logger.info(
            "Project type detected successfully."
        )

        logger.info(
            "=== Detecting test framework ==="
        )

        framework = detect_test_framework(
            project.keys(),
            project,
            project_info["type"],
        )

        if not framework:

            raise RuntimeError(
                "PatchPilot could not detect a "
                "supported test framework."
            )

        logger.info(
            "Test framework: %s",
            framework,
        )

        logger.info(
            "=== Discovering test files ==="
        )

        test_files = discover_test_files(
            *project.keys()
        )

        if not test_files:

            raise RuntimeError(
                "PatchPilot could not discover "
                "any test files."
            )

        logger.info(
            "Test files discovered: %d",
            len(test_files),
        )

        for test_file in test_files:

            logger.info(
                "Test: %s",
                test_file,
            )

        await install_dependencies(
            sandbox,
            project_info["type"],
            project.keys(),
        )

        test_result = await run_project_tests(
            sandbox,
            framework,
            REPO_PATH,
        )

        logger.info(
            "Initial tests passed: %s",
            test_result["passed"],
        )

        if test_result["passed"]:

            raise RuntimeError(
                "All tests already pass. "
                "PatchPilot expected a "
                "failing test."
            )

        logger.info(
            "Test failure detected."
        )

        repair_succeeded = False

        latest_test_result = test_result

        successful_attempt = None

        last_repair_error = None

        repair_changes = []

        for attempt in range(
            1,
            max_attempts + 1,
        ):

            logger.info(
                "=========================================="
            )

            logger.info(
                "       REPAIR ATTEMPT %d/%d",
                attempt,
                max_attempts,
            )

            logger.info(
                "=========================================="
            )

            logger.info(
                "=== Reading current project state ==="
            )

            project = await read_project(
                sandbox
            )

            logger.info(
                "=== Selecting relevant context ==="
            )

            relevant_project = (
                select_relevant_files(
                    project,
                    issue,
                    latest_test_result,
                    max_files=max_context_files,
                    max_context_chars=max_context_chars,
                    max_file_chars=max_file_context_chars,
                )
            )

            context_summary = summarize_context(
                project,
                relevant_project,
                latest_test_result,
            )

            logger.info(
                "Repository files: %s",
                context_summary["total_files"],
            )

            logger.info(
                "Relevant files selected: %s",
                context_summary["selected_files"],
            )

            logger.info(
                "Context characters: %s",
                context_summary["total_context_chars"],
            )

            logger.info(
                "Context budget: %s",
                max_context_chars,
            )

            if context_summary[
                "failing_test_files"
            ]:

                logger.warning(
                    "Failing test files:"
                )

                for file_path in (
                    context_summary[
                        "failing_test_files"
                    ]
                ):

                    logger.warning(
                        "Failure: %s",
                        file_path,
                    )

            for file_path in (
                context_summary["files"]
            ):

                logger.info(
                    "Context: %s",
                    file_path,
                )

            if context_summary[
                "truncated_files"
            ]:

                logger.warning(
                    "Truncated files:"
                )

                for file_path in (
                    context_summary[
                        "truncated_files"
                    ]
                ):

                    logger.warning(
                        "Truncated: %s",
                        file_path,
                    )

            prompt_test_result = dict(
                latest_test_result
            )

            if last_repair_error:

                previous_error = (
                    "\n\n"
                    "PATCHPILOT REPAIR ERROR:\n"
                    f"{last_repair_error}"
                )

                prompt_test_result["stderr"] = (
                    prompt_test_result.get(
                        "stderr",
                        "",
                    )
                    + previous_error
                )

            logger.info(
                "=== Building Claude repair prompt ==="
            )

            repair_prompt = build_issue_repair_prompt(
                issue,
                relevant_project,
                prompt_test_result,
                attempt=attempt,
                project_type=project_info["type"],
                language=project_info["language"],
                test_framework=framework,
            )

            logger.info(
                "Repair prompt created."
            )

            logger.info(
                "=== Asking Claude for repair ==="
            )

            try:

                claude_response = (
                    await generate_repair(
                        repair_prompt
                    )
                )

                logger.info(
                    "Claude response received."
                )

                logger.info(
                    "=== Parsing structured repair ==="
                )

                repair = parse_repair_response(
                    claude_response
                )

                if not repair.get("changes"):

                    raise RuntimeError(
                        "Claude returned no repair changes."
                    )

                validated_changes = []

                seen_files = set()

                for change in repair["changes"]:

                    if not isinstance(
                        change,
                        dict,
                    ):

                        raise RuntimeError(
                            "Each repair change must "
                            "be an object."
                        )

                    if "file" not in change:

                        raise RuntimeError(
                            "A repair change is missing "
                            "the file field."
                        )

                    if "code" not in change:

                        raise RuntimeError(
                            "A repair change is missing "
                            "the code field."
                        )

                    validated_file = (
                        validate_repair_target(
                            change["file"]
                        )
                    )

                    if validated_file in seen_files:

                        raise RuntimeError(
                            "Claude returned duplicate "
                            f"repair file: "
                            f"{validated_file}"
                        )

                    seen_files.add(
                        validated_file
                    )

                    validated_changes.append(
                        {
                            "file": validated_file,
                            "code": change["code"],
                        }
                    )

                repair_changes = (
                    validated_changes
                )

                logger.info(
                    "Number of changes: %d",
                    len(repair_changes),
                )

                logger.info(
                    "Explanation: %s",
                    repair["explanation"],
                )

                for change in repair_changes:

                    logger.info(
                        "Selected file: %s",
                        change["file"],
                    )

                await apply_repairs(
                    sandbox,
                    repair_changes,
                )

                logger.info(
                    "=== Validating repair ==="
                )

                latest_test_result = (
                    await run_project_tests(
                        sandbox,
                        framework,
                        REPO_PATH,
                    )
                )

                logger.info(
                    "Tests passed: %s",
                    latest_test_result["passed"],
                )

                if latest_test_result[
                    "passed"
                ]:

                    logger.info(
                        "=========================================="
                    )

                    logger.info(
                        "       REPAIR SUCCESSFUL"
                    )

                    logger.info(
                        "=========================================="
                    )

                    logger.info(
                        "Tests passed on attempt %d.",
                        attempt,
                    )

                    repair_succeeded = True
                    successful_attempt = attempt

                    break

                last_repair_error = (
                    "Claude's repair was applied, "
                    "but the project tests still fail."
                )

                logger.warning(
                    "Repair attempt %d did not fix the tests.",
                    attempt,
                )

                if latest_test_result[
                    "stdout"
                ]:

                    logger.warning(
                        "Latest test output:\n%s",
                        latest_test_result["stdout"],
                    )

                if latest_test_result[
                    "stderr"
                ]:

                    logger.warning(
                        "Latest test errors:\n%s",
                        latest_test_result["stderr"],
                    )

                if attempt < max_attempts:

                    await reset_before_retry(
                        sandbox,
                        REPO_PATH,
                    )

            except Exception as error:

                last_repair_error = str(
                    error
                )

                logger.error(
                    "Claude repair attempt failed: %s",
                    last_repair_error,
                )

                if attempt < max_attempts:

                    await reset_before_retry(
                        sandbox,
                        REPO_PATH,
                    )

            if attempt < max_attempts:

                logger.info(
                    "The next Claude attempt will "
                    "receive the latest project "
                    "state and failure information."
                )

        if not repair_succeeded:

            raise RuntimeError(
                "PatchPilot could not repair the "
                "repository within "
                f"{max_attempts} attempts."
            )

        logger.info(
            "=== Checking Git status ==="
        )

        status = await get_status(
            sandbox,
            REPO_PATH,
        )

        logger.info(
            "Modified: %s",
            status.modified,
        )

        logger.info(
            "Untracked: %s",
            status.untracked,
        )

        if status.clean:

            raise RuntimeError(
                "No changes detected after repair."
            )

        logger.info(
            "=== Validating Git changes ==="
        )

        changed_files = (
            list(status.modified)
            + list(status.untracked)
        )

        expected_files = [
            change["file"]
            for change in repair_changes
        ]

        validate_changed_files(
            changed_files,
            expected_files,
        )

        logger.info(
            "Changed files are valid."
        )

        logger.info(
            "=== Inspecting Git diff ==="
        )

        diff_result = await run_command(
            sandbox,
            "git",
            [
                "-C",
                REPO_PATH,
                "diff",
                "--",
                ".",
            ],
        )

        if diff_result.exitCode != 0:

            raise RuntimeError(
                "Could not inspect Git diff:\n"
                f"{diff_result.stderr}"
            )

        diff = diff_result.stdout

        validate_diff_content(
            diff,
            expected_files,
        )

        diff_summary = summarize_diff(
            diff
        )

        logger.info(
            "Diff additions: %s",
            diff_summary["additions"],
        )

        logger.info(
            "Diff deletions: %s",
            diff_summary["deletions"],
        )

        logger.debug(
            "Git diff:\n%s",
            diff,
        )

        logger.info(
            "Git diff safety check passed."
        )

        logger.info(
            "=== Staging changes ==="
        )

        await stage_all(
            sandbox,
            REPO_PATH,
        )

        logger.info(
            "=== Creating commit ==="
        )

        commit_result = await commit_changes(
            sandbox,
            REPO_PATH,
            commit_message,
            author=COMMIT_AUTHOR,
            email=COMMIT_EMAIL,
        )

        commit_hash = get_commit_hash(
            commit_result
        )

        if not commit_hash:

            raise RuntimeError(
                "Could not determine commit hash."
            )

        logger.info(
            "Commit created: %s",
            commit_hash,
        )

        logger.info(
            "=== Verifying commit ==="
        )

        await verify_commit_hash(
            sandbox,
            REPO_PATH,
            commit_hash,
        )

        logger.info(
            "Commit verified: %s",
            commit_hash,
        )

        status = await get_status(
            sandbox,
            REPO_PATH,
        )

        logger.info(
            "Working tree clean: %s",
            status.clean,
        )

        if not status.clean:

            raise RuntimeError(
                "Working tree is not clean "
                "after commit."
            )

        logger.info(
            "=== Pushing branch to GitHub ==="
        )

        await push_branch(
            sandbox,
            REPO_PATH,
            branch_name,
            repo_owner,
            github_token,
        )

        logger.info(
            "=== Verifying remote commit ==="
        )

        await verify_remote_commit_hash(
            sandbox,
            REPO_PATH,
            branch_name,
            commit_hash,
        )

        logger.info(
            "Remote commit verified: %s",
            commit_hash,
        )

        logger.info(
            "Branch pushed successfully."
        )

    finally:

        logger.info(
            "=== Cleaning up Solari sandbox ==="
        )

        await sandbox.kill()

    logger.info(
        "=== Creating GitHub Pull Request ==="
    )

    pr_body = build_pr_body(
        issue,
        commit_hash,
        successful_attempt,
    )

    pr_url = create_pull_request(
        repo_owner,
        repo_name,
        branch_name,
        BASE_BRANCH,
        pr_title,
        pr_body,
    )

    logger.info(
        "=========================================="
    )

    logger.info(
        "       PATCHPILOT COMPLETED"
    )

    logger.info(
        "=========================================="
    )

    logger.info(
        "Repository: %s/%s",
        repo_owner,
        repo_name,
    )

    logger.info(
        "Issue: #%s",
        issue["number"],
    )

    logger.info(
        "Branch: %s",
        branch_name,
    )

    logger.info(
        "Commit: %s",
        commit_hash,
    )

    logger.info(
        "Repair attempts: %s",
        successful_attempt,
    )

    logger.info(
        "Pull Request: %s",
        pr_url,
    )

    logger.info(
        "=========================================="
    )


def main():
    configure_logging()

    try:
        (
            repo_owner,
            repo_name,
            issue_number,
            max_attempts,
            max_context_files,
            max_context_chars,
            max_file_context_chars,
        ) = get_arguments()

        asyncio.run(
            run_patchpilot(
                repo_owner,
                repo_name,
                issue_number,
                max_attempts=max_attempts,
                max_context_files=max_context_files,
                max_context_chars=max_context_chars,
                max_file_context_chars=max_file_context_chars,
            )
        )

    except KeyboardInterrupt:
        logger.error(
            "PatchPilot interrupted by user."
        )
        sys.exit(130)

    except Exception as error:
        logger.error(
            "PatchPilot failed: %s",
            error,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()