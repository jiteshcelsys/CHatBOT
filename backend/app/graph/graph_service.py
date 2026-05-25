"""
GraphService — thin facade over the compiled LangGraph graph.

Provides two execution modes:
  invoke()  → returns the final GraphState after all nodes complete.
  stream()  → yields string tokens as they are generated (streaming mode).

Both modes accept the same input dict and apply default values for
optional fields before invoking the graph.
"""
import logging
import uuid
from typing import AsyncIterator

from app.graph.graph_builder import get_graph
from app.graph.nodes.generation_node import stream_generation
from app.graph.state import GraphState

logger = logging.getLogger(__name__)


def _build_initial_state(
    user_message: str,
    session_id: str | None = None,
    user_id: str = "anonymous",
    collection: str = "documents",
    stream: bool = False,
) -> GraphState:
    return GraphState(
        session_id=session_id or str(uuid.uuid4()),
        user_id=user_id,
        user_message=user_message,
        collection=collection,
        stream=stream,
        recent_messages=[],
        latest_summary="",
        persona_prompt="",
        retrieved_chunks=[],
        retrieval_skipped=False,
        needs_retrieval=True,
        needs_summary=False,
        ai_response="",
        prompt_tokens=0,
        completion_tokens=0,
        total_tokens=0,
        model_used="",
        finish_reason="",
        error=None,
        retry_count=0,
        metadata={},
    )


class GraphService:
    async def invoke(
        self,
        user_message: str,
        session_id: str | None = None,
        user_id: str = "anonymous",
        collection: str = "documents",
    ) -> GraphState:
        """Run the full graph and return the completed state."""
        initial = _build_initial_state(
            user_message=user_message,
            session_id=session_id,
            user_id=user_id,
            collection=collection,
        )
        graph = get_graph()
        result: GraphState = await graph.ainvoke(initial)
        logger.info(
            "Graph invoke done | session=%s tokens=%d",
            result.get("session_id"), result.get("total_tokens", 0),
        )
        return result

    async def stream(
        self,
        user_message: str,
        session_id: str | None = None,
        user_id: str = "anonymous",
        collection: str = "documents",
    ) -> AsyncIterator[str]:
        """
        Execute memory + routing + retrieval nodes first (synchronously),
        then stream the generation node token by token.
        Persistence is called after streaming completes.
        """
        from app.graph.nodes.memory_node import memory_node
        from app.graph.nodes.routing_node import routing_node
        from app.graph.nodes.retrieval_node import retrieval_node
        from app.graph.nodes.persistence_node import persistence_node

        state = _build_initial_state(
            user_message=user_message,
            session_id=session_id,
            user_id=user_id,
            collection=collection,
            stream=True,
        )

        # Run pre-generation nodes
        state = await memory_node(state)
        state = routing_node(state)
        state = await retrieval_node(state)

        # Stream generation
        full_response = []
        async for token in stream_generation(state):
            full_response.append(token)
            yield token

        # Persist after streaming
        state["ai_response"] = "".join(full_response)
        await persistence_node(state)
