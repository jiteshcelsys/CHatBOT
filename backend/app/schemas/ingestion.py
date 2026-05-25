from pydantic import BaseModel, Field
from app.ingestion.background_tasks import IngestionStatus


class IngestionAcceptedResponse(BaseModel):
    ingestion_id: str
    filename: str
    collection: str
    status: IngestionStatus
    message: str


class IngestionStatusResponse(BaseModel):
    ingestion_id: str
    filename: str
    collection: str
    status: IngestionStatus
    pages_loaded: int
    total_chunks: int
    new_chunks: int
    duplicate_chunks: int
    cache_hits: int
    document_ids: list[str]
    error: str | None
    created_at: str
    updated_at: str


class BatchIngestionResponse(BaseModel):
    total_files: int
    accepted: list[IngestionAcceptedResponse]
    rejected: list[dict]   # {"filename": str, "reason": str}


class DocumentListItem(BaseModel):
    ingestion_id: str
    filename: str
    collection: str
    status: IngestionStatus
    new_chunks: int
    created_at: str
    updated_at: str
