"""
File handler — manages temp-file lifecycle and dispatches to the correct parser.

Responsibilities:
  1. Write uploaded bytes to a uniquely-named temp file (async, non-blocking).
  2. Dispatch to the right parser based on extension.
  3. Return parsed LangChain Documents.
  4. Guarantee temp-file deletion via a context manager regardless of errors.

Using a context manager (FileHandler.process()) means callers never have to
remember to clean up — even if parsing raises an exception, the temp file is
removed in the __aexit__ block.
"""
import logging
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

import aiofiles
from langchain_core.documents import Document

from app.ingestion.parsers.docx_parser import parse_docx
from app.ingestion.parsers.markdown_parser import parse_markdown
from app.ingestion.parsers.pdf_parser import parse_pdf
from app.ingestion.parsers.txt_parser import parse_txt

logger = logging.getLogger(__name__)

_UPLOAD_DIR = Path("uploads")
_UPLOAD_DIR.mkdir(exist_ok=True)

_PARSER_MAP = {
    ".pdf":  parse_pdf,
    ".txt":  parse_txt,
    ".docx": parse_docx,
    ".md":   parse_markdown,
}


@asynccontextmanager
async def _temp_file(filename: str, content: bytes):
    """Write content to a unique temp path; delete on exit."""
    ext = Path(filename).suffix.lower()
    tmp = _UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
    try:
        async with aiofiles.open(str(tmp), "wb") as f:
            await f.write(content)
        yield str(tmp)
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except Exception as exc:
            logger.warning("Temp file cleanup failed: %s | %s", tmp, exc)


async def parse_file(filename: str, content: bytes) -> list[Document]:
    """
    Save content to a temp file, parse it, return Documents.
    The temp file is removed automatically after parsing.
    """
    ext = Path(filename).suffix.lower()
    parser = _PARSER_MAP.get(ext)
    if parser is None:
        raise ValueError(f"No parser registered for extension '{ext}'.")

    async with _temp_file(filename, content) as tmp_path:
        docs = await parser(tmp_path)

    logger.info("Parsed %d doc(s) from '%s'", len(docs), filename)
    return docs
