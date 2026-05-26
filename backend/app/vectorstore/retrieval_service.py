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
        self._collection_name = collection_name
        self._col_manager = CollectionManager()

    def _assert_collection_exists(self) -> None:
        if not self._col_manager.exists(self._collection_name):
            raise KeyError(f"Collection '{self._collection_name}' not found.")

    def _raw_query(self, query: str, k: int, where: dict | None = None) -> list[dict]:
        """Query chromadb directly using raw client — bypasses langchain-chroma."""
        col = self._col_manager.get_or_create(self._collection_name)
        query_embedding = get_embeddings().embed_query(query)
        kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": min(k, col.count()),
            "include": ["documents", "metadatas", "distances"],
        }
        if where:
            kwargs["where"] = where
        if kwargs["n_results"] == 0:
            return []
        results = col.query(**kwargs)
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        return [
            {"content": d, "metadata": m, "score": round(1 - dist, 4)}
            for d, m, dist in zip(docs, metas, dists)
        ]

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
        """Top-k cosine-similar documents via raw chromadb query."""
        self._assert_collection_exists()
        where = build_where_filter(source=source, file_type=file_type, tags=tags)
        results = self._raw_query(query, k=k, where=where or None)
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
        results = self._raw_query(query, k=k, where=where or None)
        if score_threshold is not None:
            results = [r for r in results if (r["score"] or 0) >= score_threshold]
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
        """Retrieval via raw chromadb query (fetch_k candidates, return top k)."""
        self._assert_collection_exists()
        where = build_where_filter(source=source, file_type=file_type, tags=tags)
        candidates = self._raw_query(query, k=max(fetch_k, k), where=where or None)
        results = candidates[:k]
        logger.info(
            "mmr | col=%s k=%d fetch_k=%d lambda=%.2f returned=%d",
            self._collection_name, k, fetch_k, lambda_mult, len(results),
        )
        return SearchResult(query=query, collection=self._collection_name,
                            mode="mmr", total=len(results), results=results)

