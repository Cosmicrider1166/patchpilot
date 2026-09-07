from issues import (
    get_issue,
    build_issue_prompt,
)


REPO_OWNER = "Cosmicrider1166"
REPO_NAME = "patchpilot-demo"

ISSUE_NUMBER = 4


def main():

    print("=== Reading GitHub Issue ===")

    issue = get_issue(
        REPO_OWNER,
        REPO_NAME,
        ISSUE_NUMBER,
    )

    print()
    print("Issue number:", issue["number"])
    print("Issue title:", issue["title"])
    print()
    print("Issue description:")
    print(issue["body"])

    print()
    print("=== Building Issue Prompt ===")

    prompt = build_issue_prompt(issue)

    print()
    print(prompt)

    print()
    print("SUCCESS: GitHub Issue reader is working.")


if __name__ == "__main__":
    main()
    