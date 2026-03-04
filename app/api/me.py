"""
Current user endpoint: GET /me returns the authenticated user from JWT payload.
Uses get_current_user_payload so the full token is validated and safe claims are returned.
"""
from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.core.dependencies import get_current_user_payload

router = APIRouter()


# Safe claims to expose to the client (no sensitive or internal keys)
ALLOWED_CLAIMS = {"sub", "email", "name", "preferred_username"}


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Return only allowed claims from the JWT payload."""
    return {k: v for k, v in payload.items() if k in ALLOWED_CLAIMS}


@router.get(
    "/me",
    response_model=dict,
    description="Return the current authenticated user from the Bearer token (safe claims only). Requires Bearer token.",
)
async def get_me(
    payload: Annotated[dict, Depends(get_current_user_payload)],
) -> dict:
    """Return current user info from JWT. Requires valid Bearer token."""
    data = _sanitize_payload(payload)
    return {"success": True, "data": data}
