from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.db.session import check_database, engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Code before yield runs at startup. Code after yield runs at shutdown."""
    yield
    await engine.dispose()  # close all pooled connections cleanly


app = FastAPI(title=settings.app_name, lifespan=lifespan)


@app.get("/health/live")
async def live() -> dict[str, str]:
    """Liveness: is the process running at all?"""
    return {"status": "ok", "environment": settings.environment}


@app.get("/health/ready")
async def ready() -> JSONResponse:
    """Readiness: can this instance actually serve requests right now?"""
    db_ok = await check_database()
    return JSONResponse(
        status_code=200 if db_ok else 503,
        content={
            "status": "ready" if db_ok else "not_ready",
            "database": "ok" if db_ok else "unreachable",
        },
    )