"""
Product business logic: search, get by id, create. Pagination on list.
Accepts Decimal for price from API; converts to float at repository boundary (DB uses float).
"""
from decimal import Decimal
from typing import Any, Optional, Union
from uuid import UUID

from app.repositories.product_repository import ProductRepository


class ProductService:
    def __init__(self, product_repo: ProductRepository) -> None:
        self._product_repo = product_repo

    async def search_products(
        self,
        q: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Returns (items, total_count) for pagination."""
        products, total = await self._product_repo.search(q=q, limit=limit, offset=offset)
        items = [
            {"id": p.id, "name": p.name, "description": p.description or "", "price": p.price}
            for p in products
        ]
        return items, total

    async def get_product_by_id(self, id: int) -> Optional[dict[str, Any]]:
        product = await self._product_repo.find_by_id(id)
        if not product:
            return None
        return {"id": product.id, "name": product.name, "description": product.description or "", "price": product.price}

    async def create_product(
        self,
        name: str,
        description: str = "",
        price: Union[Decimal, float] = 0,
        created_by_user_id: Optional[UUID] = None,
    ) -> dict[str, Any]:
        _price = float(price) if isinstance(price, Decimal) else price
        product = await self._product_repo.create(
            name=name,
            description=description,
            price=_price,
            created_by_user_id=created_by_user_id,
        )
        return {"id": product.id, "name": product.name, "description": product.description or "", "price": product.price}
