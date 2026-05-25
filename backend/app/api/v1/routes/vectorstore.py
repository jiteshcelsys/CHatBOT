"""
Vector Store management API — Phase 4

Prefix: /api/v1/vs

Collections
  POST   /collections                    — create collection
  GET    /collections                    — list all collections
  GET    /collections/{name}/stats       — detailed stats
  DELETE /collections/{name}             — delete collection

Indexing
  POST   /collections/{name}/index       — upload + index a file
  POST   /collections/{name}/reindex     — re-index (delete old + ingest fresh)
  DELETE /collections/{name}/docs/source — delete by source filename
  DELETE /collections/{name}/docs/ids    — delete by specific IDs

Search
  POST   /collections/{name}/search      — similarity / scored / MMR search

Health & Cache
  GET    /health                         — vector DB health check
  GET    /cache/stats                    — embedding cache statistics
  DELETE /cache                          — clear embedding cache
"""
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, Query, UploadFile
from fastapi.responses import JSONResponse

from app.schemas.base import ApiResponse
from app.schemas.vectorstore import (
    CacheStatsResponse,
    CollectionInfoResponse,
    CollectionStatsResponse,
    CreateCollectionRequest,
    DeleteByIdsRequest,
    DeleteByIdsResponse,
    DeleteBySourceResponse,
    IndexResponse,
    SearchChunk,
    SearchRequest,
    SearchResponse,
    VectorDBHealthResponse,
)
from app.utils.exceptions import BadRequestException, NotFoundException
from app.utils.responses import success
from app.vectorstore.cache_service import get_embedding_cache
from app.vectorstore.collection_manager import CollectionManager
from app.vectorstore.indexing_service import IndexingService
from app.vectorstore.retrieval_service import RetrievalService
from app.core.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/vs", tags=["Vector Store"])

_UPLOAD_DIR = Path("uploads")
_UPLOAD_DIR.mkdir(exist_ok=True)
_ALLOWED_EXT = {".pdf", ".txt"}

# --------------------------------------------------------------------------- #
# Dependencies
# --------------------------------------------------------------------------- #


def _col_manager() -> CollectionManager:
    return CollectionManager()


def _indexer(name: str, chunk_size: int | None = None, chunk_overlap: int | None = None) -> IndexingService:
    return IndexingService(collection_name=name, chunk_size=chunk_size, chunk_overlap=chunk_overlap)


def _retriever(name: str) -> RetrievalService:
    return RetrievalService(collection_name=name)


# --------------------------------------------------------------------------- #
# Collections
# --------------------------------------------------------------------------- #

@router.post(
    "/collections",
    summary="Create a new collection",
    response_model=ApiResponse[CollectionInfoResponse],
)
async def create_collection(body: CreateCollectionRequest):
    mgr = _col_manager()
    try:
        col = mgr.create_strict(body.name, body.description)
    except ValueError as exc:
        raise BadRequestException(str(exc))
    return success(
        CollectionInfoResponse(
            name=col.name,
            document_count=col.count(),
            metadata=col.metadata or {},
            created_at=(col.metadata or {}).get("created_at", ""),
        ).model_dump()
    )


@router.get(
    "/collections",
    summary="List all collections",
    response_model=ApiResponse[list[CollectionInfoResponse]],
)
async def list_collections():
    mgr = _col_manager()
    items = mgr.list_collections()
    return success([
        CollectionInfoResponse(
            name=c.name,
            document_count=c.document_count,
            metadata=c.metadata,
            created_at=c.created_at,
        ).model_dump()
        for c in items
    ])


@router.get(
    "/collections/{name}/stats",
    summary="Detailed collection statistics",
    response_model=ApiResponse[CollectionStatsResponse],
)
async def collection_stats(name: str):
    mgr = _col_manager()
    try:
        stats = mgr.stats(name)
    except KeyError as exc:
        raise NotFoundException(str(exc))
    return success(CollectionStatsResponse(
        name=stats.name,
        document_count=stats.document_count,
        metadata=stats.metadata,
        sample_ids=stats.sample_ids,
        sources=stats.sources,
        created_at=stats.created_at,
    ).model_dump())


@router.delete(
    "/collections/{name}",
    summary="Delete a collection and all its vectors",
    response_model=ApiResponse,
)
async def delete_collection(name: str):
    mgr = _col_manager()
    try:
        mgr.delete(name)
    except KeyError as exc:
        raise NotFoundException(str(exc))
    return success({"deleted": name})


# --------------------------------------------------------------------------- #
# Indexing
# --------------------------------------------------------------------------- #

