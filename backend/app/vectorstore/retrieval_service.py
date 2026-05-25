"""
Advanced retrieval service.

Search modes
  - similarity         : plain cosine similarity, returns top-k docs
  - similarity_scored  : same but includes relevance scores [0, 1]
  - mmr                : Maximal Marginal Relevance — balances relevance
                         with diversity, good for long documents
  - filtered           : any of the above with metadata pre-filtering

All methods accept an optional `where` dict (ChromaDB filter syntax) so
callers can narrow results by source, file_type, tags, etc.
"""
import logging
from dataclasses import dataclass

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import get_settings
from app.rag.embeddings import get_embeddings
from app.vectorstore.collection_manager import CollectionManager
from app.vectorstore.metadata_service import build_where_filter

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    query: str
    collection: str
    mode: str
    total: int
    results: list[dict]    # {"content": str, "metadata": dict, "score": float|None}


class RetrievalService:
    def __init__(self, collection_name: str = "documents"):
        settings = get_settings()
        self._collection_name = collection_name
        self._persist_dir = settings.chroma_persist_dir
        self._col_manager = CollectionManager()

    # ------------------------------------------------------------------ #
    # Internal: LangChain Chroma store handle
    # ------------------------------------------------------------------ #

    def _store(self) -> Chroma:
        return Chroma(
            collection_name=self._collection_name,
            embedding_function=get_embeddings(),
            persist_directory=self._persist_dir,
        )

    def _assert_collection_exists(self) -> None:
        if not self._col_manager.exists(self._collection_name):
            raise KeyError(f"Collection '{self._collection_name}' not found.")

    # ------------------------------------------------------------------ #
    # Similarity search
    # ------------------------------------------------------------------ #

    def similarity(
        self,
        query: str,
        k: int = 4,
        source: str | None = None,
        file_type: str | None = None,
        tags: dict | None = None,
    ) -> SearchResult:
        """Top-k cosine-similar documents, with optional metadata filter."""
        self._assert_collection_exists()
        where = build_where_filter(source=source, file_type=file_type, tags=tags)

        kwargs: dict = {"k": k}
        if where:
            kwargs["filter"] = where

        docs: list[Document] = self._store().similarity_search(query, **kwargs)
        results = [{"content": d.page_content, "metadata": d.metadata, "score": None} for d in docs]
        logger.info("similarity | col=%s k=%d returned=%d", self._collection_name, k, len(results))
        return SearchResult(query=query, collection=self._collection_name,
                            mode="similarity", total=len(results), results=results)

    def similarity_with_scores(
        self,
        query: str,
        k: int = 4,
        score_threshold: float | None = None,
        source: str | None = None,
        file_type: str | None = None,
        tags: dict | None = None,
    ) -> SearchResult:
        """Top-k results with relevance score [0, 1]. Optionally filter by threshold."""
        self._assert_collection_exists()
        where = build_where_filter(source=source, file_type=file_type, tags=tags)

        kwargs: dict = {"k": k}
        if where:
            kwargs["filter"] = where

        pairs: list[tuple[Document, float]] = (
            self._store().similarity_search_with_relevance_scores(query, **kwargs)
        )

        if score_threshold is not None:
            pairs = [(d, s) for d, s in pairs if s >= score_threshold]

        results = [
            {"content": d.page_content, "metadata": d.metadata, "score": round(s, 4)}
            for d, s in pairs
        ]
        logger.info(
            "similarity_scored | col=%s k=%d threshold=%s returned=%d",
            self._collection_name, k, score_threshold, len(results),
        )
        return SearchResult(query=query, collection=self._collection_name,
                            mode="similarity_scored", total=len(results), results=results)

    # ------------------------------------------------------------------ #
    # MMR (Maximal Marginal Relevance)
    # ------------------------------------------------------------------ #

    def mmr(
        self,
        query: str,
        k: int = 4,
        fetch_k: int = 20,
        lambda_mult: float = 0.5,
        source: str | None = None,
        file_type: str | None = None,
        tags: dict | None = None,
    ) -> SearchResult:
        """
        MMR retrieval — returns diverse top-k results.

        fetch_k  : candidate pool size before re-ranking (>= k)
        lambda_mult: 0 = max diversity, 1 = max relevance (default 0.5)
        """
        self._assert_collection_exists()
        where = build_where_filter(source=source, file_type=file_type, tags=tags)

        kwargs: dict = {"k": k, "fetch_k": max(fetch_k, k), "lambda_mult": lambda_mult}
        if where:
            kwargs["filter"] = where

        docs: list[Document] = self._store().max_marginal_relevance_search(query, **kwargs)
        results = [{"content": d.page_content, "metadata": d.metadata, "score": None} for d in docs]
        logger.info(
            "mmr | col=%s k=%d fetch_k=%d lambda=%.2f returned=%d",
            self._collection_name, k, fetch_k, lambda_mult, len(results),
        )
        return SearchResult(query=query, collection=self._collection_name,
                            mode="mmr", total=len(results), results=results)

    # ------------------------------------------------------------------ #
    # Hybrid preparation helper
    # ------------------------------------------------------------------ #

    def get_retriever(
        self,
        search_type: str = "similarity",
        k: int = 4,
        score_threshold: float | None = None,
    ):
        """
        Return a LangChain BaseRetriever for use in LCEL chains / LangGraph nodes.
        search_type: "similarity" | "mmr" | "similarity_score_threshold"
        """
        self._assert_collection_exists()
        store = self._store()

        if search_type == "mmr":
            return store.as_retriever(
                search_type="mmr",
                search_kwargs={"k": k, "fetch_k": max(k * 4, 20)},
            )
        if search_type == "similarity_score_threshold" and score_threshold is not None:
            return store.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={"score_threshold": score_threshold, "k": k},
            )
        return store.as_retriever(search_kwargs={"k": k})
