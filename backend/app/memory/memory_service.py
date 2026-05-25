import logging
import uuid
from datetime import datetime, timezone

from app.memory.supabase_client import get_supabase

logger = logging.getLogger(__name__)

TABLE = "chat_messages"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def save_message(
    session_id: str,
    user_id: str,
    role: str,
    content: str,
    metadata: dict | None = None,
    tokens_used: int = 0,
) -> dict:
    data = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "user_id": user_id,
        "role": role,
        "content": content,
        "metadata": metadata or {},
        "tokens_used": tokens_used,
        "created_at": _now(),
    }
    sb = await get_supabase()
    res = await sb.table(TABLE).insert(data).execute()
    row = res.data[0]
    logger.debug("Message saved | session=%s role=%s", session_id, role)
    return row


async def get_messages(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    sb = await get_supabase()
    res = await (
        sb.table(TABLE)
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .range(offset, offset + limit - 1)
        .execute()
    )
    return res.data or []


async def get_recent_messages(session_id: str, n: int = 10) -> list[dict]:
    sb = await get_supabase()
    res = await (
        sb.table(TABLE)
        .select("role, content, created_at")
        .eq("session_id", session_id)
        .order("created_at", desc=True)
        .limit(n)
        .execute()
    )
    messages = res.data or []
    return list(reversed(messages))


async def delete_session_messages(session_id: str) -> int:
    sb = await get_supabase()
    res = await sb.table(TABLE).delete().eq("session_id", session_id).execute()
    count = len(res.data or [])
    logger.info("Deleted %d messages for session %s", count, session_id)
    return count
