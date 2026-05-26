"""
ChromaDB vector store — persists embeddings to disk.

The store is keyed by `collection_name` so multiple document sets can
coexist in the same ChromaDB directory without interfering.
"""
import logging

from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.rag.embeddings import get_embeddings
from app.vectorstore.chroma_client import get_chroma_client

logger = logging.getLogger(__name__)

_DEFAULT_COLLECTION = "documents"


class VectorStoreService:
    def __init__(self, collection_name: str = _DEFAULT_COLLECTION):
        self._collection_name = collection_name
        self._store: Chroma | None = None

    # ------------------------------------------------------------------ #
    # Internal: lazy-load the store
    # ------------------------------------------------------------------ #

    def _get_store(self) -> Chroma:
        if self._store is None:
            self._store = Chroma(
                client=get_chroma_client(),
                collection_name=self._collection_name,
                embedding_function=get_embeddings(),
            )
            logger.info("ChromaDB Cloud store opened | collection=%s", self._collection_name)
        return self._store

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def add_documents(self, documents: list[Document]) -> list[str]:
        """Embed and store documents. Returns the assigned document IDs."""
        store = self._get_store()
        ids = store.add_documents(documents)
        logger.info("Added %d chunk(s) to collection '%s'", len(ids), self._collection_name)
        return ids

    def similarity_search(
        self,
        query: str,
        k: int = 4,
        score_threshold: float | None = None,
    ) -> list[Document]:
        """Return the top-k most similar documents to the query."""
        store = self._get_store()
        if score_threshold is not None:
            results = store.similarity_search_with_relevance_scores(query, k=k)
            return [doc for doc, score in results if score >= score_threshold]
        return store.similarity_search(query, k=k)

    def similarity_search_with_scores(
        self, query: str, k: int = 4
    ) -> list[tuple[Document, float]]:
        """Same as similarity_search but also returns relevance scores."""
        return self._get_store().similarity_search_with_relevance_scores(query, k=k)

    def delete_collection(self) -> None:
        store = self._get_store()
        store.delete_collection()
        self._store = None
        logger.warning("Deleted collection '%s'", self._collection_name)

    def collection_count(self) -> int:
        return self._get_store()._collection.count()
