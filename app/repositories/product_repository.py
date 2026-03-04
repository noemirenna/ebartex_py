"""
Product repository: async CRUD and search. Uses AsyncSession.
"""
from typing import Optional
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.product import Product


class ProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        name: str,
        description: str = "",
        price: float = 0.0,
        created_by_user_id: Optional[UUID] = None,
    ) -> Product:
        product = Product(
            name=name,
            description=description,
            price=price,
            created_by_user_id=created_by_user_id,
        )
        self._session.add(product)
        await self._session.flush()
        await self._session.refresh(product)
        return product

    async def find_by_id(self, id: int) -> Optional[Product]:
        result = await self._session.execute(select(Product).where(Product.id == id))
        return result.scalar_one_or_none()

    async def search(
        self,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Product], int]:
        """Search products; returns (items, total_count) in one query via COUNT(*) OVER ().
        Offset is clamped to MAX_PAGINATION_OFFSET to avoid O(offset) cost and DoS.
        Note: COUNT OVER loads one window of rows; if limit or join complexity grows, consider keyset pagination."""
        max_offset = get_settings().MAX_PAGINATION_OFFSET
        offset = min(offset, max_offset)
        total_col = func.count(Product.id).over().label("_total")
        stmt = select(Product, total_col)
        if q and q.strip():
            term = f"%{q.strip().lower()}%"
            stmt = stmt.where(
                or_(Product.name.ilike(term), Product.description.ilike(term))
            )
        stmt = stmt.order_by(Product.id).limit(limit).offset(offset)
        result = await self._session.execute(stmt)
        rows = result.all()
        products = [row[0] for row in rows]
        total = int(rows[0][1]) if rows else 0
        return products, total
