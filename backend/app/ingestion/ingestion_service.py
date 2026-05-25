"""
IngestionService — orchestrates the full document ingestion pipeline.

Pipeline order:
  1. Parse      → file bytes → list[Document]  (via file_handler.py)
  2. Clean      → strip noise, normalize unicode  (cleaner.py)
  3. Metadata   → attach sha256, doc_id, timestamps  (metadata_extractor.py)
  4. Dedup      → check file-level SHA-256 against ChromaDB  (duplicate_detector.py)
  5. Chunk      → RecursiveCharacterTextSplitter  (chunk_service.py)
  6. Chunk dedup→ skip chunks that already exist  (duplicate_detector.py)
  7. Embed+Store→ batch embed and write to ChromaDB  (IndexingService from Phase 4)

Returns an IngestionResult dataclass consumed by the background task runner
and the API layer.
"""
import logging
import uuid
from dataclasses import dataclass, field

from app.core.config import get_settings
from app.ingestion.background_tasks import IngestionStatus
from app.ingestion.chunking.chunk_service import ChunkService
from app.ingestion.file_handler import parse_file
from app.ingestion.preprocessors.cleaner import clean_documents
from app.ingestion.preprocessors.duplicate_detector import (
    check_file_duplicate,
    filter_duplicate_chunks,
    register_file,
)
from app.ingestion.preprocessors.metadata_extractor import (
    compute_file_sha256,
    extract_and_attach,
)
from app.vectorstore.collection_manager import CollectionManager
from app.vectorstore.indexing_service import IndexingService as VectorIndexer

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    ingestion_id: str
    filename: str
    collection: str
    status: IngestionStatus
    pages_loaded: int = 0
    total_chunks: int = 0
    new_chunks: int = 0
    duplicate_chunks: int = 0
    cache_hits: int = 0
    document_ids: list[str] = field(default_factory=list)


class IngestionService:
    def __init__(
        self,
        collection_name: str = "documents",
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
    ):
        settings = get_settings()
        self._collection_name = collection_name
        self._chunk_size = chunk_size or settings.chroma_chunk_size
        self._chunk_overlap = chunk_overlap or settings.chroma_chunk_overlap
        self._col_manager = CollectionManager()
        self._chunker = ChunkService(
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )

    async def ingest(
        self,
        filename: str,
        file_content: bytes,
        ingestion_id: str | None = None,
        extra_tags: dict | None = None,
        skip_duplicates: bool = True,
    ) -> IngestionResult:
        run_id = ingestion_id or str(uuid.uuid4())
        col = self._col_manager.get_or_create(self._collection_name)

        # ── Step 1: file-level duplicate check ──────────────────────────────
        sha256 = compute_file_sha256(file_content)
        if skip_duplicates and check_file_duplicate(col, sha256):
            logger.info("File duplicate — skipping ingest | sha256=%s...", sha256[:12])
            return IngestionResult(
                ingestion_id=run_id,
                filename=filename,
                collection=self._collection_name,
                status=IngestionStatus.DUPLICATE,
            )

        # ── Step 2: parse ────────────────────────────────────────────────────
        docs = await parse_file(filename, file_content)
        pages_loaded = len(docs)

        # ── Step 3: clean ────────────────────────────────────────────────────
        docs = clean_documents(docs)
        if not docs:
            logger.warning("All content was empty after cleaning: %s", filename)
            return IngestionResult(
                ingestion_id=run_id,
                filename=filename,
                collection=self._collection_name,
                status=IngestionStatus.FAILED,
                pages_loaded=pages_loaded,
            )

        # ── Step 4: attach metadata ──────────────────────────────────────────
        docs = extract_and_attach(
            docs,
            source=filename,
            file_content=file_content,
            collection=self._collection_name,
            ingestion_id=run_id,
            extra_tags=extra_tags,
        )

        # ── Step 5: chunk ────────────────────────────────────────────────────
        chunks = self._chunker.chunk(docs)
        total_chunks = len(chunks)

        # ── Step 6: chunk-level deduplication ────────────────────────────────
        if skip_duplicates:
            chunks, chunk_skipped = filter_duplicate_chunks(col, chunks)
        else:
            chunk_skipped = 0

        if not chunks:
            logger.info("All chunks already indexed for '%s'", filename)
            return IngestionResult(
                ingestion_id=run_id,
                filename=filename,
                collection=self._collection_name,
                status=IngestionStatus.DUPLICATE,
                pages_loaded=pages_loaded,
                total_chunks=total_chunks,
                duplicate_chunks=chunk_skipped,
            )

        # ── Step 7: embed + store ────────────────────────────────────────────
        v_indexer = VectorIndexer(
            collection_name=self._collection_name,
            chunk_size=self._chunk_size,
            chunk_overlap=self._chunk_overlap,
        )
        # Pass pre-built chunks directly to the batch-store method
        ids, cache_hits = await v_indexer._batch_store(chunks)

        # Register file hash to warm the in-memory dedup cache
        register_file(sha256)

        logger.info(
            "Ingestion complete | id=%s source=%s pages=%d chunks=%d new=%d skipped=%d",
            run_id, filename, pages_loaded, total_chunks, len(ids), chunk_skipped,
        )
        return IngestionResult(
            ingestion_id=run_id,
            filename=filename,
            collection=self._collection_name,
            status=IngestionStatus.COMPLETED,
            pages_loaded=pages_loaded,
            total_chunks=total_chunks,
            new_chunks=len(ids),
            duplicate_chunks=chunk_skipped,
            cache_hits=cache_hits,
            document_ids=ids,
        )
