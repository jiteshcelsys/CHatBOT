"""
Metadata extractor — attaches rich metadata to every Document before indexing.

Fields added / enriched:
  doc_id          : UUID v4 — unique identifier for this ingestion record
  source          : original filename
  file_type       : lowercase extension (.pdf, .txt, .docx, .md)
  file_size_bytes : size of the original uploaded file in bytes
  sha256          : hex digest of the full file content (dedup key)
  collection      : target ChromaDB collection
  ingested_at     : UTC ISO-8601 timestamp of this ingestion run
  ingestion_id    : UUID shared across all chunks from the same upload (for batch tracing)
  word_count      : approximate word count of the chunk text
  char_count      : character count of the chunk text
  **extra_tags    : caller-supplied arbitrary key/value pairs
"""
import hashlib
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from langchain_core.documents import Document

logger = logging.getLogger(__name__)


def compute_file_sha256(file_content: bytes) -> str:
    return hashlib.sha256(file_content).hexdigest()


def extract_and_attach(
    documents: list[Document],
    source: str,
    file_content: bytes,
    collection: str,
    ingestion_id: str | None = None,
    extra_tags: dict | None = None,
) -> list[Document]:
    """
    Enrich every Document with standardised metadata.
    Call this after parsing and cleaning, before chunking.
    """
    sha256 = compute_file_sha256(file_content)
    file_size = len(file_content)
    file_type = Path(source).suffix.lower()
    now = datetime.now(timezone.utc).isoformat()
    run_id = ingestion_id or str(uuid.uuid4())

    for doc in documents:
        doc.metadata.update(
            {
                "doc_id": str(uuid.uuid4()),
                "source": source,
                "file_type": file_type,
                "file_size_bytes": file_size,
                "sha256": sha256,
                "collection": collection,
                "ingested_at": now,
                "ingestion_id": run_id,
                "word_count": len(doc.page_content.split()),
                "char_count": len(doc.page_content),
                **(extra_tags or {}),
            }
        )

    logger.info(
        "Metadata attached | source=%s sha256=%s...%s docs=%d",
        source, sha256[:8], sha256[-4:], len(documents),
    )
    return documents
