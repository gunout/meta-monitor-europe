# backend/config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Redis
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    cache_enabled: bool = os.getenv("CACHE_ENABLED", "true").lower() == "true"
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL", "300"))  # 5 min

    # Rate limiting
    ratelimit_enabled: bool = os.getenv("RATELIMIT_ENABLED", "true").lower() == "true"
    ratelimit_requests: int = int(os.getenv("RATELIMIT_REQUESTS", "60"))
    ratelimit_window: int = int(os.getenv("RATELIMIT_WINDOW", "60"))  # secondes

    # Auth
    auth_enabled: bool = os.getenv("AUTH_ENABLED", "false").lower() == "true"
    api_keys: str = os.getenv("API_KEYS", "")  # CSV : "key1,key2,key3"

    # HTTP
    http_timeout: float = float(os.getenv("HTTP_TIMEOUT", "15.0"))

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()

def get_api_keys() -> set[str]:
    if not settings.api_keys:
        return set()
    return {k.strip() for k in settings.api_keys.split(",") if k.strip()}