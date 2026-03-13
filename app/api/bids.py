"""
Bid endpoints: POST /auctions/:id/bids to place a bid. Rate limited.
User identity is taken from JWT (Bearer) only. BidCreate has no userId field;
do not read user from body to avoid UUID(body.userId) and unclear/invalid-ID errors.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.dependencies import get_bidding_service, get_current_user_id
from app.core.rate_limit import rate_limit
from app.schemas.bid import BidCreate
from app.services.bidding_service import BiddingService

router = APIRouter()
settings = get_settings()


@router.post(
    "/{auction_id:int}/bids",
    response_model=dict,
    status_code=201,
    description="Place a bid on an auction. Min increment and 5-min extension apply. Requires Bearer token.",
)
async def place_bid(
    auction_id: int,
    body: BidCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: BiddingService = Depends(get_bidding_service),
    _rate_limit: None = Depends(rate_limit(settings.RATE_LIMIT_DEFAULT)),
):
    result = await service.place_bid(
        auction_id=auction_id,
        user_id=user_id,
        amount=body.amount,
        max_amount=body.maxAmount,
    )
    return {"success": True, "data": result}
