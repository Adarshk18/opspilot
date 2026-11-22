import json
from collections.abc import Callable

from app.core.config import get_settings
from app.llm.client import get_llm_client
from app.tools.shop import TOOL_FUNCTIONS, TOOLS

SYSTEM_PROMPT = """You are OpsPilot, an on-call SRE assistant investigating incidents in ShopLite, \
an online shop built with FastAPI and PostgreSQL.

How to investigate:
- Gather evidence with tools before concluding. Use health, metrics, logs, and latency probes.
- Compare against normal behaviour: healthy /products p50 latency is under 100 ms, \
and the database connection pool has 5 connections.
- Separate symptoms from causes. Cite the specific evidence (log messages, numbers) behind every claim.
- If evidence is insufficient, say so and state what you would check next.
- You can only observe. Never claim to have fixed anything.
- Focus on the last 15 minutes unless you have a reason to look further back; older events may be unrelated.
- An empty search result only means your filter matched nothing. Before concluding something did not happen, \
try a broader search.
- Report whether the problem is still happening, using first_seen and last_seen.

Final answer format:
Summary: one sentence.
Evidence: bullet list of observations with values.
Likely root cause: ...
Confidence: low, medium, or high, with the reason.
Suggested next steps: ..."""


async def execute_tool(name: str, raw_arguments: str) -> dict:
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        return {"error": f"unknown tool: {name}"}
    try:
        arguments = json.loads(raw_arguments or "{}")
    except json.JSONDecodeError:
        return {"error": "tool arguments were not valid JSON"}
    try:
        return await function(**arguments)
    except TypeError as exc:
        return {"error": f"invalid arguments: {exc}"}


async def run_agent(
    question: str,
    on_event: Callable[[dict], None] = lambda event: None,
    max_steps: int = 8,
) -> dict:
    settings = get_settings()
    client = get_llm_client()
    messages: list[dict] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    usage = {"prompt_tokens": 0, "completion_tokens": 0, "tool_calls": 0}

    for _ in range(max_steps):
        response = await client.chat.completions.create(
            model=settings.llm_model,
            messages=messages,
            tools=TOOLS,
        )
        if response.usage:
            usage["prompt_tokens"] += response.usage.prompt_tokens
            usage["completion_tokens"] += response.usage.completion_tokens

        message = response.choices[0].message
        messages.append(message.model_dump(exclude_none=True))

        if not message.tool_calls:
            return {"answer": message.content or "", "usage": usage, "model": response.model}

        for call in message.tool_calls:
            result = await execute_tool(call.function.name, call.function.arguments)
            usage["tool_calls"] += 1
            on_event({"tool": call.function.name, "arguments": call.function.arguments, "result": result})
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result, default=str),
            })

    return {"answer": "Stopped: reached the step limit without a final answer.", "usage": usage, "model": None}