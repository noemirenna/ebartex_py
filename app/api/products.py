"""
Product endpoints: search (paginated), get by id, create, create auction for product.
Create and create auction require authentication (Bearer).
"""
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from starlette.requests import Request

from app.core.config import get_settings
from app.core.dependencies import get_auction_service, get_product_service, get_current_user_id
from app.core.rate_limit import get_request, limiter
from app.schemas.product import ProductCreate
from app.schemas.auction import AuctionCreate
from app.services.auction_service import AuctionService
from app.services.product_service import ProductService
from app.utils.exceptions import ProductNotFoundError

router = APIRouter()
settings = get_settings()


@router.get(
    "/",
    response_model=dict,
    description="Search products with optional q; pagination.",
)
@limiter.limit("100/minute")
async def search_products(
    request: Annotated[Request, Depends(get_request)],
    q: Optional[str] = Query(None, max_length=200),
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    service: ProductService = Depends(get_product_service),
):
    offset = min(offset, settings.MAX_PAGINATION_OFFSET)
    items, total = await service.search_products(q=q, limit=limit, offset=offset)
    return {
        "success": True,
        "data": items,
        "limit": limit,
        "offset": offset,
        "total": total,
    }


@router.get(
    "/{product_id:int}",
    response_model=dict,
    description="Get product by id.",
)
@limiter.limit("100/minute")
async def get_product_by_id(
    request: Annotated[Request, Depends(get_request)],
    product_id: int,
    service: Annotated[ProductService, Depends(get_product_service)],
):
    product = await service.get_product_by_id(product_id)
    if not product:
        raise ProductNotFoundError()
    return {"success": True, "data": product}


@router.post(
    "/",
    response_model=dict,
    status_code=201,
    description="Create a product. Requires Bearer token.",
)
@limiter.limit("60/minute")
async def create_product(
    request: Annotated[Request, Depends(get_request)],
    body: ProductCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    service: ProductService = Depends(get_product_service),
):
    product = await service.create_product(
        name=body.name,
        description=body.description,
        price=body.price,
        created_by_user_id=user_id,
    )
    return {"success": True, "data": product}


@router.post(
    "/{product_id:int}/auctions",
    response_model=dict,
    status_code=201,
    description="Create an auction for a product (body: auction fields; product used for title/description defaults). Requires Bearer token.",
)
@limiter.limit("60/minute")
async def create_auction_for_product(
    request: Annotated[Request, Depends(get_request)],
    product_id: int,
    body: AuctionCreate,
    user_id: Annotated[UUID, Depends(get_current_user_id)],
    product_svc: ProductService = Depends(get_product_service),
    auction_svc: AuctionService = Depends(get_auction_service),
):
    product = await product_svc.get_product_by_id(product_id)
    if not product:
        raise ProductNotFoundError()
    data = body.model_dump()
    data["product_id"] = str(product_id)
    data["title"] = data.get("title") or product.get("name", "")
    data["description"] = data.get("description") or product.get("description", "")
    data["created_by_user_id"] = user_id
    auction = await auction_svc.create_auction(data)
    return {"success": True, "data": auction}
