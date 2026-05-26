"""
Chat API — Phase 7

Prefix: /api/v1/chat

Sessions
  POST   /session/create           — create a new chat session
  GET    /sessions                  — list sessions for a user
  DELETE /session/{session_id}      — deactivate a session

Messaging
  POST   /                          — send message, get full response
  POST   /stream                    — send message, get SSE stream
  GET    /history/{session_id}      — paginated message history
  GET    /messages/{session_id}     — alias for history
  GET    /sessions                  — list user sessions
"""
import logging

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.chat.chat_service import ChatService
from app.chat.response_formatter import format_chat_response
from app.chat.session_service import SessionService
from app.chat.streaming_service import stream_chat
from app.core.auth import AuthUser, get_current_user
from app.memory.memory_service import get_messages
from app.schemas.base import ApiResponse
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CreateSessionRequest,
    MessageResponse,
    SessionResponse,
    StreamChatRequest,
)
from app.utils.responses import success

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

_chat_svc = ChatService()
_session_svc = SessionService()


# --------------------------------------------------------------------------- #
# Sessions
# --------------------------------------------------------------------------- #

@router.post(
    "/session/create",
    summary="Create a new chat session",
    response_model=ApiResponse[SessionResponse],
    status_code=201,
)
async def create_session(body: CreateSessionRequest, user: AuthUser = Depends(get_current_user)):
    session = await _session_svc.create(
        user_id=user.uid,
        title=body.title,
        collection=body.collection,
    )
    return success(SessionResponse(**session).model_dump(), status_code=201)


@router.get(
    "/sessions",
    summary="List all sessions for a user",
    response_model=ApiResponse[list[SessionResponse]],
)
async def list_sessions(
    active_only: bool = Query(True),
    user: AuthUser = Depends(get_current_user),
):
    sessions = await _session_svc.list(user_id=user.uid, active_only=active_only)
    return success([SessionResponse(**s).model_dump() for s in sessions])


@router.patch(
    "/session/{session_id}",
    summary="Rename a chat session",
    response_model=ApiResponse[SessionResponse],
)
async def rename_session(
    session_id: str,
    body: dict,
    user: AuthUser = Depends(get_current_user),
):
    session = await _session_svc.rename(session_id, body.get("title", ""))
    return success(SessionResponse(**session).model_dump())


@router.delete(
    "/session/{session_id}",
    summary="Deactivate a chat session",
    response_model=ApiResponse,
)
async def delete_session(session_id: str, user: AuthUser = Depends(get_current_user)):
    await _session_svc.delete(session_id)
    return success({"deleted": session_id})


# --------------------------------------------------------------------------- #
# Messaging — standard (non-streaming)
# --------------------------------------------------------------------------- #

@router.post(
    "/",
    summary="Send a message and receive a full response",
    response_model=ApiResponse[ChatResponse],
)
async def chat(body: ChatRequest, user: AuthUser = Depends(get_current_user)):
    state = await _chat_svc.chat(
        user_message=body.message,
        session_id=body.session_id,
        user_id=user.uid,
        collection=body.collection,
    )
    return success(
        ChatResponse(**format_chat_response(state, body.session_id)).model_dump()
    )


# --------------------------------------------------------------------------- #
# Messaging — streaming (SSE)
# --------------------------------------------------------------------------- #

@router.post(
    "/stream",
    summary="Send a message and stream the response as SSE",
    response_class=StreamingResponse,
)
async def chat_stream(body: StreamChatRequest, user: AuthUser = Depends(get_current_user)):
    """
    Returns a Server-Sent Events stream.

    Each event:
      data: {"type": "token", "content": "..."}
      data: {"type": "done",  "metadata": {...}}
      data: {"type": "error", "message": "..."}
      data: [DONE]
    """
    from app.memory.session_memory import get_session
    from app.utils.exceptions import BadRequestException, NotFoundException
    import json

    async def safe_generator():
        try:
            async for chunk in stream_chat(
                user_message=body.message,
                session_id=body.session_id,
                user_id=user.uid,
                collection=body.collection,
            ):
                yield chunk
        except (NotFoundException, BadRequestException) as exc:
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as exc:
            logger.exception("Unhandled error in stream_chat")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Internal server error'})}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        safe_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# --------------------------------------------------------------------------- #
# History
# --------------------------------------------------------------------------- #

@router.get(
    "/history/{session_id}",
    summary="Get paginated message history for a session",
    response_model=ApiResponse[list[MessageResponse]],
)
async def get_history(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    messages = await get_messages(session_id, limit=limit, offset=offset)
    return success([MessageResponse(**m).model_dump() for m in messages])


@router.get(
    "/messages/{session_id}",
    summary="Alias for /history/{session_id}",
    response_model=ApiResponse[list[MessageResponse]],
)
async def get_messages_alias(
    session_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    return await get_history(session_id, limit=limit, offset=offset)
