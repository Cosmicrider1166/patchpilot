def normalize_path(file_path: str):
    return file_path.replace("\\", "/").strip()


def is_test_file(file_path: str):
    normalized = normalize_path(file_path)
    filename = normalized.split("/")[-1]

    return (
        filename.startswith("test_")
        or filename.endswith("_test.py")
        or filename.endswith(".test.js")
        or filename.endswith(".spec.js")
        or filename.endswith("Test.java")
        or filename.startswith("Test")
        or filename.endswith("_test.go")
        or filename.endswith("_test.rs")
    )


def validate_changed_files(
    changed_files,
    expected_files,
):
    """
    Validate that Git changed exactly the files
    requested by the repair.

    Safety rules:
    - At least one expected file must exist.
    - Git must contain changes.
    - No unexpected files may be modified.
    - Test files may never be modified.
    - Every expected file must actually be changed.
    """

    normalized_changed = {
        normalize_path(file_path)
        for file_path in changed_files
        if file_path and file_path.strip()
    }

    normalized_expected = {
        normalize_path(file_path)
        for file_path in expected_files
        if file_path and file_path.strip()
    }

    if not normalized_expected:
        raise RuntimeError(
            "No expected repair files were provided."
        )

    if not normalized_changed:
        raise RuntimeError(
            "Git diff is empty. "
            "No changes were detected."
        )

    unexpected_files = (
        normalized_changed - normalized_expected
    )

    if unexpected_files:
        files = ", ".join(
            sorted(unexpected_files)
        )

        raise RuntimeError(
            "PatchPilot detected unexpected "
            f"modified files: {files}"
        )

    test_files = {
        file_path
        for file_path in normalized_expected
        if is_test_file(file_path)
    }

    if test_files:
        files = ", ".join(
            sorted(test_files)
        )

        raise RuntimeError(
            "PatchPilot attempted to modify "
            f"test file(s): {files}"
        )

    missing_files = (
        normalized_expected - normalized_changed
    )

    if missing_files:
        files = ", ".join(
            sorted(missing_files)
        )

        raise RuntimeError(
            "PatchPilot expected these files to be "
            f"modified, but Git did not detect changes: {files}"
        )

    return True


def validate_diff_content(
    diff,
    expected_files,
):
    """
    Validate that the Git diff contains exactly
    the files requested by the repair.
    """

    if not diff.strip():
        raise RuntimeError(
            "Git diff is empty."
        )

    normalized_expected = {
        normalize_path(file_path)
        for file_path in expected_files
        if file_path and file_path.strip()
    }

    if not normalized_expected:
        raise RuntimeError(
            "No expected repair files were provided."
        )

    changed_in_diff = set()

    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            changed_file = normalize_path(
                line[6:]
            )

            changed_in_diff.add(changed_file)

    if not changed_in_diff:
        raise RuntimeError(
            "No changed files were found "
            "in the Git diff."
        )

    unexpected_files = (
        changed_in_diff - normalized_expected
    )

    if unexpected_files:
        files = ", ".join(
            sorted(unexpected_files)
        )

        raise RuntimeError(
            "Git diff contains unexpected "
            f"file(s): {files}"
        )

    missing_files = (
        normalized_expected - changed_in_diff
    )

    if missing_files:
        files = ", ".join(
            sorted(missing_files)
        )

        raise RuntimeError(
            "Expected repair file(s) were not found "
            f"in the Git diff: {files}"
        )

    return True


def summarize_diff(diff):
    lines = diff.splitlines()

    additions = 0
    deletions = 0

    for line in lines:
        if (
            line.startswith("+")
            and not line.startswith("+++")
        ):
            additions += 1

        elif (
            line.startswith("-")
            and not line.startswith("---")
        ):
            deletions += 1

    return {
        "additions": additions,
        "deletions": deletions,
        "lines": len(lines),
    }