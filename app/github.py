import subprocess


def clone_repository(
    sandbox,
    repo_url,
    repo_path,
):
    """
    Clone a GitHub repository into the Solari sandbox.
    """

    return sandbox.git.clone(
        repo_url,
        path=repo_path,
    )


async def create_branch(
    sandbox,
    branch_name,
    repo_path,
):
    """
    Create and switch to a new Git branch.
    """

    await sandbox.git.checkout(
        branch_name,
        cwd=repo_path,
        create=True,
    )


async def get_status(
    sandbox,
    repo_path,
):
    """
    Return the current Git status.
    """

    return await sandbox.git.status(
        repo_path
    )

async def get_current_branch(
    sandbox,
    repo_path,
):
    """
    Return the currently checked-out Git branch.
    """

    result = await sandbox.commands.run(
        "git",
        args=[
            "-C",
            repo_path,
            "rev-parse",
            "--abbrev-ref",
            "HEAD",
        ],
        cwd=repo_path,
    )

    if result.exitCode != 0:
        raise RuntimeError(
            "Could not determine the current "
            "Git branch:\n"
            f"{result.stderr}"
        )

    branch = result.stdout.strip()

    if not branch:
        raise RuntimeError(
            "Git did not return the current branch."
        )

    return branch


async def verify_base_branch(
    sandbox,
    repo_path,
    expected_branch,
):
    """
    Verify that the repository is currently
    checked out on the expected base branch.
    """

    current_branch = await get_current_branch(
        sandbox,
        repo_path,
    )

    if current_branch != expected_branch:
        raise RuntimeError(
            "PatchPilot expected the repository "
            f"to be on base branch "
            f"'{expected_branch}', but it is "
            f"currently on '{current_branch}'."
        )

    return True

async def reset_working_tree(
    sandbox,
    repo_path,
):
    """
    Restore the repository to the current HEAD.

    This removes:
    - tracked-file modifications
    - staged changes
    - untracked files

    PatchPilot uses this between failed repair
    attempts so that each retry starts from a
    clean repository state.
    """

    reset_result = await sandbox.commands.run(
        "git",
        args=[
            "-C",
            repo_path,
            "reset",
            "--hard",
            "HEAD",
        ],
        cwd=repo_path,
    )

    if reset_result.exitCode != 0:
        raise RuntimeError(
            "Could not reset the repository:\n"
            f"{reset_result.stderr}"
        )

    clean_result = await sandbox.commands.run(
        "git",
        args=[
            "-C",
            repo_path,
            "clean",
            "-fd",
        ],
        cwd=repo_path,
    )

    if clean_result.exitCode != 0:
        raise RuntimeError(
            "Could not clean untracked files:\n"
            f"{clean_result.stderr}"
        )

    return True


async def stage_all(
    sandbox,
    repo_path,
):
    """
    Stage all changes in the repository.
    """

    await sandbox.git.add(
        ["."],
        cwd=repo_path,
    )


async def commit_changes(
    sandbox,
    repo_path,
    message,
    author="PatchPilot",
    email="patchpilot@example.com",
):
    """
    Create a Git commit.
    """

    return await sandbox.git.commit(
        message,
        cwd=repo_path,
        author=author,
        email=email,
    )


async def push_branch(
    sandbox,
    repo_path,
    branch_name,
    username,
    token,
):
    """
    Push a branch to GitHub using credentials
    supplied only for this operation.
    """

    if not token:
        raise RuntimeError(
            "GitHub token is required for push."
        )

    await sandbox.git.push(
        cwd=repo_path,
        branch=branch_name,
        username=username,
        password=token,
    )


def create_pull_request(
    repo_owner,
    repo_name,
    branch_name,
    base_branch,
    title,
    body,
):
    """
    Create a GitHub Pull Request using the
    locally authenticated GitHub CLI.
    """

    command = [
        "gh",
        "pr",
        "create",
        "--repo",
        f"{repo_owner}/{repo_name}",
        "--base",
        base_branch,
        "--head",
        branch_name,
        "--title",
        title,
        "--body",
        body,
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )

    if result.returncode != 0:

        error = result.stderr.strip()

        # Handle an already-existing PR.
        if "already exists" in error.lower():

            existing = subprocess.run(
                [
                    "gh",
                    "pr",
                    "view",
                    branch_name,
                    "--repo",
                    f"{repo_owner}/{repo_name}",
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


def get_commit_hash(
    commit_result,
):
    """
    Extract the commit hash from the Solari
    Git commit result.
    """

    if isinstance(
        commit_result,
        dict,
    ):

        return (
            commit_result.get("hash")
            or commit_result.get("commitHash")
            or commit_result.get("sha")
        )

    return getattr(
        commit_result,
        "hash",
        None,
    )

async def get_current_commit_hash(
    sandbox,
    repo_path,
):
    """
    Return the commit hash currently checked out
    at HEAD.
    """

    result = await sandbox.commands.run(
        "git",
        args=[
            "-C",
            repo_path,
            "rev-parse",
            "HEAD",
        ],
        cwd=repo_path,
    )

    if result.exitCode != 0:
        raise RuntimeError(
            "Could not determine the current "
            "Git commit:\n"
            f"{result.stderr}"
        )

    commit_hash = result.stdout.strip()

    if not commit_hash:
        raise RuntimeError(
            "Git did not return the current "
            "commit hash."
        )

    return commit_hash


async def verify_commit_hash(
    sandbox,
    repo_path,
    expected_hash,
):
    """
    Verify that HEAD matches the expected
    commit hash.
    """

    if not expected_hash:
        raise RuntimeError(
            "Expected commit hash is required."
        )

    current_hash = await get_current_commit_hash(
        sandbox,
        repo_path,
    )

    if current_hash != expected_hash:
        raise RuntimeError(
            "PatchPilot detected a commit mismatch. "
            f"Expected '{expected_hash}', but "
            f"HEAD is '{current_hash}'."
        )

    return True


async def verify_remote_commit_hash(
    sandbox,
    repo_path,
    branch_name,
    expected_hash,
):
    """
    Verify that the remote branch points to the
    expected commit hash.
    """

    if not branch_name:
        raise RuntimeError(
            "Branch name is required for "
            "remote commit verification."
        )

    if not expected_hash:
        raise RuntimeError(
            "Expected commit hash is required "
            "for remote verification."
        )

    result = await sandbox.commands.run(
        "git",
        args=[
            "-C",
            repo_path,
            "ls-remote",
            "origin",
            f"refs/heads/{branch_name}",
        ],
        cwd=repo_path,
    )

    if result.exitCode != 0:
        raise RuntimeError(
            "Could not verify the remote branch:\n"
            f"{result.stderr}"
        )

    output = result.stdout.strip()

    if not output:
        raise RuntimeError(
            "GitHub did not return a remote commit "
            f"for branch '{branch_name}'."
        )

    remote_hash = output.split()[0]

    if remote_hash != expected_hash:
        raise RuntimeError(
            "PatchPilot detected a remote commit "
            "mismatch. "
            f"Expected '{expected_hash}', but "
            f"the remote branch points to "
            f"'{remote_hash}'."
        )

    return True