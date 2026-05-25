from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    file_name: str
    collection: str
    pages_loaded: int
    chunks_stored: int
    document_ids: list[str]


class RetrievalChunk(BaseModel):
    content: str
    metadata: dict
    score: float | None = None


class RetrievalResponse(BaseModel):
    query: str
    collection: str
    total_results: int
    chunks: list[RetrievalChunk]


class CollectionStatsResponse(BaseModel):
    collection: str
    total_chunks: int


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000, description="Semantic search query")
    k: int = Field(4, ge=1, le=20, description="Number of chunks to return")
    with_scores: bool = Field(False, description="Include relevance scores")
    collection: str = Field("documents", description="ChromaDB collection name")
