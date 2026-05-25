import logging
import uuid
from datetime import datetime, timezone

from app.memory.supabase_client import get_supabase

logger = logging.getLogger(__name__)

TABLE = "user_memory"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def save_memory(
    user_id: str,
    content: str,
    memory_type: str = "fact",
    importance: int = 1,
    source: str = "inferred",
) -> dict:
    data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "memory_type": memory_type,
        "content": content,
        "importance": max(1, min(5, importance)),
        "source": source,
        "is_active": True,
        "created_at": _now(),
        "updated_at": _now(),
    }
    sb = await get_supabase()
    res = await sb.table(TABLE).insert(data).execute()
    row = res.data[0]
    logger.info("Memory saved | user=%s type=%s", user_id, memory_type)
    return row


async def get_user_memories(
    user_id: str,
    memory_type: str | None = None,
    min_importance: int = 1,
    limit: int = 20,
) -> list[dict]:
    sb = await get_supabase()
    q = (
        sb.table(TABLE)
        .select("*")
        .eq("user_id", user_id)
        .eq("is_active", True)
        .gte("importance", min_importance)
        .order("importance", desc=True)
        .limit(limit)
    )
    if memory_type:
        q = q.eq("memory_type", memory_type)
    res = await q.execute()
    return res.data or []


async def build_persona_prompt(user_id: str) -> str:
    memories = await get_user_memories(user_id, min_importance=2, limit=15)
    if not memories:
        return ""
    lines = ["User context:"]
    for m in memories:
        lines.append(f"- [{m['memory_type']}] {m['content']}")
    return "\n".join(lines)


async def deactivate_memory(memory_id: str) -> bool:
    sb = await get_supabase()
    res = await (
        sb.table(TABLE)
        .update({"is_active": False, "updated_at": _now()})
        .eq("id", memory_id)
        .execute()
    )
    return bool(res.data)
