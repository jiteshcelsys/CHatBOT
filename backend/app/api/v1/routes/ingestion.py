"""
Document Ingestion API — Phase 5

Prefix: /api/v1/ingest

POST   /                    — upload single document (background)
POST   /batch               — upload multiple documents (background, each file independent)
GET    /status/{id}         — get ingestion status by ID
GET    /documents           — list all ingestion records (filterable by collection)
DELETE /documents/{id}      — delete an ingestion record (not the vectors — use VS API for that)
POST   /retry/{id}          — retry a failed ingestion
GET    /metadata/{id}       — full metadata for an ingestion record
"""
import json
import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse

from app.core.auth import AuthUser, get_current_user
from app.core.config import get_settings
from app.ingestion.background_tasks import (
    IngestionStatus,
    get_registry,
    run_ingestion_task,
)
from app.ingestion.validators import run_all_validations
from app.schemas.base import ApiResponse
from app.schemas.ingestion import (
    BatchIngestionResponse,
    DocumentListItem,
    IngestionAcceptedResponse,
    IngestionStatusResponse,
)
from app.utils.exceptions import BadRequestException, NotFoundException
from app.utils.responses import success

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ingest", tags=["Ingestion"])


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _parse_tags(tags_str: str) -> dict | None:
    if not tags_str.strip():
        return None
    try:
        return json.loads(tags_str)
    except json.JSONDecodeError:
        raise BadRequestException("'tags' must be a valid JSON object string, e.g. '{\"project\":\"alpha\"}'")


def _accepted_response(record) -> IngestionAcceptedResponse:
    return IngestionAcceptedResponse(
        ingestion_id=record.ingestion_id,
        filename=record.filename,
        collection=record.collection,
        status=record.status,
        message="File accepted and queued for ingestion. Once complete it will be saved to the database. Poll /status/{ingestion_id} for updates.",
    )


# --------------------------------------------------------------------------- #
# Single upload
# --------------------------------------------------------------------------- #

