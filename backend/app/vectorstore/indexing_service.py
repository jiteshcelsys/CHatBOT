"""
Document indexing service.

Ingest flow
  file_path → load → split → enrich metadata → deduplicate → batch-embed → store

Key features
  - Duplicate prevention via content-hash comparison before writing.
  - Batch embedding with configurable batch_size to avoid OOM on large files.
  - Embedding cache integration (EmbeddingCache) avoids redundant model calls.
  - Re-index: deletes all chunks that share the same `source` tag, then
    re-ingests the file fresh.
  - Delete by source: removes every chunk belonging to a source file.
"""
import logging
import uuid
from dataclasses import dataclass, field

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import get_settings
from app.rag.embeddings import get_embeddings
from app.rag.loaders import DocumentLoaderService
from app.rag.splitter import TextSplitterService
from app.vectorstore.cache_service import get_embedding_cache
from app.vectorstore.chroma_client import get_chroma_client
from app.vectorstore.collection_manager import CollectionManager
from app.vectorstore.metadata_service import enrich_metadata, find_duplicate_ids

logger = logging.getLogger(__name__)

_DEFAULT_BATCH = 64   # chunks per embedding call


@dataclass
class IndexResult:
    file_name: str
    collection: str
    pages_loaded: int
    total_chunks: int
    new_chunks: int          # actually embedded + stored
    duplicate_chunks: int    # skipped because hash already existed
    document_ids: list[str] = field(default_factory=list)
    cache_hits: int = 0


@dataclass
class DeleteResult:
    collection: str
    source: str
    deleted_count: int


