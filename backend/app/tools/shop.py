import asyncio
import json
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib  import Path

import httpx

from app.core.config import get_settings


settings = get_settings()


ALLOWED_PROBE_PATHS = ["/products", "/health/live", "/health/ready"]
MAX_EXCEPTION_CHARS = 600


async def _get_json(path: str)-> dict:
    try:
        async with httpx.AsyncClient(base_url=settings.shop_base_url, timeout=10) as client:
            response = await client.get(path)
        return {"status_code": response.status_code, "body": response.json()}
    except (httpx.HTTPError, ValueError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}"}

async def get_health()-> dict:
    return await _get_json("/health/ready")


async def get_metrics()-> dict:
    return await _get_json("/metrics")


async def probe_endpoint(path: str, requests: int =10)-> dict:
    if path not in ALLOWED_PROBE_PATHS:
        return {"error": f"path not allowed; use one of {ALLOWED_PROBE_PATHS}"}
    requests =max(1,min(requests,20))

    async with httpx.AsyncClient(base_url=settings.shop_base_url, timeout=15) as client:
        async def one()-> tuple[str, float]:
            start = time.perf_counter()
            try:
                response = await client.get(path)
                outcome = str(response.status_code)
            except httpx.HTTPError as exc:
                outcome = type(exc).__name__
            return outcome, (time.perf_counter()-start) * 1000

        results = await asyncio.gather(*(one() for _ in range(requests)))  

    latencies = sorted(ms for _, ms in results)
    return {
        "path": path,
        "requests": requests,
        "outcomes": dict(Counter(outcome for outcome, _ in results)),
        "p50_ms": round(latencies[len(latencies) // 2]),
        "max_ms": round(latencies[-1]),
    }         


def _exception_type(traceback_text: str) -> str:
    lines = traceback_text.strip().splitlines()
    return lines[-1].split(":", 1)[0] if lines else "unknown"


def _search_logs_sync(
    level: str | None, path: str | None, contains: str | None, minutes: int, limit: int
) -> dict:
    log_file = Path(settings.shop_log_path)
    if not log_file.exists():
        return {"error": f"log file not found at {log_file}"}

    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    needle = contains.lower() if contains else None
    matches: list[dict] = []

    with log_file.open() as f:
        for line in f:
            try:
                record = json.loads(line)
                timestamp = datetime.fromisoformat(record["timestamp"])
            except (json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
            if timestamp < cutoff:
                continue
            if level and record.get("level") != level:
                continue
            if path and record.get("path") != path:
                continue
            if needle and needle not in json.dumps(record).lower():
                continue
            matches.append(record)

    samples = matches[-limit:]
    for record in samples:
        if "exception" in record:
            record["exception"] = record["exception"][-MAX_EXCEPTION_CHARS:]

    return {
        "total_matches": len(matches),
        "first_seen": matches[0]["timestamp"] if matches else None,
        "last_seen": matches[-1]["timestamp"] if matches else None,
        "by_level": dict(Counter(r.get("level") for r in matches)),
        "by_status_code": dict(Counter(r["status_code"] for r in matches if "status_code" in r)),
        "by_exception": dict(Counter(_exception_type(r["exception"]) for r in matches if "exception" in r)),
        "samples": samples,
    }


async def search_logs(
    level: str | None = None,
    path: str | None = None,
    contains: str | None = None,
    minutes: int = 15,
    limit: int = 5,
) -> dict:
    minutes = max(1, min(minutes, 120))
    limit = max(1, min(limit, 20))
    return await asyncio.to_thread(_search_logs_sync, level, path, contains, minutes, limit)

TOOL_FUNCTIONS = {
    "get_health": get_health,
    "get_metrics": get_metrics,
    "probe_endpoint": probe_endpoint,
    "search_logs": search_logs,
}

NO_PARAMS = {"type": "object", "properties": {}, "asdditionalProperties": False}


TOOLS =[
    {
        "type": "function",
        "function":{
            "name": "get_health",
            "description": "Check Shoplite readiness: whether the service and its database is reachable.",
            "parameters": NO_PARAMS,
        }
    },
    {
        "type": "function",
        "function":{
            "name": "get_metrics",
            "description": "Current Shoplite process metrics: memory RSS in MB, DB pool size, and connections currently checked out.",
            "parameters": NO_PARAMS,
        }
    },
    {
        "type": "function",
        "function":{
            "name": "probe_endpoint",
            "description": (
                "Send concurrent GET requests to a ShopLite endpoint and report status codes and latency. "
                "Use to measure what users experience right now. Read-only."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "enum": ALLOWED_PROBE_PATHS},
                    "requests": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_logs",
            "description": (
                "Search recent ShopLite JSON logs. Returns counts across ALL matches "
                "(by level, status code, exception type), first/last seen times, and the most recent samples. "
                "'contains' searches every field (message, path, request_id, traceback). "
                "'path' filters to an exact path like /orders."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]},
                    "path": {"type": "string", "description": "Exact request path, e.g. /orders"},
                    "contains": {"type": "string", "description": "Case-insensitive text searched across all fields."},
                    "minutes": {"type": "integer", "minimum": 1, "maximum": 120},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 20},
                },
                "additionalProperties": False,
            },
        },
    },
]
        

    