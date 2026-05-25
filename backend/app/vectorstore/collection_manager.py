"""
CRUD operations on ChromaDB collections.

Responsibilities:
  - Create / get / delete collections with HNSW distance metadata.
  - List all collections with per-collection document counts.
  - Expose detailed per-collection statistics.
  - Guard against creating a collection that already exists when
    strict=True (duplicate-prevention layer for the API).
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

import chromadb
from chromadb.api.models.Collection import Collection

from app.vectorstore.chroma_client import get_chroma_client

logger = logging.getLogger(__name__)

# HNSW parameters — cosine distance is correct for normalised embeddings
_HNSW_METADATA = {"hnsw:space": "cosine"}


@dataclass
class CollectionInfo:
    name: str
    document_count: int
    metadata: dict = field(default_factory=dict)
    created_at: str = ""


@dataclass
class CollectionStats:
    name: str
    document_count: int
    metadata: dict
    sample_ids: list[str]          # first 5 IDs for a quick sanity check
    sources: list[str]             # unique source file names stored in metadata
    created_at: str


class CollectionManager:
    """Manage ChromaDB collections independent of any LangChain abstraction."""

    # ------------------------------------------------------------------ #
    # Create / Get
    # ------------------------------------------------------------------ #

    def get_or_create(self, name: str, description: str = "") -> Collection:
        """
        Return the collection if it exists, create it if it does not.
        Attaches a description and creation timestamp on first creation.
        """
        client = get_chroma_client()
        existing_names = {c.name for c in client.list_collections()}

        if name in existing_names:
            col = client.get_collection(name=name, embedding_function=None)
            logger.info("Opened existing collection: %s (%d docs)", name, col.count())
            return col

        meta = {
            **_HNSW_METADATA,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        col = client.create_collection(name=name, metadata=meta, embedding_function=None)
        logger.info("Created new collection: %s", name)
        return col

    def create_strict(self, name: str, description: str = "") -> Collection:
        """
        Create a collection; raise ValueError if it already exists.
        Used by the API POST /collections endpoint.
        """
        client = get_chroma_client()
        existing_names = {c.name for c in client.list_collections()}
        if name in existing_names:
            raise ValueError(f"Collection '{name}' already exists.")
        return self.get_or_create(name, description)

    def get(self, name: str) -> Collection:
        client = get_chroma_client()
        try:
            return client.get_collection(name=name, embedding_function=None)
        except Exception:
            raise KeyError(f"Collection '{name}' not found.")

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    def delete(self, name: str) -> None:
        client = get_chroma_client()
        try:
            client.delete_collection(name=name)
            logger.warning("Deleted collection: %s", name)
        except Exception as exc:
            raise KeyError(f"Collection '{name}' not found.") from exc

    # ------------------------------------------------------------------ #
    # List / Stats
    # ------------------------------------------------------------------ #

    def list_collections(self) -> list[CollectionInfo]:
        client = get_chroma_client()
        result = []
        for col in client.list_collections():
            try:
                full = client.get_collection(name=col.name, embedding_function=None)
                count = full.count()
                meta = full.metadata or {}
            except Exception:
                count = -1
                meta = {}
            result.append(
                CollectionInfo(
                    name=col.name,
                    document_count=count,
                    metadata=meta,
                    created_at=meta.get("created_at", ""),
                )
            )
        return result

    def stats(self, name: str) -> CollectionStats:
        col = self.get(name)
        count = col.count()
        meta = col.metadata or {}

        # Pull a small sample to surface unique sources
        sample_ids: list[str] = []
        sources: set[str] = set()
        if count > 0:
            peek = col.peek(limit=min(count, 100))
            sample_ids = (peek.get("ids") or [])[:5]
            for m in peek.get("metadatas") or []:
                if m and m.get("source"):
                    sources.add(m["source"])

        return CollectionStats(
            name=name,
            document_count=count,
            metadata=meta,
            sample_ids=sample_ids,
            sources=sorted(sources),
            created_at=meta.get("created_at", ""),
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def exists(self, name: str) -> bool:
        client = get_chroma_client()
        return name in {c.name for c in client.list_collections()}
