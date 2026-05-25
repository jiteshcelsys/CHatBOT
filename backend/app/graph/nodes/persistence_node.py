"""
Persistence node — saves the conversation turn to Supabase after generation.

Saves both the user message and the AI response in a single atomic-ish
operation. Also triggers conversation summarisation if needs_summary=True.
"""
import logging

from app.core.config import get_settings
from app.graph.state import GraphState
from app.memory.memory_service import save_message
from app.memory.session_memory import increment_message_count

logger = logging.getLogger(__name__)


async def persistence_node(state: GraphState) -> GraphState:
    """
    Input  : session_id, user_id, user_message, ai_response,
             total_tokens, needs_summary
    Output : state (unchanged — side-effects only)
    """
    session_id = state.get("session_id", "")
    user_id = state.get("user_id", "anonymous")

    if not session_id:
        logger.warning("persistence_node: no session_id — skipping save")
        return state

    try:
        # Save user message
        await save_message(
            session_id=session_id,
            user_id=user_id,
            role="user",
            content=state.get("user_message", ""),
        )

        # Save AI response with token metadata
        await save_message(
            session_id=session_id,
            user_id=user_id,
            role="assistant",
            content=state.get("ai_response", ""),
            metadata={
                "model": state.get("model_used", ""),
                "finish_reason": state.get("finish_reason", ""),
                "retrieval_used": not state.get("retrieval_skipped", True),
                "chunks_used": len(state.get("retrieved_chunks") or []),
            },
            tokens_used=state.get("total_tokens", 0),
        )

        # Increment message counter on the session
        await increment_message_count(session_id)

        logger.info("persistence_node | saved turn for session=%s", session_id)

        # Trigger summarisation if the conversation is long
        if state.get("needs_summary"):
            await _trigger_summary(state)

    except Exception as exc:
        logger.error("persistence_node failed: %s", exc)
        # Non-fatal — the user still receives their response

    return state


async def _trigger_summary(state: GraphState) -> None:
    """Generate and store a rolling summary of the conversation."""
    from app.memory.summary_service import save_summary
    from app.memory.memory_service import get_recent_messages
    from langchain_groq import ChatGroq
    from langchain_core.messages import HumanMessage, SystemMessage

    settings = get_settings()
    session_id = state.get("session_id", "")
    user_id = state.get("user_id", "anonymous")
    recent = await get_recent_messages(session_id, n=30)

    if len(recent) < 10:
        return

    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in recent
    )
    prompt = (
        "Summarise the following conversation in 2-4 sentences, "
        "capturing the key topics and user intent.\n\n" + history_text
    )
    llm = ChatGroq(api_key=settings.groq_api_key, model=settings.groq_model)
    response = await llm.ainvoke([
        SystemMessage(content="You are a summarisation assistant."),
        HumanMessage(content=prompt),
    ])
    summary_text = response.content or ""
    await save_summary(
        session_id=session_id,
        user_id=user_id,
        summary=summary_text,
        message_range={"from": 0, "to": len(recent)},
    )
    logger.info("Summary generated for session=%s", session_id)
