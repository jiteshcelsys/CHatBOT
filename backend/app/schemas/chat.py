from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    session_id: str = Field(..., description="Active session UUID")
    user_id: str = Field("anonymous")
    collection: str = Field("documents", description="ChromaDB collection to retrieve from")


class ChatResponse(BaseModel):
    session_id: str
    response: str
    model: str
    finish_reason: str
    retrieval_used: bool
    chunks_retrieved: int
    tokens: dict
    timestamp: str
    error: str | None = None


class StreamChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=8000)
    session_id: str
    user_id: str = "anonymous"
    collection: str = "documents"


class CreateSessionRequest(BaseModel):
    title: str = Field("New Chat", max_length=120)
    collection: str = Field("documents")


class SessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    collection: str
    is_active: bool
    message_count: int
    created_at: str
    updated_at: str


class MessageResponse(BaseModel):
    id: str
    session_id: str
    user_id: str
    role: str
    content: str
    metadata: dict
    tokens_used: int
    created_at: str
