"""
Redis Cache, Session, Image Cache, Receipt Lock & Rate-Limit Manager
(with seamless in-memory + SQLite fallback when REDIS_URL is not set).
- Session storage in Redis (24-hour TTL, instant access across restarts)
- Presentation cache in Redis (30-day TTL — 100 users ask same topic -> 1 generation!)
- Slide Image cache in Redis (30-day TTL — caches both DDG and OpenAI gpt-image-2 images!)
- Concurrent Receipt Lock (blocks sending multiple receipts simultaneously)
- Rate limiting in Redis (atomic SET NX EX)
"""
import hashlib
import logging
import time
from typing import Optional, Dict, Set

import config

try:
    import redis
except ImportError:
    redis = None

logger = logging.getLogger(__name__)

_redis_client = None
_redis_checked = False

# In-memory fallbacks when Redis server is not running locally
_mem_image_cache: Dict[str, str] = {}
_active_receipt_locks: Dict[int, float] = {}


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


def _make_img_cache_key(query: str, source: str = "ddg") -> str:
    norm = " ".join((query or "").lower().strip().split())
    h = hashlib.sha256(f"{source}::{norm}".encode("utf-8")).hexdigest()[:24]
    return f"cache:img:{source}:{h}"


def redis_get_cached_image_b64(query: str, source: str = "ddg") -> Optional[str]:
    """Fetches a cached slide image (base64 JPEG) from Redis or in-memory fallback."""
    key = _make_img_cache_key(query, source)
    val = redis_get(key)
    if val:
        return val
    return _mem_image_cache.get(key)


def redis_set_cached_image_b64(query: str, image_b64: str, source: str = "ddg", ttl_seconds: int = 86400 * 30) -> None:
    """Stores a slide image (base64 JPEG) in Redis (30-day TTL) and in-memory fallback."""
    if not image_b64:
        return
    key = _make_img_cache_key(query, source)
    _mem_image_cache[key] = image_b64
    if len(_mem_image_cache) > 500:
        oldest_key = next(iter(_mem_image_cache))
        _mem_image_cache.pop(oldest_key, None)
    redis_set(key, image_b64, ttl_seconds=ttl_seconds)


def acquire_receipt_lock(user_id: int, lock_ttl_seconds: int = 30) -> bool:
    """
    Atomically locks receipt verification for `user_id` so the user CANNOT send multiple
    receipts simultaneously (Бірнеше чекті бір уақытта жіберуді блоктау).
    Returns True if lock acquired, False if another receipt from this user is currently being processed.
    """
    r = get_redis()
    key = f"lock:receipt:{user_id}"
    if r:
        try:
            acquired = r.set(key, str(time.time()), nx=True, ex=lock_ttl_seconds)
            return bool(acquired)
        except Exception:
            pass

    now = time.time()
    prev = _active_receipt_locks.get(user_id)
    if prev and (now - prev) < lock_ttl_seconds:
        return False
    _active_receipt_locks[user_id] = now
    return True


def release_receipt_lock(user_id: int) -> None:
    """Releases the concurrent receipt verification lock for `user_id`."""
    _active_receipt_locks.pop(user_id, None)
    r = get_redis()
    if r:
        try:
            r.delete(f"lock:receipt:{user_id}")
        except Exception:
            pass


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
