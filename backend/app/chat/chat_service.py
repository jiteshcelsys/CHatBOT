"""
ChatService — orchestrates a single chat turn through the LangGraph workflow.

Validates that the session exists and belongs to the correct user, then
delegates to GraphService.invoke() for the full reasoning pipeline.
"""
import logging

from app.graph.graph_service import GraphService
from app.graph.state import GraphState
from app.memory.session_memory import get_session
from app.utils.exceptions import BadRequestException, NotFoundException

logger = logging.getLogger(__name__)

_graph_service = GraphService()


class ChatService:
    async def chat(
        self,
        user_message: str,
        session_id: str,
        user_id: str,
        collection: str = "documents",
    ) -> GraphState:
        if not user_message.strip():
            raise BadRequestException("Message cannot be empty.")

        # Validate session
        session = await get_session(session_id)
        if not session:
            raise NotFoundException(f"Session '{session_id}' not found.")
        if not session.get("is_active"):
            raise BadRequestException("Session is no longer active.")

        result = await _graph_service.invoke(
            user_message=user_message,
            session_id=session_id,
            user_id=user_id,
            collection=session.get("collection", collection),
        )
        return result
