"""
Memory retrieval — assembles all context needed by the LangGraph memory node.

Returns a MemoryContext dataclass containing:
  - recent_messages  : last N turns from chat_messages
  - latest_summary   : most recent conversation summary (if any)
  - persona_prompt   : compressed user facts for system prompt injection
"""
import logging
from dataclasses import dataclass, field

from app.memory.memory_service import get_recent_messages
from app.memory.persona_service import build_persona_prompt
from app.memory.summary_service import get_latest_summary

logger = logging.getLogger(__name__)


@dataclass
class MemoryContext:
    session_id: str
    user_id: str
    recent_messages: list[dict] = field(default_factory=list)
    latest_summary: str = ""
    persona_prompt: str = ""


async def load_memory_context(
    session_id: str,
    user_id: str,
    recent_n: int = 10,
) -> MemoryContext:
    """
    Fetch all memory layers in parallel-ish fashion.
    Used by the memory_node in the LangGraph workflow.
    """
    ctx = MemoryContext(session_id=session_id, user_id=user_id)

    # Recent conversation turns
    ctx.recent_messages = await get_recent_messages(session_id, n=recent_n)

    # Latest summary (compressed older context)
    summary_row = await get_latest_summary(session_id)
    if summary_row:
        ctx.latest_summary = summary_row.get("summary", "")

    # User persona / long-term memory
    ctx.persona_prompt = await build_persona_prompt(user_id)

    logger.debug(
        "MemoryContext loaded | session=%s messages=%d has_summary=%s has_persona=%s",
        session_id, len(ctx.recent_messages),
        bool(ctx.latest_summary), bool(ctx.persona_prompt),
    )
    return ctx
