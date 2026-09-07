import asyncio
import os

from github import (
    clone_repository,
    create_branch,
    get_status,
    stage_all,
    commit_changes,
    push_branch,
    create_pull_request,
    get_commit_hash,
)


REPO_OWNER = "Cosmicrider1166"
REPO_NAME = "patchpilot-demo"

REPO_URL = (
    f"https://github.com/"
    f"{REPO_OWNER}/{REPO_NAME}.git"
)

REPO_PATH = "/work/github-test"

BRANCH_NAME = "patchpilot/module-test"

BASE_BRANCH = "master"

COMMIT_MESSAGE = "Test GitHub module"


async def main():

    print("=== Checking GitHub token ===")

    token = os.environ.get(
        "GITHUB_TOKEN",
        "",
    ).strip()

    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN is not set."
        )

    print("GitHub token available.")

    # --------------------------------------------------------
    # Create sandbox
    # --------------------------------------------------------

    from solari import create_sandbox

    client, sandbox, ctx = await create_sandbox()

    try:

        # ----------------------------------------------------
        # Clone
        # ----------------------------------------------------

        print("=== Cloning repository ===")

        await clone_repository(
            sandbox,
            REPO_URL,
            REPO_PATH,
        )

        print("Repository cloned.")

        # ----------------------------------------------------
        # Create branch
        # ----------------------------------------------------

        print("=== Creating branch ===")

        await create_branch(
            sandbox,
            BRANCH_NAME,
            REPO_PATH,
        )

        status = await get_status(
            sandbox,
            REPO_PATH,
        )

        print(
            "Current branch:",
            status.branch,
        )

        # ----------------------------------------------------
        # Verify clean repository
        # ----------------------------------------------------

        if not status.clean:
            raise RuntimeError(
                "Repository should be clean after cloning."
            )

        print("Working tree is clean.")

        # ----------------------------------------------------
        # Create a harmless change
        # ----------------------------------------------------

        print("=== Creating test change ===")

        from solari import write_file

        test_file = (
            f"{REPO_PATH}/patchpilot_module_test.txt"
        )

        await write_file(
            sandbox,
            test_file,
            "PatchPilot GitHub module test\n",
        )

        # ----------------------------------------------------
        # Check status
        # ----------------------------------------------------

        print("=== Checking modified files ===")

        status = await get_status(
            sandbox,
            REPO_PATH,
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
        # Stage
        # ----------------------------------------------------

        print("=== Staging changes ===")

        await stage_all(
            sandbox,
            REPO_PATH,
        )

        # ----------------------------------------------------
        # Commit
        # ----------------------------------------------------

        print("=== Creating commit ===")

        commit_result = await commit_changes(
            sandbox,
            REPO_PATH,
            COMMIT_MESSAGE,
        )

        commit_hash = get_commit_hash(
            commit_result
        )

        print(
            "Commit hash:",
            commit_hash,
        )

        if not commit_hash:
            raise RuntimeError(
                "Could not determine commit hash."
            )

        # ----------------------------------------------------
        # Verify clean tree
        # ----------------------------------------------------

        status = await get_status(
            sandbox,
            REPO_PATH,
        )

        print(
            "Working tree clean:",
            status.clean,
        )

        if not status.clean:
            raise RuntimeError(
                "Working tree should be clean after commit."
            )

        # ----------------------------------------------------
        # Push
        # ----------------------------------------------------

        print("=== Pushing branch ===")

        await push_branch(
            sandbox,
            REPO_PATH,
            BRANCH_NAME,
            REPO_OWNER,
            token,
        )

        print(
            "Branch pushed successfully."
        )

    finally:

        print("=== Cleaning up sandbox ===")

        await sandbox.kill()

    # --------------------------------------------------------
    # Create PR
    # --------------------------------------------------------

    print("=== Creating Pull Request ===")

    pr_url = create_pull_request(
        REPO_OWNER,
        REPO_NAME,
        BRANCH_NAME,
        BASE_BRANCH,
        "Test GitHub module",
        (
            "This PR verifies that the PatchPilot "
            "GitHub module can create branches, "
            "commit changes, push branches, and "
            "create Pull Requests."
        ),
    )

    print()
    print(
        "PR created successfully:"
    )

    print(pr_url)

    print()
    print(
        "SUCCESS: github.py is working."
    )


if __name__ == "__main__":
    asyncio.run(main())
    