"""
Retrieval node — queries ChromaDB for context relevant to the user message.

Uses MMR (Maximal Marginal Relevance) so the returned chunks are diverse
rather than all saying the same thing.  Falls back to plain similarity
if the collection is empty or retrieval fails.
"""
import logging

from app.graph.state import GraphState
from app.vectorstore.collection_manager import CollectionManager
from app.vectorstore.retrieval_service import RetrievalService

logger = logging.getLogger(__name__)

_DEFAULT_K = 4


async def retrieval_node(state: GraphState) -> GraphState:
    """
    Input  : user_message, collection, needs_retrieval
    Output : retrieved_chunks, retrieval_skipped
    """
    if not state.get("needs_retrieval", True):
        logger.debug("retrieval_node skipped (needs_retrieval=False)")
        return {**state, "retrieved_chunks": [], "retrieval_skipped": True}

    collection = state.get("collection", "documents")
    query = state.get("user_message", "")

    try:
        mgr = CollectionManager()
        if not mgr.exists(collection):
            logger.info("retrieval_node | collection '%s' does not exist — skipping", collection)
            return {**state, "retrieved_chunks": [], "retrieval_skipped": True}

        svc = RetrievalService(collection_name=collection)
        result = svc.mmr(query, k=_DEFAULT_K, fetch_k=_DEFAULT_K * 4, lambda_mult=0.6)

        chunks = [
            {"content": c["content"], "metadata": c["metadata"]}
            for c in result.results
        ]
        logger.info("retrieval_node | collection=%s returned=%d chunks", collection, len(chunks))
        return {**state, "retrieved_chunks": chunks, "retrieval_skipped": False}

    except Exception as exc:
        logger.warning("retrieval_node failed (non-fatal): %s", exc)
        return {**state, "retrieved_chunks": [], "retrieval_skipped": True}
