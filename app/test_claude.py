import subprocess


def main():
    prompt = (
        "You are helping develop PatchPilot. "
        "Explain in one sentence what a Python unit test is."
    )

    result = subprocess.run(
        [
            "claude",
            "-p",
            prompt,
        ],
        capture_output=True,
        text=True,
    )

    print("=== Claude exit code ===")
    print(result.returncode)

    print("=== Claude response ===")
    print(result.stdout)

    if result.stderr:
        print("=== Claude stderr ===")
        print(result.stderr)


if __name__ == "__main__":
    main()
    