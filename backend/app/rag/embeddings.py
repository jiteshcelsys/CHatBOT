"""
Local HuggingFace embeddings — no API key required.

Model: all-MiniLM-L6-v2 (384-dim, ~80 MB, fast on CPU)
Why: Groq does not provide an embeddings endpoint; this model is
     free, runs locally, and produces high-quality semantic vectors
     for RAG retrieval.

The singleton pattern avoids reloading the ~80 MB model on every request.
"""
import logging

from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_embeddings_instance: HuggingFaceEmbeddings | None = None


def get_embeddings() -> HuggingFaceEmbeddings:
    """Return a shared HuggingFaceEmbeddings instance (lazy-init singleton)."""
    global _embeddings_instance
    if _embeddings_instance is None:
        settings = get_settings()
        logger.info("Loading embedding model: %s", settings.embedding_model)
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=settings.embedding_model,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},  # cosine similarity works correctly
        )
        logger.info("Embedding model loaded: %s", settings.embedding_model)
    return _embeddings_instance
