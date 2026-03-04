"""
Bid endpoints: POST /auctions/:id/bids to place a bid. Rate limited.
User identity is taken from JWT (Bearer) only. BidCreate has no userId field;
do not read user from body to avoid UUID(body.userId) and unclear/invalid-ID errors.
"""
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from starlette.requests import Request

from app.core.dependencies import get_bidding_service, get_current_user_id
from app.core.rate_limit import get_request, limiter
from app.schemas.bid import BidCreate
from app.services.bidding_service import BiddingService

router = APIRouter()


@router.post(
    "/{auction_id:int}/bids",
    response_model=dict,
    status_code=201,
    description="Place a bid on an auction. Min increment and 5-min extension apply. Requires Bearer token.",
)
@limiter.limit("60/minute")
async def place_bid(
    request: Annotated[Request, Depends(get_request)],
    auction_id: int,
    body: BidCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: BiddingService = Depends(get_bidding_service),
):
    result = await service.place_bid(
        auction_id=auction_id,
        user_id=user_id,
        amount=body.amount,
        max_amount=body.maxAmount,
    )
    return {"success": True, "data": result}
