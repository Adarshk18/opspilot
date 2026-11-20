import logging
import time
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.logging import setup_logging
from app.core.request_context import request_id_var
from app.db.session import check_database, engine
from app.routes import router

settings = get_settings()
setup_logging(settings.service_name, settings.log_level)

logger = logging.getLogger("shoplite.http")

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await engine.dispose()

app = FastAPI(title="Shoplite", lifespan=lifespan)
app.include_router(router)

@app.middleware("http")
async def request_logging(request: Request, call_next):
    """Runs around every request: assigns an ID, times it, and logs the result."""
    request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
    token = request_id_var.set(request_id)
    start = time.perf_counter()
    status_code = 500  # assume failure until we get a real response

    try:
        response = await call_next(request)
        status_code = response.status_code
        response.headers["x-request-id"] = request_id
        return response
    except Exception:
        logger.exception("unhandled exception")
        return JSONResponse(
            status_code=500,
            content={"error": "internal_server_error", "request_id": request_id},
            headers={"x-request-id": request_id},
        )
    finally:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        level = logging.ERROR if status_code >= 500 else logging.INFO
        logger.log(
            level,
            "request completed",
            extra={"fields": {
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "duration_ms": duration_ms,
            }},
        )
        request_id_var.reset(token)  # always the very last step

    


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}

@app.get("/health/ready")
async def ready() -> JSONResponse:
    db_ok = await check_database()
    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={"status": "ready" if db_ok else "not_ready", "database": "ok" if db_ok else "unreachable"},
    )


@app.get("/debug/error")
async def debug_error() -> None:
    """Deliberately crashes, so we can see what an error log looks like. Local only."""
    if settings.environment != "local":
        raise HTTPException(status_code=404)
    raise RuntimeError("Deliberate test failure")
