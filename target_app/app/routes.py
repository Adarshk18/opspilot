import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models import Order, Product
from app.schemas import OrderCreate, OrderOut, ProductOut
from sqlalchemy import select, text
from app import chaos, payments


router = APIRouter()
logger = logging.getLogger("shoplite.orders")

SessionDep = Annotated[AsyncSession, Depends(get_session)]

@router.get("/products", response_model=list[ProductOut])
async def list_products(session: SessionDep)-> list[Product]:
    chaos.maybe_leak()
    cfg = chaos.get_config()
    if cfg.db_latency_seconds > 0:
        await session.execute(text("SELECT pg_sleep(:s)"), {"s": cfg.db_latency_seconds})
    result = await session.execute(select(Product).order_by(Product.price))
    return list(result.scalars().all())



@router.post("/orders", response_model=OrderOut, status_code=201)
async def create_order(payload: OrderCreate, session: SessionDep)-> Order:
    await payments.authorize(payload.product_id, payload.quantity)
    async with session.begin():
        product = await session.scalar(
            select(Product).where(Product.id == payload.product_id).with_for_update()
        )

        if product is None:
            raise HTTPException(status_code=404, detail="Product not found")

        hold = chaos.get_config().hold_connection_seconds
        if hold > 0:
            await session.execute(text("SELECT pg_sleep(:s)"), {"s": hold})

        if product.stock < payload.quantity:
            logger.warning(
                "insufficient stock",
                extra={"fields":{
                    "product_id": product.id,
                    "requested": payload.quantity,
                    "available": product.stock,
                }},
            )    
            raise HTTPException(status_code=409, detail="Insufficient stock")

        product.stock -= payload.quantity
        order = Order(
            product_id=product.id,
            quantity=payload.quantity,
            total_paise=product.price_paise * payload.quantity,
        )
        session.add(order)
    logger.info(
        "order placed",
        extra={"fields":{
            "order_id": order.id,
            "product_id": order.product_id,
            "quantity": order.quantity,
            "total_paise": order.total_paise,
        }},
    )    
    return order


