import asyncio
import json
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

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
        suggestion = "/" + path.lstrip("/")
        hint = f" Did you mean '{suggestion}'?" if suggestion in ALLOWED_PROBE_PATHS else ""
        return {"error": f"Path '{path}' is not allowed. Use one of {ALLOWED_PROBE_PATHS}.{hint}"}

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

    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
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

