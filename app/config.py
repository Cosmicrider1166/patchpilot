REPO_PATH = "/work/patchpilot"

BASE_BRANCH = "master"

COMMIT_AUTHOR = "PatchPilot"
COMMIT_EMAIL = "patchpilot@example.com"

MAX_REPAIR_ATTEMPTS = 3

MAX_CONTEXT_FILES = 20
MAX_CONTEXT_CHARS = 30000
MAX_FILE_CONTEXT_CHARS = 12000


def validate_configuration(
    max_repair_attempts=MAX_REPAIR_ATTEMPTS,
    max_context_files=MAX_CONTEXT_FILES,
    max_context_chars=MAX_CONTEXT_CHARS,
    max_file_context_chars=MAX_FILE_CONTEXT_CHARS,
):
    """
    Validate PatchPilot runtime configuration.

    All numeric limits must be greater than zero.
    """

    values = {
        "max_repair_attempts": max_repair_attempts,
        "max_context_files": max_context_files,
        "max_context_chars": max_context_chars,
        "max_file_context_chars": max_file_context_chars,
    }

    for name, value in values.items():

        if not isinstance(value, int):
            raise ValueError(
                f"{name} must be an integer."
            )

        if value <= 0:
            raise ValueError(
                f"{name} must be greater than zero."
            )

    return True
