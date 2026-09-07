# PatchPilot

PatchPilot is an autonomous GitHub Issue repair agent that investigates failing software projects, modifies source code inside an isolated Solari sandbox, verifies the repair with the project's test suite, and creates a GitHub Pull Request.

## Workflow

```text
GitHub Issue
     │
     ▼
PatchPilot
     │
     ▼
Solari Sandbox
     │
     ├── Clone repository
     ├── Verify base branch
     ├── Detect project type
     ├── Detect test framework
     ├── Select relevant context
     ├── Install dependencies
     └── Run tests
             │
             ▼
        Claude Code
             │
             ├── Investigate failure
             └── Generate structured repair
             │
             ▼
        Apply source changes
             │
             ▼
        Run tests again
             │
        ┌────┴────┐
        │         │
      FAIL      PASS
        │         │
      Retry       ▼
               Git safety
                  │
                  ▼
               Commit
                  │
                  ▼
                Push
                  │
                  ▼
           Verify remote commit
                  │
                  ▼
           GitHub Pull Request
```

## What PatchPilot Does

PatchPilot automates the repetitive parts of a software-maintenance workflow:

1. Reads a GitHub Issue.
2. Creates an isolated Solari sandbox.
3. Clones the target repository.
4. Verifies the configured base branch.
5. Creates a dedicated repair branch.
6. Detects the project type and language.
7. Detects the test framework.
8. Discovers test files.
9. Selects relevant repository context.
10. Installs project dependencies.
11. Runs the existing test suite.
12. Sends the failure and relevant context to Claude Code.
13. Receives a structured repair.
14. Validates the proposed files and paths.
15. Applies the source-code changes.
16. Runs the tests again.
17. Retries failed repairs when configured.
18. Validates the resulting Git diff.
19. Commits the repair.
20. Verifies the local commit hash.
21. Pushes the repair branch.
22. Verifies the remote commit hash.
23. Creates a GitHub Pull Request.

PatchPilot is deliberately conservative: if the repair cannot be verified safely, it does not create a Pull Request.

## Architecture

The project is divided into focused modules:

```text
app/
├── agent.py      # Claude Code integration and response validation
├── config.py     # Runtime configuration and validation
├── context.py    # Relevant-file selection and context budgeting
├── github.py     # Git/GitHub operations and verification
├── issues.py     # GitHub Issue retrieval and repair prompts
├── main.py       # Main PatchPilot orchestration
├── project.py    # Project/language detection
├── safety.py     # Repair and Git diff safety checks
├── solari.py     # Solari sandbox operations
└── tests.py      # Test discovery, commands and result parsing
```

## Supported Projects

PatchPilot currently supports:

| Project | Detection | Package Manager | Test Framework |
|---|---|---|---|
| Python | `requirements.txt`, `pyproject.toml`, `setup.py`, etc. | pip | pytest |
| Node.js | `package.json` | npm | npm |
| Java / Maven | `pom.xml` | Maven | Maven |
| Java / Gradle | `build.gradle`, `build.gradle.kts` | Gradle | Gradle |
| Go | `go.mod` | Go Modules | Go |
| Rust | `Cargo.toml` | Cargo | Cargo |

Test discovery supports language-specific conventions including Python, JavaScript, Java, Go, and Rust test filenames.

## Claude Code Integration

Claude Code is used to investigate the failing project and propose source-code repairs.

PatchPilot expects a structured response containing:

```json
{
  "explanation": "Short explanation of the root cause",
  "changes": [
    {
      "file": "src/example.py",
      "code": "complete corrected source code"
    }
  ]
}
```

The response is validated before any changes are written to the repository.

Validation includes:

- JSON/structured-response validation
- Required fields
- Non-empty explanation
- Non-empty repair list
- File-path validation
- Duplicate-file detection
- Test-file protection
- Maximum generated-code size
- Semantic repair validation

## Context Management

PatchPilot does not blindly send an entire repository to Claude.

Relevant context is selected using:

- GitHub Issue information
- Test failures
- Test files
- Source files
- Project type
- Test framework
- Repository structure

Context is bounded by configurable limits:

```text
Maximum context files
Maximum total context characters
Maximum characters per file
```

This keeps prompts focused and predictable.

## Multi-File Repairs

A repair can modify multiple source files when necessary.

PatchPilot validates that:

- Every expected file actually changed.
- No unexpected files changed.
- Test files were not modified.
- The Git diff contains exactly the expected repair files.

## Safety

PatchPilot includes multiple safety layers.

### Test protection

Claude is prevented from targeting test files such as:

```text
test_*.py
*_test.py
*.test.js
*.spec.js
*Test.java
Test*.java
*_test.go
*_test.rs
```

### Path validation

Unsafe paths such as these are rejected:

```text
../file.py
../../file.py
/work/file.py
C:\file.py
\\server\file.py
```

### Git diff validation

Before committing, PatchPilot verifies:

- Changes actually exist.
- Only expected files changed.
- Test files were not modified.
- The diff contains the expected files.

### Branch verification

The repository's base branch is verified immediately after cloning before a repair branch is created.

### Commit verification

After committing, PatchPilot verifies that `HEAD` matches the expected commit hash.

### Remote verification

After pushing, PatchPilot verifies that the remote branch points to the same commit.

## Retry System

PatchPilot can retry a repair when the first attempt does not resolve the test failure.

For each failed attempt:

