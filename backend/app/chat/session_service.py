"""
Session management facade — wraps memory/session_memory.py with
business-logic guards (max sessions per user, title auto-generation).
"""
import logging

from app.core.config import get_settings
from app.memory.session_memory import (
    create_session,
    deactivate_session,
    get_session,
    list_sessions,
    update_session_title,
)
from app.utils.exceptions import BadRequestException, NotFoundException

logger = logging.getLogger(__name__)


class SessionService:
    async def create(
        self,
        user_id: str,
        title: str = "New Chat",
        collection: str = "documents",
    ) -> dict:
        settings = get_settings()
        # Enforce max active sessions per user
        active = await list_sessions(user_id, active_only=True)
        if len(active) >= settings.chat_max_sessions_per_user:
            raise BadRequestException(
                f"Maximum of {settings.chat_max_sessions_per_user} active sessions per user."
            )
        session = await create_session(user_id=user_id, title=title, collection=collection)
        logger.info("Session created | id=%s user=%s", session["id"], user_id)
        return session

    async def get(self, session_id: str) -> dict:
        session = await get_session(session_id)
        if not session:
            raise NotFoundException(f"Session '{session_id}' not found.")
        return session

    async def list(self, user_id: str, active_only: bool = True) -> list[dict]:
        return await list_sessions(user_id, active_only=active_only)

    async def delete(self, session_id: str) -> bool:
        result = await deactivate_session(session_id)
        if not result:
            raise NotFoundException(f"Session '{session_id}' not found.")
        return True

    async def rename(self, session_id: str, title: str) -> dict:
        row = await update_session_title(session_id, title)
        if not row:
            raise NotFoundException(f"Session '{session_id}' not found.")
        return row
