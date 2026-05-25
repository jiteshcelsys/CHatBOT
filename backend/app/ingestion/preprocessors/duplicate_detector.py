"""
Duplicate detector — two-level detection strategy.

Level 1 — File-level (SHA-256 of the entire file).
  If the exact same file bytes were already ingested into this collection,
  skip the whole file immediately.  Checked against the in-process registry
  (fast, no DB round-trip) AND against ChromaDB metadata.

Level 2 — Chunk-level (SHA-256 of chunk text, first 16 hex chars).
  Individual chunks from a partially-updated document may already exist.
  This prevents doubling up on unchanged sections when a doc is lightly edited.

The registry is kept in memory (process lifetime) as a fast first-pass cache.
For production multi-process deployments the ChromaDB check acts as the source
of truth since the in-memory registry is not shared across workers.
"""
import hashlib
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# In-memory file-level registry: {sha256: ingestion_timestamp}
_file_registry: dict[str, str] = {}


# --------------------------------------------------------------------------- #
# File-level
# --------------------------------------------------------------------------- #

def register_file(sha256: str) -> None:
    _file_registry[sha256] = datetime.now(timezone.utc).isoformat()


def is_file_duplicate_in_memory(sha256: str) -> bool:
    return sha256 in _file_registry


def is_file_duplicate_in_chroma(collection, sha256: str) -> bool:
    """
    Query ChromaDB metadata to see if any chunk from this file exists.
    Returns True if at least one chunk carries this sha256.
    """
    if collection.count() == 0:
        return False
    try:
        result = collection.get(
            where={"sha256": {"$eq": sha256}},
            limit=1,
            include=[],
        )
        return len(result.get("ids") or []) > 0
    except Exception as exc:
        logger.warning("ChromaDB duplicate check failed: %s", exc)
        return False


def check_file_duplicate(collection, sha256: str) -> bool:
    """
    Returns True if this file (by SHA-256) is already indexed.
    Checks memory first, then ChromaDB.
    """
    if is_file_duplicate_in_memory(sha256):
        logger.info("File duplicate detected (memory) | sha256=%s...", sha256[:12])
        return True
    if is_file_duplicate_in_chroma(collection, sha256):
        logger.info("File duplicate detected (chroma) | sha256=%s...", sha256[:12])
        register_file(sha256)   # warm the memory cache
        return True
    return False


# --------------------------------------------------------------------------- #
# Chunk-level
# --------------------------------------------------------------------------- #

def chunk_hash(text: str) -> str:
    return hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16]


def filter_duplicate_chunks(collection, chunks: list) -> tuple[list, int]:
    """
    Remove chunks whose content hash already exists in the collection.
    Returns (new_chunks, skipped_count).
    """
    if collection.count() == 0:
        return chunks, 0

    hashes = [chunk_hash(c.page_content) for c in chunks]
    unique_hashes = list(set(hashes))

    existing: set[str] = set()
    batch = 100
    for i in range(0, len(unique_hashes), batch):
        sub = unique_hashes[i : i + batch]
        try:
            result = collection.get(
                where={"doc_hash": {"$in": sub}},
                include=["metadatas"],
            )
            for m in result.get("metadatas") or []:
                if m and m.get("doc_hash"):
                    existing.add(m["doc_hash"])
        except Exception as exc:
            logger.warning("Chunk duplicate check batch failed: %s", exc)

    new_chunks = [c for c, h in zip(chunks, hashes) if h not in existing]
    skipped = len(chunks) - len(new_chunks)

    if skipped:
        logger.info("Skipped %d duplicate chunk(s) out of %d", skipped, len(chunks))

    return new_chunks, skipped
