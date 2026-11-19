import logging
import time
import uuid
import token

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from app.core.logging import setup_logging
from app.core.config import get_settings

from app.core.request_context import request_id_var

settings = get_settings()
setup_logging(settings.service_name, settings.log_level)

logger = logging.getLogger("shoplite.http")

app = FastAPI(title="Shoplite")


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

    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    response.headers["x-request-id"] = request_id
    logger.info(
        "request completed",
        extra={"fields": {
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
        }},
    )
    return response


@app.get("/health/live")
async def live() -> dict[str, str]:
    return {"status": "ok", "service": settings.service_name}


@app.get("/products")
async def list_products() -> list[dict]:
    # Temporary hard-coded data. Next lesson, this comes from the database.
    return [
        {"id": 1, "name": "Mechanical Keyboard", "price": 4999},
        {"id": 2, "name": "USB-C Hub", "price": 1899},
    ]


@app.get("/debug/error")
async def debug_error() -> None:
    """Deliberately crashes, so we can see what an error log looks like. Local only."""
    if settings.environment != "local":
        raise HTTPException(status_code=404)
    raise RuntimeError("Deliberate test failure")
