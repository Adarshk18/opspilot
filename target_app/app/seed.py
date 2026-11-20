import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal, engine
from app.models import Product

PRODUCTS = [
    {"sku": "KB-001", "name": "Mechanical Keyboard", "price_paise": 499900, "stock": 50},
    {"sku": "HUB-002", "name": "USB-C Hub", "price_paise": 189900, "stock": 100},
    {"sku": "MON-003", "name": "27-inch Monitor", "price_paise": 1849900, "stock": 5},
]


async def seed() -> None:
    async with SessionLocal() as session, session.begin():
        for data in PRODUCTS:
            existing_id = await session.scalar(
                select(Product.id).where(Product.sku == data["sku"])
            )
            if existing_id is None:
                session.add(Product(**data))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())