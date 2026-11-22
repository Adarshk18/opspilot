import asyncio
import json
import sys

from app.agent.loop import run_agent


def show_event(event: dict) -> None:
    print(f"\n→ {event['tool']}({event['arguments']})")
    print(f"  ← {json.dumps(event['result'], default=str)[:400]}")


async def main() -> None:
    question = " ".join(sys.argv[1:]) or "ShopLite users report problems. Investigate."
    result = await run_agent(question, on_event=show_event)
    print("\n" + "=" * 70)
    print(result["answer"])
    print("=" * 70)
    print(f"model: {result['model']}  usage: {result['usage']}")


if __name__ == "__main__":
    asyncio.run(main())