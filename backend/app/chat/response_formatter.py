"""
Formats raw GraphState into clean API response dicts.
"""
from datetime import datetime, timezone

from app.graph.state import GraphState


def format_chat_response(state: GraphState, session_id: str) -> dict:
    return {
        "session_id": session_id,
        "response": state.get("ai_response", ""),
        "model": state.get("model_used", ""),
        "finish_reason": state.get("finish_reason", ""),
        "retrieval_used": not state.get("retrieval_skipped", True),
        "chunks_retrieved": len(state.get("retrieved_chunks") or []),
        "tokens": {
            "prompt": state.get("prompt_tokens", 0),
            "completion": state.get("completion_tokens", 0),
            "total": state.get("total_tokens", 0),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "error": state.get("error"),
    }
