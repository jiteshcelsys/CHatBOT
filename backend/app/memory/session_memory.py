import logging
import uuid
from datetime import datetime, timezone

from app.memory.supabase_client import get_supabase

logger = logging.getLogger(__name__)

TABLE = "chat_sessions"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def create_session(
    user_id: str,
    title: str = "New Chat",
    collection: str = "documents",
) -> dict:
    data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "title": title,
        "collection": collection,
        "is_active": True,
        "message_count": 0,
        "created_at": _now(),
        "updated_at": _now(),
    }
    try:
        sb = await get_supabase()
        res = await sb.table(TABLE).insert(data).execute()
        row = res.data[0]
        logger.info("Session created | id=%s user=%s", row["id"], user_id)
        return row
    except Exception as e:
        logger.error("create_session failed: %s", e, exc_info=True)
        raise


async def get_session(session_id: str) -> dict | None:
    sb = await get_supabase()
    res = await sb.table(TABLE).select("*").eq("id", session_id).limit(1).execute()
    return res.data[0] if res.data else None


async def list_sessions(user_id: str, active_only: bool = True) -> list[dict]:
    sb = await get_supabase()
    q = sb.table(TABLE).select("*").eq("user_id", user_id)
    if active_only:
        q = q.eq("is_active", True)
    res = await q.order("updated_at", desc=True).execute()
    return res.data or []


async def update_session_title(session_id: str, title: str) -> dict | None:
    sb = await get_supabase()
    res = await sb.table(TABLE).update({"title": title, "updated_at": _now()}).eq("id", session_id).execute()
    return res.data[0] if res.data else None


async def increment_message_count(session_id: str) -> None:
    sb = await get_supabase()
    res = await sb.table(TABLE).select("message_count").eq("id", session_id).limit(1).execute()
    if res.data:
        new_count = (res.data[0].get("message_count") or 0) + 1
        await sb.table(TABLE).update(
            {"message_count": new_count, "updated_at": _now()}
        ).eq("id", session_id).execute()


async def deactivate_session(session_id: str) -> bool:
    sb = await get_supabase()
    res = await sb.table(TABLE).update({"is_active": False, "updated_at": _now()}).eq("id", session_id).execute()
    return bool(res.data)
