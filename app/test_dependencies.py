from tests import build_dependency_command


def test_requirements_txt():

    command = build_dependency_command(
        "python",
        "/work/project",
        {
            "calculator.py",
            "requirements.txt",
            "test_calculator.py",
        },
    )

    assert command == [
        "python3",
        "-m",
        "pip",
        "install",
        "-r",
        "/work/project/requirements.txt",
    ]


def test_requirements_dev():

    command = build_dependency_command(
        "python",
        "/work/project",
        {
            "calculator.py",
            "requirements-dev.txt",
            "test_calculator.py",
        },
    )

    assert command == [
        "python3",
        "-m",
        "pip",
        "install",
        "-r",
        "/work/project/requirements-dev.txt",
    ]


def test_requirements_test():

    command = build_dependency_command(
        "python",
        "/work/project",
        {
            "calculator.py",
            "requirements-test.txt",
            "test_calculator.py",
        },
    )

    assert command == [
        "python3",
        "-m",
        "pip",
        "install",
        "-r",
        "/work/project/requirements-test.txt",
    ]


def test_pyproject():

    command = build_dependency_command(
        "python",
        "/work/project",
        {
            "calculator.py",
            "pyproject.toml",
            "test_calculator.py",
        },
    )

    assert command == [
        "python3",
        "-m",
        "pip",
        "install",
        "/work/project",
    ]


def test_python_without_dependencies():

    command = build_dependency_command(
        "python",
        "/work/project",
        {
            "calculator.py",
            "test_calculator.py",
        },
    )

    assert command is None


def test_node():

    command = build_dependency_command(
        "node",
        "/work/project",
        {
            "package.json",
        },
    )

    assert command == [
        "npm",
        "install",
        "--no-package-lock",
    ]


def main():

    print(
        "=== PatchPilot Dependency Tests ==="
    )

    test_requirements_txt()
    print("PASS: requirements.txt")

    test_requirements_dev()
    print("PASS: requirements-dev.txt")

    test_requirements_test()
    print("PASS: requirements-test.txt")

    test_pyproject()
    print("PASS: pyproject.toml")

    test_python_without_dependencies()
    print("PASS: Python without dependency file")

    test_node()
    print("PASS: Node.js")

    print()
    print(
        "SUCCESS: Dependency detection works."
    )


if __name__ == "__main__":
    main()