class IndexingService:
    def __init__(
        self,
        collection_name: str = "documents",
        chunk_size: int | None = None,
        chunk_overlap: int | None = None,
        batch_size: int = _DEFAULT_BATCH,
    ):
        settings = get_settings()
        self._collection_name = collection_name
        self._persist_dir = settings.chroma_persist_dir
        self._batch_size = batch_size

        self._loader = DocumentLoaderService()
        self._splitter = TextSplitterService(
            chunk_size=chunk_size or settings.chroma_chunk_size,
            chunk_overlap=chunk_overlap or settings.chroma_chunk_overlap,
        )
        self._col_manager = CollectionManager()
        self._cache = get_embedding_cache()

    # ------------------------------------------------------------------ #
    # LangChain Chroma store (for add_documents / delete convenience)
    # ------------------------------------------------------------------ #

    def _lc_store(self) -> Chroma:
        """LangChain Chroma wrapper for this collection."""
        return Chroma(
            client=get_chroma_client(),
            collection_name=self._collection_name,
            embedding_function=get_embeddings(),
        )

    # ------------------------------------------------------------------ #
    # Ingest
    # ------------------------------------------------------------------ #

    async def ingest(
        self,
        file_path: str,
        source_name: str,
        extra_tags: dict | None = None,
        skip_duplicates: bool = True,
    ) -> IndexResult:
        """
        Full ingest pipeline:
          load → split → enrich → deduplicate → batch-embed → store
        """
        # 1. Load
        docs: list[Document] = await self._loader.load(file_path)
        pages_loaded = len(docs)

        # 2. Split
        chunks = self._splitter.split(docs)

        # 3. Enrich metadata
        enrich_metadata(chunks, source=source_name,
                        collection=self._collection_name, extra_tags=extra_tags)

        # 4. Deduplicate
        duplicate_hashes: set[str] = set()
        if skip_duplicates:
            raw_col = self._col_manager.get_or_create(self._collection_name)
            duplicate_hashes = find_duplicate_ids(raw_col, chunks)

        new_chunks = [
            c for c in chunks
            if c.metadata.get("doc_hash") not in duplicate_hashes
        ]
        skipped = len(chunks) - len(new_chunks)

        if not new_chunks:
            logger.info(
                "All %d chunks already indexed for source '%s' — skipping",
                len(chunks), source_name,
            )
            return IndexResult(
                file_name=source_name,
                collection=self._collection_name,
                pages_loaded=pages_loaded,
                total_chunks=len(chunks),
                new_chunks=0,
                duplicate_chunks=skipped,
            )

        # 5. Batch-embed and store
        ids, cache_hits = await self._batch_store(new_chunks)

        logger.info(
            "Ingest complete | source=%s pages=%d total=%d new=%d skipped=%d cache_hits=%d",
            source_name, pages_loaded, len(chunks), len(ids), skipped, cache_hits,
        )
        return IndexResult(
            file_name=source_name,
            collection=self._collection_name,
            pages_loaded=pages_loaded,
            total_chunks=len(chunks),
            new_chunks=len(ids),
            duplicate_chunks=skipped,
            document_ids=ids,
            cache_hits=cache_hits,
        )

    # ------------------------------------------------------------------ #
    # Re-index
    # ------------------------------------------------------------------ #

    async def reindex(
        self,
        file_path: str,
        source_name: str,
        extra_tags: dict | None = None,
    ) -> IndexResult:
        """Delete all existing chunks for source_name, then ingest fresh."""
        deleted = self.delete_by_source(source_name)
        logger.info("Re-index: removed %d old chunks for source '%s'", deleted.deleted_count, source_name)
        return await self.ingest(file_path, source_name, extra_tags, skip_duplicates=False)

    # ------------------------------------------------------------------ #
    # Delete
    # ------------------------------------------------------------------ #

    def delete_by_source(self, source_name: str) -> DeleteResult:
        """Remove all chunks whose `source` metadata equals source_name."""
        raw_col = self._col_manager.get_or_create(self._collection_name)
        try:
            result = raw_col.get(
                where={"source": {"$eq": source_name}},
                include=[],
            )
            ids_to_delete: list[str] = result.get("ids") or []
        except Exception as exc:
            logger.warning("delete_by_source get failed: %s", exc)
            ids_to_delete = []

        if ids_to_delete:
            raw_col.delete(ids=ids_to_delete)
            logger.info(
                "Deleted %d chunks | source=%s collection=%s",
                len(ids_to_delete), source_name, self._collection_name,
            )

        return DeleteResult(
            collection=self._collection_name,
            source=source_name,
            deleted_count=len(ids_to_delete),
        )

    def delete_by_ids(self, doc_ids: list[str]) -> int:
        """Delete specific document chunks by their ChromaDB IDs."""
        if not doc_ids:
            return 0
        raw_col = self._col_manager.get_or_create(self._collection_name)
        raw_col.delete(ids=doc_ids)
        logger.info("Deleted %d chunks by ID from '%s'", len(doc_ids), self._collection_name)
        return len(doc_ids)

    # ------------------------------------------------------------------ #
    # Internal: batch embedding with cache
    # ------------------------------------------------------------------ #

    async def _batch_store(
        self, chunks: list[Document]
    ) -> tuple[list[str], int]:
        """
        Split chunks into batches, check cache, embed uncached ones,
        then store all in ChromaDB.  Returns (ids, cache_hit_count).
        """
        embeddings_model = get_embeddings()
        store = self._lc_store()

        all_ids: list[str] = []
        cache_hits = 0

        for i in range(0, len(chunks), self._batch_size):
            batch = chunks[i : i + self._batch_size]

            # Separate cached from uncached
            cached_vectors: dict[int, list[float]] = {}
            texts_to_embed: list[tuple[int, str]] = []

            for j, chunk in enumerate(batch):
                vec = self._cache.get(chunk.page_content)
                if vec is not None:
                    cached_vectors[j] = vec
                    cache_hits += 1
                else:
                    texts_to_embed.append((j, chunk.page_content))

            # Embed uncached texts
            if texts_to_embed:
                raw_texts = [t for _, t in texts_to_embed]
                vectors = embeddings_model.embed_documents(raw_texts)
                for (j, text), vec in zip(texts_to_embed, vectors):
                    self._cache.set(text, vec)
                    cached_vectors[j] = vec

            # Reconstruct ordered vectors for this batch
            ordered_vectors = [cached_vectors[j] for j in range(len(batch))]

            # Assign stable UUIDs
            batch_ids = [str(uuid.uuid4()) for _ in batch]

            # Store directly via the raw collection to pass pre-computed vectors
            raw_col = self._col_manager.get_or_create(self._collection_name)
            raw_col.add(
                ids=batch_ids,
                embeddings=ordered_vectors,
                documents=[c.page_content for c in batch],
                metadatas=[c.metadata for c in batch],
            )
            all_ids.extend(batch_ids)

        return all_ids, cache_hits
