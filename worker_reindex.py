"""
Standalone worker: consume reindex requests from Redis and call BRX_Search reindex.
Run with: python -m worker_reindex (or python worker_reindex.py)
Requires REDIS_URL and SEARCH_* env vars.
"""
import asyncio
import sys

# Ensure app is on path
sys.path.insert(0, ".")

from app.infrastructure.http_client import init_http_client, close_http_client
from app.infrastructure.redis_client import init_redis, close_redis, get_redis_optional
from app.services.reindex_queue import consume_reindex_queue
from app.infrastructure.search_client import trigger_reindex
from loguru import logger


async def run_once() -> bool:
    """Process one reindex request from queue; return True if one was processed."""
    reason = await consume_reindex_queue()
    if reason is None:
        return False
    logger.info("Processing reindex request", reason=reason)
    ok = await trigger_reindex()
    if not ok:
        logger.warning("Reindex trigger failed; consider re-queuing")
    return True


async def main() -> None:
    logger.info("Reindex worker starting")
    init_http_client()
    await init_redis()
    if get_redis_optional() is None:
        logger.error("Redis connection failed; worker cannot run")
        sys.exit(1)
    delay_sec = 5.0
    max_delay_sec = 300.0
    try:
        while True:
            try:
                ok = await run_once()
                if ok:
                    delay_sec = 5.0  # reset backoff on success
                # No sleep when queue empty: consume_reindex_queue() already blocks with short timeout.
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception("Worker loop error: {}", e)
                await asyncio.sleep(delay_sec)
                delay_sec = min(delay_sec * 2, max_delay_sec)
    finally:
        await close_http_client()
        await close_redis()
    logger.info("Reindex worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
