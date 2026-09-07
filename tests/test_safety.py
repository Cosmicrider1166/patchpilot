from safety import (
    validate_changed_files,
    validate_diff_content,
    summarize_diff,
)


def main():

    print(
        "=== PatchPilot Safety Tests ==="
    )

    # --------------------------------------------------------
    # Test 1: Valid file change
    # --------------------------------------------------------

    validate_changed_files(
        ["calculator.py"],
        "calculator.py",
    )

    print(
        "PASS: Valid source change"
    )

    # --------------------------------------------------------
    # Test 2: Unexpected file change
    # --------------------------------------------------------

    try:

        validate_changed_files(
            [
                "calculator.py",
                "README.md",
            ],
            "calculator.py",
        )

        raise RuntimeError(
            "Unexpected file test should have failed."
        )

    except RuntimeError:

        print(
            "PASS: Unexpected file rejected"
        )

    # --------------------------------------------------------
    # Test 3: Test file modification
    # --------------------------------------------------------

    try:

        validate_changed_files(
            ["test_calculator.py"],
            "test_calculator.py",
        )

        raise RuntimeError(
            "Test file modification should have failed."
        )

    except RuntimeError:

        print(
            "PASS: Test file rejected"
        )

    # --------------------------------------------------------
    # Test 4: Valid diff
    # --------------------------------------------------------

    diff = """diff --git a/calculator.py b/calculator.py
index 1234567..7654321 100644
--- a/calculator.py
+++ b/calculator.py
@@ -1,2 +1,2 @@
 def add(a, b):
-    return a - b
+    return a + b
"""

    validate_diff_content(
        diff,
        "calculator.py",
    )

    print(
        "PASS: Valid diff"
    )

    # --------------------------------------------------------
    # Test 5: Diff summary
    # --------------------------------------------------------

    summary = summarize_diff(
        diff
    )

    print(
        "Additions:",
        summary["additions"],
    )

    print(
        "Deletions:",
        summary["deletions"],
    )

    if summary["additions"] != 1:
        raise RuntimeError(
            "Expected one addition."
        )

    if summary["deletions"] != 1:
        raise RuntimeError(
            "Expected one deletion."
        )

    print(
        "PASS: Diff summary"
    )

    print()
    print(
        "SUCCESS: Safety checks are working."
    )


if __name__ == "__main__":
    main()