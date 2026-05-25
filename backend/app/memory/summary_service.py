import logging
import uuid
from datetime import datetime, timezone

from app.memory.supabase_client import get_supabase

logger = logging.getLogger(__name__)

TABLE = "conversation_summaries"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def save_summary(
    session_id: str,
    user_id: str,
    summary: str,
    message_range: dict | None = None,
    token_count: int = 0,
) -> dict:
    data = {
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "user_id": user_id,
        "summary": summary,
        "message_range": message_range or {},
        "token_count": token_count,
        "created_at": _now(),
    }
    sb = await get_supabase()
    res = await sb.table(TABLE).insert(data).execute()
    row = res.data[0]
    logger.info("Summary saved | session=%s tokens=%d", session_id, token_count)
    return row


async def get_latest_summary(session_id: str) -> dict | None:
    sb = await get_supabase()
    res = await sb.table(TABLE).select("*").eq("session_id", session_id).order("created_at", desc=True).limit(1).execute()
    return res.data[0] if res.data else None


async def get_all_summaries(session_id: str) -> list[dict]:
    sb = await get_supabase()
    res = await (
        sb.table(TABLE)
        .select("*")
        .eq("session_id", session_id)
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []
