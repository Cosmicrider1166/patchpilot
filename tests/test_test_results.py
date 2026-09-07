from types import SimpleNamespace

from solari import parse_test_result


def make_result(
    stdout,
    stderr="",
    exit_code=0,
):
    return SimpleNamespace(
        stdout=stdout,
        stderr=stderr,
        exitCode=exit_code,
    )


def test_pytest_failure():

    result = make_result(
        """
============================= test session starts =============================
collected 1 item

test_calculator.py::test_add FAILED

================================== FAILURES ===================================
___________________________________ test_add ___________________________________
E       assert -10 == 30

=========================== short test summary info ============================
FAILED test_calculator.py::test_add - AssertionError
============================== 1 failed in 0.02s ===============================
""",
        exit_code=1,
    )

    parsed = parse_test_result(
        result,
        "pytest",
    )

    assert parsed["passed"] is False
    assert parsed["summary"]["failed"] == 1
    assert len(
        parsed["failed_tests"]
    ) == 1

    assert (
        parsed["failed_tests"][0]["file"]
        == "test_calculator.py"
    )

    assert (
        parsed["assertion"]["actual"]
        == "-10"
    )

    assert (
        parsed["assertion"]["expected"]
        == "30"
    )


def test_pytest_success():

    result = make_result(
        """
1 passed in 0.01s
"""
    )

    parsed = parse_test_result(
        result,
        "pytest",
    )

    assert parsed["passed"] is True
    assert parsed["summary"]["passed"] == 1


def test_go_failure():

    result = make_result(
        """
--- FAIL: TestAdd (0.00s)
--- PASS: TestSubtract (0.00s)
FAIL
""",
        exit_code=1,
    )

    parsed = parse_test_result(
        result,
        "go",
    )

    assert parsed["passed"] is False
    assert parsed["summary"]["failed"] == 1
    assert parsed["summary"]["passed"] == 1


def test_cargo_failure():

    result = make_result(
        """
running 2 tests
test test_add ... FAILED
test test_subtract ... ok
test result: FAILED. 1 passed; 1 failed
""",
        exit_code=1,
    )

    parsed = parse_test_result(
        result,
        "cargo",
    )

    assert parsed["passed"] is False
    assert parsed["summary"]["failed"] == 1
    assert parsed["summary"]["passed"] == 1


def main():

    print(
        "=== PatchPilot Universal Test Parser ==="
    )

    test_pytest_failure()

    print(
        "PASS: pytest failure"
    )

    test_pytest_success()

    print(
        "PASS: pytest success"
    )

    test_go_failure()

    print(
        "PASS: Go failure"
    )

    test_cargo_failure()

    print(
        "PASS: Cargo failure"
    )

    print()
    print(
        "SUCCESS: Universal test-result parsing works."
    )


if __name__ == "__main__":
    main()

    