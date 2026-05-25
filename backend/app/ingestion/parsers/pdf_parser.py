"""PDF parser — extracts per-page text via PyPDF."""
import logging
from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document

logger = logging.getLogger(__name__)


async def parse_pdf(file_path: str) -> list[Document]:
    path = Path(file_path)
    loader = PyPDFLoader(str(path))
    docs = loader.load()

    # Attach page number to every document
    for i, doc in enumerate(docs):
        doc.metadata.setdefault("page", i + 1)
        doc.metadata.setdefault("total_pages", len(docs))

    logger.info("PDF parsed | file=%s pages=%d", path.name, len(docs))
    return docs
