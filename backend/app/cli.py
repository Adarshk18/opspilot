import asyncio
import json
import sys

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.errors import GraphRecursionError

from app.agent.graph import build_graph

RECURSION_LIMIT = 20


async def main() -> None:
    question = " ".join(sys.argv[1:]) or "ShopLite users report problems. Investigate."
    graph = build_graph()
    usage = {"input_tokens": 0, "output_tokens": 0, "tool_calls": 0}
    answer = ""

    try:
        async for update in graph.astream(
            {"messages": [HumanMessage(question)]},
            config={"recursion_limit": RECURSION_LIMIT},
            stream_mode="updates",
        ):
            for node_output in update.values():
                for message in node_output["messages"]:
                    if isinstance(message, AIMessage):
                        if message.usage_metadata:
                            usage["input_tokens"] += message.usage_metadata["input_tokens"]
                            usage["output_tokens"] += message.usage_metadata["output_tokens"]
                        for call in message.tool_calls:
                            usage["tool_calls"] += 1
                            print(f"\n→ {call['name']}({json.dumps(call['args'])})")
                        if not message.tool_calls:
                            answer = message.content if isinstance(message.content, str) else str(message.content)
                    elif isinstance(message, ToolMessage):
                        print(f"  ← {str(message.content)[:400]}")
    except GraphRecursionError:
        answer = "Stopped: step limit reached without a final answer."

    print("\n" + "=" * 70)
    print(answer)
    print("=" * 70)
    print(f"usage: {usage}")


if __name__ == "__main__":
    asyncio.run(main())