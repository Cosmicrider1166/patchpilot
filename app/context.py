import ast
import os


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "env",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
}


IGNORED_FILES = {
    ".gitignore",
    ".gitattributes",
}


DEFAULT_MAX_FILES = 20
DEFAULT_MAX_CONTEXT_CHARS = 30000
DEFAULT_MAX_FILE_CHARS = 12000


def normalize_path(file_path: str):
    """
    Normalize a repository-relative file path.
    """

    return file_path.replace(
        "\\",
        "/",
    ).strip()


def is_test_file(file_path: str):
    """
    Determine whether a repository file is a test file.

    Supported conventions:

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

    normalized = normalize_path(file_path)
    filename = normalized.split("/")[-1]

    return (
        # Python
        filename.startswith("test_")
        or filename.endswith("_test.py")

        # JavaScript
        or filename.endswith(".test.js")
        or filename.endswith(".spec.js")

        # Java
        or filename.endswith("Test.java")
        or filename.startswith("Test")

        # Go
        or filename.endswith("_test.go")

        # Rust
        or filename.endswith("_test.rs")
    )

def is_source_file(file_path: str):
    """
    Determine whether a repository file is a source file.

    Supported languages:

        Python
        JavaScript
        Java
        Go
        Rust
    """

    normalized = normalize_path(file_path)

    source_extensions = (
        ".py",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".java",
        ".go",
        ".rs",
    )

    if not normalized.endswith(
        source_extensions
    ):
        return False

    if is_test_file(normalized):
        return False

    return True


def is_ignored_file(file_path: str):
    """
    Determine whether a file should be excluded
    from Claude's debugging context.
    """

    normalized = normalize_path(
        file_path
    )

    filename = normalized.split("/")[-1]

    if filename in IGNORED_FILES:
        return True

    path_parts = normalized.split("/")

    for part in path_parts:

        if part in IGNORED_DIRECTORIES:
            return True

    return False


def extract_imports(source_code: str):
    """
    Extract imported Python module names.
    """

    imports = set()

    try:

        tree = ast.parse(
            source_code
        )

    except SyntaxError:

        return imports

    for node in ast.walk(tree):

        if isinstance(
            node,
            ast.Import,
        ):

            for alias in node.names:

                imports.add(
                    alias.name
                )

        elif isinstance(
            node,
            ast.ImportFrom,
        ):

            if node.module:

                imports.add(
                    node.module
                )

    return imports


def build_module_map(project):
    """
    Build mappings from Python module names
    to repository file paths.
    """

    module_to_file = {}

    for file_path in project:

        normalized = normalize_path(
            file_path
        )

        if not normalized.endswith(".py"):
            continue

        filename = os.path.basename(
            normalized
        )

        module_name = os.path.splitext(
            filename
        )[0]

        module_to_file[
            module_name
        ] = normalized

        module_path = normalized[:-3]

        if module_path.endswith(
            "/__init__"
        ):

            module_path = module_path[
                :-len("/__init__")
            ]

        module_name_from_path = (
            module_path.replace(
                "/",
                ".",
            )
        )

        module_to_file[
            module_name_from_path
        ] = normalized

    return module_to_file


def build_import_graph(project):
    """
    Build a Python import graph.

    Example:

        test_calculator.py
            -> calculator.py
    """

    module_to_file = build_module_map(
        project
    )

    graph = {}

    for file_path in project:

        normalized = normalize_path(
            file_path
        )

        if not normalized.endswith(".py"):
            continue

        graph[normalized] = set()

        source = project.get(
            file_path,
            "",
        )

        imports = extract_imports(
            source
        )

        for imported_module in imports:

            imported_file = None

            if imported_module in module_to_file:

                imported_file = (
                    module_to_file[
                        imported_module
                    ]
                )

            if imported_file is None:

                short_module = (
                    imported_module.split(
                        "."
                    )[-1]
                )

                imported_file = (
                    module_to_file.get(
                        short_module
                    )
                )

            if imported_file:

                graph[normalized].add(
                    imported_file
                )

    return graph


def get_failing_test_files(
    test_result,
    project,
):
    """
    Identify repository test files involved
    in the latest test failure.
    """

    failing_files = set()

    failed_tests = (
        test_result.get(
            "failed_tests",
            [],
        )
        if test_result
        else []
    )

    project_paths = {
        normalize_path(
            path
        )
        for path in project
    }

    for failed_test in failed_tests:

        file_path = normalize_path(
            failed_test.get(
                "file",
                "",
            )
        )

        if not file_path:
            continue

        if file_path in project_paths:

            failing_files.add(
                file_path
            )

            continue

        filename = (
            file_path.split("/")[-1]
        )

        for project_path in project_paths:

            if (
                project_path.split("/")[-1]
                == filename
            ):

                failing_files.add(
                    project_path
                )

    return failing_files


def calculate_dependency_scores(
    import_graph,
    starting_files,
):
    """
    Calculate relevance based on dependency
    relationships.
    """

    scores = {}

    current_level = set(
        starting_files
    )

    visited = set(
        starting_files
    )

    depth = 0

    while current_level:

        if depth == 0:

            points = 100

        elif depth == 1:

            points = 80

        elif depth == 2:

            points = 50

        else:

            points = 25

        next_level = set()

        for file_path in current_level:

            scores[file_path] = (
                scores.get(
                    file_path,
                    0,
                )
                + points
            )

            dependencies = (
                import_graph.get(
                    file_path,
                    set(),
                )
            )

            for dependency in dependencies:

                if dependency in visited:
                    continue

                visited.add(
                    dependency
                )

                next_level.add(
                    dependency
                )

        current_level = next_level

        depth += 1

        if depth > 4:
            break

    return scores


def calculate_file_relevance(
    file_path: str,
    issue,
    import_graph=None,
    failing_test_files=None,
    dependency_scores=None,
):
    """
    Calculate a relevance score for a file.
    """

    normalized = normalize_path(
        file_path
    )

    filename = normalized.split("/")[-1]

    title = issue.get(
        "title",
        "",
    ).lower()

    body = issue.get(
        "body",
        "",
    ).lower()

    issue_text = (
        f"{title} {body}"
    )

    score = 0

    # --------------------------------------------------------
    # Failing test
    # --------------------------------------------------------

    if failing_test_files:

        if normalized in failing_test_files:

            score += 300

    # --------------------------------------------------------
    # Test file
    # --------------------------------------------------------

    if is_test_file(normalized):

        score += 30

    # --------------------------------------------------------
    # Python source
    # --------------------------------------------------------

    if is_source_file(normalized):

        score += 20

    # --------------------------------------------------------
    # Issue keyword matching
    # --------------------------------------------------------

    filename_without_extension = (
        os.path.splitext(
            filename
        )[0].lower()
    )

    issue_words = {
        word
        for word in issue_text.replace(
            "_",
            " ",
        ).replace(
            "-",
            " ",
        ).split()
        if len(word) >= 3
    }

    filename_words = set(
        filename_without_extension.replace(
            "_",
            " ",
        ).split()
    )

    if issue_words.intersection(
        filename_words
    ):

        score += 50

    # --------------------------------------------------------
    # Project metadata
    # --------------------------------------------------------

    if filename.lower() in {
        "readme.md",
        "pyproject.toml",
        "setup.py",
        "setup.cfg",
        "requirements.txt",
    }:

        score += 5

    # --------------------------------------------------------
    # Import relationships
    # --------------------------------------------------------

    if import_graph:

        imported_by_count = sum(
            1
            for dependencies
            in import_graph.values()
            if normalized in dependencies
        )

        score += (
            imported_by_count * 25
        )

        test_import_count = sum(
            1
            for source_file, dependencies
            in import_graph.items()
            if is_test_file(source_file)
            and normalized in dependencies
        )

        score += (
            test_import_count * 50
        )

    # --------------------------------------------------------
    # Failure dependency chain
    # --------------------------------------------------------

    if dependency_scores:

        score += dependency_scores.get(
            normalized,
            0,
        )

    return score


def rank_relevant_files(
    project,
    issue,
    test_result=None,
):
    """
    Rank repository files by debugging relevance.

    Returns:

        [
            (score, file_path),
            ...
        ]
    """

    import_graph = build_import_graph(
        project
    )

    failing_test_files = (
        get_failing_test_files(
            test_result,
            project,
        )
    )

    dependency_scores = (
        calculate_dependency_scores(
            import_graph,
            failing_test_files,
        )
    )

    candidates = []

    for file_path in project:

        normalized = normalize_path(
            file_path
        )

        if is_ignored_file(normalized):
            continue

        score = calculate_file_relevance(
            normalized,
            issue,
            import_graph,
            failing_test_files,
            dependency_scores,
        )

        candidates.append(
            (
                score,
                normalized,
            )
        )

    candidates.sort(
        key=lambda item: (
            -item[0],
            item[1],
        )
    )

    return candidates


def truncate_file_content(
    content: str,
    max_chars: int,
):
    """
    Limit a file's content while preserving
    both the beginning and end of the file.

    Small files are returned unchanged.
    """

    if len(content) <= max_chars:

        return content, False

    marker = (
        "\n\n"
        "# ... PATCHPILOT CONTEXT TRUNCATED ...\n"
        "# Middle of this file was omitted because "
        "of the context budget.\n\n"
    )

    available = (
        max_chars - len(marker)
    )

    if available <= 0:

        return (
            content[:max_chars],
            True,
        )

    head_chars = available // 2

    tail_chars = (
        available - head_chars
    )

    truncated = (
        content[:head_chars]
        + marker
        + content[-tail_chars:]
    )

    return truncated, True


def select_relevant_files(
    project,
    issue,
    test_result=None,
    max_files=DEFAULT_MAX_FILES,
    max_context_chars=DEFAULT_MAX_CONTEXT_CHARS,
    max_file_chars=DEFAULT_MAX_FILE_CHARS,
):
    """
    Select relevant files while respecting a context budget.

    The highest-ranked files are considered first.

    Large files are truncated when necessary.

    Returns a dictionary containing the selected
    file contents.
    """

    ranked_files = rank_relevant_files(
        project,
        issue,
        test_result,
    )

    selected_project = {}

    total_chars = 0

    for score, file_path in ranked_files:

        if len(
            selected_project
        ) >= max_files:

            break

        original_content = project.get(
            file_path,
            "",
        )

        remaining_chars = (
            max_context_chars
            - total_chars
        )

        if remaining_chars <= 0:
            break

        file_limit = min(
            max_file_chars,
            remaining_chars,
        )

        content, _ = truncate_file_content(
            original_content,
            file_limit,
        )

        if not content:
            continue

        selected_project[
            file_path
        ] = content

        total_chars += len(
            content
        )

    return selected_project


def summarize_context(
    project,
    selected_project,
    test_result=None,
):
    """
    Return information about the selected
    debugging context.
    """

    failing_test_files = (
        get_failing_test_files(
            test_result,
            project,
        )
    )

    total_chars = sum(
        len(content)
        for content
        in selected_project.values()
    )

    truncated_files = []

    for file_path, content in selected_project.items():

        original_content = project.get(
            file_path,
            "",
        )

        if len(content) < len(
            original_content
        ):

            truncated_files.append(
                file_path
            )

    return {
        "total_files": len(
            project
        ),
        "selected_files": len(
            selected_project
        ),
        "total_context_chars": total_chars,
        "files": list(
            selected_project.keys()
        ),
        "failing_test_files": list(
            failing_test_files
        ),
        "truncated_files": truncated_files,
    }