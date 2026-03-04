"""
Auction business logic: create, list, get by id. Validates product exists when product_id given.
Accepts Decimal for monetary fields from API; converts to float at repository boundary (DB uses float).
"""
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from app.models.auction import Auction
from app.repositories.auction_repository import AuctionRepository
from app.repositories.product_repository import ProductRepository
from app.services.auction_domain import (
    _to_datetime,
    auction_to_dict,
    compute_status,
    STATUS_ACTIVE,
    STATUS_CLOSED,
    STATUS_DRAFT,
    with_current_status,
    with_winner_info,
)
from app.utils.exceptions import (
    AuctionNotFoundError,
    InvalidAuctionDataError,
    InvalidIdError,
    ProductNotFoundError,
    ValidationError,
)


class AuctionService:
    """
    Auction CRUD and list. When product_repo is provided, create_auction validates product_id
    (exists and positive). When product_repo is None, product_id is not validated—caller must
    ensure validity or omit product_id.
    """

    def __init__(
        self,
        auction_repo: AuctionRepository,
        product_repo: Optional[ProductRepository] = None,
    ) -> None:
        self._auction_repo = auction_repo
        self._product_repo = product_repo

    async def create_auction(self, data: dict[str, Any]) -> dict[str, Any]:
        title = data.get("title")
        starting_price = data.get("starting_price")
        start_time = data.get("start_time")
        end_time = data.get("end_time")
        seller_username = data.get("seller_username")
        if not title or starting_price is None or not start_time or not end_time:
            raise InvalidAuctionDataError("Missing required fields: title, starting_price, start_time, end_time.")
        # seller_username is required and non-empty at API level (AuctionCreate schema)
        product_id = data.get("product_id")
        if product_id is not None and str(product_id).strip() and self._product_repo:
            try:
                pid = int(product_id) if isinstance(product_id, (int, str)) else 0
            except (ValueError, TypeError):
                raise InvalidIdError(f"product_id must be a valid integer, got: {product_id!r}.")
            if pid <= 0:
                raise InvalidIdError("product_id must be a positive integer.")
            if (await self._product_repo.find_by_id(pid)) is None:
                raise ProductNotFoundError(f"Product {product_id} not found.")
        start = _to_datetime(start_time)
        end = _to_datetime(end_time)
        if start is None or end is None:
            detail = {}
            if start is None and start_time is not None:
                detail["start_time"] = "Must be datetime or ISO 8601 string."
            if end is None and end_time is not None:
                detail["end_time"] = "Must be datetime or ISO 8601 string."
            raise ValidationError(
                "start_time and end_time must be datetime or ISO format string.",
                detail=detail if detail else None,
            )
        if end <= start:
            raise InvalidAuctionDataError("endTime must be after startTime.")
        _start = float(starting_price) if isinstance(starting_price, Decimal) else starting_price
        if _start < 0:
            raise InvalidAuctionDataError("startingPrice must be non-negative.")
        reserve_price = data.get("reserve_price")
        _reserve: Optional[float] = None
        if reserve_price is not None:
            _reserve = float(reserve_price) if isinstance(reserve_price, Decimal) else reserve_price
            if _reserve < 0:
                raise InvalidAuctionDataError("reservePrice must be non-negative.")
            if _reserve < _start:
                raise InvalidAuctionDataError("reservePrice must be >= startingPrice.")
        now = datetime.now(timezone.utc)
        status = STATUS_DRAFT if now < start else (STATUS_ACTIVE if now < end else STATUS_CLOSED)
        create_data = {
            "title": title,
            "description": data.get("description", ""),
            "seller_username": seller_username,
            "starting_price": _start,
            "current_price": _start,
            "reserve_price": _reserve,
            "start_time": start,
            "end_time": end,
            "status": status,
            "highest_bidder_id": None,
            "created_by_user_id": data.get("created_by_user_id"),
            "product_id": str(product_id) if product_id else None,
            "game": data.get("game") or [],
            "card_name": data.get("card_name") or [],
            "condition": data.get("condition") or [],
            "images": data.get("images") or [],
        }
        auction = await self._auction_repo.create(create_data)
        d = auction_to_dict(auction)
        return with_winner_info(with_current_status(d))

    async def list_auctions(
        self,
        q: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """Returns (items, total_count) for pagination. status filters by auction status (e.g. ACTIVE)."""
        auctions, total = await self._auction_repo.find_all(
            q=q, status=status, limit=limit, offset=offset
        )
        items = [with_winner_info(with_current_status(auction_to_dict(a))) for a in auctions]
        return items, total

    async def get_auction_by_id(self, id: int) -> dict[str, Any]:
        auction = await self._auction_repo.find_by_id(id)
        if not auction:
            raise AuctionNotFoundError()
        return with_winner_info(with_current_status(auction_to_dict(auction)))
