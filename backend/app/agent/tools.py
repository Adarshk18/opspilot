from typing import Literal

from langchain_core.tools import tool

from app.tools import github, shop


@tool
async def get_health()->dict:
    """Check Shoplite readiness: whether the services responds and its database is reachable."""
    return await shop.get_health()


@tool
async def get_metrics()->dict:
    """Current Shoplite process metrics: memory RSS in MB, DB pool size, and connections checked out."""
    return await shop.get_metrics()


@tool(parse_docstring=True)
async def probe_endpoint(
        path: Literal["/products", "health/live", "/health/ready"],
        requests: int = 10,
    )->dict:
    """Send concurrent GET requests to a Shoplite endpoint and resport status codes and latency. Read-only.
    
    Args:
        path: Endpoint to probe.
        requests: Number of requests to send, 1 to 20.
    """

    return await shop.probe_endpoint(path,requests)


@tool(parse_docstring=True)
async def search_logs(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] | None = None,
    path: str | None = None,
    contains: str | None = None,
    minutes: int = 15,
    limit: int = 5,
)-> dict:
    """Search recent ShopLite JSON logs. Returns counts across ALL matches (by level, status code,
    exception type), first and last seen times, and the most recent samples.
    
    Args:
        level: Only return logs at this level.
        path: Exact request path, for example /orders.
        contains: Case-insensitive text searched across every field, including tracebacks.
        minutes: How far back to search, 1 to 120.
        limit: Number of sample logs to return, 1 to 20.
    """

    return await shop.search_logs(level, path, contains, minutes, limit)

@tool(parse_docstring=True)
async def get_recent_deploys(hours: int=24)->dict:
    """List recent ShopLite deploys (commits to main that changed the app), newest first.
    Use to check whether a code change lines up with when a problem started.

    Args:
        hours: How far back to look, 1 to 168.
    """
    return await github.get_recent_deploys(hours)


TOOLS = [get_health, get_metrics, probe_endpoint,search_logs,get_recent_deploys]
