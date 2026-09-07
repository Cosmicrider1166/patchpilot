import asyncio

from agent import (
    generate_repair,
    parse_repair_response,
)


async def main():

    prompt = """You are a Python debugging agent.

A Python function is broken.

Current code:

def add(a, b):
    return a - b

The test expects:

add(10, 20) == 30

Return ONLY valid JSON with exactly these fields:

{
  "file": "calculator.py",
  "explanation": "Brief explanation of the bug.",
  "code": "Complete corrected source code."
}

Do not use Markdown.
Do not use code fences.
Do not include text outside the JSON object.
"""

    print(
        "=== Testing structured Claude response ==="
    )

    response = await generate_repair(
        prompt
    )

    print()
    print(
        "=== Raw Claude response ==="
    )

    print(
        response
    )

    print()
    print(
        "=== Parsing response ==="
    )

    repair = parse_repair_response(
        response
    )

    print(
        "File:",
        repair["file"],
    )

    print(
        "Explanation:",
        repair["explanation"],
    )

    print(
        "Code:"
    )

    print(
        repair["content"]
    )

    print()
    print(
        "SUCCESS: Structured Claude repair works."
    )


if __name__ == "__main__":
    asyncio.run(
        main()
    )
    