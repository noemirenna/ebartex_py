"""
Application settings from environment.
Maps exactly the env vars injected by start.sh (AWS SSM → docker-compose).
No defaults for security-sensitive variables: app crashes at startup if any is missing.
"""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root (ebartex_aste_py), so .env is found even when running from other dirs (e.g. alembic).
# .env must NOT be committed (it is in .gitignore); deploy via env vars or secret manager only.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Required (no default): injected by host / start.sh ---
    DB_USER: str = Field(..., description="PostgreSQL user")
    DB_PASS: str = Field(..., description="PostgreSQL password")
    DB_HOST: str = Field(..., description="PostgreSQL host (e.g. RDS endpoint)")
    DB_NAME: str = Field(..., description="PostgreSQL database name")
    DB_PORT: int = Field(default=5432, description="PostgreSQL port")

    MEILISEARCH_MASTER_KEY: str = Field(..., description="Meilisearch master key")
    SEARCH_ADMIN_API_KEY: str = Field(..., description="X-Admin-API-Key for reindex endpoint")
    SECRET_KEY: str = Field(..., description="Application secret key")
    # Optional: reserved for future use (e.g. encrypting cardtrader_token in UserSyncSettings).
    # If/when encryption is implemented, set FERNET_KEY and use it; until then leaving it unset avoids unused secrets.
    FERNET_KEY: str = Field(default="", description="Fernet encryption key (optional; for future token encryption)")
    JWT_PRIVATE_KEY: str = Field(..., description="JWT private key PEM (Auth service)")
    JWT_PUBLIC_KEY: str = Field(..., description="JWT public key PEM for token validation")

    # --- Computed: async PostgreSQL URL (never log this; use DATABASE_URL_MASKED for logs) ---
    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASS}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @computed_field
    @property
    def DATABASE_URL_MASKED(self) -> str:
        """Same as DATABASE_URL but with password redacted. Use only for logging/traces."""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:***"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # --- Optional / non-sensitive (defaults allowed) ---
    DEBUG: bool = Field(default=False, description="Debug mode")
    # Explicit opt-in for OpenAPI docs (/docs, /redoc). Do not rely on DEBUG alone in production.
    ENABLE_OPENAPI_DOCS: bool = Field(
        default=False,
        description="If True, expose /docs and /redoc. Set explicitly; avoid DEBUG=true in production.",
    )
    # When True, rate limiting uses X-Forwarded-For (real client IP behind proxy). Set True only behind a trusted proxy that sets/validates this header; otherwise clients can spoof it.
    TRUSTED_PROXY: bool = Field(
        default=False,
        description="True only if behind a trusted proxy that sets X-Forwarded-For; else rate limit uses direct client IP.",
    )
    LOG_LEVEL: str = Field(default="INFO", description="Log level")
    HOST: str = Field(default="0.0.0.0", description="Bind host")
    PORT: int = Field(default=8000, description="Bind port")

    DB_POOL_SIZE: int = Field(default=20, description="Connection pool size (high traffic)")
    DB_MAX_OVERFLOW: int = Field(default=30, description="Max overflow connections")

    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis URL for cache, rate limit, reindex queue",
    )
    REDIS_MAX_CONNECTIONS: int = Field(
        default=50,
        description="Max connections in the Redis connection pool (app + reindex); tune under high concurrency.",
    )
    REDIS_SOCKET_CONNECT_TIMEOUT: float = Field(
        default=5.0,
        description="Redis socket connect timeout in seconds.",
    )

    JWT_ALGORITHM: str = Field(default="RS256", description="JWT algorithm")
    JWT_KEY_REFRESH_SECONDS: int = Field(
        default=300,
        description="Seconds after which JWT public key is re-read from config (0 = no refresh, key loaded once).",
    )

    SEARCH_BASE_URL: str = Field(
        default="http://localhost:8001",
        description="BRX_Search / Meilisearch base URL",
    )

    AUTH_BASE_URL: str = Field(
        default="",
        description="Auth service base URL for GET /api/auth/me (user info/role). Empty = disabled.",
    )
    AUTH_TIMEOUT_SECONDS: float = Field(
        default=10.0,
        description="Timeout in seconds for GET /api/auth/me calls.",
    )

    CORS_ORIGINS: str = Field(
        default="http://localhost:3000",
        description="Comma-separated allowed origins",
    )

    RATE_LIMIT_DEFAULT: int = Field(default=60, description="Default requests per minute per IP")
    RATE_LIMIT_SEARCH: int = Field(default=100, description="Search endpoint limit per minute")
    RATE_LIMIT_AUTH_LIKE: int = Field(default=5, description="Auth-like endpoints limit per minute")

    # Pagination: max offset to avoid O(offset) DB cost and DoS (PostgreSQL still scans skipped rows).
    MAX_PAGINATION_OFFSET: int = Field(
        default=10_000,
        description="Maximum allowed offset for list/search endpoints; offsets above this are clamped.",
    )
    # Max bids returned in place_bid response (avoids unbounded list for auctions with many bids).
    PLACE_BID_RESPONSE_BIDS_LIMIT: int = Field(default=50, description="Max bids returned after placing a bid.")

    REDIS_REINDEX_QUEUE: str = Field(
        default="ebartex:reindex:queue",
        description="Redis list key for reindex requests",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
