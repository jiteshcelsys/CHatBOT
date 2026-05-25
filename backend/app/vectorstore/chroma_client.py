"""
Singleton wrapper around the native chromadb.PersistentClient.

Every other module in app/vectorstore/ imports get_chroma_client()
instead of constructing its own client.  This guarantees:
  - One SQLite connection shared across the process.
  - Settings (persist_dir, tenant, database) applied once at startup.
  - Easy swap to HttpClient for a remote Chroma server later.
"""
import logging
from pathlib import Path

import chromadb
from chromadb import PersistentClient
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client: PersistentClient | None = None


def get_chroma_client() -> PersistentClient:
    """Return the process-wide ChromaDB persistent client (lazy-init)."""
    global _client
    if _client is None:
        settings = get_settings()
        persist_dir = Path(settings.chroma_persist_dir).resolve()
        persist_dir.mkdir(parents=True, exist_ok=True)

        _client = chromadb.PersistentClient(
            path=str(persist_dir),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,           # needed for test teardown / collection wipe
            ),
        )
        logger.info("ChromaDB PersistentClient ready | path=%s", persist_dir)
    return _client


def reset_chroma_client() -> None:
    """Force the next call to get_chroma_client() to create a fresh instance.
    Used in tests; not called in production code."""
    global _client
    if _client is not None:
        try:
            _client.reset()
        except Exception:
            pass
        _client = None
