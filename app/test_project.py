from project import (
    detect_project_type,
    detect_project,
    build_project_summary,
)


def main():

    print(
        "=== PatchPilot Project Detection ==="
    )

    # --------------------------------------------------------
    # Python
    # --------------------------------------------------------

    python_files = [
        "README.md",
        "calculator.py",
        "requirements.txt",
        "test_calculator.py",
    ]

    project_type = detect_project_type(
        python_files
    )

    print(
        "Python repository:",
        project_type,
    )

    if project_type != "python":

        raise RuntimeError(
            "Python project was not detected."
        )

    project = detect_project(
        python_files
    )

    print(
        build_project_summary(
            project
        )
    )

    if not project["supported"]:

        raise RuntimeError(
            "Python project should be supported."
        )

    print(
        "PASS: Python detection"
    )

    # --------------------------------------------------------
    # Node.js
    # --------------------------------------------------------

    node_files = [
        "README.md",
        "package.json",
        "index.js",
    ]

    project_type = detect_project_type(
        node_files
    )

    print(
        "Node repository:",
        project_type,
    )

    if project_type != "node":

        raise RuntimeError(
            "Node.js project was not detected."
        )

    project = detect_project(
        node_files
    )

    if project["supported"]:

        raise RuntimeError(
            "Node.js should not be executable yet."
        )

    print(
        "PASS: Node.js detection"
    )

    # --------------------------------------------------------
    # Java Maven
    # --------------------------------------------------------

    java_files = [
        "README.md",
        "pom.xml",
        "src/Main.java",
    ]

    project_type = detect_project_type(
        java_files
    )

    print(
        "Maven repository:",
        project_type,
    )

    if project_type != "java_maven":

        raise RuntimeError(
            "Maven project was not detected."
        )

    print(
        "PASS: Maven detection"
    )

    # --------------------------------------------------------
    # Go
    # --------------------------------------------------------

    go_files = [
        "README.md",
        "go.mod",
        "main.go",
    ]

    project_type = detect_project_type(
        go_files
    )

    print(
        "Go repository:",
        project_type,
    )

    if project_type != "go":

        raise RuntimeError(
            "Go project was not detected."
        )

    print(
        "PASS: Go detection"
    )

    # --------------------------------------------------------
    # Rust
    # --------------------------------------------------------

    rust_files = [
        "README.md",
        "Cargo.toml",
        "src/main.rs",
    ]

    project_type = detect_project_type(
        rust_files
    )

    print(
        "Rust repository:",
        project_type,
    )

    if project_type != "rust":

        raise RuntimeError(
            "Rust project was not detected."
        )

    print(
        "PASS: Rust detection"
    )

    print()
    print(
        "SUCCESS: Project detection is working."
    )


if __name__ == "__main__":
    main()