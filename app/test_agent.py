import asyncio

from agent import (
    build_repair_prompt,
    generate_repair,
    parse_repair_response,
    validate_repair_target,
)


async def main():
    project = {
        "calculator.py": """def add(a, b):
    return a - b
""",
        "test_calculator.py": """from calculator import add


def test_add():
    assert add(10, 20) == 30
""",
    }

    test_result = {
        "passed": False,
        "exit_code": 1,
        "stdout": (
            "FAILED test_calculator.py::test_add\n"
            "E assert -10 == 30"
        ),
    }

    print("=== Building Claude prompt ===")

    prompt = build_repair_prompt(
        project,
        test_result,
    )

    print("Prompt created successfully.")
    print()

    print("=== Asking Claude ===")

    response = await generate_repair(
        prompt
    )

    print("Claude response:")
    print(response)
    print()

    print("=== Parsing Claude response ===")

    repair = parse_repair_response(
        response
    )

    print(
        "Selected file:",
        repair["file"],
    )

    print(
        "Code extracted successfully."
    )

    print()

    print("=== Validating repair target ===")

    target = validate_repair_target(
        repair["file"]
    )

    print(
        "Validated target:",
        target,
    )

    print()
    print(
        "SUCCESS: agent.py is working."
    )


if __name__ == "__main__":
    asyncio.run(main())
    