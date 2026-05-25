"""
LangGraph typed state definition.

GraphState is the single shared data bag that flows through every node.
All fields are Optional so any node can be skipped without crashing.

Lifecycle:
  input_message → memory_node → retrieval_node → generation_node
               → persistence_node → END
"""
from __future__ import annotations

from typing import Any
from typing_extensions import TypedDict


class GraphState(TypedDict, total=False):
    # ── Input ──────────────────────────────────────────────────────────────
    session_id: str
    user_id: str
    user_message: str
    collection: str          # ChromaDB collection to retrieve from
    stream: bool             # caller wants a streaming response

    # ── Memory layer (memory_node output) ──────────────────────────────────
    recent_messages: list[dict]   # [{"role": str, "content": str}]
    latest_summary: str
    persona_prompt: str

    # ── Retrieval layer (retrieval_node output) ────────────────────────────
    retrieved_chunks: list[dict]  # [{"content": str, "metadata": dict}]
    retrieval_skipped: bool       # True if collection was empty

    # ── Generation layer (generation_node output) ─────────────────────────
    ai_response: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    model_used: str
    finish_reason: str

    # ── Routing ────────────────────────────────────────────────────────────
    needs_retrieval: bool    # routing_node decision
    needs_summary: bool      # trigger summarisation if conversation is long

    # ── Error handling ─────────────────────────────────────────────────────
    error: str | None
    retry_count: int

    # ── Misc ────────────────────────────────────────────────────────────────
    metadata: dict[str, Any]
