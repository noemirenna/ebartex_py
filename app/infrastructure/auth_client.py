"""
Optional HTTP client for Auth service (e.g. GET /api/auth/me for user info/role).
Uses httpx async. Timeout and errors are configurable and differentiated.
Error handling is explicit: only known exception types are caught; unexpected
exceptions propagate so callers and logs can distinguish auth failures from
service/network issues.
"""
import json
from dataclasses import dataclass
from typing import Any, Literal, Optional

import httpx
from loguru import logger

from app.core.config import get_settings
from app.infrastructure.http_client import get_http_client


@dataclass
class AuthMeResult:
    """Result of get_auth_me; allows distinguishing success, 4xx, 5xx, and network errors."""

    success: bool
    payload: Optional[dict[str, Any]] = None
    error_type: Optional[
        Literal["not_authenticated", "service_error", "network_error"]
    ] = None

    @property
    def is_not_authenticated(self) -> bool:
        return self.error_type == "not_authenticated"

    @property
    def is_service_error(self) -> bool:
        return self.error_type == "service_error"

    @property
    def is_network_error(self) -> bool:
        return self.error_type == "network_error"


async def get_auth_me(bearer_token: str) -> Optional[AuthMeResult]:
    """
    Call GET /api/auth/me with Bearer token.
    Returns None only when AUTH_BASE_URL is empty (feature disabled).
    Otherwise returns AuthMeResult so callers can distinguish:
    - success + payload (200)
    - not_authenticated (4xx)
    - service_error (5xx, invalid JSON) — logged
    - network_error (timeout, connection, transport) — logged with distinct messages.
    Only known httpx/JSON errors are caught; any other exception propagates.
    """
    settings = get_settings()
    base = settings.AUTH_BASE_URL
    if not base:
        return None
    url = f"{base.rstrip('/')}/api/auth/me"
    timeout = settings.AUTH_TIMEOUT_SECONDS
    try:
        client = get_http_client()
        r = await client.get(
            url,
            headers={"Authorization": f"Bearer {bearer_token}"},
            timeout=timeout,
        )
    except httpx.TimeoutException as exc:
        logger.warning(
            "Auth service timeout after {}s: {}",
            timeout,
            type(exc).__name__,
            exc_info=False,
        )
        return AuthMeResult(success=False, error_type="network_error")
    except httpx.ConnectError as exc:
        logger.warning(
            "Auth service connection failed (unreachable): {}",
            type(exc).__name__,
            exc_info=False,
        )
        return AuthMeResult(success=False, error_type="network_error")
    except httpx.RequestError as exc:
        logger.warning(
            "Auth service request error (transport): {}",
            type(exc).__name__,
            exc_info=False,
        )
        return AuthMeResult(success=False, error_type="network_error")

    if r.status_code == 200:
        try:
            return AuthMeResult(success=True, payload=r.json())
        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "Auth service invalid JSON response: {}",
                exc,
                exc_info=False,
            )
            return AuthMeResult(success=False, error_type="service_error")

    if 400 <= r.status_code < 500:
        return AuthMeResult(
            success=False,
            error_type="not_authenticated",
        )
    # 5xx or other
    logger.warning(
        "Auth service returned {}",
        r.status_code,
    )
    return AuthMeResult(
        success=False,
        error_type="service_error",
    )
