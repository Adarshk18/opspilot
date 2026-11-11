from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name)


@app.get("/health")
def health() -> dict[str, str]:
    """Health check endpoint. Docker, Render, and monitoring tools call this to see if the service is alive."""
    return {"status": "ok", "environment": settings.environment}