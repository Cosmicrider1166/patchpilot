from context import (
    select_relevant_files,
    summarize_context,
)


def main():

    project = {
        ".gitignore": "ignored",
        "README.md": "PatchPilot demo",
        "calculator.py": (
            "def add(a, b):\n"
            "    return a - b\n"
        ),
        "requirements.txt": "pytest\n",
        "test_calculator.py": (
            "def test_add():\n"
            "    assert add(10, 20) == 30\n"
        ),
        "docs/example.py": (
            "def example():\n"
            "    pass\n"
        ),
    }

    issue = {
        "number": 4,
        "title": "Fix calculator addition",
        "body": (
            "The add function is returning "
            "the wrong result."
        ),
    }

    selected = select_relevant_files(
        project,
        issue,
    )

    summary = summarize_context(
        project,
        selected,
    )

    print(
        "=== PatchPilot Context Selection ==="
    )

    print(
        "Total files:",
        summary["total_files"],
    )

    print(
        "Selected files:",
        summary["selected_files"],
    )

    print()

    for file_path in summary["files"]:
        print(
            "Selected:",
            file_path,
        )

    print()

    if "calculator.py" not in selected:
        raise RuntimeError(
            "calculator.py was not selected."
        )

    if "test_calculator.py" not in selected:
        raise RuntimeError(
            "test_calculator.py was not selected."
        )

    if ".gitignore" in selected:
        raise RuntimeError(
            ".gitignore should not be selected."
        )

    print(
        "SUCCESS: Context selection is working."
    )


if __name__ == "__main__":
    main()