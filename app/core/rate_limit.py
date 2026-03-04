"""
Rate limiting: per-IP limits shared across instances via Redis.
When TRUSTED_PROXY is True, uses X-Forwarded-For (real client IP behind proxy).
When False, uses direct client IP only to avoid spoofing (X-Forwarded-For is client-controlled).

Routes that use @limiter.limit(...) must receive Request via Depends(get_request) so the limiter
can compute the client key; use Annotated[Request, Depends(get_request)] to keep the dependency explicit.
"""
from starlette.requests import Request

from fastapi import Depends
from slowapi import Limiter
from slowapi.util import get_ipaddr

from app.core.config import get_settings

settings = get_settings()


def get_request(request: Request) -> Request:
    """Dependency that provides Request for rate limiting. Use in route signatures with @limiter.limit(...).
    Injects the same Request FastAPI would pass; required so SlowAPI can compute the client key."""
    return request


def _rate_limit_key(request: Request) -> str:
    """IP for rate limit: X-Forwarded-For only when behind a trusted proxy, else direct client IP."""
    if settings.TRUSTED_PROXY:
        return get_ipaddr(request)
    if request.client:
        return request.client.host or "0.0.0.0"
    return "0.0.0.0"


# Redis storage: limit is shared across all app replicas; key = client IP (see _rate_limit_key).
# SlowAPI/limits opens its own Redis connections from REDIS_URL; the app uses init_redis() for the
# reindex queue (see redis_client). Two pools toward the same Redis: set REDIS_MAX_CONNECTIONS in
# config for the app pool; ensure Redis server maxclients can accommodate both app and limiter.
limiter = Limiter(
    key_func=_rate_limit_key,
    storage_uri=settings.REDIS_URL,
)
