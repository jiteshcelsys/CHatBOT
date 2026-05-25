"""
Metadata enrichment and filter-building for ChromaDB queries.

Responsibilities:
  1. Enrich every Document chunk with standard metadata fields before
     it is stored (source, file_type, ingested_at, doc_hash, chunk_index).
  2. Build ChromaDB `where` filter dicts from user-supplied filter params.
  3. Compute a content hash for duplicate detection.

ChromaDB WHERE clause syntax (v1.x):
  Single condition : {"field": {"$eq": "value"}}
  AND of conditions: {"$and": [{"f1": {"$eq": v1}}, {"f2": {"$eq": v2}}]}
"""
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def content_hash(text: str) -> str:
    """SHA-256 of normalised text — used as a duplicate fingerprint."""
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]


def enrich_metadata(
    documents: list[Document],
    source: str,
    collection: str,
    extra_tags: dict | None = None,
) -> list[Document]:
    """
    Stamp every chunk with:
      - source        : original filename
      - file_type     : extension (.pdf / .txt / …)
      - collection    : target collection name
      - ingested_at   : UTC ISO-8601 timestamp
      - doc_hash      : first 16 chars of content SHA-256 (dedup key)
      - chunk_index   : position within the source document
      - **extra_tags  : any caller-supplied key/value pairs
    """
    now = datetime.now(timezone.utc).isoformat()
    file_type = Path(source).suffix.lower() if source else ""

    for idx, doc in enumerate(documents):
        doc.metadata.update(
            {
                "source": source,
                "file_type": file_type,
                "collection": collection,
                "ingested_at": now,
                "doc_hash": content_hash(doc.page_content),
                "chunk_index": idx,
                **(extra_tags or {}),
            }
        )
    return documents


# --------------------------------------------------------------------------- #
# Filter builder
# --------------------------------------------------------------------------- #


def build_where_filter(
    source: str | None = None,
    file_type: str | None = None,
    tags: dict | None = None,
) -> dict | None:
    """
    Build a ChromaDB WHERE clause from optional filter fields.
    Returns None when no filters are requested (avoids passing an empty dict).
    """
    conditions: list[dict] = []

    if source:
        conditions.append({"source": {"$eq": source}})
    if file_type:
        ft = file_type if file_type.startswith(".") else f".{file_type}"
        conditions.append({"file_type": {"$eq": ft}})
    if tags:
        for k, v in tags.items():
            conditions.append({k: {"$eq": v}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def find_duplicate_ids(
    collection,           # chromadb Collection
    chunks: list[Document],
    batch_size: int = 100,
) -> set[str]:
    """
    Return the set of doc_hash values that already exist in the collection.
    Used by the indexing service to skip or overwrite duplicates.
    """
    hashes = {content_hash(doc.page_content) for doc in chunks}
    existing: set[str] = set()

    if not hashes or collection.count() == 0:
        return existing

    # ChromaDB `where` supports $in for a list of values
    for chunk in range(0, len(list(hashes)), batch_size):
        batch = list(hashes)[chunk : chunk + batch_size]
        try:
            result = collection.get(
                where={"doc_hash": {"$in": batch}},
                include=["metadatas"],
            )
            for meta in result.get("metadatas") or []:
                if meta and meta.get("doc_hash"):
                    existing.add(meta["doc_hash"])
        except Exception as exc:
            logger.warning("Duplicate check failed for batch: %s", exc)

    return existing