@router.post(
    "/",
    summary="Upload a single document for background ingestion",
    response_model=ApiResponse[IngestionAcceptedResponse],
    status_code=202,
)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="PDF, TXT, DOCX, or Markdown file"),
    collection: str = Form("documents", description="Target ChromaDB collection"),
    skip_duplicates: bool = Form(True),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    tags: str = Form("", description='JSON object, e.g. \'{"project":"alpha"}\''),
    user: AuthUser = Depends(get_current_user),
):
    content = await file.read()
    run_all_validations(file.filename or "", content, file.content_type or "")

    extra_tags = _parse_tags(tags)
    registry = get_registry()
    record = registry.create(filename=file.filename or "unknown", collection=collection)

    background_tasks.add_task(
        run_ingestion_task,
        ingestion_id=record.ingestion_id,
        filename=file.filename or "unknown",
        file_content=content,
        collection=collection,
        extra_tags=extra_tags,
        skip_duplicates=skip_duplicates,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    logger.info("Accepted ingestion | id=%s file=%s", record.ingestion_id, file.filename)
    return JSONResponse(
        status_code=202,
        content=ApiResponse.ok(_accepted_response(record).model_dump()).model_dump(),
    )


# --------------------------------------------------------------------------- #
# Batch upload
# --------------------------------------------------------------------------- #

@router.post(
    "/batch",
    summary="Upload multiple documents for background ingestion",
    response_model=ApiResponse[BatchIngestionResponse],
    status_code=202,
)
async def upload_batch(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(..., description="Up to 10 files"),
    collection: str = Form("documents"),
    skip_duplicates: bool = Form(True),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    tags: str = Form(""),
    user: AuthUser = Depends(get_current_user),
):
    settings = get_settings()
    if len(files) > settings.ingestion_max_batch_files:
        raise BadRequestException(
            f"Batch too large: {len(files)} files. "
            f"Max allowed: {settings.ingestion_max_batch_files}."
        )

    extra_tags = _parse_tags(tags)
    registry = get_registry()
    accepted: list[IngestionAcceptedResponse] = []
    rejected: list[dict] = []

    for file in files:
        try:
            content = await file.read()
            run_all_validations(file.filename or "", content, file.content_type or "")
        except BadRequestException as exc:
            rejected.append({"filename": file.filename, "reason": exc.detail["message"]})
            continue

        record = registry.create(filename=file.filename or "unknown", collection=collection)
        background_tasks.add_task(
            run_ingestion_task,
            ingestion_id=record.ingestion_id,
            filename=file.filename or "unknown",
            file_content=content,
            collection=collection,
            extra_tags=extra_tags,
            skip_duplicates=skip_duplicates,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        accepted.append(_accepted_response(record))

    return JSONResponse(
        status_code=202,
        content=ApiResponse.ok(
            BatchIngestionResponse(
                total_files=len(files),
                accepted=accepted,
                rejected=rejected,
            ).model_dump()
        ).model_dump(),
    )


# --------------------------------------------------------------------------- #
# Status
# --------------------------------------------------------------------------- #

@router.get(
    "/status/{ingestion_id}",
    summary="Get ingestion status by ID",
    response_model=ApiResponse[IngestionStatusResponse],
)
async def get_status(ingestion_id: str):
    record = get_registry().get(ingestion_id)
    if not record:
        raise NotFoundException(f"Ingestion ID '{ingestion_id}' not found.")

    status_messages = {
        IngestionStatus.PENDING:    "File is queued for processing.",
        IngestionStatus.PROCESSING: "File is being processed.",
        IngestionStatus.COMPLETED:  f"'{record.filename}' has been successfully added to the database ({record.new_chunks} chunks indexed).",
        IngestionStatus.DUPLICATE:  f"'{record.filename}' already exists in the database — skipped.",
        IngestionStatus.FAILED:     f"Ingestion failed: {record.error}",
    }

    return success({
        **IngestionStatusResponse(
            ingestion_id=record.ingestion_id,
            filename=record.filename,
            collection=record.collection,
            status=record.status,
            pages_loaded=record.pages_loaded,
            total_chunks=record.total_chunks,
            new_chunks=record.new_chunks,
            duplicate_chunks=record.duplicate_chunks,
            cache_hits=record.cache_hits,
            document_ids=record.document_ids,
            error=record.error,
            created_at=record.created_at,
            updated_at=record.updated_at,
        ).model_dump(),
        "message": status_messages.get(record.status, ""),
    })


# --------------------------------------------------------------------------- #
# List documents
# --------------------------------------------------------------------------- #

@router.get(
    "/documents",
    summary="List ingestion records",
    response_model=ApiResponse[list[DocumentListItem]],
)
async def list_documents(
    collection: str | None = Query(None, description="Filter by collection name"),
    status: IngestionStatus | None = Query(None, description="Filter by status"),
):
    registry = get_registry()
    records = (
        registry.list_by_collection(collection)
        if collection
        else registry.list_all()
    )
    if status:
        records = [r for r in records if r.status == status]

    return success([
        DocumentListItem(
            ingestion_id=r.ingestion_id,
            filename=r.filename,
            collection=r.collection,
            status=r.status,
            new_chunks=r.new_chunks,
            created_at=r.created_at,
            updated_at=r.updated_at,
        ).model_dump()
        for r in records
    ])


# --------------------------------------------------------------------------- #
# Delete record
# --------------------------------------------------------------------------- #

@router.delete(
    "/documents/{ingestion_id}",
    summary="Remove an ingestion record (does NOT delete vectors — use /vs API)",
    response_model=ApiResponse,
)
async def delete_document(ingestion_id: str):
    deleted = get_registry().delete(ingestion_id)
    if not deleted:
        raise NotFoundException(f"Ingestion ID '{ingestion_id}' not found.")
    return success({"deleted": ingestion_id})


# --------------------------------------------------------------------------- #
# Retry failed ingestion
# --------------------------------------------------------------------------- #

@router.post(
    "/retry/{ingestion_id}",
    summary="Retry a failed ingestion",
    response_model=ApiResponse[IngestionAcceptedResponse],
    status_code=202,
)
async def retry_ingestion(ingestion_id: str, background_tasks: BackgroundTasks):
    record = get_registry().get(ingestion_id)
    if not record:
        raise NotFoundException(f"Ingestion ID '{ingestion_id}' not found.")
    if record.status not in (IngestionStatus.FAILED,):
        raise BadRequestException(
            f"Cannot retry ingestion with status '{record.status}'. "
            "Only 'failed' ingestions can be retried."
        )

    # Reset status to pending
    record.status = IngestionStatus.PENDING
    record.error = None
    get_registry().update(record)

    # Note: we cannot re-read the original file bytes after the request.
    # The caller must re-upload. We surface this as a clear error message.
    raise BadRequestException(
        "Retry requires re-uploading the file. "
        "Please POST to /ingest/ again with the same file."
    )


# --------------------------------------------------------------------------- #
# Full metadata
# --------------------------------------------------------------------------- #

@router.get(
    "/metadata/{ingestion_id}",
    summary="Full ingestion metadata",
    response_model=ApiResponse[IngestionStatusResponse],
)
async def get_metadata(ingestion_id: str):
    # Same as status endpoint — keeping as a separate named route for discoverability
    return await get_status(ingestion_id)
