"""
RAG API endpoints

POST /api/v1/rag/ingest      — upload + ingest a PDF or TXT file
POST /api/v1/rag/query       — semantic search over ingested documents
GET  /api/v1/rag/stats       — collection document count
DELETE /api/v1/rag/collection — wipe a collection (dev/testing use)
"""
import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.rag.rag_service import RAGService
from app.schemas.base import ApiResponse
from app.schemas.rag import (
    CollectionStatsResponse,
    IngestResponse,
    QueryRequest,
    RetrievalChunk,
    RetrievalResponse,
)
from app.utils.exceptions import BadRequestException, NotFoundException
from app.utils.responses import error, success

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/rag", tags=["RAG"])

_ALLOWED_EXTENSIONS = {".pdf", ".txt"}
_UPLOAD_DIR = Path("uploads")
_UPLOAD_DIR.mkdir(exist_ok=True)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _rag(collection: str) -> RAGService:
    return RAGService(collection_name=collection)


def _validate_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    if suffix not in _ALLOWED_EXTENSIONS:
        raise BadRequestException(
            f"Unsupported file type '{suffix}'. Allowed: {', '.join(_ALLOWED_EXTENSIONS)}"
        )
    return suffix


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #


@router.post(
    "/ingest",
    summary="Upload and ingest a document",
    response_model=ApiResponse[IngestResponse],
)
async def ingest_document(
    file: UploadFile = File(..., description="PDF or TXT file to ingest"),
    collection: str = Form("documents", description="Target ChromaDB collection"),
):
    """
    1. Saves the uploaded file to disk (uploads/).
    2. Loads and splits it into chunks.
    3. Generates OpenAI embeddings and stores them in ChromaDB.
    """
    _validate_extension(file.filename or "")

    # Save upload to a temp path so LangChain loaders can read it from disk
    unique_name = f"{uuid.uuid4().hex}_{file.filename}"
    save_path = _UPLOAD_DIR / unique_name

    try:
        content = await file.read()
        if len(content) == 0:
            raise BadRequestException("Uploaded file is empty.")
        save_path.write_bytes(content)

        svc = _rag(collection)
        result = await svc.ingest_file(str(save_path))

        return success(
            IngestResponse(
                file_name=file.filename or unique_name,
                collection=result.collection,
                pages_loaded=result.pages_loaded,
                chunks_stored=result.chunks_stored,
                document_ids=result.document_ids,
            ).model_dump()
        )
    except (BadRequestException, ValueError) as exc:
        raise
    except Exception as exc:
        logger.error("Ingest failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        # Remove the temp file whether or not ingest succeeded
        if save_path.exists():
            save_path.unlink()


@router.post(
    "/query",
    summary="Semantic search over ingested documents",
    response_model=ApiResponse[RetrievalResponse],
)
async def query_documents(body: QueryRequest):
    """
    Embeds the query with OpenAI, performs a cosine similarity search in
    ChromaDB, and returns the top-k most relevant chunks.
    """
    try:
        svc = _rag(body.collection)
        result = svc.retrieve(body.query, k=body.k, with_scores=body.with_scores)

        if not result.chunks:
            return success(
                RetrievalResponse(
                    query=body.query,
                    collection=body.collection,
                    total_results=0,
                    chunks=[],
                ).model_dump()
            )

        return success(
            RetrievalResponse(
                query=body.query,
                collection=body.collection,
                total_results=len(result.chunks),
                chunks=[RetrievalChunk(**c) for c in result.chunks],
            ).model_dump()
        )
    except Exception as exc:
        logger.error("Query failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get(
    "/stats",
    summary="Collection statistics",
    response_model=ApiResponse[CollectionStatsResponse],
)
async def collection_stats(
    collection: str = Query("documents", description="ChromaDB collection name"),
):
    try:
        svc = _rag(collection)
        stats = svc.collection_stats()
        return success(CollectionStatsResponse(**stats).model_dump())
    except Exception as exc:
        logger.error("Stats failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.delete(
    "/collection",
    summary="Delete a ChromaDB collection (dev only)",
    response_model=ApiResponse,
)
async def delete_collection(
    collection: str = Query("documents", description="ChromaDB collection name"),
):
    try:
        svc = _rag(collection)
        svc.delete_collection()
        return success({"deleted": collection})
    except Exception as exc:
        logger.error("Delete collection failed: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
