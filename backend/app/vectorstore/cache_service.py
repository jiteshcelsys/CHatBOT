"""
In-memory embedding cache with TTL.

Why: Embedding the same text chunk multiple times (e.g. during re-index or
     duplicate uploads) wastes CPU time on the local sentence-transformer model.
     A simple LRU+TTL cache halves embedding work for repeated content.

Design:
  - Key: SHA-256 of the text (avoids storing large strings as keys).
  - Value: the embedding vector as a list[float].
  - Max size: 2 000 entries (configurable).
  - TTL: 3 600 seconds (1 hour, configurable).
  - Thread-safe: uses a threading.Lock around all mutations.
"""
import hashlib
import logging
import threading
import time
from collections import OrderedDict

logger = logging.getLogger(__name__)


class EmbeddingCache:
    def __init__(self, max_size: int = 2_000, ttl_seconds: int = 3_600):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, tuple[list[float], float]] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get(self, text: str) -> list[float] | None:
        key = self._hash(text)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                self._misses += 1
                return None
            vector, ts = entry
            if time.monotonic() - ts > self._ttl:
                del self._cache[key]
                self._misses += 1
                return None
            # Move to end (LRU)
            self._cache.move_to_end(key)
            self._hits += 1
            return vector

    def set(self, text: str, vector: list[float]) -> None:
        key = self._hash(text)
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = (vector, time.monotonic())
            if len(self._cache) > self._max_size:
                evicted_key, _ = self._cache.popitem(last=False)
                logger.debug("Cache eviction: %s", evicted_key[:12])

    def invalidate(self, text: str) -> bool:
        key = self._hash(text)
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> int:
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            logger.info("Embedding cache cleared (%d entries)", count)
            return count

    def stats(self) -> dict:
        with self._lock:
            total = self._hits + self._misses
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "ttl_seconds": self._ttl,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": round(self._hits / total, 4) if total else 0.0,
            }

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()


# Process-level singleton
_cache = EmbeddingCache()


def get_embedding_cache() -> EmbeddingCache:
    return _cache
