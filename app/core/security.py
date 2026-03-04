"""
JWT RS256 validation. Tokens are issued by BRX_auth; we validate with public key.
Public key is re-read periodically (JWT_KEY_REFRESH_SECONDS) so rotation works without restart.
Cache access is protected by _key_cache_lock to avoid race in multi-worker/async environments.
"""
import threading
import time
from typing import Any, Optional

import jwt
from jwt import DecodeError, InvalidTokenError

from app.core.config import Settings, get_settings

# Cache: (key_bytes, timestamp). Refreshed when TTL expires so key rotation is picked up.
_key_cache: Optional[tuple[bytes, float]] = None
_key_cache_lock = threading.Lock()


def _format_pem_key(key_str: str, is_private: bool = False) -> bytes:
    """Ensure PEM has proper headers and newlines."""
    key_str = (key_str or "").strip()
    if not key_str:
        raise ValueError("Empty key")
    if "-----BEGIN" in key_str:
        return key_str.encode("utf-8")
    header = "-----BEGIN PRIVATE KEY-----" if is_private else "-----BEGIN PUBLIC KEY-----"
    footer = "-----END PRIVATE KEY-----" if is_private else "-----END PUBLIC KEY-----"
    lines = [line.strip() for line in key_str.replace(header, "").replace(footer, "").split() if line.strip()]
    return (header + "\n" + "\n".join(lines) + "\n" + footer).encode("utf-8")


def _load_key_from_settings(settings: Settings) -> bytes:
    """Parse and return public key bytes from settings."""
    key_str = settings.JWT_PUBLIC_KEY
    if not key_str:
        raise ValueError("JWT_PUBLIC_KEY not configured")
    return _format_pem_key(key_str, is_private=False)


def _should_refresh(settings: Settings) -> bool:
    """True if cache is missing or older than JWT_KEY_REFRESH_SECONDS. Caller must hold _key_cache_lock when reading _key_cache."""
    if _key_cache is None:
        return True
    ttl = settings.JWT_KEY_REFRESH_SECONDS
    if ttl <= 0:
        return False
    return (time.monotonic() - _key_cache[1]) >= ttl


def load_public_key() -> bytes:
    """Load JWT public key and prime cache. Called at startup to fail fast if misconfigured."""
    global _key_cache
    settings = get_settings()
    key_bytes = _load_key_from_settings(settings)
    with _key_cache_lock:
        _key_cache = (key_bytes, time.monotonic())
    return key_bytes


def get_public_key_bytes() -> bytes:
    """Return current public key; re-read from config when TTL expires (supports key rotation). Thread-safe.
    Lock is held for the entire check-refresh-return so only one thread performs refresh, avoiding duplicate loads."""
    global _key_cache
    settings = get_settings()
    with _key_cache_lock:
        if _should_refresh(settings):
            key_bytes = _load_key_from_settings(settings)
            _key_cache = (key_bytes, time.monotonic())
        return _key_cache[0]


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate JWT (signature + exp).
    Raises InvalidTokenError or DecodeError on failure.
    Returns payload dict; use payload['sub'] for user_id.
    """
    settings = get_settings()
    key = get_public_key_bytes()
    payload = jwt.decode(
        token,
        key,
        algorithms=[settings.JWT_ALGORITHM],
        options={"verify_exp": True, "verify_signature": True},
    )
    if payload.get("type") != "access":
        raise InvalidTokenError("Token type must be access")
    return payload
