"""
Wraps the vector store in a LangChain BaseRetriever so it can be
dropped into any LCEL chain or LangGraph node without modification.
"""
import logging

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from app.rag.vector_store import VectorStoreService

logger = logging.getLogger(__name__)


class ChromaRetriever(BaseRetriever):
    """LangChain-compatible retriever backed by ChromaDB."""

    vector_store: VectorStoreService
    k: int = 4
    score_threshold: float | None = None

    class Config:
        arbitrary_types_allowed = True

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        logger.debug("Retrieving top-%d docs for query: %s", self.k, query[:80])
        return self.vector_store.similarity_search(
            query, k=self.k, score_threshold=self.score_threshold
        )


def build_retriever(
    collection_name: str = "documents",
    k: int = 4,
    score_threshold: float | None = None,
) -> ChromaRetriever:
    """Convenience factory used by the RAG service and LangGraph nodes."""
    vs = VectorStoreService(collection_name=collection_name)
    return ChromaRetriever(vector_store=vs, k=k, score_threshold=score_threshold)
