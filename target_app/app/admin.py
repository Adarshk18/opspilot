import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app import chaos
from app.core.config import get_settings


def require_admin(x_admin_token: Annotated[str | None, Header()] = None) -> None:
    expected = get_settings().admin_token
    if not expected or x_admin_token is None or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=404)


router = APIRouter(prefix="/admin/chaos", dependencies=[Depends(require_admin)])


@router.get("")
async def get_chaos() -> dict:
    return {"config": chaos.get_config().model_dump(), "leaked_mb": chaos.leaked_mb()}


@router.put("")
async def set_chaos(config: chaos.ChaosConfig) -> dict:
    chaos.set_config(config)
    return {"config": config.model_dump()}


@router.delete("")
async def reset_chaos() -> dict:
    chaos.reset()
    return {"config": chaos.get_config().model_dump()}