"""
Persists ingestion records to Supabase `ingested_documents` table.
"""
import logging
from app.memory.supabase_client import get_supabase
from app.ingestion.background_tasks import IngestionRecord, IngestionStatus

logger = logging.getLogger(__name__)

TABLE = "ingested_documents"


async def upsert_document_record(record: IngestionRecord) -> None:
    try:
        sb = await get_supabase()
        await sb.table(TABLE).upsert({
            "ingestion_id":     record.ingestion_id,
            "filename":         record.filename,
            "collection":       record.collection,
            "status":           record.status.value,
            "pages_loaded":     record.pages_loaded,
            "total_chunks":     record.total_chunks,
            "new_chunks":       record.new_chunks,
            "duplicate_chunks": record.duplicate_chunks,
            "document_ids":     record.document_ids,
            "error":            record.error,
            "updated_at":       record.updated_at,
        }, on_conflict="ingestion_id").execute()
    except Exception as exc:
        logger.error("Failed to persist ingestion record to Supabase | id=%s error=%s", record.ingestion_id, exc)
