"""Optional Redis cache for Gauntlet detection results.

Caches DetectionResult objects keyed by input text + layer configuration.
Completely opt-in: only activated when redis_url is passed to Gauntlet.
Fail-open: all Redis errors are caught and logged, detection continues without cache.
"""

import hashlib
import logging

from gauntlet.models import DetectionResult

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis-backed cache for detection results.

    Uses lazy import of redis package (follows project pattern for optional deps).
    All operations are fail-open: Redis errors never block detection.

    Args:
        url: Redis connection URL (e.g., "redis://localhost:6379/0").
        ttl: Cache entry time-to-live in seconds.
        prefix: Key prefix for all cache entries.
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        ttl: int = 3600,
        prefix: str = "gauntlet",
    ) -> None:
        self._ttl = ttl
        self._prefix = prefix
        self._available = False
        self._client = None

        try:
            import redis

            self._client = redis.Redis.from_url(url, decode_responses=True)
            self._client.ping()
            self._available = True
            logger.debug("Redis cache connected: %s", url)
        except ImportError:
            logger.warning("redis package not installed — cache disabled")
        except Exception as e:
            logger.warning("Redis unavailable (%s) — cache disabled", type(e).__name__)

    def _make_key(self, text: str, layers: list[int]) -> str:
        """Generate cache key from text and layer configuration.

        Key format: {prefix}:detect:{sha256(text|sorted_layers)}
        """
        sorted_layers = sorted(layers)
        payload = text + "|" + ",".join(str(l) for l in sorted_layers)
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return f"{self._prefix}:detect:{digest}"

    def get(self, text: str, layers: list[int]) -> DetectionResult | None:
        """Retrieve cached detection result.

        Returns None on cache miss or any Redis error.
        """
        if not self._available:
            return None

        try:
            key = self._make_key(text, layers)
            data = self._client.get(key)
            if data is None:
                logger.debug("Cache miss: %s", key)
                return None
            logger.debug("Cache hit: %s", key)
            return DetectionResult.model_validate_json(data)
        except Exception as e:
            logger.warning("Cache get failed (%s) — continuing without cache", type(e).__name__)
            return None

    def set(self, text: str, layers: list[int], result: DetectionResult) -> None:
        """Store detection result in cache.

        Silently fails on any Redis error.
        """
        if not self._available:
            return

        try:
            key = self._make_key(text, layers)
            data = result.model_dump_json()
            self._client.set(key, data, ex=self._ttl)
            logger.debug("Cache store: %s (ttl=%ds)", key, self._ttl)
        except Exception as e:
            logger.warning("Cache set failed (%s) — continuing without cache", type(e).__name__)
