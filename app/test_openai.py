import asyncio

from openai import AsyncOpenAI


async def main():
    client = AsyncOpenAI()

    response = await client.responses.create(
        model="gpt-5.6-luna",
        input="Explain in one sentence what a Python function is.",
    )

    print("=== OpenAI response ===")
    print(response.output_text)


if __name__ == "__main__":
    asyncio.run(main())

    