"""
Singleton wrapper around ChromaDB client.
Uses ChromaDB Cloud (HttpClient) when CHROMA_CLOUD_API_KEY is set,
otherwise falls back to local PersistentClient for development.
"""
import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client = None


def get_chroma_client():
    """Return the process-wide ChromaDB client (lazy-init)."""
    global _client
    if _client is None:
        settings = get_settings()

        if settings.chroma_cloud_api_key:
            _client = chromadb.HttpClient(
                ssl=True,
                host="api.trychroma.com",
                tenant=settings.chroma_cloud_tenant,
                database=settings.chroma_cloud_database,
                headers={"x-chroma-token": settings.chroma_cloud_api_key},
            )
            logger.info(
                "ChromaDB Cloud client ready | tenant=%s database=%s",
                settings.chroma_cloud_tenant,
                settings.chroma_cloud_database,
            )
        else:
            persist_dir = Path(settings.chroma_persist_dir).resolve()
            persist_dir.mkdir(parents=True, exist_ok=True)
            _client = chromadb.PersistentClient(
                path=str(persist_dir),
                settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
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
