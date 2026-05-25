"""
cache.py — Redis caching helper

Provides simple get/set/delete operations for caching API responses.
Caching reduces database load — repeated identical requests are served
from Redis memory instead of hitting PostgreSQL every time.
"""
import os
import json
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_TTL = int(os.getenv("REDIS_TTL", "60"))  # seconds to keep cached data


def get_redis_client():
    """
    Returns a Redis client connection.
    decode_responses=True = return strings instead of bytes.
    """
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True
    )


def cache_get(key: str):
    """
    Get a value from Redis cache.
    Returns the Python object (deserialized from JSON), or None if not cached.
    """
    client = get_redis_client()
    value = client.get(key)
    if value:
        return json.loads(value)  # JSON string → Python dict/list
    return None


def cache_set(key: str, value, ttl: int = REDIS_TTL):
    """
    Store a value in Redis cache with an expiry time.
    ttl = Time To Live in seconds — Redis automatically deletes the key after this.
    """
    client = get_redis_client()
    client.setex(
        name=key,
        time=ttl,
        value=json.dumps(value, default=str)  # Python object → JSON string
    )


def cache_delete(key: str):
    """Remove a key from cache (call this when data is updated/deleted)."""
    client = get_redis_client()
    client.delete(key)


def cache_delete_pattern(pattern: str):
    """Remove all keys matching a pattern (e.g. 'items:*')."""
    client = get_redis_client()
    keys = client.keys(pattern)
    if keys:
        client.delete(*keys)
