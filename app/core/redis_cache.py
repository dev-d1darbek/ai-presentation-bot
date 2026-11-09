"""
Redis Cache, Session & Rate-Limit Manager (with seamless fallback when REDIS_URL is not set).
- Session storage in Redis (24-hour TTL, instant access across restarts)
- Presentation cache in Redis (30-day TTL)
- Rate limiting in Redis (atomic SET NX EX)
"""
import json
import logging
import time
from typing import Optional

import config

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)

_redis_client = None
_redis_checked = False


def get_redis():
    """Returns a connected Redis client if REDIS_URL is configured and reachable, else None."""
    global _redis_client, _redis_checked
    if _redis_checked:
        return _redis_client
    _redis_checked = True
    if not config.REDIS_URL or redis is None:
        return None
    try:
        client = redis.from_url(config.REDIS_URL, decode_responses=True, socket_timeout=2.0)
        client.ping()
        _redis_client = client
        logger.info("Connected to Redis successfully!")
    except Exception as e:
        logger.warning(f"Redis connection unavailable ({e}); using SQLite + in-memory fallback.")
        _redis_client = None
    return _redis_client


def redis_get(key: str) -> Optional[str]:
    r = get_redis()
    if not r:
        return None
    try:
        return r.get(key)
    except Exception:
        return None


def redis_set(key: str, value: str, ttl_seconds: int = 86400) -> bool:
    r = get_redis()
    if not r:
        return False
    try:
        r.setex(key, ttl_seconds, value)
        return True
    except Exception:
        return False


def redis_check_rate_limit(user_id: int, cooldown_seconds: int = 5) -> Optional[bool]:
    """
    Returns True if rate-limited, False if allowed, or None if Redis is not enabled.
    """
    r = get_redis()
    if not r:
        return None
    key = f"ratelimit:gen:{user_id}"
    try:
        was_set = r.set(key, str(time.time()), nx=True, ex=cooldown_seconds)
        return not bool(was_set)
    except Exception:
        return None
