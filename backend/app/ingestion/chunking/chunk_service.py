"""
Chunking service — splits cleaned Documents into embedding-ready chunks.

Uses RecursiveCharacterTextSplitter with configurable size and overlap.
After splitting, each chunk receives:
  - chunk_index  : 0-based position within the source document
  - chunk_total  : total number of chunks from this document
  - doc_hash     : content fingerprint for chunk-level deduplication
  - start_index  : character offset in the original text (from splitter)
"""
import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.preprocessors.duplicate_detector import chunk_hash

logger = logging.getLogger(__name__)


class ChunkService:
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] | None = None,
    ):
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            add_start_index=True,
            separators=separators or ["\n\n", "\n", ". ", " ", ""],
        )
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    def chunk(self, documents: list[Document]) -> list[Document]:
        """Split documents into chunks and stamp each with positional metadata."""
        all_chunks: list[Document] = []

        for doc in documents:
            splits = self._splitter.split_documents([doc])
            total = len(splits)
            for idx, chunk in enumerate(splits):
                chunk.metadata["chunk_index"] = idx
                chunk.metadata["chunk_total"] = total
                chunk.metadata["doc_hash"] = chunk_hash(chunk.page_content)
                chunk.metadata.setdefault("chunk_size_cfg", self._chunk_size)
                chunk.metadata.setdefault("chunk_overlap_cfg", self._chunk_overlap)
            all_chunks.extend(splits)

        logger.info(
            "Chunking complete | input_docs=%d output_chunks=%d",
            len(documents), len(all_chunks),
        )
        return all_chunks
