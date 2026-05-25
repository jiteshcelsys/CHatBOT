from typing import Literal

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# Collection schemas
# --------------------------------------------------------------------------- #

class CreateCollectionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    description: str = Field("", max_length=256)


class CollectionInfoResponse(BaseModel):
    name: str
    document_count: int
    metadata: dict
    created_at: str


class CollectionStatsResponse(BaseModel):
    name: str
    document_count: int
    metadata: dict
    sample_ids: list[str]
    sources: list[str]
    created_at: str


# --------------------------------------------------------------------------- #
# Index / Delete schemas
# --------------------------------------------------------------------------- #

class IndexResponse(BaseModel):
    file_name: str
    collection: str
    pages_loaded: int
    total_chunks: int
    new_chunks: int
    duplicate_chunks: int
    document_ids: list[str]
    cache_hits: int


class DeleteBySourceResponse(BaseModel):
    collection: str
    source: str
    deleted_count: int


class DeleteByIdsRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1)


class DeleteByIdsResponse(BaseModel):
    collection: str
    deleted_count: int


# --------------------------------------------------------------------------- #
# Search schemas
# --------------------------------------------------------------------------- #

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    k: int = Field(4, ge=1, le=20)
    mode: Literal["similarity", "similarity_scored", "mmr"] = "similarity"
    score_threshold: float | None = Field(None, ge=0.0, le=1.0)
    fetch_k: int = Field(20, ge=1, le=100)
    lambda_mult: float = Field(0.5, ge=0.0, le=1.0)
    # Metadata filters
    source: str | None = None
    file_type: str | None = None
    tags: dict | None = None
    collection: str = "documents"


class SearchChunk(BaseModel):
    content: str
    metadata: dict
    score: float | None = None


class SearchResponse(BaseModel):
    query: str
    collection: str
    mode: str
    total: int
    chunks: list[SearchChunk]


# --------------------------------------------------------------------------- #
# Health / Cache schemas
# --------------------------------------------------------------------------- #

class VectorDBHealthResponse(BaseModel):
    status: str
    persist_dir: str
    total_collections: int
    collections: list[str]


class CacheStatsResponse(BaseModel):
    size: int
    max_size: int
    ttl_seconds: int
    hits: int
    misses: int
    hit_rate: float
