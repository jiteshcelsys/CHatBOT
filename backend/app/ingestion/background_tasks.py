"""
Background task worker for document ingestion.

FastAPI's BackgroundTasks runs these functions after the HTTP response is
returned, so the upload endpoint responds instantly (202 Accepted) and
ingestion happens in the background.

Status tracking is done via an in-process dict (IngestionRegistry).
For multi-process/multi-worker deployments, swap this for a Redis or
Supabase-backed registry (Phase 6).
"""
import logging
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Status model
# --------------------------------------------------------------------------- #

class IngestionStatus(str, Enum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"
    DUPLICATE  = "duplicate"


@dataclass
class IngestionRecord:
    ingestion_id: str
    filename: str
    collection: str
    status: IngestionStatus = IngestionStatus.PENDING
    pages_loaded: int = 0
    total_chunks: int = 0
    new_chunks: int = 0
    duplicate_chunks: int = 0
    cache_hits: int = 0
    document_ids: list[str] = field(default_factory=list)
    error: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# In-process registry
# --------------------------------------------------------------------------- #

class IngestionRegistry:
    """Thread-safe in-memory store for ingestion records."""

    def __init__(self) -> None:
        self._records: dict[str, IngestionRecord] = {}

    def create(self, filename: str, collection: str) -> IngestionRecord:
        record = IngestionRecord(
            ingestion_id=str(uuid.uuid4()),
            filename=filename,
            collection=collection,
        )
        self._records[record.ingestion_id] = record
        return record

    def get(self, ingestion_id: str) -> IngestionRecord | None:
        return self._records.get(ingestion_id)

    def list_all(self) -> list[IngestionRecord]:
        return list(self._records.values())

    def list_by_collection(self, collection: str) -> list[IngestionRecord]:
        return [r for r in self._records.values() if r.collection == collection]

    def delete(self, ingestion_id: str) -> bool:
        return self._records.pop(ingestion_id, None) is not None

    def update(self, record: IngestionRecord) -> None:
        record.touch()
        self._records[record.ingestion_id] = record


# Process-wide singleton
_registry = IngestionRegistry()


def get_registry() -> IngestionRegistry:
    return _registry


# --------------------------------------------------------------------------- #
# Background task worker
# --------------------------------------------------------------------------- #

async def run_ingestion_task(
    ingestion_id: str,
    filename: str,
    file_content: bytes,
    collection: str,
    extra_tags: dict | None,
    skip_duplicates: bool,
    chunk_size: int,
    chunk_overlap: int,
) -> None:
    """
    Full ingestion pipeline executed as a background task.
    Updates the IngestionRecord status at each stage.
    """
    from app.ingestion.ingestion_service import IngestionService

    registry = get_registry()
    record = registry.get(ingestion_id)
    if record is None:
        logger.error("Background task: ingestion_id %s not found in registry", ingestion_id)
        return

    record.status = IngestionStatus.PROCESSING
    registry.update(record)
    logger.info("Background ingestion started | id=%s file=%s", ingestion_id, filename)

    from app.ingestion.document_store import upsert_document_record

    try:
        svc = IngestionService(
            collection_name=collection,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        result = await svc.ingest(
            filename=filename,
            file_content=file_content,
            ingestion_id=ingestion_id,
            extra_tags=extra_tags,
            skip_duplicates=skip_duplicates,
        )

        if result.status == IngestionStatus.DUPLICATE:
            record.status = IngestionStatus.DUPLICATE
        else:
            record.status = IngestionStatus.COMPLETED

        record.pages_loaded = result.pages_loaded
        record.total_chunks = result.total_chunks
        record.new_chunks = result.new_chunks
        record.duplicate_chunks = result.duplicate_chunks
        record.cache_hits = result.cache_hits
        record.document_ids = result.document_ids
        registry.update(record)
        await upsert_document_record(record)

        logger.info(
            "Background ingestion done | id=%s status=%s chunks=%d",
            ingestion_id, record.status, record.new_chunks,
        )

    except Exception as exc:
        record.status = IngestionStatus.FAILED
        record.error = str(exc)
        registry.update(record)
        await upsert_document_record(record)
        logger.error(
            "Background ingestion failed | id=%s file=%s\n%s",
            ingestion_id, filename, traceback.format_exc(),
        )
