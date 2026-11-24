from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOLS
from app.core.config import get_settings


def build_graph():
    settings = get_settings()

    llm= ChatOpenAI(
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        timeout=90,
        max_retries=0
    )
    llm_with_tools = llm.bind_tools(TOOLS)

    async def agent(state: MessagesState)->dict:
        messages = [SystemMessage(SYSTEM_PROMPT), *state["messages"]]
        response = await llm_with_tools.ainvoke(messages)
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", agent)
    builder.add_node("tools", ToolNode(TOOLS))

    builder.add_edge(START, "agent")
    builder.add_conditional_edges("agent", tools_condition)
    builder.add_edge("tools", "agent")

    return builder.compile()


