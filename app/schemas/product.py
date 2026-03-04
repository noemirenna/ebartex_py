"""
Pydantic schemas for products. Monetary fields use Decimal to avoid float rounding issues.
"""
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ProductCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=10_000)
    price: Decimal = Field(default=Decimal("0"), ge=0)

    model_config = ConfigDict(extra="forbid")


class ProductResponse(BaseModel):
    id: int
    name: str
    description: str
    price: Decimal

    model_config = ConfigDict(from_attributes=True)


class ProductListResponse(BaseModel):
    items: list[ProductResponse]
    total: Optional[int] = None
    limit: int
    offset: int
