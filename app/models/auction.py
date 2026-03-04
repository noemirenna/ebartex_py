"""
SQLAlchemy model for auctions (marketplace). Status: DRAFT | ACTIVE | CLOSED.
"""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from sqlalchemy import BigInteger, DateTime, Float, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database import Base


class Auction(Base):
    __tablename__ = "auctions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    seller_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    starting_price: Mapped[float] = mapped_column(Float, nullable=False)
    current_price: Mapped[float] = mapped_column(Float, nullable=False)
    reserve_price: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    start_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")  # DRAFT | ACTIVE | CLOSED
    highest_bidder_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    created_by_user_id: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    product_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    game: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True, default=list)
    card_name: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True, default=list)
    condition: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True, default=list)
    images: Mapped[Optional[List[str]]] = mapped_column(ARRAY(Text), nullable=True, default=list)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # relationship to bids (optional, for ORM loading)
    # bids: Mapped[list["Bid"]] = relationship("Bid", back_populates="auction", lazy="selectin")
