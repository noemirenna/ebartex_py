"""
Shared async HTTP client for outbound calls (Auth, BRX_Search).
Connection pooling is used when the same client is reused; init at startup and close at shutdown.
FastAPI: init in lifespan. Worker: init at start of main(), close in finally.
"""
from typing import Optional

import httpx


_client: Optional[httpx.AsyncClient] = None


def get_http_client() -> httpx.AsyncClient:
    """Return the shared async client. Must call init_http_client() before first use."""
    if _client is None:
        raise RuntimeError("HTTP client not initialized; call init_http_client() at startup")
    return _client


def init_http_client(
    timeout: float = 30.0,
    limits: Optional[httpx.Limits] = None,
) -> httpx.AsyncClient:
    """Create and set the global async client. Idempotent: if already set, returns it."""
    global _client
    if _client is not None:
        return _client
    _client = httpx.AsyncClient(
        timeout=timeout,
        limits=limits or httpx.Limits(max_keepalive_connections=20, max_connections=50),
    )
    return _client


async def close_http_client() -> None:
    """Close the global client. No-op if not set."""
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
