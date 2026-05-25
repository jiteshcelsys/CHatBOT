"""
High-level RAG orchestrator.

Ingest flow : file → load → split → embed → store
Query flow  : query → retrieve → return ranked chunks
"""
import logging
import os
import shutil
import uuid
from dataclasses import dataclass, field

from langchain_core.documents import Document

from app.rag.loaders import DocumentLoaderService
from app.rag.retriever import build_retriever
from app.rag.splitter import TextSplitterService
from app.rag.vector_store import VectorStoreService
from app.services.base import BaseService

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    file_name: str
    collection: str
    pages_loaded: int
    chunks_stored: int
    document_ids: list[str] = field(default_factory=list)


@dataclass
class RetrievalResult:
    query: str
    collection: str
    chunks: list[dict]   # [{"content": str, "metadata": dict, "score": float|None}]


class RAGService(BaseService):
    def __init__(
        self,
        collection_name: str = "documents",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self._collection_name = collection_name
        self._loader = DocumentLoaderService()
        self._splitter = TextSplitterService(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )
        self._vector_store = VectorStoreService(collection_name=collection_name)

    # ------------------------------------------------------------------ #
    # Ingest
    # ------------------------------------------------------------------ #

    async def ingest_file(self, file_path: str) -> IngestResult:
        """Load → split → embed → store a single file."""
        file_name = os.path.basename(file_path)
        logger.info("Ingesting file: %s → collection: %s", file_name, self._collection_name)

        # 1. Load
        docs: list[Document] = await self._loader.load(file_path)

        # 2. Split
        chunks = self._splitter.split(docs)

        # 3. Enrich metadata so every chunk knows its origin
        for chunk in chunks:
            chunk.metadata.setdefault("source", file_name)
            chunk.metadata.setdefault("collection", self._collection_name)

        # 4. Store
        ids = self._vector_store.add_documents(chunks)

        logger.info(
            "Ingest complete | file=%s pages=%d chunks=%d",
            file_name,
            len(docs),
            len(chunks),
        )
        return IngestResult(
            file_name=file_name,
            collection=self._collection_name,
            pages_loaded=len(docs),
            chunks_stored=len(chunks),
            document_ids=ids,
        )

    # ------------------------------------------------------------------ #
    # Query / Retrieve
    # ------------------------------------------------------------------ #

    def retrieve(
        self,
        query: str,
        k: int = 4,
        with_scores: bool = False,
    ) -> RetrievalResult:
        """Return the top-k semantically relevant chunks for a query."""
        logger.info(
            "Retrieving | collection=%s k=%d query=%s",
            self._collection_name,
            k,
            query[:80],
        )

        if with_scores:
            pairs = self._vector_store.similarity_search_with_scores(query, k=k)
            chunks = [
                {"content": doc.page_content, "metadata": doc.metadata, "score": round(score, 4)}
                for doc, score in pairs
            ]
        else:
            docs = self._vector_store.similarity_search(query, k=k)
            chunks = [
                {"content": doc.page_content, "metadata": doc.metadata, "score": None}
                for doc in docs
            ]

        return RetrievalResult(
            query=query,
            collection=self._collection_name,
            chunks=chunks,
        )

    # ------------------------------------------------------------------ #
    # Utility
    # ------------------------------------------------------------------ #

    def collection_stats(self) -> dict:
        return {
            "collection": self._collection_name,
            "total_chunks": self._vector_store.collection_count(),
        }

    def delete_collection(self) -> None:
        self._vector_store.delete_collection()
        logger.warning("Collection deleted: %s", self._collection_name)