@router.post(
    "/collections/{name}/index",
    summary="Upload and index a document",
    response_model=ApiResponse[IndexResponse],
)
async def index_document(
    name: str,
    file: UploadFile = File(...),
    skip_duplicates: bool = Form(True),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    tags: str = Form(""),   # JSON string, e.g. '{"project":"alpha"}'
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise BadRequestException(f"Unsupported file type '{ext}'. Allowed: {', '.join(_ALLOWED_EXT)}")

    content = await file.read()
    if not content:
        raise BadRequestException("Uploaded file is empty.")

    # Parse optional tags JSON
    import json
    extra_tags: dict | None = None
    if tags.strip():
        try:
            extra_tags = json.loads(tags)
        except json.JSONDecodeError:
            raise BadRequestException("'tags' must be a valid JSON object string.")

    tmp_path = _UPLOAD_DIR / f"{uuid.uuid4().hex}_{file.filename}"
    tmp_path.write_bytes(content)

    try:
        svc = _indexer(name, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        result = await svc.ingest(
            file_path=str(tmp_path),
            source_name=file.filename or tmp_path.name,
            extra_tags=extra_tags,
            skip_duplicates=skip_duplicates,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    return success(IndexResponse(
        file_name=result.file_name,
        collection=result.collection,
        pages_loaded=result.pages_loaded,
        total_chunks=result.total_chunks,
        new_chunks=result.new_chunks,
        duplicate_chunks=result.duplicate_chunks,
        document_ids=result.document_ids,
        cache_hits=result.cache_hits,
    ).model_dump())


@router.post(
    "/collections/{name}/reindex",
    summary="Re-index a document (replaces existing chunks for the same source)",
    response_model=ApiResponse[IndexResponse],
)
async def reindex_document(
    name: str,
    file: UploadFile = File(...),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
):
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_EXT:
        raise BadRequestException(f"Unsupported file type '{ext}'.")

    content = await file.read()
    if not content:
        raise BadRequestException("Uploaded file is empty.")

    tmp_path = _UPLOAD_DIR / f"{uuid.uuid4().hex}_{file.filename}"
    tmp_path.write_bytes(content)

    try:
        svc = _indexer(name, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        result = await svc.reindex(
            file_path=str(tmp_path),
            source_name=file.filename or tmp_path.name,
        )
    finally:
        tmp_path.unlink(missing_ok=True)

    return success(IndexResponse(
        file_name=result.file_name,
        collection=result.collection,
        pages_loaded=result.pages_loaded,
        total_chunks=result.total_chunks,
        new_chunks=result.new_chunks,
        duplicate_chunks=result.duplicate_chunks,
        document_ids=result.document_ids,
        cache_hits=result.cache_hits,
    ).model_dump())


@router.delete(
    "/collections/{name}/docs/source",
    summary="Delete all chunks from a specific source file",
    response_model=ApiResponse[DeleteBySourceResponse],
)
async def delete_by_source(
    name: str,
    source: str = Query(..., description="Exact source filename as stored in metadata"),
):
    svc = _indexer(name)
    result = svc.delete_by_source(source)
    return success(DeleteBySourceResponse(
        collection=result.collection,
        source=result.source,
        deleted_count=result.deleted_count,
    ).model_dump())


@router.delete(
    "/collections/{name}/docs/ids",
    summary="Delete specific chunks by their ChromaDB IDs",
    response_model=ApiResponse[DeleteByIdsResponse],
)
async def delete_by_ids(name: str, body: DeleteByIdsRequest):
    svc = _indexer(name)
    count = svc.delete_by_ids(body.ids)
    return success(DeleteByIdsResponse(collection=name, deleted_count=count).model_dump())


# --------------------------------------------------------------------------- #
# Search
# --------------------------------------------------------------------------- #

@router.post(
    "/collections/{name}/search",
    summary="Search documents — similarity / scored / MMR",
    response_model=ApiResponse[SearchResponse],
)
async def search(name: str, body: SearchRequest):
    svc = _retriever(name)
    try:
        if body.mode == "mmr":
            result = svc.mmr(
                body.query, k=body.k,
                fetch_k=body.fetch_k, lambda_mult=body.lambda_mult,
                source=body.source, file_type=body.file_type, tags=body.tags,
            )
        elif body.mode == "similarity_scored":
            result = svc.similarity_with_scores(
                body.query, k=body.k,
                score_threshold=body.score_threshold,
                source=body.source, file_type=body.file_type, tags=body.tags,
            )
        else:
            result = svc.similarity(
                body.query, k=body.k,
                source=body.source, file_type=body.file_type, tags=body.tags,
            )
    except KeyError as exc:
        raise NotFoundException(str(exc))

    return success(SearchResponse(
        query=result.query,
        collection=result.collection,
        mode=result.mode,
        total=result.total,
        chunks=[SearchChunk(**c) for c in result.results],
    ).model_dump())


# --------------------------------------------------------------------------- #
# Health & Cache
# --------------------------------------------------------------------------- #

@router.get(
    "/health",
    summary="Vector database health check",
    response_model=ApiResponse[VectorDBHealthResponse],
)
async def vectordb_health():
    from app.vectorstore.chroma_client import get_chroma_client
    settings = get_settings()
    client = get_chroma_client()
    cols = client.list_collections()
    return success(VectorDBHealthResponse(
        status="ok",
        persist_dir=str(Path(settings.chroma_persist_dir).resolve()),
        total_collections=len(cols),
        collections=[c.name for c in cols],
    ).model_dump())


@router.get(
    "/cache/stats",
    summary="Embedding cache statistics",
    response_model=ApiResponse[CacheStatsResponse],
)
async def cache_stats():
    cache = get_embedding_cache()
    return success(CacheStatsResponse(**cache.stats()).model_dump())


@router.delete(
    "/cache",
    summary="Clear the embedding cache",
    response_model=ApiResponse,
)
async def clear_cache():
    cache = get_embedding_cache()
    cleared = cache.clear()
    return success({"cleared_entries": cleared})
