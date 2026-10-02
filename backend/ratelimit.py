# backend/ratelimit.py
# Rate-limiting en mémoire (par IP + API key)
import time
from collections import defaultdict
from fastapi import Request, HTTPException
from config import settings

# Structure : {key: [timestamp1, timestamp2, ...]}
_buckets: dict[str, list[float]] = defaultdict(list)


def _get_client_id(request: Request) -> str:
    # Priorité à l'API key, sinon IP
    api_key = request.headers.get("X-API-Key", "").strip()
    if api_key:
        return f"key:{api_key[:16]}"

    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"

    ip = request.client.host if request.client else "unknown"
    return f"ip:{ip}"


def _clean_old(bucket: list[float], window: float) -> list[float]:
    now = time.time()
    cutoff = now - window
    return [t for t in bucket if t > cutoff]


async def check_ratelimit(request: Request):
    if not settings.ratelimit_enabled:
        return

    client_id = _get_client_id(request)
    window = settings.ratelimit_window
    max_requests = settings.ratelimit_requests

    now = time.time()
    bucket = _clean_old(_buckets[client_id], window)
    bucket.append(now)
    _buckets[client_id] = bucket

    if len(bucket) > max_requests:
        retry_after = int(window - (now - bucket[0])) + 1
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Trop de requêtes",
                "limit": max_requests,
                "window_seconds": window,
                "retry_after": retry_after,
            },
            headers={
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(max_requests),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(int(now + retry_after)),
            },
        )


async def ratelimit_headers(request: Request) -> dict:
    if not settings.ratelimit_enabled:
        return {}
    client_id = _get_client_id(request)
    window = settings.ratelimit_window
    max_requests = settings.ratelimit_requests
    bucket = _clean_old(_buckets.get(client_id, []), window)
    return {
        "X-RateLimit-Limit": str(max_requests),
        "X-RateLimit-Remaining": str(max(0, max_requests - len(bucket))),
        "X-RateLimit-Window": str(window),
    }