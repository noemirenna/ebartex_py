"""
Pydantic schemas for auctions (request/response). Pagination for list.
Monetary fields use Decimal to avoid float rounding issues.
"""
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AuctionCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=10_000)
    seller_username: str = Field(..., min_length=1, max_length=255)
    starting_price: Decimal = Field(..., ge=0)
    reserve_price: Optional[Decimal] = Field(None, ge=0)
    start_time: datetime
    end_time: datetime
    product_id: Optional[str] = Field(None, max_length=100)
    game: list[str] = Field(default_factory=list, max_length=50)
    card_name: list[str] = Field(default_factory=list, max_length=50)
    condition: list[str] = Field(default_factory=list, max_length=50)
    images: list[str] = Field(default_factory=list, max_length=20)

    model_config = ConfigDict(extra="forbid")


class AuctionResponse(BaseModel):
    id: int
    title: str
    description: str
    seller_username: Optional[str] = None
    starting_price: Decimal
    current_price: Decimal
    reserve_price: Optional[Decimal] = None
    start_time: datetime
    end_time: datetime
    status: str
    highest_bidder_id: Optional[UUID] = None
    product_id: Optional[str] = None
    game: list[str] = Field(default_factory=list)
    card_name: list[str] = Field(default_factory=list)
    condition: list[str] = Field(default_factory=list)
    images: list[str] = Field(default_factory=list)
    winner_id: Optional[UUID] = None
    reserve_not_reached_message: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AuctionListResponse(BaseModel):
    items: list[AuctionResponse]
    total: Optional[int] = None
    limit: int
    offset: int
