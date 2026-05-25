"""
Memory node — loads conversation history, summary, and user persona
from Supabase and injects them into the graph state.

Runs first in the workflow so every subsequent node has full context.
"""
import logging

from app.graph.state import GraphState
from app.memory.retrieval_memory import load_memory_context

logger = logging.getLogger(__name__)


async def memory_node(state: GraphState) -> GraphState:
    """
    Input  : session_id, user_id
    Output : recent_messages, latest_summary, persona_prompt
    """
    session_id = state.get("session_id", "")
    user_id = state.get("user_id", "anonymous")

    try:
        ctx = await load_memory_context(
            session_id=session_id,
            user_id=user_id,
            recent_n=10,
        )
        logger.info(
            "memory_node | session=%s msgs=%d summary=%s persona=%s",
            session_id,
            len(ctx.recent_messages),
            bool(ctx.latest_summary),
            bool(ctx.persona_prompt),
        )
        return {
            **state,
            "recent_messages": ctx.recent_messages,
            "latest_summary": ctx.latest_summary,
            "persona_prompt": ctx.persona_prompt,
        }

    except Exception as exc:
        logger.warning("memory_node failed (non-fatal): %s", exc)
        # Memory failure is non-fatal — continue without history
        return {
            **state,
            "recent_messages": [],
            "latest_summary": "",
            "persona_prompt": "",
        }
