import os


PROJECT_DEFINITIONS = {
    "python": {
        "files": {
            "requirements.txt",
            "requirements-dev.txt",
            "requirements-test.txt",
            "pyproject.toml",
            "setup.py",
            "setup.cfg",
        },
        "language": "Python",
        "package_manager": "pip",
    },
    "node": {
        "files": {
            "package.json",
        },
        "language": "JavaScript/Node.js",
        "package_manager": "npm",
    },
    "java_maven": {
        "files": {
            "pom.xml",
        },
        "language": "Java",
        "package_manager": "Maven",
    },
    "java_gradle": {
        "files": {
            "build.gradle",
            "build.gradle.kts",
        },
        "language": "Java",
        "package_manager": "Gradle",
    },
    "go": {
        "files": {
            "go.mod",
        },
        "language": "Go",
        "package_manager": "Go Modules",
    },
    "rust": {
        "files": {
            "Cargo.toml",
        },
        "language": "Rust",
        "package_manager": "Cargo",
    },
}


def normalize_path(file_path: str):
    """
    Normalize a repository-relative path.
    """

    return file_path.replace(
        "\\",
        "/",
    ).strip()


def detect_project_type(files):
    """
    Detect the project type from repository files.

    Returns:

        python
        node
        java_maven
        java_gradle
        go
        rust
        None
    """

    normalized_files = {
        os.path.basename(
            normalize_path(file_path)
        )
        for file_path in files
    }

    scores = {}

    for project_type, definition in (
        PROJECT_DEFINITIONS.items()
    ):

        score = 0

        for marker_file in definition["files"]:

            if marker_file in normalized_files:

                score += 1

        if score > 0:

            scores[project_type] = score

    if not scores:

        return None

    return max(
        scores,
        key=scores.get,
    )


def detect_project(files):
    """
    Detect the project's language,
    package manager, and project type.
    """

    project_type = detect_project_type(
        files
    )

    if not project_type:

        return {
            "supported": False,
            "type": None,
            "language": None,
            "package_manager": None,
        }

    definition = PROJECT_DEFINITIONS[
        project_type
    ]

    return {
        "supported": True,
        "type": project_type,
        "language": definition["language"],
        "package_manager": definition[
            "package_manager"
        ],
    }


def build_project_summary(project):
    """
    Build a human-readable project summary.
    """

    if not project["type"]:

        return (
            "Project type could not be detected."
        )

    return (
        f"Project type: {project['type']}\n"
        f"Language: {project['language']}\n"
        f"Package manager: "
        f"{project['package_manager']}\n"
        f"Supported by PatchPilot: "
        f"{project['supported']}"
    )