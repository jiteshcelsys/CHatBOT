"""
Routing node — decides whether retrieval is needed and whether
summarisation should be triggered.

Rules:
  needs_retrieval = True unless the message is a pure social exchange
                    ("hi", "thanks", "bye") that clearly doesn't need docs.
  needs_summary   = True when the session has ≥ summary_threshold messages.
"""
import logging
import re

from app.core.config import get_settings
from app.graph.state import GraphState

logger = logging.getLogger(__name__)

# Patterns that indicate a conversational filler — no document lookup needed
_SOCIAL_PATTERNS = re.compile(
    r"^(hi|hello|hey|thanks|thank you|bye|goodbye|ok|okay|sure|"
    r"yes|no|yep|nope|cool|great|awesome|got it|understood)[\s!.?]*$",
    re.IGNORECASE,
)


def routing_node(state: GraphState) -> GraphState:
    """
    Input  : user_message, recent_messages
    Output : needs_retrieval, needs_summary
    """
    settings = get_settings()
    message = (state.get("user_message") or "").strip()
    recent = state.get("recent_messages") or []

    # Retrieval decision
    needs_retrieval = not bool(_SOCIAL_PATTERNS.match(message))

    # Summary trigger
    needs_summary = len(recent) >= settings.chat_summary_threshold

    logger.debug(
        "routing_node | needs_retrieval=%s needs_summary=%s msgs=%d",
        needs_retrieval, needs_summary, len(recent),
    )
    return {**state, "needs_retrieval": needs_retrieval, "needs_summary": needs_summary}
