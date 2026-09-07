import re


def discover_test_files(*files):
    """
    Discover test files from repository-relative paths.

    Supported patterns:

        Python:
            test_*.py
            *_test.py

        JavaScript:
            *.test.js
            *.spec.js

        Java:
            *Test.java
            Test*.java

        Go:
            *_test.go

        Rust:
            *_test.rs
    """

    test_files = []

    for file_path in files:

        normalized = file_path.replace(
            "\\",
            "/",
        ).strip()

        filename = normalized.split("/")[-1]

        # ========================================================
        # Python
        # ========================================================

        if normalized.endswith(".py"):

            if (
                filename.startswith("test_")
                or filename.endswith("_test.py")
            ):
                test_files.append(
                    normalized
                )

        # ========================================================
        # JavaScript
        # ========================================================

        elif normalized.endswith(".js"):

            if (
                filename.endswith(".test.js")
                or filename.endswith(".spec.js")
            ):
                test_files.append(
                    normalized
                )

        # ========================================================
        # Java
        # ========================================================

        elif normalized.endswith(".java"):

            if (
                filename.endswith("Test.java")
                or filename.startswith("Test")
            ):
                test_files.append(
                    normalized
                )

        # ========================================================
        # Go
        # ========================================================

        elif normalized.endswith(".go"):

            if filename.endswith("_test.go"):
                test_files.append(
                    normalized
                )

        # ========================================================
        # Rust
        # ========================================================

        elif normalized.endswith(".rs"):

            if filename.endswith("_test.rs"):
                test_files.append(
                    normalized
                )

    return sorted(
        set(test_files)
    )


def detect_test_framework(
    files,
    project=None,
    project_type=None,
):
    """
    Detect the project's test framework.

    Supported:

        Python / pytest
        Node.js / npm
        Java / Maven
        Java / Gradle
        Go
        Rust
    """

    normalized_files = {
        file_path.replace(
            "\\",
            "/",
        )
        for file_path in files
    }

    # ========================================================
    # Python / pytest
    # ========================================================

    if (
        project_type == "python"
        or project_type is None
    ):

        if "pytest.ini" in normalized_files:
            return "pytest"

        if "pyproject.toml" in normalized_files:

            if project:

                pyproject = project.get(
                    "pyproject.toml",
                    "",
                )

                if "pytest" in pyproject.lower():
                    return "pytest"

        if "setup.cfg" in normalized_files:

            if project:

                setup_cfg = project.get(
                    "setup.cfg",
                    "",
                )

                if "pytest" in setup_cfg.lower():
                    return "pytest"

        dependency_files = [
            "requirements.txt",
            "requirements-dev.txt",
            "requirements-test.txt",
        ]

        for dependency_file in dependency_files:

            if dependency_file not in normalized_files:
                continue

            if not project:
                continue

            dependencies = project.get(
                dependency_file,
                "",
            )

            if "pytest" in dependencies.lower():
                return "pytest"

        test_files = discover_test_files(
            *files
        )

        if test_files:
            return "pytest"

    # ========================================================
    # Node.js
    # ========================================================

    if project_type == "node":

        if "package.json" in normalized_files:
            return "npm"

    # ========================================================
    # Maven
    # ========================================================

    if project_type == "java_maven":

        if "pom.xml" in normalized_files:
            return "maven"

    # ========================================================
    # Gradle
    # ========================================================

    if project_type == "java_gradle":

        if (
            "build.gradle" in normalized_files
            or "build.gradle.kts" in normalized_files
        ):
            return "gradle"

    # ========================================================
    # Go
    # ========================================================

    if project_type == "go":

        if "go.mod" in normalized_files:
            return "go"

    # ========================================================
    # Rust
    # ========================================================

    if project_type == "rust":

        if "Cargo.toml" in normalized_files:
            return "cargo"

    return None


def build_dependency_command(
    project_type,
    repo_path,
    project_files=None,
):
    """
    Build the dependency installation command.

    Python projects may use:

        requirements.txt
        requirements-dev.txt
        requirements-test.txt
        pyproject.toml

    Other supported project types use their
    standard package manager.
    """

    project_files = {
        file_path.replace(
            "\\",
            "/",
        )
        for file_path in (
            project_files or []
        )
    }

    # ========================================================
    # Python
    # ========================================================

    if project_type == "python":

        if "requirements.txt" in project_files:

            return [
                "python3",
                "-m",
                "pip",
                "install",
                "-r",
                f"{repo_path}/requirements.txt",
            ]

        if "requirements-dev.txt" in project_files:

            return [
                "python3",
                "-m",
                "pip",
                "install",
                "-r",
                f"{repo_path}/requirements-dev.txt",
            ]

        if "requirements-test.txt" in project_files:

            return [
                "python3",
                "-m",
                "pip",
                "install",
                "-r",
                f"{repo_path}/requirements-test.txt",
            ]

        if "pyproject.toml" in project_files:

            return [
                "python3",
                "-m",
                "pip",
                "install",
                f"{repo_path}",
            ]

        return None

    # ========================================================
    # Node.js
    # ========================================================

    if project_type == "node":

        return [
            "npm",
            "install",
            "--no-package-lock",
        ]

    # ========================================================
    # Maven
    # ========================================================

    if project_type == "java_maven":

        return [
            "mvn",
            "dependency:go-offline",
        ]

    # ========================================================
    # Gradle
    # ========================================================

    if project_type == "java_gradle":

        return [
            "gradle",
            "dependencies",
        ]

    # ========================================================
    # Go
    # ========================================================

    if project_type == "go":

        return [
            "go",
            "mod",
            "download",
        ]

    # ========================================================
    # Rust
    # ========================================================

    if project_type == "rust":

        return [
            "cargo",
            "fetch",
        ]

    raise RuntimeError(
        f"Unsupported project type: "
        f"{project_type}"
    )


def build_test_command(
    framework,
    repo_path,
):
    """
    Build the command used to execute
    the detected test framework.
    """

    if framework == "pytest":

        return [
            "python3",
            "-m",
            "pytest",
            "-v",
            repo_path,
        ]

    if framework == "npm":

        return [
            "npm",
            "test",
        ]

    if framework == "maven":

        return [
            "mvn",
            "test",
        ]

    if framework == "gradle":

        return [
            "gradle",
            "test",
        ]

    if framework == "go":

        return [
            "go",
            "test",
            "./...",
        ]

    if framework == "cargo":

        return [
            "cargo",
            "test",
        ]

    raise RuntimeError(
        f"Unsupported test framework: "
        f"{framework}"
    )


def parse_test_summary(output):
    """
    Extract a simple test summary.

    Supports common pytest output.
    """

    summary = {
        "passed": 0,
        "failed": 0,
        "errors": 0,
    }

    passed_match = re.search(
        r"(\d+)\s+passed",
        output,
        re.IGNORECASE,
    )

    failed_match = re.search(
        r"(\d+)\s+failed",
        output,
        re.IGNORECASE,
    )

    error_match = re.search(
        r"(\d+)\s+errors?",
        output,
        re.IGNORECASE,
    )

    if passed_match:

        summary["passed"] = int(
            passed_match.group(1)
        )

    if failed_match:

        summary["failed"] = int(
            failed_match.group(1)
        )

    if error_match:

        summary["errors"] = int(
            error_match.group(1)
        )

    return summary