from tests import (
    discover_test_files,
    detect_test_framework,
    build_test_command,
    parse_test_summary,
)


def main():

    print(
        "=== PatchPilot Test Discovery ==="
    )

    files = [
        ".gitignore",
        "README.md",
        "calculator.py",
        "requirements.txt",
        "test_calculator.py",
    ]

    print()
    print(
        "Repository files:"
    )

    for file_path in files:
        print(
            " ",
            file_path,
        )

    # --------------------------------------------------------
    # Discover test files
    # --------------------------------------------------------

    print()
    print(
        "=== Discovering test files ==="
    )

    test_files = discover_test_files(
        files
    )

    for test_file in test_files:
        print(
            "Found test:",
            test_file,
        )

    if not test_files:
        raise RuntimeError(
            "No test files were discovered."
        )

    # --------------------------------------------------------
    # Detect framework
    # --------------------------------------------------------

    print()
    print(
        "=== Detecting test framework ==="
    )

    framework = detect_test_framework(
        files
    )

    print(
        "Framework:",
        framework,
    )

    if framework != "pytest":
        raise RuntimeError(
            "Expected pytest to be detected."
        )

    # --------------------------------------------------------
    # Build command
    # --------------------------------------------------------

    print()
    print(
        "=== Building test command ==="
    )

    command = build_test_command(
        framework,
        "/work/patchpilot",
    )

    print(
        "Command:",
        " ".join(command),
    )

    # --------------------------------------------------------
    # Parse example result
    # --------------------------------------------------------

    print()
    print(
        "=== Testing result parser ==="
    )

    summary = parse_test_summary(
        "1 failed, 4 passed"
    )

    print(
        "Passed:",
        summary["passed"],
    )

    print(
        "Failed:",
        summary["failed"],
    )

    print(
        "Errors:",
        summary["errors"],
    )

    if summary["passed"] != 4:
        raise RuntimeError(
            "Test summary parser failed."
        )

    if summary["failed"] != 1:
        raise RuntimeError(
            "Test summary parser failed."
        )

    print()
    print(
        "SUCCESS: Test discovery is working."
    )


if __name__ == "__main__":
    main()
    