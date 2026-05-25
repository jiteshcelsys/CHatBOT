"""
Generation node — builds the full prompt and calls the Groq LLM.

Prompt assembly order:
  1. System prompt (role + instructions)
  2. Persona prompt (user facts from long-term memory)
  3. Conversation summary (if any — compressed older history)
  4. Recent messages (last N turns)
  5. RAG context (retrieved chunks)
  6. Current user message

Token tracking is extracted from the Groq response's usage metadata.
"""
import logging
from typing import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from app.core.config import get_settings
from app.graph.state import GraphState

logger = logging.getLogger(__name__)

_SYSTEM_TEMPLATE = """\
You are a helpful, knowledgeable AI assistant.
Answer the user's questions clearly and concisely.
When you use information from the provided documents, cite the source.
If you don't know something, say so honestly.
"""


def _build_messages(state: GraphState) -> list:
    """Assemble the full message list for the LLM."""
    parts: list[str] = [_SYSTEM_TEMPLATE]

    persona = state.get("persona_prompt", "")
    if persona:
        parts.append(f"\n{persona}")

    summary = state.get("latest_summary", "")
    if summary:
        parts.append(f"\nConversation summary so far:\n{summary}")

    system_content = "\n".join(parts)
    messages = [SystemMessage(content=system_content)]

    # Recent history
    for msg in state.get("recent_messages") or []:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))

    # RAG context injected as a system-style block before the current question
    chunks = state.get("retrieved_chunks") or []
    if chunks:
        ctx_text = "\n\n---\n".join(
            f"[Source: {c['metadata'].get('source', 'unknown')}]\n{c['content']}"
            for c in chunks
        )
        rag_msg = (
            f"Relevant document context:\n\n{ctx_text}\n\n"
            "Use this context to answer the question below if relevant."
        )
        messages.append(SystemMessage(content=rag_msg))

    # Current user turn
    messages.append(HumanMessage(content=state.get("user_message", "")))
    return messages


def _get_llm() -> ChatGroq:
    settings = get_settings()
    return ChatGroq(
        api_key=settings.groq_api_key,
        model=settings.groq_model,
        temperature=0.7,
        max_retries=3,
    )


async def generation_node(state: GraphState) -> GraphState:
    """
    Input  : user_message, recent_messages, retrieved_chunks, persona_prompt,
             latest_summary
    Output : ai_response, prompt_tokens, completion_tokens, total_tokens,
             model_used, finish_reason
    """
    messages = _build_messages(state)
    llm = _get_llm()

    try:
        response = await llm.ainvoke(messages)
        ai_text = response.content or ""

        # Extract token usage from response metadata
        usage = getattr(response, "usage_metadata", None) or {}
        prompt_tokens = usage.get("input_tokens", 0)
        completion_tokens = usage.get("output_tokens", 0)
        total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

        # Finish reason from additional_kwargs
        finish_reason = (
            response.additional_kwargs.get("finish_reason")
            or response.response_metadata.get("finish_reason", "stop")
        )

        logger.info(
            "generation_node | tokens=%d model=%s finish=%s",
            total_tokens, llm.model_name, finish_reason,
        )
        return {
            **state,
            "ai_response": ai_text,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
            "model_used": llm.model_name,
            "finish_reason": finish_reason,
            "error": None,
        }

    except Exception as exc:
        logger.error("generation_node failed: %s", exc)
        return {
            **state,
            "ai_response": "I'm sorry, I encountered an error. Please try again.",
            "error": str(exc),
            "finish_reason": "error",
        }


async def stream_generation(state: GraphState) -> AsyncIterator[str]:
    """
    Streaming variant — yields text tokens as they arrive.
    Used by the /chat/stream endpoint.
    """
    messages = _build_messages(state)
    llm = _get_llm()

    async for chunk in llm.astream(messages):
        token = chunk.content
        if token:
            yield token
