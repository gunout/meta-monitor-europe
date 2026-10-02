# backend/cache.py
# Cache Redis avec fallback mémoire
import json
import hashlib
from typing import Optional, Any
from config import settings

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Fallback : cache mémoire si Redis indisponible
_memory_cache: dict[str, tuple[str, float]] = {}


class Cache:
    def __init__(self):
        self.client: Optional[Any] = None
        self.enabled = settings.cache_enabled

    async def connect(self):
        if not self.enabled:
            return
        if not REDIS_AVAILABLE:
            print("[cache] redis-py non installé → fallback mémoire")
            return
        try:
            self.client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
            )
            await self.client.ping()
            print(f"[cache] ✅ Redis connecté : {settings.redis_url}")
        except Exception as e:
            print(f"[cache] ⚠️ Redis indisponible ({e}) → fallback mémoire")
            self.client = None

    async def close(self):
        if self.client:
            await self.client.close()

    def _make_key(self, prefix: str, params: dict) -> str:
        # Clé déterministe : tri des params
        payload = json.dumps(params, sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return f"mm:{prefix}:{digest}"

    async def get(self, prefix: str, params: dict) -> Optional[dict]:
        if not self.enabled:
            return None
        key = self._make_key(prefix, params)

        if self.client:
            try:
                raw = await self.client.get(key)
                if raw:
                    return json.loads(raw)
            except Exception as e:
                print(f"[cache] get error: {e}")

        # Fallback mémoire
        import time
        entry = _memory_cache.get(key)
        if entry:
            value, expire_at = entry
            if time.time() < expire_at:
                return json.loads(value)
            else:
                del _memory_cache[key]

        return None

    async def set(self, prefix: str, params: dict, value: dict, ttl: Optional[int] = None):
        if not self.enabled:
            return
        key = self._make_key(prefix, params)
        ttl = ttl or settings.cache_ttl_seconds
        payload = json.dumps(value, ensure_ascii=False)

        if self.client:
            try:
                await self.client.setex(key, ttl, payload)
                return
            except Exception as e:
                print(f"[cache] set error: {e}")

        # Fallback mémoire
        import time
        _memory_cache[key] = (payload, time.time() + ttl)

    async def clear(self):
        if self.client:
            try:
                keys = await self.client.keys("mm:*")
                if keys:
                    await self.client.delete(*keys)
            except Exception:
                pass
        _memory_cache.clear()

    async def stats(self) -> dict:
        if self.client:
            try:
                info = await self.client.info("stats")
                return {
                    "type": "redis",
                    "connected": True,
                    "keys": await self.client.dbsize(),
                    "hits": info.get("keyspace_hits", 0),
                    "misses": info.get("keyspace_misses", 0),
                }
            except Exception as e:
                return {"type": "redis", "connected": False, "error": str(e)}
        return {
            "type": "memory",
            "connected": False,
            "keys": len(_memory_cache),
        }


cache = Cache()