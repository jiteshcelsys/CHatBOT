"""
Streaming chat service — wraps GraphService.stream() and formats output
as Server-Sent Events (SSE) for the /chat/stream endpoint.

SSE format:
  data: {"type": "token", "content": "Hello"}\n\n
  data: {"type": "token", "content": " world"}\n\n
  data: {"type": "done", "metadata": {...}}\n\n
  data: [DONE]\n\n
"""
import json
import logging
from typing import AsyncIterator

from app.graph.graph_service import GraphService
from app.memory.session_memory import get_session
from app.utils.exceptions import BadRequestException, NotFoundException

logger = logging.getLogger(__name__)

_graph_service = GraphService()


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


async def stream_chat(
    user_message: str,
    session_id: str,
    user_id: str,
    collection: str = "documents",
) -> AsyncIterator[str]:
    """
    Validate session, then stream LLM tokens as SSE events.
    Yields strings — FastAPI's StreamingResponse consumes them directly.
    """
    if not user_message.strip():
        raise BadRequestException("Message cannot be empty.")

    session = await get_session(session_id)
    if not session:
        raise NotFoundException(f"Session '{session_id}' not found.")
    if not session.get("is_active"):
        raise BadRequestException("Session is no longer active.")

    full_response: list[str] = []

    async for token in _graph_service.stream(
        user_message=user_message,
        session_id=session_id,
        user_id=user_id,
        collection=session.get("collection", collection),
    ):
        full_response.append(token)
        yield _sse({"type": "token", "content": token})

    yield _sse({
        "type": "done",
        "metadata": {
            "session_id": session_id,
            "total_chars": sum(len(t) for t in full_response),
        },
    })
    yield "data: [DONE]\n\n"
