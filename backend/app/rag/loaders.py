"""
Document loaders for PDF and plain-text files.

Returns a flat list of LangChain Document objects.  Each Document carries
the raw page text in `.page_content` and source metadata in `.metadata`.
"""
import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


class DocumentLoaderService:
    """Load PDF or TXT files from disk into LangChain Documents."""

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    async def load(self, file_path: str) -> list[Document]:
        """Detect file type and delegate to the appropriate loader."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        suffix = path.suffix.lower()
        if suffix == ".pdf":
            return await self._load_pdf(str(path))
        if suffix == ".txt":
            return await self._load_txt(str(path))

        raise ValueError(f"Unsupported file type '{suffix}'. Supported: .pdf, .txt")

    # ------------------------------------------------------------------ #
    # Private helpers
    # ------------------------------------------------------------------ #

    async def _load_pdf(self, file_path: str) -> list[Document]:
        logger.info("Loading PDF: %s", file_path)
        loader = PyPDFLoader(file_path)
        docs = loader.load()
        logger.info("Loaded %d page(s) from PDF", len(docs))
        return docs

    async def _load_txt(self, file_path: str) -> list[Document]:
        logger.info("Loading TXT: %s", file_path)
        loader = TextLoader(file_path, encoding="utf-8")
        docs = loader.load()
        logger.info("Loaded %d document(s) from TXT", len(docs))
        return docs
