"""
Auction endpoints: create, list (paginated), get by id. Rate limited.
Create requires authentication (Bearer).
"""
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from starlette.requests import Request

from app.core.config import get_settings
from app.core.dependencies import get_auction_service, get_current_user_id
from app.core.rate_limit import get_request, limiter
from app.schemas.auction import AuctionCreate, AuctionResponse, AuctionListResponse
from app.services.auction_service import AuctionService

router = APIRouter()
settings = get_settings()


@router.post(
    "/",
    response_model=dict,
    status_code=201,
    description="Create a new auction. Validates product_id if provided. Requires Bearer token.",
)
@limiter.limit("60/minute")
async def create_auction(
    request: Annotated[Request, Depends(get_request)],
    body: AuctionCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: AuctionService = Depends(get_auction_service),
):
    data = body.model_dump()
    data["created_by_user_id"] = user_id
    auction = await service.create_auction(data)
    return {"success": True, "data": auction}


@router.get(
    "/",
    response_model=dict,
    description="List auctions with optional search (q) and pagination.",
)
@limiter.limit("100/minute")
async def list_auctions(
    request: Annotated[Request, Depends(get_request)],
    q: Optional[str] = Query(None, max_length=200),
    status: Optional[str] = Query(None, description="Filter by status (e.g. ACTIVE, CLOSED, DRAFT)"),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    service: AuctionService = Depends(get_auction_service),
):
    offset = min(offset, settings.MAX_PAGINATION_OFFSET)
    items, total = await service.list_auctions(q=q, status=status, limit=limit, offset=offset)
    return {
        "success": True,
        "data": items,
        "limit": limit,
        "offset": offset,
        "total": total,
    }


@router.get(
    "/{auction_id:int}",
    response_model=dict,
    description="Get auction by id.",
)
@limiter.limit("100/minute")
async def get_auction_by_id(
    request: Annotated[Request, Depends(get_request)],
    auction_id: int,
    service: AuctionService = Depends(get_auction_service),
):
    auction = await service.get_auction_by_id(auction_id)
    return {"success": True, "data": auction}
