"""
Splits a list of Documents into smaller overlapping chunks.

Why RecursiveCharacterTextSplitter?
  It tries to split on paragraph breaks, then sentence breaks, then word
  breaks — producing chunks that are semantically coherent rather than
  arbitrarily cut mid-sentence.
"""
import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

logger = logging.getLogger(__name__)

# Default values match what works well for OpenAI text-embedding-3-small
# (max 8191 tokens ≈ ~32 000 chars; 1000 chars ≈ ~250 tokens).
_DEFAULT_CHUNK_SIZE = 1000
_DEFAULT_CHUNK_OVERLAP = 200


class TextSplitterService:
    def __init__(
        self,
        chunk_size: int = _DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = _DEFAULT_CHUNK_OVERLAP,
    ):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            add_start_index=True,   # stores char offset in metadata for traceability
        )

    def split(self, documents: list[Document]) -> list[Document]:
        chunks = self._splitter.split_documents(documents)
        logger.info(
            "Split %d document(s) into %d chunk(s)", len(documents), len(chunks)
        )
        return chunks