```text
Test failure
     ↓
Reset repository
     ↓
Re-read current state
     ↓
Provide failure information to Claude
     ↓
Generate another repair
     ↓
Run tests
```

The maximum number of attempts is configurable.

Default:

```text
3 attempts
```

## Configuration

Current defaults are:

```text
Repository path:
    /work/patchpilot

Base branch:
    master

Maximum repair attempts:
    3

Maximum context files:
    20

Maximum total context characters:
    30000

Maximum characters per file:
    12000
```

These values can be overridden from the command line.

## Installation

Create and activate the Python virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Install the project dependencies:

```powershell
pip install -r requirements.txt
```

Make sure the required external tools are available:

- Git
- GitHub CLI (`gh`)
- Claude Code
- Solari Sandbox access

Authenticate GitHub CLI:

```powershell
gh auth login
```

## Environment Variables

PatchPilot requires credentials for the external services it uses.

### Solari

```text
SOLARI_API_KEY
```

### GitHub

```text
GITHUB_TOKEN
```

For example, when GitHub CLI is authenticated:

```powershell
$env:GITHUB_TOKEN = (gh auth token)
```

Never commit API keys, tokens, or other credentials to the repository.

## Usage

Basic usage:

```powershell
python app\main.py OWNER/REPOSITORY ISSUE_NUMBER
```

Example:

```powershell
python app\main.py Cosmicrider1166/patchpilot-demo 4
```

### Runtime options

Maximum repair attempts:

```powershell
python app\main.py OWNER/REPOSITORY ISSUE_NUMBER --max-attempts 5
```

Maximum context files:

```powershell
python app\main.py OWNER/REPOSITORY ISSUE_NUMBER --max-context-files 10
```

Maximum total context size:

```powershell
python app\main.py OWNER/REPOSITORY ISSUE_NUMBER --max-context-chars 20000
```

Maximum context size per file:

```powershell
python app\main.py OWNER/REPOSITORY ISSUE_NUMBER --max-file-context-chars 8000
```

Invalid configuration values are rejected before the PatchPilot workflow begins.

## Testing

Run the complete test suite with:

```powershell
$env:PYTHONPATH="$PWD\app"
python -m pytest -q
```

The current regression baseline is:

```text
60 passed
```

The project may display deprecation warnings from the Solari dependency stack. These warnings originate from external dependencies and are separate from PatchPilot test failures.

## Example

Consider a repository containing:

```python
def add(a, b):
    return a - b
```

and a test:

```python
def test_add():
    assert add(10, 20) == 30
```

A GitHub Issue reports that addition is broken.

PatchPilot can:

```text
1. Read the GitHub Issue
2. Clone the repository into Solari
3. Verify the base branch
4. Create a repair branch
5. Detect Python/pytest
6. Run the failing test
7. Select relevant context
8. Ask Claude to investigate
9. Receive a structured repair
10. Validate the repair
11. Apply the source change
12. Run the tests again
13. Validate the Git diff
14. Commit the repair
15. Verify the commit
16. Push the branch
17. Verify the remote commit
18. Create a Pull Request
```

The resulting Pull Request can then be reviewed by a human developer.

## Design Principles

### Verify, don't assume

AI-generated code is never considered correct simply because Claude produced it. The repository's tests must validate the repair.

### Minimize changes

Claude is instructed to make the smallest source changes necessary.

### Protect tests

Tests are treated as validation infrastructure rather than repair targets.

### Isolate execution

Repository execution takes place inside a Solari sandbox.

### Bound AI context

Repository context is selected and size-limited before being sent to Claude.

### Verify Git state

Branches, changed files, diffs, commits, and remote state are explicitly checked.

### Fail safely

If a repair cannot be verified, PatchPilot fails rather than creating an unverified Pull Request.

## Current Status

PatchPilot currently implements an end-to-end autonomous software-repair workflow:

```text
GitHub Issue
    ↓
Issue Analysis
    ↓
Isolated Solari Sandbox
    ↓
Repository Clone
    ↓
Base Branch Verification
    ↓
Project Detection
    ↓
Test Detection
    ↓
Dependency Installation
    ↓
Test Execution
    ↓
Context Selection
    ↓
Claude Investigation
    ↓
Structured Repair
    ↓
Repair Validation
    ↓
Source Changes
    ↓
Test Verification
    ↓
Retry if Necessary
    ↓
Git Diff Safety
    ↓
Commit Verification
    ↓
Remote Verification
    ↓
Pull Request
```

## Limitations

PatchPilot is currently a project/research implementation rather than a production autonomous software-maintenance platform.

Current limitations include:

- Supported ecosystems are limited to the detected project types.
- Test-framework detection relies on repository conventions.
- Claude-generated repairs can still be incorrect.
- Unusual build systems may require additional support.
- Dependency installation depends on the sandbox environment.
- External service availability can affect execution.
- GitHub and Solari credentials must be configured correctly.

The system intentionally prefers a failed repair over an unsafe or unverified Pull Request.

## Future Improvements

Potential future improvements include:

- Broader language and build-system support
- More advanced test-failure extraction
- Improved context ranking
- Patch/diff-based AI responses
- Static-analysis integration
- CI/CD integration
- GitHub App authentication
- Persistent repair history
- Observability and metrics
- Human approval workflows
- Repair-quality evaluation
- Parallel issue processing

## License

This project is currently developed as a personal engineering project and demonstration of autonomous software-repair workflows.
