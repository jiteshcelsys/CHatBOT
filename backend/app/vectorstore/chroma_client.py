"""
Singleton wrapper around ChromaDB Cloud client (HTTP-only, no local server).
Requires CHROMA_CLOUD_API_KEY, CHROMA_CLOUD_TENANT to be set.
"""
import logging

import chromadb

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_client = None


def get_chroma_client():
    """Return the process-wide ChromaDB Cloud client (lazy-init)."""
    global _client
    if _client is None:
        settings = get_settings()

        if not settings.chroma_cloud_api_key:
            raise RuntimeError(
                "CHROMA_CLOUD_API_KEY is not set. "
                "This deployment uses Chroma Cloud — set the env var and retry."
            )

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

    return _client


def reset_chroma_client() -> None:
    """Force the next call to get_chroma_client() to create a fresh instance (tests only)."""
    global _client
    _client = None
